import re
import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

SHORTCODE_RE = re.compile(r"^[A-Za-z0-9._~-]+$")


def check_shortcode(value: str) -> str:
    value = value.strip()
    if not SHORTCODE_RE.match(value):
        raise ValueError(
            "Le shortcode ne peut contenir que lettres, chiffres, - . _ ~ "
            "(il est concaténé dans une URL)"
        )
    return value


Shortcode = Annotated[
    str, Field(min_length=1, max_length=120), AfterValidator(check_shortcode)
]
Name = Annotated[str, Field(min_length=1, max_length=200)]


class _CatalogBase(BaseModel):
    name: Name
    shortcode: Shortcode
    is_active: bool = True


class _CatalogUpdate(BaseModel):
    name: Name | None = None
    shortcode: Shortcode | None = None
    is_active: bool | None = None


class EmployeeRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    shortcode: str
    is_active: bool


class ShopRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    shortcode: str
    is_active: bool


class ShopCreate(_CatalogBase):
    employee_ids: list[uuid.UUID] = Field(default_factory=list)


class ShopUpdate(_CatalogUpdate):
    employee_ids: list[uuid.UUID] | None = None


class ShopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    shortcode: str
    is_active: bool
    employees: list[EmployeeRef] = Field(default_factory=list)


class EmployeeCreate(_CatalogBase):
    shop_ids: list[uuid.UUID] = Field(default_factory=list)


class EmployeeUpdate(_CatalogUpdate):
    shop_ids: list[uuid.UUID] | None = None


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    shortcode: str
    is_active: bool
    shops: list[ShopRef] = Field(default_factory=list)


class AppointmentTypeCreate(_CatalogBase):
    pass


class AppointmentTypeUpdate(_CatalogUpdate):
    pass


class AppointmentTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    shortcode: str
    is_active: bool
