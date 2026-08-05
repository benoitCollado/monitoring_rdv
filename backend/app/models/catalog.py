import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk

# An employee can work in several shops (e.g. Anatole Blondiaux is both at Paris
# Centre and Rive Droite), hence the association table rather than a FK.
employee_shops = sa.Table(
    "employee_shops",
    Base.metadata,
    sa.Column(
        "employee_id",
        sa.Uuid,
        sa.ForeignKey("employees.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "shop_id",
        sa.Uuid,
        sa.ForeignKey("shops.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Shop(TimestampMixin, Base):
    __tablename__ = "shops"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    shortcode: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    company = relationship("Company", back_populates="shops")
    employees = relationship(
        "Employee", secondary=employee_shops, back_populates="shops", lazy="selectin"
    )

    __table_args__ = (
        sa.UniqueConstraint("company_id", "shortcode", name="uq_shop_shortcode"),
    )


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    shortcode: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    company = relationship("Company", back_populates="employees")
    shops = relationship(
        "Shop", secondary=employee_shops, back_populates="employees", lazy="selectin"
    )

    __table_args__ = (
        sa.UniqueConstraint("company_id", "shortcode", name="uq_employee_shortcode"),
    )


class AppointmentType(TimestampMixin, Base):
    __tablename__ = "appointment_types"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    shortcode: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    company = relationship("Company", back_populates="appointment_types")

    __table_args__ = (
        sa.UniqueConstraint(
            "company_id", "shortcode", name="uq_appointment_type_shortcode"
        ),
    )
