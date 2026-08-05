"""Charge le catalogue Blandin & Delloye (boutiques, conseillers, types de RDV).

Idempotent : relancer le script met à jour les libellés et les rattachements
sans dupliquer les lignes, puis régénère les liens.

    SEED_BASE_URL=https://mon-odoo.example/r/ python -m scripts.seed_blandin_delloye

L'URL de base par défaut est un exemple : mettez la vôtre (celle à laquelle on
concatène `guichet_bdvalencia_3480`), soit via SEED_BASE_URL, soit ensuite dans
l'écran Entreprise du front.
"""

import asyncio
import os
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.catalog import AppointmentType, Employee, Shop
from app.models.company import Company
from app.services.link_generator import sync_links

COMPANY_NAME = "Blandin & Delloye"
BASE_URL = os.environ.get("SEED_BASE_URL", "https://www.blandin-delloye.com/r/")

APPOINTMENT_TYPES = [
    ("Atelier Découverte", "3480"),
    ("Essayage", "3511"),
    ("Commande costume", "3512"),
    ("Commande costume mariage", "3597"),
    ("Recommande express", "3637"),
    ("Recommande", "3636"),
    ("Commande autre", "3596"),
    ("Commande costume femme", "3598"),
]

# (boutique, shortcode boutique, [(conseiller, code, actif)])
SHOPS: list[tuple[str, str, list[tuple[str, str, bool]]]] = [
    ("Annecy", "blandin-delloye-annecy-annecy", [
        ("Frederic Dionisio", "2619", True),
        ("Kenzo Perret", "2640", True),
    ]),
    ("Avignon", "avignon", [("Julien Marchand", "2636", True)]),
    ("Bordeaux", "showroom-bordeaux-bordeaux", [
        ("Ammata Phimphrachanh", "867", True),
        ("Edwin Uzan", "2219", True),
        ("Lou-Anne Marchi", "2626", True),
        ("Kewin Connin", "2667", True),
    ]),
    ("Bruxelles", "blandin-delloye-bruxelles-bruxelles", [
        ("Nelson Cabuy", "2025", True),
    ]),
    ("Caen", "bdcaen", [("Ivan Petit", "2616", True), ("Ogu", "2660", True)]),
    ("Clermont-Ferrand", "clermontferrand", [
        ("Nathan Camus", "1944", True),
        ("Quentin Duron", "1884", True),
    ]),
    ("Dijon", "blandin-delloye-dijon-dijon", [("Maxime Bridoux", "2635", True)]),
    ("Le Mans", "blandin-delloye-le-mans", [
        ("Romain Pizzanelli", "2232", True),
        ("Elohann Chocron", "2664", True),
    ]),
    ("Les Sables d'Olonne", "blandin-delloye-les-sables-les-sables-d-a-olonne", [
        ("Yves Dron", "2634", True),
    ]),
    ("Liège", "blandin-delloye-liege", [("Ornella Mausen", "2641", True)]),
    ("Lille", "lille-lille", [
        ("Karim Benhaddouche", "1387", True),
        ("Remi Dhalluin", "2347", True),
        ("Geoffrey Danel", "1751", True),
        ("Téo Sussin", "2644", True),
    ]),
    ("Lyon", "blandin-delloye-lyon-lyon", [
        ("Thomas Monnin Delhom", "2028", True),
        ("Xavier Bourdila", "2379", True),
        ("Sam Petitot", "2268", True),
    ]),
    ("Montpellier", "bdmontpellier", [("Loïc Laumondais", "2662", True)]),
    ("Montréal", "montrn-al-montreal", [
        ("Gauthier Torres", "2280", True),
        ("Megan Bernier", "2471", True),
        ("Jacky Chen", "2700", True),
    ]),
    ("Nantes", "blandin-delloye-nantes-nantes", [("Thomas Guyomard", "2382", True)]),
    ("Ottawa", "blandin-delloye-ottawa-ottawa", [("Steve Perigny", "2629", True)]),
    ("Paris Centre", "blandin-delloye", [
        ("Norbert Thor", "1261", True),
        # Compte partagé, présent aussi sur Rive Droite.
        ("Anatole Blondiaux", "9999", True),
    ]),
    ("Reims", "reims-reims", [("Pauline Bardel", "2638", True)]),
    ("Rennes", "bdrennes", [("Mathilde Jan", "2661", True)]),
    ("Rive Droite", "showroom-paris-17-paris", [
        ("Elodie Desmet", "2078", True),
        ("Grégory Lépine", "2639", True),
        ("Anatole Blondiaux", "9999", True),
    ]),
    ("Rive Gauche", "paris-6-paris", [
        ("Sylvain Chevalier", "2110", True),
        ("Rehia Demes", "1793", True),
        ("Martin Pougin", "1851", False),  # utilisateur inactif
    ]),
    ("Rouen", "rouen", [("Thomas Bertein", "2637", True)]),
    ("Strasbourg", "blandin-delloye-strasbourg-strasbourg", [
        ("Alain Schellenberg", "2342", True),
        ("Timothé Dekeyser", "2666", True),
    ]),
    ("Toulouse", "bd-toulouse", [("Thierry Barroca", "2104", True)]),
    ("Valencia", "bdvalencia", [("Maxime Pozuelo", "2663", True)]),
    ("La Rochelle", "bdlarochelle", [("Eva Sire", "2668", True)]),
    ("Toronto", "bdtoronto", [("Pedro Lage", "2665", True)]),
]


async def seed() -> None:
    async with SessionLocal() as session:
        company = await session.scalar(
            select(Company).where(Company.name == COMPANY_NAME)
        )
        if company is None:
            company = Company(name=COMPANY_NAME, base_url=BASE_URL)
            session.add(company)
            await session.commit()
            await session.refresh(company)
            print(f"Entreprise créée : {COMPANY_NAME}")
        else:
            print(f"Entreprise existante : {COMPANY_NAME} (base_url conservée)")

        # Types de RDV
        existing_types = {
            t.shortcode: t
            for t in (
                await session.scalars(
                    select(AppointmentType).where(
                        AppointmentType.company_id == company.id
                    )
                )
            ).all()
        }
        for name, code in APPOINTMENT_TYPES:
            appointment_type = existing_types.get(code)
            if appointment_type is None:
                session.add(
                    AppointmentType(
                        company_id=company.id, name=name, shortcode=code
                    )
                )
            else:
                appointment_type.name = name
        await session.commit()

        # Conseillers (un même code peut servir sur plusieurs boutiques)
        existing_employees = {
            e.shortcode: e
            for e in (
                await session.scalars(
                    select(Employee).where(Employee.company_id == company.id)
                )
            ).all()
        }
        for _, _, staff in SHOPS:
            for name, code, is_active in staff:
                employee = existing_employees.get(code)
                if employee is None:
                    employee = Employee(
                        company_id=company.id,
                        name=name,
                        shortcode=code,
                        is_active=is_active,
                    )
                    session.add(employee)
                    existing_employees[code] = employee
                else:
                    employee.name = name
                    employee.is_active = is_active
        await session.commit()

        # Boutiques + rattachements
        existing_shops = {
            s.shortcode: s
            for s in (
                await session.scalars(
                    select(Shop).where(Shop.company_id == company.id)
                )
            ).all()
        }
        for name, code, staff in SHOPS:
            shop = existing_shops.get(code)
            if shop is None:
                shop = Shop(company_id=company.id, name=name, shortcode=code)
                session.add(shop)
                existing_shops[code] = shop
            else:
                shop.name = name
            shop.employees = [existing_employees[c] for _, c, _ in staff]
        await session.commit()

        await session.refresh(company)
        result = await sync_links(session, company)
        print(
            f"Liens : {result.created} créés, {result.revived} réactivés, "
            f"{result.updated} mis à jour, {result.archived} archivés "
            f"— {result.total_active} actifs au total"
        )
        print(f"URL de base utilisée : {company.base_url}")
        if company.base_url == "https://www.blandin-delloye.com/r/":
            print(
                "  /!\\ URL de base d'exemple — corrigez-la dans l'écran "
                "Entreprise, puis relancez la génération.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    asyncio.run(seed())
