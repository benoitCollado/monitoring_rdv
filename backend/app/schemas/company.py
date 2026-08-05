import uuid
import zoneinfo
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models.company import (
    DEFAULT_EMPLOYEE_TEMPLATE,
    DEFAULT_ERROR_PATTERNS,
    DEFAULT_SHOP_TEMPLATE,
)


def check_base_url(value: str) -> str:
    value = value.strip()
    if not value.startswith(("http://", "https://")):
        raise ValueError("L'URL de base doit commencer par http:// ou https://")
    return value


def check_shop_template(value: str) -> str:
    missing = [p for p in ("{shop}", "{type}") if p not in value]
    if missing:
        raise ValueError(f"Le modèle boutique doit contenir {' et '.join(missing)}")
    if "{employee}" in value:
        raise ValueError("Le modèle boutique ne peut pas contenir {employee}")
    return value


def check_employee_template(value: str) -> str:
    missing = [p for p in ("{shop}", "{type}", "{employee}") if p not in value]
    if missing:
        raise ValueError(f"Le modèle conseiller doit contenir {' et '.join(missing)}")
    return value


def check_timezone(value: str) -> str:
    try:
        zoneinfo.ZoneInfo(value)
    except Exception as exc:  # noqa: BLE001 - surfaced as a 422
        raise ValueError(f"Fuseau horaire inconnu : {value}") from exc
    return value


BaseUrl = Annotated[
    str, Field(min_length=1, max_length=500), AfterValidator(check_base_url)
]
ShopTemplate = Annotated[
    str, Field(max_length=200), AfterValidator(check_shop_template)
]
EmployeeTemplate = Annotated[
    str, Field(max_length=200), AfterValidator(check_employee_template)
]
Timezone = Annotated[str, Field(max_length=64), AfterValidator(check_timezone)]
Hour = Annotated[int, Field(ge=0, le=23)]
Minute = Annotated[int, Field(ge=0, le=59)]
CompanyName = Annotated[str, Field(min_length=1, max_length=200)]


class CompanyCreate(BaseModel):
    name: CompanyName
    base_url: BaseUrl
    shop_link_template: ShopTemplate = DEFAULT_SHOP_TEMPLATE
    employee_link_template: EmployeeTemplate = DEFAULT_EMPLOYEE_TEMPLATE
    error_patterns: list[str] = Field(
        default_factory=lambda: list(DEFAULT_ERROR_PATTERNS)
    )
    check_hour: Hour = 6
    check_minute: Minute = 0
    timezone: Timezone = "Europe/Paris"
    is_active: bool = True


class CompanyUpdate(BaseModel):
    name: CompanyName | None = None
    base_url: BaseUrl | None = None
    shop_link_template: ShopTemplate | None = None
    employee_link_template: EmployeeTemplate | None = None
    error_patterns: list[str] | None = None
    check_hour: Hour | None = None
    check_minute: Minute | None = None
    timezone: Timezone | None = None
    is_active: bool | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    base_url: str
    shop_link_template: str
    employee_link_template: str
    error_patterns: list[str]
    check_hour: int
    check_minute: int
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
