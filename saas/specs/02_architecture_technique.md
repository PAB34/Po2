# Architecture Technique — PatrimoineOp v0.2

## 1. Objectif de cette version

Cette architecture couvre uniquement le **MVP v0.1** :

* inscription / connexion utilisateur,
* choix de la ville à l’inscription,
* page d’accueil avec carte communale,
* liste des bâtiments filtrés par ville,
* création et modification manuelle de bâtiments,
* identification d’un bâtiment sur carte via OpenStreetMap,
* création automatique d’un local principal,
* gestion simple des locaux,
* section minimale “Équipements bâtiments”,
* page “Compte utilisateur”.

Les modules suivants sont exclus de cette version :

* ENEDIS,
* OPERAT,
* plan pluriannuel de travaux,
* imports documentaires,
* IA,
* multi-tenant complexe par collectivité.

---

## 2. Vue d’ensemble

```text
┌──────────────────────────────────────────────────────────────┐
│                        APPLICATION WEB                       │
│                                                              │
│  Frontend React + Vite + TypeScript                         │
│  - Connexion / inscription                                  │
│  - Accueil (carte communale)                                │
│  - Bâtiments                                                │
│  - Fiche bâtiment                                           │
│  - Locaux                                                   │
│  - Équipements bâtiments                                    │
│  - Compte utilisateur                                       │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼───────────────────────────────┐
│                    API FastAPI (Python)                      │
│                                                              │
│  - Authentification                                          │
│  - Gestion utilisateurs                                      │
│  - Référentiel villes                                        │
│  - Import DGFiP                                              │
│  - Gestion bâtiments                                         │
│  - Gestion locaux                                            │
│  - Intégration OSM / géocodage                               │
│  - Gestion simple équipements                                │
└───────────────┬───────────────────────┬──────────────────────┘
                │                       │
                │ SQL                   │ HTTP
┌───────────────▼──────────────┐   ┌────▼──────────────────────┐
│ PostgreSQL + PostGIS         │   │ APIs externes             │
│                              │   │ - OpenStreetMap tiles     │
│ - utilisateurs               │   │ - Nominatim (géocodage)   │
│ - villes                     │   │ - Overpass / objets OSM   │
│ - lignes DGFiP               │   └───────────────────────────┘
│ - bâtiments                  │
│ - métadonnées OSM            │
│ - locaux                     │
│ - équipements                │
└──────────────────────────────┘
```

---

## 3. Choix techniques

## 3.1 Frontend

### Stack

* React 18
* Vite
* TypeScript
* Tailwind CSS
* shadcn/ui
* React Router
* React Query
* React Hook Form + Zod
* React Leaflet

### Pourquoi React Leaflet

Le besoin immédiat est une carte simple, interactive, centrée sur la commune, avec affichage de points et sélection cartographique.
Comme vous n’avez pas de clé Mapbox prévue à ce stade, il vaut mieux partir directement sur **Leaflet + fonds OpenStreetMap**. 

---

## 3.2 Backend

### Stack

* FastAPI
* SQLAlchemy 2.x
* Alembic
* Pydantic v2
* Passlib / bcrypt
* JWT
* httpx
* pytest

### Choix d’authentification

Pour ce MVP, l’authentification doit rester **gérée par l’application** :

* email,
* mot de passe hashé,
* JWT côté API.

Pas d’Azure AD B2C dans cette version.
Le besoin actuel ne justifie pas encore cette complexité. Le fichier d’architecture précédent en faisait une brique centrale, mais ce n’est pas adapté à ce premier périmètre. 

---

## 3.3 Base de données

### Stack

* PostgreSQL
* extension PostGIS

### Pourquoi PostGIS

Même si le MVP reste simple, il est utile dès maintenant pour :

* stocker latitude / longitude,
* préparer la recherche spatiale,
* gérer plus tard des polygones ou des zones.

## 3.4 Exploitation et déploiement cible

### Petite production cible

Pour la petite production, la solution cible doit rester la plus économique possible :

* un VPS Linux unique,
* PostgreSQL + PostGIS sur la même machine,
* backend FastAPI conteneurisé,
* frontend React/Vite compilé puis servi en statique,
* orchestration par Docker Compose.

### Portabilité future

Cette cible économique ne doit pas bloquer une migration future vers Azure.
L’application doit donc rester portable :

* conteneurs standards,
* configuration par variables d’environnement,
* migrations gérées par Alembic,
* absence de dépendance forte à un service Azure spécifique au MVP.

---

## 4. Référentiel de données

L’architecture repose sur 6 blocs de tables :

* utilisateurs,
* référentiel villes,
* lignes sources DGFiP,
* bâtiments,
* locaux,
* équipements simples.

---

## 5. Modèle de données simplifié

```sql
users
  id
  email
  password_hash
  nom
  prenom
  telephone
  city_id
  role
  is_active
  created_at
  updated_at

cities
  id
  nom_commune
  code_commune nullable
  code_postal nullable
  latitude nullable
  longitude nullable
  source_file
  created_at

dgfip_source_rows
  id
  city_id
  nom_commune
  numero_voirie
  nature_voie
  nom_voie
  prefixe
  section
  numero_plan
  batiment_source nullable
  entree nullable
  niveau nullable
  porte nullable
  numero_majic nullable
  code_droit nullable
  numero_siren nullable
  denomination nullable
  source_file
  created_at

buildings
  id
  city_id
  dgfip_source_row_id nullable
  nom_batiment nullable
  nom_commune
  numero_voirie nullable
  nature_voie nullable
  nom_voie nullable
  prefixe nullable
  section nullable
  numero_plan nullable
  adresse_reconstituee nullable
  latitude nullable
  longitude nullable
  osm_id nullable
  osm_type nullable
  osm_name nullable
  osm_display_name nullable
  osm_tags_json nullable
  source_creation (DGFIP|MANUEL)
  statut_geocodage (NON_FAIT|PARTIEL|VALIDE|ECHEC)
  created_at
  updated_at

locals
  id
  building_id
  nom_local
  type_local
  niveau nullable
  surface_m2 nullable
  usage nullable
  statut_occupation nullable
  commentaire nullable
  created_at
  updated_at

building_equipments
  id
  building_id
  local_id nullable
  nom_equipement
  categorie
  commentaire nullable
  created_at
  updated_at
```

---

## 6. Règles métier structurantes

### 6.1 Ville à l’inscription

L’utilisateur choisit sa ville dans une liste déroulante issue des **communes distinctes** du fichier DGFiP source.

### 6.2 Périmètre utilisateur

Par défaut :

* un utilisateur voit les bâtiments de sa ville,
* les créations manuelles sont rattachées à cette ville.

### 6.3 Bâtiment

Un bâtiment peut être créé :

* depuis une ligne source DGFiP,
* manuellement.

### 6.4 Local obligatoire

Chaque bâtiment doit avoir **au moins un local**.

À la création d’un bâtiment :

* le système crée automatiquement un local par défaut,
* si `nom_batiment` existe, alors `nom_local = nom_batiment`,
* sinon `nom_local = Local principal`.

### 6.5 OSM

OSM fournit :

* une aide au positionnement,
* des coordonnées,
* un nom si disponible,
* des tags éventuels.

Le nom OSM n’est jamais une vérité absolue.
Il s’agit d’une proposition que l’utilisateur peut conserver, modifier ou ignorer.

---

## 7. Référentiel de données : alimentation

## 7.1 Chargement initial du fichier DGFiP

Un script d’import lit le fichier source et alimente :

* `cities`
* `dgfip_source_rows`

## 7.2 Construction de la liste de villes

La table `cities` est générée à partir des valeurs distinctes de commune contenues dans le fichier DGFiP.

## 7.3 Création des bâtiments de départ

Deux stratégies possibles :

### Mode A — création immédiate depuis DGFiP

Chaque ligne utile DGFiP devient une ligne dans `buildings`.

### Mode B — affichage source puis création à la demande

Le système affiche d’abord les lignes sources, puis l’utilisateur les transforme en bâtiments.

### Recommandation

Pour votre besoin actuel, je recommande le **Mode A** :

* plus simple à développer,
* plus rapide à démontrer,
* compatible avec votre souhait d’avoir immédiatement une liste ligne par ligne.

---

## 8. Flux fonctionnels

## 8.1 Inscription utilisateur

```text
1. L’utilisateur ouvre la page d’inscription
2. Il saisit prénom, nom, email, mot de passe
3. Il choisit sa ville dans la liste déroulante
4. Le backend crée son compte
5. À la première connexion, l’utilisateur arrive sur Accueil
6. La carte est centrée sur sa ville
```

---

## 8.2 Accueil

```text
1. Lecture de la ville de l’utilisateur
2. Chargement des bâtiments de cette ville
3. Affichage de la carte communale
4. Affichage des marqueurs géolocalisés
5. Résumé :
   - nb bâtiments
   - nb bâtiments nommés
   - nb bâtiments sans coordonnées
   - nb locaux
```

---

## 8.3 Liste des bâtiments

```text
1. L’utilisateur ouvre "Bâtiments"
2. Le backend filtre sur sa ville
3. Le frontend affiche les colonnes :
   - Nom bâtiment
   - Nom de la commune
   - N° voirie
   - Nature voie
   - Nom voie
   - Préfixe
   - Section
   - N° plan
4. Chaque ligne propose :
   - ouvrir la fiche
   - modifier
   - identifier sur carte
```

---

## 8.4 Création manuelle d’un bâtiment

```text
1. L’utilisateur clique "Créer un bâtiment"
2. Il saisit les champs de base
3. Le backend crée le bâtiment
4. Le backend crée automatiquement le local principal
5. Le bâtiment apparaît dans la liste
```

---

## 8.5 Identification sur carte via OSM

```text
1. L’utilisateur ouvre un bâtiment
2. Il clique "Identifier sur carte"
3. Le backend reconstitue l’adresse
4. Géocodage via Nominatim
5. La carte s’ouvre centrée sur la zone
6. L’utilisateur clique sur le bâtiment visible
7. Le frontend envoie le point sélectionné
8. Le backend interroge OSM / Overpass
9. Le backend récupère :
   - coordonnées
   - osm_id
   - type
   - nom éventuel
   - display_name
   - tags
10. Ces informations sont stockées
11. Si un nom OSM existe, il peut être proposé pour remplir le nom bâtiment
```

---

## 9. API REST à prévoir

## 9.1 Auth

* `POST /auth/register`
* `POST /auth/login`
* `GET /auth/me`
* `PUT /auth/me`
* `POST /auth/change-password`

## 9.2 Villes

* `GET /cities`

## 9.3 Bâtiments

* `GET /buildings`
* `POST /buildings`
* `GET /buildings/{id}`
* `PUT /buildings/{id}`
* `DELETE /buildings/{id}` facultatif
* `POST /buildings/{id}/identify-osm`

## 9.4 Locaux

* `GET /buildings/{id}/locals`
* `POST /buildings/{id}/locals`
* `PUT /locals/{id}`
* `DELETE /locals/{id}`

## 9.5 Équipements bâtiments

* `GET /buildings/{id}/equipments`
* `POST /buildings/{id}/equipments`
* `PUT /equipments/{id}`
* `DELETE /equipments/{id}`

## 9.6 Import DGFiP

* `POST /admin/import-dgfip`
* `GET /admin/import-dgfip/status`

---

## 10. Interfaces frontend

## 10.1 Layout

* menu latéral gauche
* dépliable / repliable
* éléments :

  * Accueil
  * Bâtiments
  * Équipements bâtiments
  * Compte utilisateur

## 10.2 Pages

* `/login`
* `/register`
* `/`
* `/buildings`
* `/buildings/:id`
* `/buildings/:id/map`
* `/equipments`
* `/account`

---

## 11. Intégration cartographique

## 11.1 Fond de carte

* OpenStreetMap tiles

## 11.2 Géocodage

* Nominatim pour rechercher l’adresse reconstituée

## 11.3 Sélection bâtiment

Deux options techniques :

### Option simple

Clic sur la carte → récupération point + reverse geocoding

### Option recommandée

Clic sur la carte → interrogation d’objets bâtiment proches via Overpass pour récupérer :

* nom,
* géométrie,
* tags.

### Recommandation

Démarrer en deux temps :

* V1.1 : géocodage + point + stockage coordonnées,
* V1.2 : clic bâtiment enrichi OSM.

Ainsi, le développement est plus robuste.

---

## 12. Environnement de développement

### Recommandation

GitHub Codespaces

L’environnement de développement doit pouvoir être utilisé depuis un navigateur, sans installation locale sur le poste de travail.
Cette contrainte est importante pour un contexte d’ordinateur d’entreprise verrouillé.

### Services exécutés dans le devcontainer distant

* backend FastAPI
* frontend Vite
* PostgreSQL + PostGIS
* pgAdmin facultatif

### Intégration et déploiement continus

* GitHub Actions pour les tests et builds
* déploiement automatisé vers le VPS via SSH

Pas de Redis dans cette version.
Le document précédent le prévoyait pour Celery, mais ce n’est pas utile au MVP ciblé. 

---

## 13. Structure du projet

```text
saas/
├── .github/
│   └── workflows/
│       └── deploy.yml
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── auth/
│   │   │   ├── dgfip/
│   │   │   ├── buildings/
│   │   │   ├── osm/
│   │   │   └── locals/
│   │   └── core/
│   ├── alembic/
│   ├── scripts/
│   │   └── import_dgfip.py
│   └── requirements.txt
│
├── data/
│   ├── raw/
│   │   └── PM_25_B_340.csv
│   └── seeds/
│
├── infra/
│   ├── docker-compose.prod.yml
│   ├── caddy/
│   └── backup/
│
└── .devcontainer/
```

---

## 14. Déploiement

Pour le MVP, prévoir trois niveaux :

### Niveau développement distant

* Codespaces
* exécution du frontend, du backend et de PostgreSQL + PostGIS dans un environnement distant
* aucun prérequis d’installation locale sur le poste utilisateur

### Niveau petite production

* un VPS Linux unique
* déploiement par Docker Compose
* frontend compilé servi en statique via Caddy ou Nginx
* backend FastAPI conteneurisé
* base PostgreSQL + PostGIS sur la même machine
* certificats TLS Let's Encrypt
* sauvegardes automatiques quotidiennes

### Niveau cible future

* architecture portable vers Azure
* frontend migrable vers Azure Static Web Apps
* backend migrable vers Azure Container Apps ou App Service
* base migrable vers Azure Database for PostgreSQL Flexible Server

L’objectif n’est pas de formaliser toute l’infrastructure Azure dès maintenant, mais de conserver une trajectoire de migration simple et sans réécriture majeure.

---

## 15. Hors périmètre volontaire

Ce document ne couvre pas encore :

* organisations multiples par collectivité,
* invitations avancées,
* authentification entreprise,
* ENEDIS,
* OPERAT,
* IA documentaire,
* baux,
* PPI,
* coûts travaux,
* workflows complexes.

---

## 16. Ordre de développement

### Lot 1

* auth
* table cities
* inscription avec choix ville
* compte utilisateur

### Lot 2

* import DGFiP
* liste bâtiments
* création / modification bâtiment

### Lot 3

* fiche bâtiment
* création automatique du local principal
* gestion des locaux

### Lot 4

* carte accueil
* carte bâtiment
* intégration OSM

### Lot 5

* section simple équipements bâtiments