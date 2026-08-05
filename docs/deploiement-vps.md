# Déploiement sur VPS

Cible : un VPS Linux avec Docker, derrière le nginx déjà installé sur la machine.
Aucun port n'est exposé publiquement par la stack : tout est publié sur `127.0.0.1`,
et seul nginx est joignable depuis Internet.

```
Internet → nginx (VPS, TLS) → 127.0.0.1:5173 → conteneur frontend (nginx)
                                                 ├── /        → SPA Vue
                                                 └── /api/    → backend:8000 (réseau Docker)
                                                                    └── postgres:5432
```

Le front et l'API sont donc servis sur la **même origine** : pas de CORS à gérer.

## 1. Prérequis sur le VPS

```bash
docker --version && docker compose version && git --version
```

Si Docker manque (Debian/Ubuntu) :

```bash
curl -fsSL https://get.docker.com | sh
```

## 2. Cloner et configurer

```bash
sudo mkdir -p /opt/odoo-link-monitor && sudo chown "$USER" /opt/odoo-link-monitor
git clone <URL_DU_DEPOT> /opt/odoo-link-monitor
cd /opt/odoo-link-monitor
cp .env.example .env
```

Générer les deux secrets et les reporter dans `.env` :

```bash
openssl rand -hex 32   # -> API_KEY
openssl rand -hex 24   # -> POSTGRES_PASSWORD
```

`.env` à viser :

```ini
POSTGRES_USER=app
POSTGRES_PASSWORD=<le secret généré>
POSTGRES_DB=odoo_link_monitor

# Obligatoire en production : sans clé, l'API et le dashboard sont ouverts à tous.
API_KEY=<le secret généré>

SCHEDULER_ENABLED=true
CHECK_CONCURRENCY=8
CHECK_TIMEOUT_SECONDS=15

# Le front est servi sur la même origine que l'API : aucune origine externe requise.
CORS_ORIGINS=https://moniteur.mondomaine.fr
VITE_API_BASE_URL=/api
```

`.env` est ignoré par git : il ne quitte jamais le serveur.

## 3. Démarrer

```bash
docker compose up -d --build
```

Les migrations Alembic s'appliquent au démarrage du backend. Les trois services sont en
`restart: unless-stopped` : ils repartent après un reboot du VPS.

Vérifier :

```bash
curl -s localhost:8000/api/health                    # {"status":"ok"}
curl -s -o /dev/null -w '%{http_code}\n' localhost:5173   # 200 (SPA)
docker compose logs backend | grep -i "cron programmé"
```

## 4. nginx sur le VPS

`/etc/nginx/sites-available/moniteur` :

```nginx
server {
    listen 80;
    server_name moniteur.mondomaine.fr;

    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/moniteur /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d moniteur.mondomaine.fr    # TLS
```

Une seule `location` suffit : `/api` est déjà routé à l'intérieur du conteneur frontend.

## 5. Charger le catalogue Blandin & Delloye

**Remplacez l'URL de base par la vôtre** — celle à laquelle Odoo concatène
`guichet_bdvalencia_3480` :

```bash
docker compose exec backend \
  env SEED_BASE_URL=https://mon-odoo.example/r/ \
  python -m scripts.seed_blandin_delloye
```

Sortie attendue : `584 créés`. Le script est idempotent, on peut le relancer.

Ensuite, dans l'interface : sélectionner l'entreprise, régler l'heure du cron, puis
« Vérifier maintenant » pour un premier passage.

## 6. Exploitation

```bash
docker compose logs -f backend          # runs quotidiens, erreurs
docker compose ps                       # état des services
docker compose restart backend          # redémarrage simple
```

Mettre à jour après un `git push` depuis le poste de dev :

```bash
cd /opt/odoo-link-monitor
git pull
docker compose up -d --build
```

Sauvegarde de la base :

```bash
docker compose exec -T postgres pg_dump -U app odoo_link_monitor | gzip > backup-$(date +%F).sql.gz
```

Restauration :

```bash
gunzip -c backup-2026-08-05.sql.gz | docker compose exec -T postgres psql -U app odoo_link_monitor
```

## Points d'attention

- **`API_KEY` vide = aucune authentification.** Le dashboard expose tous les liens de
  toutes les entreprises ; ne jamais déployer sans clé.
- **Un seul réplica backend.** Le cron tourne dans le process API : deux réplicas
  lanceraient deux runs quotidiens. Pour scaler, ne garder `SCHEDULER_ENABLED=true` que
  sur une instance.
- **`CHECK_CONCURRENCY`** est le nombre de requêtes simultanées envoyées à Odoo. 8 est
  prudent (≈580 liens en quelques secondes) ; l'augmenter charge davantage l'instance
  Odoo.
- **L'heure du cron** est celle de l'entreprise, avec son fuseau (`Europe/Paris` par
  défaut) : elle ne dépend pas du fuseau du VPS.
