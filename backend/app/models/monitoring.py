import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk

LINK_KIND_SHOP = "shop"
LINK_KIND_EMPLOYEE = "employee"

STATUS_UNKNOWN = "unknown"
STATUS_OK = "ok"
STATUS_BROKEN = "broken"

REASON_OK = "ok"
REASON_HTTP_STATUS = "http_status"
REASON_ERROR_PATTERN = "error_pattern"
REASON_NETWORK = "network"


class MonitoredLink(TimestampMixin, Base):
    """One generated combination.

    Rows are never deleted when a combination stops being valid (a shop is
    deactivated, an employee leaves): they are archived (``is_active = False``)
    so their check history survives, and revived if the combination comes back.
    """

    __tablename__ = "monitored_links"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    shop_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False
    )
    appointment_type_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("appointment_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=True
    )

    kind: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(400), nullable=False)
    url: Mapped[str] = mapped_column(sa.String(900), nullable=False)

    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    status: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, default=STATUS_UNKNOWN
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_status_code: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    last_response_time_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    last_reason: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    broken_since: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    shop = relationship("Shop", lazy="joined")
    appointment_type = relationship("AppointmentType", lazy="joined")
    employee = relationship("Employee", lazy="joined")

    __table_args__ = (
        sa.UniqueConstraint("company_id", "slug", name="uq_link_slug"),
        sa.Index("ix_links_company_status", "company_id", "status"),
        sa.CheckConstraint(
            "kind in ('shop', 'employee')", name="ck_link_kind"
        ),
        sa.CheckConstraint(
            "status in ('unknown', 'ok', 'broken')", name="ck_link_status"
        ),
    )


class CheckRun(Base):
    """One batch — the daily cron pass, or a manual "tout revérifier"."""

    __tablename__ = "check_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    trigger: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="cron")
    status: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, default="running"
    )
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    checked_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    ok_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    broken_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (
        sa.Index("ix_runs_company_started", "company_id", "started_at"),
        sa.CheckConstraint(
            "status in ('running', 'done', 'failed')", name="ck_run_status"
        ),
    )


class LinkCheck(Base):
    __tablename__ = "link_checks"

    id: Mapped[uuid.UUID] = uuid_pk()
    link_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("monitored_links.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("check_runs.id", ondelete="SET NULL"), nullable=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    ok: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    status_code: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    final_url: Mapped[str | None] = mapped_column(sa.String(900), nullable=True)
    reason: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (sa.Index("ix_checks_link_checked", "link_id", "checked_at"),)
