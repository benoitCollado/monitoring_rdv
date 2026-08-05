import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_api_key
from app.controllers.deps import get_company
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.scheduler import remove_company_job, schedule_company

router = APIRouter(
    prefix="/api/companies", tags=["companies"], dependencies=[Depends(require_api_key)]
)


@router.get("", response_model=list[CompanyRead])
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[Company]:
    result = await db.scalars(select(Company).order_by(Company.name))
    return list(result.all())


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate, db: AsyncSession = Depends(get_db)
) -> Company:
    company = Company(**payload.model_dump())
    db.add(company)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une entreprise porte déjà ce nom",
        ) from exc
    await db.refresh(company)
    schedule_company(company)
    return company


@router.get("/{company_id}", response_model=CompanyRead)
async def get_one(company: Company = Depends(get_company)) -> Company:
    return company


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    payload: CompanyUpdate,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> Company:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une entreprise porte déjà ce nom",
        ) from exc
    await db.refresh(company)
    # Templates or base URL may have changed: the links are regenerated on the
    # next "générer", but the cron window is applied right away.
    schedule_company(company)
    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company: Company = Depends(get_company), db: AsyncSession = Depends(get_db)
) -> None:
    company_id: uuid.UUID = company.id
    await db.delete(company)
    await db.commit()
    remove_company_job(company_id)
