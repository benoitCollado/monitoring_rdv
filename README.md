# Moniteur de liens Odoo

Génère tous les liens de prise de RDV Odoo d'une entreprise (boutique × type de RDV ×
conseiller) et vérifie **une fois par jour** que chacun répond, pour repérer les 404
avant les clients.

Deux formes de liens sont produites, à partir de shortcodes configurables :

| Forme | Modèle par défaut | Exemple |
| --- | --- | --- |
| Boutique seule | `guichet_{shop}_{type}` | `guichet_bdvalencia_3480` |
| Boutique + conseiller | `{shop}_{type}_{employee}` | `bdvalencia_3480_2663` |

Le slug est concaténé à l'URL de base de l'entreprise. Plusieurs entreprises peuvent
cohabiter dans la même instance, chacune avec son URL de base, ses modèles de lien, son
heure de vérification et son fuseau.

## Architecture

```
backend/     FastAPI en MVC (monolithe, pas de microservice)
  app/models/        M — SQLAlchemy 2 (Company, Shop, Employee, AppointmentType,
                         MonitoredLink, CheckRun, LinkCheck)
  app/controllers/   C — routeurs FastAPI (companies, catalog, monitoring)
  app/schemas/           validation et sérialisation Pydantic (la « vue » JSON)
  app/services/          logique métier : génération des liens, checker HTTP,
                         orchestration des runs, cron APScheduler
  alembic/               migrations
  scripts/               seed du catalogue Blandin & Delloye
frontend/    Vue 3 + Vite + TypeScript + Pinia (application séparée)
docker-compose.yml  Postgres 16 + backend + frontend (nginx)
```

Le cron tourne **dans le process API** via APScheduler : un job par entreprise, à
l'heure et dans le fuseau qu'elle définit, reprogrammé dès qu'on modifie l'entreprise.
Pas de worker supplémentaire à déployer.

## Démarrer

```bash
cp .env.example .env && docker compose up --build
```

Pour un déploiement sur serveur, suivre [docs/deploiement-vps.md](docs/deploiement-vps.md)
plutôt que cette section.

- Front : http://localhost:5173
- API + docs OpenAPI : http://localhost:8000/docs
- Postgres : `localhost:5433` (5433 pour ne pas entrer en conflit avec un autre Postgres)

Les migrations Alembic sont appliquées au démarrage du backend (`entrypoint.sh`).

### Développement sans Docker

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/odoo_link_monitor .venv/bin/alembic upgrade head
.venv/bin/python -m uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev   # proxy /api -> http://localhost:8000
```

## Premiers pas dans l'app

1. **Entreprises** → créer l'entreprise : nom, URL de base, heure du cron, motifs de page
   d'erreur. L'aperçu montre les URLs qui seront produites.
2. **Boutiques**, **Conseillers**, **Types de RDV** → saisir le catalogue. Un conseiller
   peut être rattaché à plusieurs boutiques ; il ne génère de liens que pour
   celles-là.
3. **Moniteur** → « Générer les liens », puis « Vérifier maintenant » (le cron prend le
   relais chaque jour).

Le catalogue Blandin & Delloye (27 boutiques, 8 types de RDV, 46 rattachements) peut
être chargé d'un coup — **remplacez l'URL de base par la vôtre** :

```bash
docker compose exec backend env SEED_BASE_URL=https://mon-odoo.example/r/ python -m scripts.seed_blandin_delloye
```

Le script est idempotent : le relancer met à jour les libellés et rattachements, puis
régénère les liens (584 liens sur ce catalogue).

## Comment un lien est déclaré cassé

- statut HTTP >= 400 (redirections suivies), **ou**
- réponse 200 dont le corps contient l'un des motifs configurés sur l'entreprise
  (`page introuvable`, `page not found`, `404 not found` par défaut) — Odoo renvoie
  parfois une page d'erreur avec un 200, et un contrôle du seul code HTTP la
  laisserait passer, **ou**
- erreur réseau / timeout (15 s par défaut).

Chaque vérification est historisée (`link_checks`), avec le statut, le temps de réponse
et l'URL finale après redirection. Un lien cassé conserve sa date de première casse et
son nombre d'échecs consécutifs.

## Régénération et archivage

« Générer les liens » réconcilie les combinaisons attendues avec la base :

- nouvelle combinaison → lien créé ;
- combinaison disparue (boutique désactivée, conseiller parti) → lien **archivé**, pas
  supprimé : il sort du monitoring mais son historique reste consultable ;
- combinaison qui revient → le même lien est réactivé.

## Configuration

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `DATABASE_URL` | postgres local | DSN asyncpg |
| `API_KEY` | *(vide)* | Vide = aucune authentification (dev). Sinon en-tête `X-API-Key` exigé sur toute l'API, et le front demande la clé. |
| `SCHEDULER_ENABLED` | `true` | Désactive le cron (utile pour un process one-shot) |
| `CHECK_CONCURRENCY` | `8` | Requêtes HTTP simultanées |
| `CHECK_TIMEOUT_SECONDS` | `15` | Timeout par lien |
| `CORS_ORIGINS` | `*` | À restreindre en production |

En production, l'API n'est pas exposée directement : le nginx du front proxifie `/api`
vers le backend, ce qui évite tout CORS.

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q
```

28 tests : génération des combinaisons (dont les slugs exacts de l'exemple Valencia),
détection des 404 durs et souples, transitions de statut, et les routes API
(portée par entreprise, archivage, filtres).
