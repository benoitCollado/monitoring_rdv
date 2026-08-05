import uuid
from types import SimpleNamespace

from app.services.link_generator import build_url, expected_combinations


def _shop(name, shortcode, employees, is_active=True):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        shortcode=shortcode,
        is_active=is_active,
        employees=employees,
    )


def _employee(name, shortcode, is_active=True):
    return SimpleNamespace(
        id=uuid.uuid4(), name=name, shortcode=shortcode, is_active=is_active
    )


def _type(name, shortcode, is_active=True):
    return SimpleNamespace(
        id=uuid.uuid4(), name=name, shortcode=shortcode, is_active=is_active
    )


def _company(base_url="https://odoo.example/r/"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        base_url=base_url,
        shop_link_template="guichet_{shop}_{type}",
        employee_link_template="{shop}_{type}_{employee}",
    )


def test_build_url_joins_without_double_slash():
    assert build_url("https://o.example/r/", "abc") == "https://o.example/r/abc"
    assert build_url("https://o.example/r", "abc") == "https://o.example/r/abc"
    assert (
        build_url("https://o.example/x?code={slug}", "abc")
        == "https://o.example/x?code=abc"
    )


def test_valencia_combinations_match_the_odoo_naming():
    """The exact slugs from the Valencia example."""
    pozuelo = _employee("Maxime Pozuelo", "2663")
    shops = [_shop("Valencia", "bdvalencia", [pozuelo])]
    types = [
        _type("Atelier Découverte", "3480"),
        _type("Essayage", "3511"),
        _type("Commande costume", "3512"),
    ]

    slugs = [c.slug for c in expected_combinations(_company(), shops, types)]

    assert slugs == [
        "guichet_bdvalencia_3480",
        "bdvalencia_3480_2663",
        "guichet_bdvalencia_3511",
        "bdvalencia_3511_2663",
        "guichet_bdvalencia_3512",
        "bdvalencia_3512_2663",
    ]


def test_shop_link_exists_even_without_employees():
    shops = [_shop("Rouen", "rouen", [])]
    combos = expected_combinations(_company(), shops, [_type("Essayage", "3511")])
    assert [c.slug for c in combos] == ["guichet_rouen_3511"]


def test_inactive_rows_are_skipped():
    active = _employee("Actif", "111")
    inactive = _employee("Inactif", "222", is_active=False)
    shops = [
        _shop("Paris", "paris", [active, inactive]),
        _shop("Fermée", "fermee", [active], is_active=False),
    ]
    types = [_type("Essayage", "3511"), _type("Ancien", "0000", is_active=False)]

    slugs = {c.slug for c in expected_combinations(_company(), shops, types)}

    assert slugs == {"guichet_paris_3511", "paris_3511_111"}


def test_employee_shared_between_two_shops_gets_one_link_per_shop():
    shared = _employee("Anatole Blondiaux", "9999")
    shops = [
        _shop("Paris Centre", "blandin-delloye", [shared]),
        _shop("Rive Droite", "showroom-paris-17-paris", [shared]),
    ]
    combos = expected_combinations(_company(), shops, [_type("Essayage", "3511")])

    assert [c.slug for c in combos] == [
        "guichet_blandin-delloye_3511",
        "blandin-delloye_3511_9999",
        "guichet_showroom-paris-17-paris_3511",
        "showroom-paris-17-paris_3511_9999",
    ]


def test_urls_are_built_from_the_company_base_url():
    shops = [_shop("Valencia", "bdvalencia", [])]
    combos = expected_combinations(
        _company("https://odoo.example/r/"), shops, [_type("Atelier", "3480")]
    )
    assert combos[0].url == "https://odoo.example/r/guichet_bdvalencia_3480"
