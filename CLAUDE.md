# Moniteur de liens Odoo — repères pour travailler sur ce dépôt

Génère les liens de prise de RDV Odoo (boutique × type de RDV × conseiller) et vérifie
une fois par jour qu'ils répondent. Voir [README.md](README.md) pour l'usage,
[docs/architecture.md](docs/architecture.md) pour les décisions,
[docs/deploiement-vps.md](docs/deploiement-vps.md) pour la mise en production.

## Structure

```
backend/app/models/        SQLAlchemy 2 (Company, Shop, Employee, AppointmentType,
                           MonitoredLink, CheckRun, LinkCheck)
backend/app/controllers/   routeurs FastAPI ; toutes les routes métier sont nichées
                           sous /api/companies/{company_id}/...
backend/app/schemas/       Pydantic v2, validation via Annotated + AfterValidator
backend/app/services/      link_generator (combinaisons), link_checker (1 URL),
                           monitor_service (un run), scheduler (cron APScheduler)
backend/alembic/versions/  migrations, écrites à la main
frontend/src/              Vue 3 <script setup> + Pinia + vue-router
```

## Commandes

```bash
# Tests backend (28, aucun service externe requis : sqlite en mémoire)
cd backend && .venv/bin/python -m pytest -q

# API en local
cd backend && .venv/bin/python -m uvicorn app.main:app --reload

# Front
cd frontend && npm run dev        # proxy /api -> localhost:8000
cd frontend && npm run build      # inclut le typecheck vue-tsc

# Stack complète
docker compose up -d --build
```

## Conventions

- **Le domaine est en français, le code en anglais.** Les modèles, champs et fonctions
  sont en anglais (`Shop`, `shortcode`, `sync_links`) ; les messages d'erreur d'API et
  l'interface sont en français, parce qu'ils sont lus par l'utilisateur final.
- **Tout est porté par `Company`** (multi-entreprise). Chaque route vérifie que
  l'objet visé appartient bien à l'entreprise de l'URL, et l'unicité des shortcodes est
  par entreprise. Ne jamais introduire de requête qui ignore `company_id`.
- **Les modèles de slug sont de la configuration, pas du code** : ne pas coder en dur
  `guichet_` ni l'ordre des composants, ils viennent de
  `Company.shop_link_template` / `employee_link_template`.
- **Archiver, pas supprimer** : une combinaison disparue passe `is_active = False` pour
  garder son historique de vérifications.
- **Migrations écrites à la main** dans `backend/alembic/versions/`, numérotées
  `0002_...`, `0003_...`. Toute modification de modèle en exige une.
- SQLAlchemy en **asynchrone** partout : pas d'accès à une relation non chargée en
  dehors d'une session (les relations utilisées sont en `lazy="selectin"` ou
  `"joined"`).

## Pièges connus

- Le cron vit dans le process API (APScheduler). Un second réplica backend ferait un
  second run quotidien : `SCHEDULER_ENABLED=true` sur une seule instance.
- `API_KEY` vide désactive toute authentification — acceptable en local, jamais en
  production.
- Odoo renvoie parfois une page d'erreur avec un statut 200 : le checker teste aussi le
  corps de la réponse contre `Company.error_patterns`. Ne pas « simplifier » en ne
  regardant que le code HTTP.
