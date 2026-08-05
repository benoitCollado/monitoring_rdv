"""Boutiques, conseillers et types de RDV — le catalogue d'une entreprise."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.deps import get_company
from app.core.database import get_db
from app.core.security import require_api_key
from app.models.catalog import AppointmentType, Employee, Shop
from app.models.company import Company
from app.schemas.catalog import (
    AppointmentTypeCreate,
    AppointmentTypeRead,
    AppointmentTypeUpdate,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    ShopCreate,
    ShopRead,
    ShopUpdate,
)

router = APIRouter(
    prefix="/api/companies/{company_id}",
    tags=["catalog"],
    dependencies=[Depends(require_api_key)],
)

DUPLICATE_DETAIL = "Ce shortcode est déjà utilisé dans cette entreprise"


async def _commit(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_DETAIL
        ) from exc


async def _fetch_scoped(db: AsyncSession, model, company: Company, obj_id: uuid.UUID):
    obj = await db.get(model, obj_id)
    if obj is None or obj.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Introuvable")
    return obj


async def _resolve_employees(
    db: AsyncSession, company: Company, ids: list[uuid.UUID]
) -> list[Employee]:
    if not ids:
        return []
    rows = list(
        (
            await db.scalars(
                select(Employee).where(
                    Employee.id.in_(ids), Employee.company_id == company.id
                )
            )
        ).all()
    )
    if len(rows) != len(set(ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un conseiller référencé n'appartient pas à cette entreprise",
        )
    return rows


async def _resolve_shops(
    db: AsyncSession, company: Company, ids: list[uuid.UUID]
) -> list[Shop]:
    if not ids:
        return []
    rows = list(
        (
            await db.scalars(
                select(Shop).where(Shop.id.in_(ids), Shop.company_id == company.id)
            )
        ).all()
    )
    if len(rows) != len(set(ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une boutique référencée n'appartient pas à cette entreprise",
        )
    return rows


# --------------------------------------------------------------------------- #
# Boutiques
# --------------------------------------------------------------------------- #


@router.get("/shops", response_model=list[ShopRead])
async def list_shops(
    company: Company = Depends(get_company), db: AsyncSession = Depends(get_db)
) -> list[Shop]:
    rows = await db.scalars(
        select(Shop).where(Shop.company_id == company.id).order_by(Shop.name)
    )
    return list(rows.all())


@router.post("/shops", response_model=ShopRead, status_code=status.HTTP_201_CREATED)
async def create_shop(
    payload: ShopCreate,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> Shop:
    data = payload.model_dump(exclude={"employee_ids"})
    shop = Shop(company_id=company.id, **data)
    shop.employees = await _resolve_employees(db, company, payload.employee_ids)
    db.add(shop)
    await _commit(db)
    await db.refresh(shop)
    return shop


@router.patch("/shops/{shop_id}", response_model=ShopRead)
async def update_shop(
    shop_id: uuid.UUID,
    payload: ShopUpdate,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> Shop:
    shop = await _fetch_scoped(db, Shop, company, shop_id)
    data = payload.model_dump(exclude_unset=True, exclude={"employee_ids"})
    for field, value in data.items():
        setattr(shop, field, value)
    if payload.employee_ids is not None:
        shop.employees = await _resolve_employees(db, company, payload.employee_ids)
    await _commit(db)
    await db.refresh(shop)
    return shop


@router.delete("/shops/{shop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shop(
    shop_id: uuid.UUID,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> None:
    shop = await _fetch_scoped(db, Shop, company, shop_id)
    await db.delete(shop)
    await db.commit()


# --------------------------------------------------------------------------- #
# Conseillers
# --------------------------------------------------------------------------- #


@router.get("/employees", response_model=list[EmployeeRead])
async def list_employees(
    company: Company = Depends(get_company), db: AsyncSession = Depends(get_db)
) -> list[Employee]:
    rows = await db.scalars(
        select(Employee).where(Employee.company_id == company.id).order_by(Employee.name)
    )
    return list(rows.all())


@router.post(
    "/employees", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED
)
async def create_employee(
    payload: EmployeeCreate,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    data = payload.model_dump(exclude={"shop_ids"})
    employee = Employee(company_id=company.id, **data)
    employee.shops = await _resolve_shops(db, company, payload.shop_ids)
    db.add(employee)
    await _commit(db)
    await db.refresh(employee)
    return employee


@router.patch("/employees/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    employee = await _fetch_scoped(db, Employee, company, employee_id)
    data = payload.model_dump(exclude_unset=True, exclude={"shop_ids"})
    for field, value in data.items():
        setattr(employee, field, value)
    if payload.shop_ids is not None:
        employee.shops = await _resolve_shops(db, company, payload.shop_ids)
    await _commit(db)
    await db.refresh(employee)
    return employee


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: uuid.UUID,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> None:
    employee = await _fetch_scoped(db, Employee, company, employee_id)
    await db.delete(employee)
    await db.commit()


# --------------------------------------------------------------------------- #
# Types de RDV
# --------------------------------------------------------------------------- #


@router.get("/appointment-types", response_model=list[AppointmentTypeRead])
async def list_appointment_types(
    company: Company = Depends(get_company), db: AsyncSession = Depends(get_db)
) -> list[AppointmentType]:
    rows = await db.scalars(
        select(AppointmentType)
        .where(AppointmentType.company_id == company.id)
        .order_by(AppointmentType.name)
    )
    return list(rows.all())


@router.post(
    "/appointment-types",
    response_model=AppointmentTypeRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_appointment_type(
    payload: AppointmentTypeCreate,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> AppointmentType:
    appointment_type = AppointmentType(company_id=company.id, **payload.model_dump())
    db.add(appointment_type)
    await _commit(db)
    await db.refresh(appointment_type)
    return appointment_type


@router.patch("/appointment-types/{type_id}", response_model=AppointmentTypeRead)
async def update_appointment_type(
    type_id: uuid.UUID,
    payload: AppointmentTypeUpdate,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> AppointmentType:
    appointment_type = await _fetch_scoped(db, AppointmentType, company, type_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(appointment_type, field, value)
    await _commit(db)
    await db.refresh(appointment_type)
    return appointment_type


@router.delete(
    "/appointment-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_appointment_type(
    type_id: uuid.UUID,
    company: Company = Depends(get_company),
    db: AsyncSession = Depends(get_db),
) -> None:
    appointment_type = await _fetch_scoped(db, AppointmentType, company, type_id)
    await db.delete(appointment_type)
    await db.commit()
