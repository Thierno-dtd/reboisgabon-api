# ReboisGabon — API Django REST Framework

API de gestion des programmes de reboisement au Gabon : sites de reboisement,
campagnes de plantation, suivis de croissance, authentification sécurisée
(JWT + 2FA), gestion financière (partenaires/bailleurs), dashboard analytique,
audit trail, notifications, exports de rapports, géolocalisation, objectifs
de reboisement, scoring écologique explicable et intelligence prédictive.

Projet réalisé dans le cadre du cahier des charges "Sujet n°7 — ReboisGabon"
(architecture 3 niveaux : client JavaFX / API Django REST Framework / PostgreSQL).

## Stack technique

| Composant | Technologie |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Authentification | JWT (djangorestframework-simplejwt) + TOTP 2FA (pyotp) |
| Base de données | PostgreSQL |
| Cache | LocMemCache (local) — bascule Redis possible, voir section dédiée |
| Filtres | django-filter |
| Documentation API | drf-spectacular (Swagger UI + Redoc) |
| Rate limiting | django-ratelimit |
| Export PDF | reportlab |
| Export Excel | openpyxl |
| Machine Learning | scikit-learn, pandas, joblib |

## Prérequis

- Python 3.11+
- PostgreSQL 14+
- (Optionnel) Docker & Docker Compose — uniquement si tu réactives Redis

## Installation

### 1. Cloner et créer l'environnement

```bash
git clone <url-du-repo>
cd reboisgabon-api
python3 -m venv venv
source venv/bin/activate   # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurer PostgreSQL

```bash
sudo -u postgres psql
CREATE DATABASE reboisgabon;
CREATE USER reboisgabon_user WITH PASSWORD 'motdepasse_solide';
GRANT ALL PRIVILEGES ON DATABASE reboisgabon TO reboisgabon_user;
\q
```

### 3. Variables d'environnement

```bash
cp .env.example .env
# éditer .env avec tes identifiants PostgreSQL
```

### 4. Migrations et données de démonstration

```bash
python manage.py migrate
python manage.py seed_data --flush
python manage.py shell -c "from apps.audit.models import JournalActivite; JournalActivite.objects.all().delete()"
python manage.py entrainer_ia
```

Le seed génère automatiquement :
- 1 compte administrateur : `admin@reboisgabon.ga` / `Admin@123`
- 12 comptes agents de terrain (`Agent@123`)
- 10 essences gabonaises typiques (Okoumé, Moabi, Padouk, Kevazingo, etc.)
- 18 sites de reboisement répartis sur les 9 provinces du Gabon
- ~100 campagnes de plantation sur 2 ans d'historique
- ~400 suivis de croissance avec tendances réalistes
- 7 partenaires/bailleurs avec financements et budgets associés
- Plusieurs objectifs de reboisement (national, par province, par site)

### 5. Lancer le serveur

```bash
python manage.py runserver
```

L'API est disponible sur `http://localhost:8000/`.

## Documentation interactive (Swagger / Redoc)

| Interface | URL | Usage |
|---|---|---|
| Swagger UI | `http://localhost:8000/api/docs/` | Documentation interactive, testable directement dans le navigateur |
| Redoc | `http://localhost:8000/api/redoc/` | Documentation en lecture, mise en page alternative |
| Schéma OpenAPI brut | `http://localhost:8000/api/schema/` | JSON/YAML brut du schéma, exploitable par n'importe quel générateur de client |

**Pour tester un endpoint protégé depuis Swagger :**
1. `POST /api/auth/login/` (section Authentification) avec un compte de démo
2. Copier le champ `access` de la réponse
3. Cliquer sur le bouton **Authorize** en haut de la page
4. Coller le token (sans le préfixe `Bearer`, Swagger l'ajoute automatiquement)
5. N'importe quel endpoint protégé peut ensuite être testé via "Try it out" → "Execute"

**Vérifier que Swagger fonctionne correctement :**
```bash
python manage.py spectacular --file schema.yaml   # génère le schéma, plante si mal configuré
pip show drf-spectacular                          # confirme l'installation du paquet
```

## Cache — Redis (désactivé par défaut, LocMemCache actif)

Le projet utilise actuellement un cache mémoire local (`LocMemCache`), sans
dépendance Docker, pour simplifier les tests en développement. La logique de
cache (dashboard, rate limiting) est écrite de façon backend-agnostique :
aucune modification de code n'est nécessaire pour changer de backend.

**Pour réactiver Redis** (recommandé en production ou pour tester le
comportement multi-processus) :

1. Dans `config/settings.py`, décommenter le bloc `CACHES (Redis)` et
   commenter le bloc `CACHES (local, actif)`.
2. Installer la dépendance si besoin : `pip install django-redis`
3. Lancer le conteneur Redis :
   ```bash
   docker compose up -d redis
   docker compose ps
   ```
4. Vérifier la connexion :
   ```bash
   python manage.py shell -c "from django.core.cache import cache; cache.set('t','ok',10); print(cache.get('t'))"
   ```
5. (Optionnel) Décommenter aussi les lignes `SESSION_ENGINE` /
   `SESSION_CACHE_ALIAS` pour stocker les sessions Django sur Redis plutôt
   qu'en base.

Le fichier `docker-compose.yml` à la racine du projet contient déjà la
configuration du conteneur Redis, prête à l'emploi.

## Authentification — flux complet

1. `POST /api/auth/login/` — `{email, password}`
   - Si 2FA désactivée → tokens JWT directement (`access`, `refresh`)
   - Si 2FA activée → `{requires_2fa: true, temp_token}`
2. `POST /api/auth/login/2fa/verify/` — `{temp_token, otp_code}` → tokens JWT
3. `POST /api/auth/token/refresh/` — `{refresh}` → nouvel `access`
4. `POST /api/auth/password/forgot/` — `{email}` → envoie un lien de reset (token 1h)
5. `POST /api/auth/password/reset/` — `{token, new_password}`
6. `POST /api/auth/2fa/setup/init/` — génère le secret TOTP (QR code à scanner)
7. `POST /api/auth/2fa/setup/confirm/` — `{otp_code}` → active la 2FA
8. `POST /api/auth/2fa/disable/` — désactive la 2FA
9. `GET /api/auth/me/` — profil de l'utilisateur connecté

Rate limiting appliqué : 5 tentatives/min sur le login, 10/min sur la
vérification 2FA, 3/min sur le mot de passe oublié.

## Module Utilisateurs (admin uniquement)

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/users/` | Liste, `?search=`, `?role=`, `?is_active=` |
| POST | `/api/users/` | Créer un compte |
| GET/PATCH | `/api/users/{id}/` | Détail / modifier |
| DELETE | `/api/users/{id}/?confirm=true` | Désactiver (soft delete) |
| POST | `/api/users/{id}/reactivate/` | Réactiver |
| PATCH | `/api/me/update/` | Modifier son propre profil |
| POST | `/api/me/change-password/` | Changer son mot de passe |

## CRUD métier & filtres

| Ressource | Endpoint | Filtres disponibles |
|---|---|---|
| Sites | `/api/sites/` | localité, province, statut, superficie min/max, taux de survie min |
| Campagnes | `/api/campagnes/` | site, essence, période (date_debut/date_fin), taux de survie min/max |
| Suivis | `/api/suivis/` | campagne, site, essence, période, taux de survie min/max |
| Essences | `/api/essences/` | recherche texte |
| Photos terrain | `/api/photos-suivi/` | par suivi |
| Objectifs | `/api/objectifs/` | portée, statut, province, site, échéance |

Tous les filtres sont combinables :
```
GET /api/campagnes/?essence_nom=okoume&date_debut=2025-01-01&taux_survie_min=70
```

Suppression : toutes les entités nécessitent `?confirm=true` (sinon 400).

## Finances

| Ressource | Endpoint |
|---|---|
| Partenaires/bailleurs | `/api/partenaires/` |
| Financements | `/api/financements/` |
| Budgets de campagne | `/api/budgets-campagne/` |

## Dashboard analytique

| Endpoint | Contenu |
|---|---|
| `/api/dashboard/overview/` | Chiffres clés globaux |
| `/api/dashboard/sites/` | Classement des sites (meilleurs/à risque) |
| `/api/dashboard/essences/` | Comparaison des essences |
| `/api/dashboard/provinces/` | Agrégation géographique |
| `/api/dashboard/evolution/` | Séries temporelles mensuelles |
| `/api/dashboard/alertes/` | Alertes (taux critique, suivi manquant) |
| `/api/dashboard/responsables/` | Performance par agent |
| `/api/dashboard/financier/` | Vue financière globale |
| `/api/dashboard/objectifs/` | Progression des objectifs |
| `/api/dashboard/scores-ecologiques/` | Classement par score écologique |
| `/api/dashboard/carte-provinces/` | Statistiques géographiques par province |

## Géolocalisation

| Endpoint | Description |
|---|---|
| `/api/sites-geojson/` | Sites au format GeoJSON (pour carte) |
| `/api/sites-proximite/?lat=&lon=&rayon_km=` | Sites dans un rayon donné |

## Scoring écologique

| Endpoint | Description |
|---|---|
| `/api/sites/{id}/score-ecologique/` | Score détaillé et explicable d'un site |
| `/api/dashboard/scores-ecologiques/` | Classement de tous les sites |

Formule : 50% survie + 20% régularité des suivis + 15% diversité des
essences + 15% statut du site. Chaque composante est renvoyée en détail
(pas une boîte noire).

## Intelligence écologique (Machine Learning)

| Endpoint | Description |
|---|---|
| `POST /api/intelligence/predire-survie/` | Prédit le taux de survie d'une campagne hypothétique |
| `GET /api/intelligence/recommander-essence/?province=` | Recommande les essences les plus performantes historiquement |
| `GET /api/intelligence/detection-risque/` | Détecte les campagnes récentes à risque prédictif (avant tout suivi réel) |
| `POST /api/intelligence/reentrainer/` | Réentraîne le modèle (admin) |

Modèle : `RandomForestRegressor` (scikit-learn), entraîné sur les campagnes
historiques de la base via `python manage.py entrainer_ia`. À réentraîner
après tout enrichissement significatif des données réelles.

## Audit (journal d'activité)

| Endpoint | Description |
|---|---|
| `GET /api/journal/` | Historique complet (admin uniquement), filtres `?utilisateur=`, `?action=`, `?modele=`, `?date_debut=`, `?date_fin=` |

Alimenté automatiquement par signaux Django — aucune action de
création/modification/suppression sur les entités sensibles n'échappe au
journal.

## Notifications & planification

| Endpoint | Description |
|---|---|
| `GET /api/notifications/` | Notifications de l'utilisateur connecté |
| `GET /api/notifications/non_lues/` | Compteur non lues |
| `POST /api/notifications/{id}/marquer_lue/` | Marquer comme lue |
| `POST /api/notifications/marquer-toutes-lues/` | Tout marquer comme lu |
| `GET /api/calendrier-suivis/?horizon=30` | Suivis programmés à venir + en retard |
| `python manage.py check_alertes` | Commande à planifier en cron pour détecter les campagnes à risque |

## Exports de rapports

| Endpoint | Format |
|---|---|
| `/api/exports/rapport-synthese/pdf/` | PDF — chiffres clés, top sites, essences |
| `/api/exports/rapport-financier/pdf/` | PDF — financement par partenaire, coût par plant |
| `/api/exports/sites/excel/` | XLSX — tous les sites |
| `/api/exports/campagnes/excel/` | XLSX — toutes les campagnes avec budget |
| `/api/exports/financements/excel/` | XLSX — tous les financements |

## Système

`GET /api/health/` — healthcheck (statut API + connexion base de données).

## Sécurité

- Mots de passe hachés (PBKDF2, natif Django)
- JWT à durée de vie courte (30 min) + refresh token avec rotation
- 2FA TOTP compatible Google Authenticator
- Rate limiting anti brute-force sur login/2FA/forgot-password
- Tokens de reset à usage unique avec expiration (1h)
- Aucune inscription publique — comptes créés exclusivement par un administrateur
- Soft delete sur les utilisateurs (préserve l'intégrité de l'historique métier)
- Journal d'activité automatique et non contournable (signaux Django)

## Performance

- Cache sur les endpoints dashboard (LocMemCache en local, Redis en
  production — voir section dédiée), invalidation automatique dès qu'une
  donnée métier change
- `select_related`/`prefetch_related` systématiques (évite les requêtes N+1)
- Pagination par défaut (10 éléments/page)

## Tests

```bash
python manage.py test
```

## Architecture

```
reboisgabon-api/
├── docker-compose.yml      # Redis (optionnel, désactivé par défaut)
├── config/                 # settings, urls racine, schéma Swagger custom
├── ml_models/               # modèles ML entraînés (non versionnés)
├── apps/
│   ├── accounts/            # User custom, JWT, 2FA, module Utilisateurs
│   ├── reforestation/       # Sites, Campagnes, Suivis, Essences, Photos,
│   │                        # Objectifs, Scoring, Géolocalisation
│   ├── finances/            # Partenaires, Financements, Budgets
│   ├── dashboard/           # Endpoints analytiques (+ cache)
│   ├── audit/                # Journal d'activité automatique
│   ├── notifications/        # Notifications + détection d'alertes
│   ├── exports/               # Rapports PDF/Excel
│   └── intelligence/           # Prédiction, recommandation, ML
└── manage.py
```

## Tâches planifiées (cron)

```bash
# Détection quotidienne des campagnes à risque (notifications)
0 7 * * * cd /chemin/vers/reboisgabon-api && venv/bin/python manage.py check_alertes

# Réentraînement hebdomadaire du modèle prédictif
0 3 * * 0 cd /chemin/vers/reboisgabon-api && venv/bin/python manage.py entrainer_ia
```

## Checklist de soutenance (10-15 min)

1. **Contexte** (1 min) — besoin réel : pilotage des programmes de reboisement au Gabon.
2. **Architecture** (1-2 min) — schéma 3 niveaux (JavaFX / Django REST / PostgreSQL), aucun accès direct JavaFX→PostgreSQL.
3. **Authentification live** (3 min) — login → 2FA (QR + code) → forgot password → reset → reconnexion.
4. **Module Utilisateurs** (1-2 min) — 403 pour un agent, création par l'admin.
5. **CRUD + filtres** (3 min) — création d'un site/campagne/suivi, filtre combiné.
6. **Dashboard** (3-4 min) — overview, classements, alertes, évolution, carte, scoring écologique.
7. **Modules avancés** (2-3 min) — objectifs de reboisement, prédiction ML, export PDF/Excel.
8. **Questions du jury** — anticiper : choix UUID, soft delete, sécurité des mots de passe, limites du modèle ML, gestion de l'expiration JWT côté client.