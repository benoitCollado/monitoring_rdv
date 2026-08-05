"""One daily cron job per company, kept in sync with the companies table.

APScheduler runs in the API process — no extra worker to deploy. The jobs are
rebuilt at startup and whenever a company is created, updated or deleted, so
changing "vérifier à 6h05" in the UI takes effect immediately.
"""

import logging
import uuid
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.company import Company
from app.services.monitor_service import run_checks_for_company_id

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def job_id(company_id: uuid.UUID) -> str:
    return f"company-check:{company_id}"


def schedule_company(company: Company) -> None:
    jid = job_id(company.id)
    if not company.is_active:
        remove_company_job(company.id)
        return

    scheduler.add_job(
        run_checks_for_company_id,
        trigger=CronTrigger(
            hour=company.check_hour,
            minute=company.check_minute,
            timezone=company.timezone,
        ),
        id=jid,
        args=[company.id],
        kwargs={"trigger": "cron"},
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    logger.info(
        "Cron programmé pour %s à %02d:%02d (%s)",
        company.name,
        company.check_hour,
        company.check_minute,
        company.timezone,
    )


def remove_company_job(company_id: uuid.UUID) -> None:
    job = scheduler.get_job(job_id(company_id))
    if job is not None:
        job.remove()


def next_run_at(company_id: uuid.UUID) -> datetime | None:
    job = scheduler.get_job(job_id(company_id))
    return getattr(job, "next_run_time", None) if job else None


async def sync_all_jobs() -> None:
    async with SessionLocal() as session:
        companies = (await session.scalars(select(Company))).all()
    for company in companies:
        schedule_company(company)


async def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
    await sync_all_jobs()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
