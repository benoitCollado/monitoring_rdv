# Décisions d'architecture

## Monolithe MVC, pas de microservices

Le domaine tient en sept tables et une tâche périodique. Un monolithe FastAPI structuré
en MVC (`models` / `controllers` / `services`, avec les schémas Pydantic comme couche de
présentation) donne des transactions simples et un seul déploiement. Le front est en
revanche une application séparée (Vue 3 + Vite), servie par nginx, qui ne parle à l'API
qu'en JSON.

## Le shortcode est une donnée, pas du code

Chaque boutique, conseiller et type de RDV porte un `shortcode`. La forme du slug est
elle-même configurable par entreprise via deux modèles :

- `shop_link_template`, par défaut `guichet_{shop}_{type}` ;
- `employee_link_template`, par défaut `{shop}_{type}_{employee}`.

Une autre instance Odoo qui nommerait ses liens autrement se configure sans toucher au
code. La validation impose la présence des placeholders nécessaires, ce qui évite de
générer des centaines de liens identiques par erreur.

L'URL finale est `base_url + slug`, avec deux cas : si `base_url` contient `{slug}`, le
slug y est substitué (utile pour un paramètre de requête) ; sinon il est concaténé, un
`/` n'étant ajouté que si l'URL de base n'en a pas déjà un.

## Multi-entreprise

`Company` est la racine : URL de base, modèles de lien, motifs d'erreur, heure de cron
et fuseau. Tout le catalogue et tous les liens lui sont rattachés en cascade, et chaque
route vérifie que l'objet visé appartient bien à l'entreprise de l'URL. L'unicité des
shortcodes est par entreprise, jamais globale.

## Conseiller ↔ boutique en many-to-many

Un conseiller peut travailler dans plusieurs boutiques (Anatole Blondiaux est à Paris
Centre et Rive Droite dans les données réelles), et une boutique a plusieurs
conseillers. La table `employee_shops` porte la relation ; la génération ne produit un
lien conseiller que pour les boutiques auxquelles il est rattaché — c'est ce qui évite
l'explosion combinatoire d'un produit cartésien complet.

## Archivage plutôt que suppression

Quand une combinaison disparaît du catalogue, son lien passe à `is_active = false` au
lieu d'être supprimé. L'historique des vérifications reste consultable, et si la
combinaison revient (conseiller réactivé), la même ligne est réutilisée : la continuité
de l'historique est préservée. La suppression n'a lieu que si l'on supprime réellement
la boutique, le conseiller ou le type (cascade SQL).

## Détection des faux 200

Odoo ne renvoie pas toujours 404 sur un lien de RDV mort : un shortcode invalide peut
tomber sur une page générique servie en 200. Le checker considère donc un lien cassé
si le statut est >= 400, si le corps contient l'un des motifs configurés sur
l'entreprise, ou en cas d'erreur réseau. Les motifs sont éditables dans l'UI parce
qu'ils dépendent de la langue et du thème de l'instance.

## Cron dans le process API

APScheduler (`AsyncIOScheduler`) enregistre un job par entreprise, avec le fuseau de
celle-ci, et les jobs sont reconstruits au démarrage et à chaque écriture sur
l'entreprise. Pas de worker ni de broker à opérer. Conséquence assumée : avec plusieurs
réplicas du backend, chaque réplica déclencherait son propre run — dans ce cas il
faudrait un job store partagé ou n'activer `SCHEDULER_ENABLED` que sur une instance.

Les vérifications d'un run sont menées en parallèle avec une sémaphore
(`CHECK_CONCURRENCY`, 8 par défaut) : ~580 liens sont vérifiés en quelques secondes
sans marteler l'instance Odoo.

## Authentification

L'API accepte une clé unique en en-tête `X-API-Key` (variable `API_KEY`). Vide, la
protection est désactivée pour le confort du dev local ; renseignée, elle s'applique à
toutes les routes métier — seuls `/api/health` et `/api/config` restent ouverts, ce
dernier servant au front à savoir s'il doit demander la clé. Ce n'est pas de la gestion
d'utilisateurs : si plusieurs personnes doivent accéder à l'outil avec des droits
distincts, il faudra ajouter une vraie couche d'authentification.
