import pytest


async def _bootstrap(client):
    """One company, two shops, two employees, two appointment types."""
    company = (
        await client.post(
            "/api/companies",
            json={"name": "Blandin & Delloye", "base_url": "https://odoo.example/r/"},
        )
    ).json()
    cid = company["id"]

    valencia = (
        await client.post(
            f"/api/companies/{cid}/shops",
            json={"name": "Valencia", "shortcode": "bdvalencia"},
        )
    ).json()
    rouen = (
        await client.post(
            f"/api/companies/{cid}/shops", json={"name": "Rouen", "shortcode": "rouen"}
        )
    ).json()

    pozuelo = (
        await client.post(
            f"/api/companies/{cid}/employees",
            json={
                "name": "Maxime Pozuelo",
                "shortcode": "2663",
                "shop_ids": [valencia["id"]],
            },
        )
    ).json()

    for name, code in (("Atelier Découverte", "3480"), ("Essayage", "3511")):
        await client.post(
            f"/api/companies/{cid}/appointment-types",
            json={"name": name, "shortcode": code},
        )

    return {"company": company, "valencia": valencia, "rouen": rouen, "pozuelo": pozuelo}


async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_company_crud_and_duplicate_name(client):
    payload = {"name": "Acme", "base_url": "https://odoo.example/r/"}
    created = await client.post("/api/companies", json=payload)
    assert created.status_code == 201
    assert created.json()["shop_link_template"] == "guichet_{shop}_{type}"

    duplicate = await client.post("/api/companies", json=payload)
    assert duplicate.status_code == 409

    cid = created.json()["id"]
    patched = await client.patch(
        f"/api/companies/{cid}", json={"check_hour": 5, "check_minute": 30}
    )
    assert patched.status_code == 200
    assert patched.json()["check_hour"] == 5

    assert (await client.delete(f"/api/companies/{cid}")).status_code == 204
    assert (await client.get(f"/api/companies/{cid}")).status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_url", "odoo.example"),
        ("shop_link_template", "guichet_{shop}"),
        ("employee_link_template", "{shop}_{type}"),
        ("timezone", "Mars/Olympus"),
    ],
)
async def test_company_validation_rejects_bad_config(client, field, value):
    payload = {"name": f"X{field}", "base_url": "https://odoo.example/r/", field: value}
    response = await client.post("/api/companies", json=payload)
    assert response.status_code == 422


async def test_shortcode_must_be_url_safe(client):
    cid = (
        await client.post(
            "/api/companies",
            json={"name": "Acme", "base_url": "https://odoo.example/r/"},
        )
    ).json()["id"]

    response = await client.post(
        f"/api/companies/{cid}/shops", json={"name": "Bad", "shortcode": "bd valencia"}
    )
    assert response.status_code == 422


async def test_generate_produces_shop_and_employee_links(client):
    data = await _bootstrap(client)
    cid = data["company"]["id"]

    generated = await client.post(f"/api/companies/{cid}/links/generate")
    assert generated.status_code == 200
    # 2 shops x 2 types = 4 shop links, + 1 employee on Valencia x 2 types.
    assert generated.json()["created"] == 6
    assert generated.json()["total_active"] == 6

    links = (await client.get(f"/api/companies/{cid}/links")).json()
    slugs = {item["slug"] for item in links["items"]}
    assert slugs == {
        "guichet_bdvalencia_3480",
        "guichet_bdvalencia_3511",
        "guichet_rouen_3480",
        "guichet_rouen_3511",
        "bdvalencia_3480_2663",
        "bdvalencia_3511_2663",
    }
    valencia_link = next(
        i for i in links["items"] if i["slug"] == "bdvalencia_3480_2663"
    )
    assert valencia_link["url"] == "https://odoo.example/r/bdvalencia_3480_2663"
    assert valencia_link["employee_name"] == "Maxime Pozuelo"
    assert valencia_link["status"] == "unknown"


async def test_generate_is_idempotent_and_archives_stale_links(client):
    data = await _bootstrap(client)
    cid = data["company"]["id"]
    await client.post(f"/api/companies/{cid}/links/generate")

    again = (await client.post(f"/api/companies/{cid}/links/generate")).json()
    assert again["created"] == 0
    assert again["archived"] == 0

    # The employee leaves: their two links are archived, not deleted.
    await client.patch(
        f"/api/companies/{cid}/employees/{data['pozuelo']['id']}",
        json={"is_active": False},
    )
    after = (await client.post(f"/api/companies/{cid}/links/generate")).json()
    assert after["archived"] == 2

    active = (await client.get(f"/api/companies/{cid}/links")).json()
    assert active["total"] == 4

    with_archived = (
        await client.get(f"/api/companies/{cid}/links?include_archived=true")
    ).json()
    assert with_archived["total"] == 6

    # Back on duty: the same rows are revived.
    await client.patch(
        f"/api/companies/{cid}/employees/{data['pozuelo']['id']}",
        json={"is_active": True},
    )
    revived = (await client.post(f"/api/companies/{cid}/links/generate")).json()
    assert revived == {
        "created": 0,
        "revived": 2,
        "archived": 0,
        "updated": 0,
        "total_active": 6,
    }


async def test_changing_the_base_url_rewrites_the_urls(client):
    data = await _bootstrap(client)
    cid = data["company"]["id"]
    await client.post(f"/api/companies/{cid}/links/generate")

    await client.patch(
        f"/api/companies/{cid}", json={"base_url": "https://new.example/appointment"}
    )
    result = (await client.post(f"/api/companies/{cid}/links/generate")).json()
    assert result["updated"] == 6

    links = (await client.get(f"/api/companies/{cid}/links")).json()
    assert all(
        item["url"].startswith("https://new.example/appointment/")
        for item in links["items"]
    )


async def test_links_can_be_filtered(client):
    data = await _bootstrap(client)
    cid = data["company"]["id"]
    await client.post(f"/api/companies/{cid}/links/generate")

    shop_only = (await client.get(f"/api/companies/{cid}/links?kind=shop")).json()
    assert shop_only["total"] == 4

    by_shop = (
        await client.get(f"/api/companies/{cid}/links?shop_id={data['rouen']['id']}")
    ).json()
    assert by_shop["total"] == 2

    searched = (await client.get(f"/api/companies/{cid}/links?q=2663")).json()
    assert searched["total"] == 2


async def test_summary_counts_links(client):
    data = await _bootstrap(client)
    cid = data["company"]["id"]
    await client.post(f"/api/companies/{cid}/links/generate")

    summary = (await client.get(f"/api/companies/{cid}/summary")).json()
    assert summary["total"] == 6
    assert summary["unknown"] == 6
    assert summary["ok"] == 0
    assert summary["broken"] == 0
    assert summary["last_run"] is None


async def test_catalog_is_scoped_to_its_company(client):
    data = await _bootstrap(client)
    other = (
        await client.post(
            "/api/companies", json={"name": "Autre", "base_url": "https://x.example/r/"}
        )
    ).json()

    # A shop of company A cannot be attached to an employee of company B.
    response = await client.post(
        f"/api/companies/{other['id']}/employees",
        json={
            "name": "Intrus",
            "shortcode": "0001",
            "shop_ids": [data["valencia"]["id"]],
        },
    )
    assert response.status_code == 400

    # And it cannot be reached through the other company's URL either.
    response = await client.patch(
        f"/api/companies/{other['id']}/shops/{data['valencia']['id']}",
        json={"name": "Volée"},
    )
    assert response.status_code == 404


async def test_duplicate_shortcode_in_the_same_company_is_rejected(client):
    data = await _bootstrap(client)
    cid = data["company"]["id"]
    response = await client.post(
        f"/api/companies/{cid}/shops",
        json={"name": "Doublon", "shortcode": "bdvalencia"},
    )
    assert response.status_code == 409
