import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk

DEFAULT_SHOP_TEMPLATE = "guichet_{shop}_{type}"
DEFAULT_EMPLOYEE_TEMPLATE = "{shop}_{type}_{employee}"
DEFAULT_ERROR_PATTERNS = ["page introuvable", "page not found", "404 not found"]


class Company(TimestampMixin, Base):
    """An Odoo tenant: one base URL, one set of shops/employees/types.

    The two templates are what makes the slug shape configurable instead of
    hardcoded — Odoo instances do not all name their appointment links the same
    way. Placeholders: ``{shop}``, ``{type}``, ``{employee}``.
    """

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(sa.String(500), nullable=False)

    shop_link_template: Mapped[str] = mapped_column(
        sa.String(200), nullable=False, default=DEFAULT_SHOP_TEMPLATE
    )
    employee_link_template: Mapped[str] = mapped_column(
        sa.String(200), nullable=False, default=DEFAULT_EMPLOYEE_TEMPLATE
    )

    # Case-insensitive substrings that mark a soft 404 (HTTP 200 + error page).
    error_patterns: Mapped[list[str]] = mapped_column(
        sa.JSON, nullable=False, default=lambda: list(DEFAULT_ERROR_PATTERNS)
    )

    check_hour: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False, default=6)
    check_minute: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False, default=0)
    timezone: Mapped[str] = mapped_column(
        sa.String(64), nullable=False, default="Europe/Paris"
    )

    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    shops = relationship(
        "Shop", back_populates="company", cascade="all, delete-orphan", lazy="selectin"
    )
    employees = relationship(
        "Employee",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    appointment_types = relationship(
        "AppointmentType",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        sa.CheckConstraint("check_hour >= 0 AND check_hour <= 23", name="ck_check_hour"),
        sa.CheckConstraint(
            "check_minute >= 0 AND check_minute <= 59", name="ck_check_minute"
        ),
    )
