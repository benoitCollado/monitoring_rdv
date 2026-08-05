"""Runs a batch of checks and records the outcome.

A *run* is one pass over the active links of one company — either the daily
cron, or a manual "revérifier maintenant" from the dashboard.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.company import Company
from app.models.monitoring import (
    STATUS_BROKEN,
    STATUS_OK,
    CheckRun,
    LinkCheck,
    MonitoredLink,
)
from app.services.link_checker import CheckOutcome, check_url

logger = logging.getLogger(__name__)


def apply_outcome(
    link: MonitoredLink, outcome: CheckOutcome, now: datetime | None = None
) -> None:
    now = now or datetime.now(timezone.utc)
    link.last_checked_at = now
    link.last_status_code = outcome.status_code
    link.last_response_time_ms = outcome.response_time_ms
    link.last_reason = outcome.reason
    link.last_error = outcome.error

    if outcome.ok:
        link.status = STATUS_OK
        link.consecutive_failures = 0
        link.broken_since = None
    else:
        if link.status != STATUS_BROKEN:
            link.broken_since = now
        link.status = STATUS_BROKEN
        link.consecutive_failures += 1


async def _check_links(
    company: Company, links: list[MonitoredLink]
) -> list[tuple[MonitoredLink, CheckOutcome]]:
    settings = get_settings()
    semaphore = asyncio.Semaphore(max(1, settings.check_concurrency))
    limits = httpx.Limits(max_connections=max(1, settings.check_concurrency))

    async with httpx.AsyncClient(
        timeout=settings.check_timeout_seconds,
        follow_redirects=True,
        limits=limits,
        headers={"User-Agent": settings.user_agent},
    ) as client:

        async def run_one(link: MonitoredLink) -> tuple[MonitoredLink, CheckOutcome]:
            async with semaphore:
                outcome = await check_url(
                    client,
                    link.url,
                    list(company.error_patterns or []),
                    body_read_bytes=settings.check_body_read_bytes,
                )
                return link, outcome

        return list(await asyncio.gather(*(run_one(link) for link in links)))


async def run_checks(
    session: AsyncSession,
    company: Company,
    *,
    trigger: str = "cron",
    link_ids: list[uuid.UUID] | None = None,
) -> CheckRun:
    query = select(MonitoredLink).where(
        MonitoredLink.company_id == company.id, MonitoredLink.is_active.is_(True)
    )
    if link_ids:
        query = query.where(MonitoredLink.id.in_(link_ids))
    links = list((await session.scalars(query)).all())

    run = CheckRun(company_id=company.id, trigger=trigger, status="running")
    session.add(run)
    await session.commit()
    await session.refresh(run)

    try:
        results = await _check_links(company, links)
    except Exception as exc:  # noqa: BLE001 - the run must be closed either way
        logger.exception("Échec du run de vérification pour %s", company.name)
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"
        run.finished_at = datetime.now(timezone.utc)
        await session.commit()
        return run

    now = datetime.now(timezone.utc)
    ok_count = 0
    for link, outcome in results:
        apply_outcome(link, outcome, now)
        if outcome.ok:
            ok_count += 1
        session.add(
            LinkCheck(
                link_id=link.id,
                run_id=run.id,
                checked_at=now,
                ok=outcome.ok,
                status_code=outcome.status_code,
                response_time_ms=outcome.response_time_ms,
                final_url=outcome.final_url,
                reason=outcome.reason,
                error=outcome.error,
            )
        )

    run.checked_count = len(results)
    run.ok_count = ok_count
    run.broken_count = len(results) - ok_count
    run.status = "done"
    run.finished_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(run)

    logger.info(
        "Run %s (%s) : %s liens, %s OK, %s cassés",
        run.id,
        company.name,
        run.checked_count,
        run.ok_count,
        run.broken_count,
    )
    return run


async def run_checks_for_company_id(
    company_id: uuid.UUID, *, trigger: str = "cron"
) -> None:
    """Entry point used by the scheduler and by background tasks.

    Opens its own session: the request that triggered it may already be gone.
    """
    async with SessionLocal() as session:
        company = await session.get(Company, company_id)
        if company is None:
            logger.warning("Entreprise %s introuvable, run ignoré", company_id)
            return
        if not company.is_active:
            logger.info("Entreprise %s inactive, run ignoré", company.name)
            return
        await run_checks(session, company, trigger=trigger)
