"""Initial schema: companies, catalog, generated links and check history.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("shop_link_template", sa.String(length=200), nullable=False),
        sa.Column("employee_link_template", sa.String(length=200), nullable=False),
        sa.Column("error_patterns", sa.JSON(), nullable=False),
        sa.Column("check_hour", sa.SmallInteger(), nullable=False, server_default="6"),
        sa.Column("check_minute", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Europe/Paris",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("check_hour >= 0 AND check_hour <= 23", name="ck_check_hour"),
        sa.CheckConstraint(
            "check_minute >= 0 AND check_minute <= 59", name="ck_check_minute"
        ),
    )

    for table in ("shops", "employees", "appointment_types"):
        unique_name = {
            "shops": "uq_shop_shortcode",
            "employees": "uq_employee_shortcode",
            "appointment_types": "uq_appointment_type_shortcode",
        }[table]
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "company_id",
                sa.Uuid(),
                sa.ForeignKey("companies.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("shortcode", sa.String(length=120), nullable=False),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint("company_id", "shortcode", name=unique_name),
        )

    op.create_table(
        "employee_shops",
        sa.Column(
            "employee_id",
            sa.Uuid(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "shop_id",
            sa.Uuid(),
            sa.ForeignKey("shops.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "check_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "trigger", sa.String(length=16), nullable=False, server_default="cron"
        ),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="running"
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ok_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("broken_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status in ('running', 'done', 'failed')", name="ck_run_status"
        ),
    )
    op.create_index("ix_runs_company_started", "check_runs", ["company_id", "started_at"])

    op.create_table(
        "monitored_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "shop_id",
            sa.Uuid(),
            sa.ForeignKey("shops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "appointment_type_id",
            sa.Uuid(),
            sa.ForeignKey("appointment_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.Uuid(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("slug", sa.String(length=400), nullable=False),
        sa.Column("url", sa.String(length=900), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="unknown"
        ),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_response_time_ms", sa.Integer(), nullable=True),
        sa.Column("last_reason", sa.String(length=32), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "consecutive_failures", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("broken_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("company_id", "slug", name="uq_link_slug"),
        sa.CheckConstraint("kind in ('shop', 'employee')", name="ck_link_kind"),
        sa.CheckConstraint(
            "status in ('unknown', 'ok', 'broken')", name="ck_link_status"
        ),
    )
    op.create_index(
        "ix_links_company_status", "monitored_links", ["company_id", "status"]
    )

    op.create_table(
        "link_checks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "link_id",
            sa.Uuid(),
            sa.ForeignKey("monitored_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("check_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("final_url", sa.String(length=900), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_checks_link_checked", "link_checks", ["link_id", "checked_at"])


def downgrade() -> None:
    op.drop_table("link_checks")
    op.drop_table("monitored_links")
    op.drop_table("check_runs")
    op.drop_table("employee_shops")
    op.drop_table("appointment_types")
    op.drop_table("employees")
    op.drop_table("shops")
    op.drop_table("companies")
