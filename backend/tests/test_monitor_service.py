from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.catalog import AppointmentType, Shop
from app.models.company import Company
from app.models.monitoring import (
    REASON_HTTP_STATUS,
    REASON_OK,
    STATUS_BROKEN,
    STATUS_OK,
    LinkCheck,
    MonitoredLink,
)
from app.services import monitor_service
from app.services.link_checker import CheckOutcome
from app.services.link_generator import sync_links

OK = CheckOutcome(ok=True, reason=REASON_OK, status_code=200, response_time_ms=42)
BROKEN = CheckOutcome(
    ok=False,
    reason=REASON_HTTP_STATUS,
    status_code=404,
    response_time_ms=12,
    error="HTTP 404",
)


def test_apply_outcome_marks_broken_and_keeps_the_first_failure_date():
    link = MonitoredLink(
        company_id=None, shop_id=None, appointment_type_id=None, kind="shop",
        slug="s", url="u", status="unknown", consecutive_failures=0,
    )
    first = datetime(2026, 8, 1, 6, 0, tzinfo=timezone.utc)

    monitor_service.apply_outcome(link, BROKEN, first)
    assert link.status == STATUS_BROKEN
    assert link.consecutive_failures == 1
    assert link.broken_since == first

    monitor_service.apply_outcome(link, BROKEN, first + timedelta(days=1))
    assert link.consecutive_failures == 2
    assert link.broken_since == first, "la date de première casse ne bouge pas"

    monitor_service.apply_outcome(link, OK, first + timedelta(days=2))
    assert link.status == STATUS_OK
    assert link.consecutive_failures == 0
    assert link.broken_since is None
    assert link.last_status_code == 200


async def _company_with_one_link(db):
    company = Company(name="Acme", base_url="https://odoo.example/r/")
    db.add(company)
    await db.commit()
    await db.refresh(company)

    db.add(Shop(company_id=company.id, name="Valencia", shortcode="bdvalencia"))
    db.add(
        AppointmentType(company_id=company.id, name="Atelier", shortcode="3480")
    )
    await db.commit()
    await sync_links(db, company)
    return company


async def test_run_checks_records_a_run_and_the_history(db, monkeypatch):
    company = await _company_with_one_link(db)

    async def fake_check(company_arg, links):
        return [(link, BROKEN) for link in links]

    monkeypatch.setattr(monitor_service, "_check_links", fake_check)

    run = await monitor_service.run_checks(db, company, trigger="manual")

    assert run.status == "done"
    assert (run.checked_count, run.ok_count, run.broken_count) == (1, 0, 1)

    link = await db.scalar(select(MonitoredLink))
    assert link.status == STATUS_BROKEN
    assert link.last_error == "HTTP 404"

    checks = (await db.scalars(select(LinkCheck))).all()
    assert len(checks) == 1
    assert checks[0].run_id == run.id
    assert checks[0].ok is False


async def test_a_failing_run_is_closed_as_failed(db, monkeypatch):
    company = await _company_with_one_link(db)

    async def boom(company_arg, links):
        raise RuntimeError("réseau HS")

    monkeypatch.setattr(monitor_service, "_check_links", boom)

    run = await monitor_service.run_checks(db, company)

    assert run.status == "failed"
    assert "réseau HS" in (run.error or "")
    assert run.finished_at is not None
