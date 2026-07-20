# ReboisGabon — API Django REST Framework

API de gestion des programmes de reboisement au Gabon : sites de reboisement,
campagnes de plantation, suivis de croissance, authentification sécurisée
(JWT + 2FA) et dashboard analytique pour le pilotage décisionnel.

## Stack technique

- **Backend** : Django 5 + Django REST Framework
- **Auth** : JWT (djangorestframework-simplejwt) + TOTP 2FA (pyotp)
- **Base de données** : PostgreSQL
- **Filtres** : django-filter
- **Documentation API** : drf-spectacular (Swagger/OpenAPI)

## Prérequis

- Python 3.11+
- PostgreSQL 14+
- pip / venv

## Installation

### 1. Cloner et créer l'environnement

\`\`\`bash
git clone <url-du-repo>
cd reboisgabon-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
\`\`\`

### 2. Configurer la base de données

\`\`\`bash
sudo -u postgres psql
CREATE DATABASE reboisgabon;
CREATE USER reboisgabon_user WITH PASSWORD 'motdepasse_solide';
GRANT ALL PRIVILEGES ON DATABASE reboisgabon TO reboisgabon_user;
\q
\`\`\`

### 3. Variables d'environnement

\`\`\`bash
cp .env.example .env
# éditer .env avec vos identifiants PostgreSQL
\`\`\`

### 4. Migrations et données de démonstration

\`\`\`bash
python manage.py migrate
python manage.py seed_data --flush
\`\`\`

Cela crée automatiquement :
- 1 compte administrateur : `admin@reboisgabon.ga` / `Admin@123`
- 12 comptes agents (`Agent@123`)
- 10 essences gabonaises typiques
- 18 sites de reboisement répartis sur les 9 provinces
- ~100 campagnes de plantation sur 2 ans d'historique
- ~400 suivis de croissance avec tendances réalistes

### 5. Lancer le serveur

\`\`\`bash
python manage.py runserver
\`\`\`

L'API est disponible sur `http://localhost:8000/`.

## Documentation interactive

- Swagger UI : `http://localhost:8000/api/docs/`
- Schéma OpenAPI brut : `http://localhost:8000/api/schema/`

## Authentification — flux complet

1. `POST /api/auth/login/` — email + mot de passe
   - Si 2FA désactivée → tokens JWT directement
   - Si 2FA activée → `{requires_2fa: true, temp_token}`
2. `POST /api/auth/login/2fa/verify/` — `{temp_token, otp_code}` → tokens JWT
3. `POST /api/auth/token/refresh/` — renouveler l'access token
4. `POST /api/auth/password/forgot/` — envoie un lien de réinitialisation (token 1h)
5. `POST /api/auth/password/reset/` — `{token, new_password}`
6. `POST /api/auth/2fa/setup/init/` — génère le secret TOTP (à scanner via Google Authenticator)
7. `POST /api/auth/2fa/setup/confirm/` — `{otp_code}` active la 2FA
8. `GET /api/auth/me/` — profil de l'utilisateur connecté

## Module Utilisateurs (admin uniquement)

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/users/` | Liste, recherche `?search=`, filtres `?role=`, `?is_active=` |
| POST | `/api/users/` | Créer un compte |
| PATCH | `/api/users/{id}/` | Modifier |
| DELETE | `/api/users/{id}/?confirm=true` | Désactiver (soft delete) |
| POST | `/api/users/{id}/reactivate/` | Réactiver |
| PATCH | `/api/me/update/` | Mettre à jour son propre profil |
| POST | `/api/me/change-password/` | Changer son mot de passe |

## CRUD métier & filtres

| Ressource | Endpoint | Filtres |
|---|---|---|
| Sites | `/api/sites/` | localité, province, statut, superficie min/max, taux de survie min |
| Campagnes | `/api/campagnes/` | site, essence, période (date_debut/date_fin), taux de survie |
| Suivis | `/api/suivis/` | campagne, site, essence, période, taux de survie |
| Essences | `/api/essences/` | recherche texte |

Tous les filtres sont combinables, ex :
\`\`\`
GET /api/campagnes/?essence_nom=okoume&date_debut=2025-01-01&taux_survie_min=70
\`\`\`

## Dashboard analytique

| Endpoint | Contenu |
|---|---|
| `/api/dashboard/overview/` | Chiffres clés globaux |
| `/api/dashboard/sites/` | Classement des sites (meilleurs / à risque) |
| `/api/dashboard/essences/` | Comparaison des essences |
| `/api/dashboard/provinces/` | Agrégation géographique |
| `/api/dashboard/evolution/` | Séries temporelles mensuelles |
| `/api/dashboard/alertes/` | Alertes automatiques (taux critique, absence de suivi) |
| `/api/dashboard/responsables/` | Performance par agent |

## Tests

\`\`\`bash
python manage.py test
\`\`\`

## Architecture

\`\`\`
reboisgabon-api/
├── config/            # settings, urls racine
├── apps/
│   ├── accounts/       # User custom, JWT, 2FA, module Utilisateurs
│   ├── reforestation/  # Sites, Campagnes, Suivis + filtres
│   └── dashboard/      # Endpoints analytiques
└── manage.py
\`\`\`

## Sécurité

- Mots de passe hachés (PBKDF2, natif Django)
- Tokens JWT à durée de vie courte (30 min) + refresh token avec rotation
- 2FA TOTP compatible Google Authenticator
- Tokens de reset à usage unique avec expiration (1h)
- Aucune inscription publique — comptes créés exclusivement par un administrateur
- Soft delete sur les utilisateurs (préserve l'intégrité de l'historique métier)