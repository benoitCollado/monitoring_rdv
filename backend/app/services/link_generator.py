"""Turn the catalog (shops x types x employees) into the list of links to watch.

The rules, straight from the Odoo naming convention:

* for every shop and every appointment type, one *shop-only* link
  (``guichet_bdvalencia_3480``);
* for every employee attached to that shop, one link per appointment type
  (``bdvalencia_3480_2663``).

Only active rows take part, and an employee only produces links for the shops
they are actually attached to.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import AppointmentType, Shop
from app.models.company import Company
from app.models.monitoring import (
    LINK_KIND_EMPLOYEE,
    LINK_KIND_SHOP,
    STATUS_UNKNOWN,
    MonitoredLink,
)
from app.schemas.monitoring import GenerateResult


def build_url(base_url: str, slug: str) -> str:
    """Append the slug to the company base URL.

    ``{slug}`` anywhere in the base URL wins; otherwise the slug is appended,
    inserting a ``/`` only when the base URL does not already end with one
    (Odoo link-tracker bases usually look like ``https://host/r/``).
    """
    if "{slug}" in base_url:
        return base_url.replace("{slug}", slug)
    if base_url.endswith("/"):
        return base_url + slug
    return f"{base_url}/{slug}"


@dataclass(frozen=True)
class Combination:
    kind: str
    slug: str
    url: str
    shop_id: object
    appointment_type_id: object
    employee_id: object | None


def expected_combinations(
    company: Company,
    shops: list[Shop],
    appointment_types: list[AppointmentType],
) -> list[Combination]:
    combos: list[Combination] = []
    seen: set[str] = set()

    active_types = [t for t in appointment_types if t.is_active]

    for shop in shops:
        if not shop.is_active:
            continue
        employees = [e for e in shop.employees if e.is_active]
        for appointment_type in active_types:
            shop_slug = company.shop_link_template.format(
                shop=shop.shortcode, type=appointment_type.shortcode
            )
            if shop_slug not in seen:
                seen.add(shop_slug)
                combos.append(
                    Combination(
                        kind=LINK_KIND_SHOP,
                        slug=shop_slug,
                        url=build_url(company.base_url, shop_slug),
                        shop_id=shop.id,
                        appointment_type_id=appointment_type.id,
                        employee_id=None,
                    )
                )
            for employee in employees:
                slug = company.employee_link_template.format(
                    shop=shop.shortcode,
                    type=appointment_type.shortcode,
                    employee=employee.shortcode,
                )
                if slug in seen:
                    continue
                seen.add(slug)
                combos.append(
                    Combination(
                        kind=LINK_KIND_EMPLOYEE,
                        slug=slug,
                        url=build_url(company.base_url, slug),
                        shop_id=shop.id,
                        appointment_type_id=appointment_type.id,
                        employee_id=employee.id,
                    )
                )
    return combos


async def sync_links(session: AsyncSession, company: Company) -> GenerateResult:
    """Reconcile ``monitored_links`` with what the catalog currently implies.

    Combinations that disappear are archived rather than deleted, so their
    check history stays readable; if they come back the same row is revived.
    """
    shops = (
        await session.scalars(
            select(Shop).where(Shop.company_id == company.id).order_by(Shop.name)
        )
    ).all()
    types = (
        await session.scalars(
            select(AppointmentType)
            .where(AppointmentType.company_id == company.id)
            .order_by(AppointmentType.name)
        )
    ).all()

    combos = expected_combinations(company, list(shops), list(types))
    expected = {c.slug: c for c in combos}

    existing = (
        await session.scalars(
            select(MonitoredLink).where(MonitoredLink.company_id == company.id)
        )
    ).all()
    by_slug = {link.slug: link for link in existing}

    created = revived = archived = updated = 0

    for slug, combo in expected.items():
        link = by_slug.get(slug)
        if link is None:
            session.add(
                MonitoredLink(
                    company_id=company.id,
                    shop_id=combo.shop_id,
                    appointment_type_id=combo.appointment_type_id,
                    employee_id=combo.employee_id,
                    kind=combo.kind,
                    slug=slug,
                    url=combo.url,
                    is_active=True,
                    status=STATUS_UNKNOWN,
                )
            )
            created += 1
            continue

        if not link.is_active:
            link.is_active = True
            revived += 1

        changed = False
        if link.url != combo.url:
            link.url = combo.url
            changed = True
        # The FKs can move when a shortcode is reused by another row.
        for field, value in (
            ("shop_id", combo.shop_id),
            ("appointment_type_id", combo.appointment_type_id),
            ("employee_id", combo.employee_id),
            ("kind", combo.kind),
        ):
            if getattr(link, field) != value:
                setattr(link, field, value)
                changed = True
        if changed:
            updated += 1

    for slug, link in by_slug.items():
        if slug not in expected and link.is_active:
            link.is_active = False
            archived += 1

    await session.commit()

    return GenerateResult(
        created=created,
        revived=revived,
        archived=archived,
        updated=updated,
        total_active=len(expected),
    )
