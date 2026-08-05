"""Le moniteur : génération des liens, état courant, historique des runs."""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.deps import get_company
from app.core.database import get_db
from app.core.security import require_api_key
from app.models.catalog import AppointmentType, Shop
from app.models.company import Company
from app.models.monitoring import (
    STATUS_BROKEN,
    STATUS_OK,
    STATUS_UNKNOWN,
    CheckRun,
    LinkCheck,
    MonitoredLink,
)
from app.schemas.monitoring import (
    CheckRunRead,
    CompanySummary,
    GenerateResult,
    LinkCheckRead,
    LinkPage,
    LinkRead,
)
from app.services import scheduler as scheduler_service
from app.services.link_generator import expected_combinations, sync_links
from app.services.monitor_service import run_checks, run_checks_for_company_id

router = APIRouter(
    prefix="/api/companies/{company_id}",
    tags=["monitoring"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/links/generate", response_model=GenerateResult)
async def generate_links(
    company: Company = Depends(get_company), db: AsyncSession = Depends(get_db)
) -> GenerateResult:
    return await sync_links(db, company)


@router.get("/links", response_model=LinkPage)
async def list_links(
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    kind: str | None = None,
    shop_id: uuid.UUID | None = None,
    appointment_type_id: uuid.UUID | None = None,
    employee_id: uuid.UUID | None = None,
    q: str | None = None,
    include_archived: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> LinkPage:
    filters = [MonitoredLink.company_id == company.id]
    if not include_archived:
        filters.append(MonitoredLink.is_active.is_(True))
    if status_filter:
        if status_filter not in (STATUS_OK, STATUS_BROKEN, STATUS_UNKNOWN):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Statut inconnu"
            )
        filters.append(MonitoredLink.status == status_filter)
    if kind:
        filters.append(MonitoredLink.kind == kind)
    if shop_id:
        filters.append(MonitoredLink.shop_id == shop_id)
    if appointment_type_id:
        filters.append(MonitoredLink.appointment_type_id == appointment_type_id)
    if employee_id:
        filters.append(MonitoredLink.employee_id == employee_id)
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(MonitoredLink.slug.ilike(pattern), MonitoredLink.url.ilike(pattern))
        )

    total = await db.scalar(
        select(func.count()).select_from(MonitoredLink).where(*filters)
    )
    rows = await db.scalars(
        select(MonitoredLink)
        .where(*filters)
        # Broken first: the dashboard is there to show what needs fixing.
        .order_by(
            (MonitoredLink.status == STATUS_BROKEN).desc(), MonitoredLink.slug
        )
        .limit(limit)
        .offset(offset)
    )
    items = [LinkRead.from_model(link) for link in rows.unique().all()]
    return LinkPage(items=items, total=total or 0, limit=limit, offset=offset)


@router.get("/summary", response_model=CompanySummary)
async def company_summary(
    company: Company = Depends(get_company), db: AsyncSession = Depends(get_db)
) -> CompanySummary:
    counts = dict(
        (
            await db.execute(
                select(MonitoredLink.status, func.count())
                .where(
                    MonitoredLink.company_id == company.id,
                    MonitoredLink.is_active.is_(True),
                )
                .group_by(MonitoredLink.status)
            )
        ).all()
    )
    archived = await db.scalar(
        select(func.count())
        .select_from(MonitoredLink)
        .where(
            MonitoredLink.company_id == company.id,
            MonitoredLink.is_active.is_(False),
        )
    )
    last_run = await db.scalar(
        select(CheckRun)
        .where(CheckRun.company_id == company.id)
        .order_by(CheckRun.started_at.desc())
        .limit(1)
    )

    ok = counts.get(STATUS_OK, 0)
    broken = counts.get(STATUS_BROKEN, 0)
    unknown = counts.get(STATUS_UNKNOWN, 0)
    return CompanySummary(
        company_id=company.id,
        total=ok + broken + unknown,
        ok=ok,
        broken=broken,
        unknown=unknown,
        archived=archived or 0,
        last_run=CheckRunRead.model_validate(last_run) if last_run else None,
        next_run_at=scheduler_service.next_run_at(company.id),
    )


@router.post("/checks/run", status_code=status.HTTP_202_ACCEPTED)
async def trigger_run(
    background_tasks: BackgroundTasks, company: Company = Depends(get_company)
) -> dict[str, str]:
    """Fire the same pass as the cron, right now, in the background."""
    background_tasks.add_task(
        run_checks_for_company_id, company.id, trigger="manual"
    )
    return {"status": "scheduled"}


@router.get("/runs", response_model=list[CheckRunRead])
async def list_runs(
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=200),
) -> list[CheckRun]:
    rows = await db.scalars(
        select(CheckRun)
        .where(CheckRun.company_id == company.id)
        .order_by(CheckRun.started_at.desc())
        .limit(limit)
    )
    return list(rows.all())


async def _get_link(
    db: AsyncSession, company: Company, link_id: uuid.UUID
) -> MonitoredLink:
    link = await db.get(MonitoredLink, link_id)
    if link is None or link.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lien introuvable"
        )
    return link


@router.get("/links/{link_id}", response_model=LinkRead)
async def get_link(
    link_id: uuid.UUID,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> LinkRead:
    return LinkRead.from_model(await _get_link(db, company, link_id))


@router.post("/links/{link_id}/check", response_model=LinkRead)
async def check_single_link(
    link_id: uuid.UUID,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> LinkRead:
    link = await _get_link(db, company, link_id)
    await run_checks(db, company, trigger="manual", link_ids=[link.id])
    await db.refresh(link)
    return LinkRead.from_model(link)


@router.get("/links/{link_id}/checks", response_model=list[LinkCheckRead])
async def link_history(
    link_id: uuid.UUID,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[LinkCheck]:
    link = await _get_link(db, company, link_id)
    rows = await db.scalars(
        select(LinkCheck)
        .where(LinkCheck.link_id == link.id)
        .order_by(LinkCheck.checked_at.desc())
        .limit(limit)
    )
    return list(rows.all())


@router.get("/preview", response_model=list[str])
async def preview_slugs(
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=200),
) -> list[str]:
    """A few example URLs, to sanity-check the templates before generating."""
    shops = list(
        (
            await db.scalars(
                select(Shop).where(Shop.company_id == company.id).order_by(Shop.name)
            )
        ).all()
    )
    types = list(
        (
            await db.scalars(
                select(AppointmentType)
                .where(AppointmentType.company_id == company.id)
                .order_by(AppointmentType.name)
            )
        ).all()
    )
    combos = expected_combinations(company, shops, types)
    return [c.url for c in combos[:limit]]
