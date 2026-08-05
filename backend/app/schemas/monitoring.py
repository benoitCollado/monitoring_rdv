import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    kind: str
    slug: str
    url: str
    is_active: bool
    status: str
    last_checked_at: datetime | None
    last_status_code: int | None
    last_response_time_ms: int | None
    last_reason: str | None
    last_error: str | None
    consecutive_failures: int
    broken_since: datetime | None

    shop_id: uuid.UUID
    shop_name: str
    appointment_type_id: uuid.UUID
    appointment_type_name: str
    employee_id: uuid.UUID | None
    employee_name: str | None

    @classmethod
    def from_model(cls, link) -> "LinkRead":
        return cls(
            id=link.id,
            company_id=link.company_id,
            kind=link.kind,
            slug=link.slug,
            url=link.url,
            is_active=link.is_active,
            status=link.status,
            last_checked_at=link.last_checked_at,
            last_status_code=link.last_status_code,
            last_response_time_ms=link.last_response_time_ms,
            last_reason=link.last_reason,
            last_error=link.last_error,
            consecutive_failures=link.consecutive_failures,
            broken_since=link.broken_since,
            shop_id=link.shop_id,
            shop_name=link.shop.name,
            appointment_type_id=link.appointment_type_id,
            appointment_type_name=link.appointment_type.name,
            employee_id=link.employee_id,
            employee_name=link.employee.name if link.employee else None,
        )


class LinkPage(BaseModel):
    items: list[LinkRead]
    total: int
    limit: int
    offset: int


class LinkCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    link_id: uuid.UUID
    run_id: uuid.UUID | None
    checked_at: datetime
    ok: bool
    status_code: int | None
    response_time_ms: int | None
    final_url: str | None
    reason: str
    error: str | None


class CheckRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    trigger: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    checked_count: int
    ok_count: int
    broken_count: int
    error: str | None


class GenerateResult(BaseModel):
    created: int
    revived: int
    archived: int
    updated: int
    total_active: int


class CompanySummary(BaseModel):
    company_id: uuid.UUID
    total: int
    ok: int
    broken: int
    unknown: int
    archived: int
    last_run: CheckRunRead | None
    next_run_at: datetime | None
