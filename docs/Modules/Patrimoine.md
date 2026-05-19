# Module — Patrimoine

> Inventaire des bâtiments et locaux possédés ou loués par la collectivité.

## Périmètre

| Fonctionnalité roadmap | Statut |
|---|---|
| 1.1 Inventaire bâtiment propriétaire (DGFIP open data) | ✅ Fait |
| 1.2 Inventaire bâtiment locataire (baux PDF) | 🔴 Todo |

## Modèle de données

### `Building` (`saas/backend/app/models/building.py`)
Champs principaux : `id`, `city_id`, `dgfip_*` (source MAJIC), `ign_*` (source IGN), `osm_*` (source OSM), géométrie PostGIS, `nom`, `adresse`, `code_postal`, etc.

### `Local` (`saas/backend/app/models/local.py`)
Sous-unités d'un bâtiment (étages, locaux séparés). Lié à `Building.id`.

### `City` (`saas/backend/app/models/city.py`)
Scope tenant — chaque `User` et `Building` a un `city_id`.

## Workflows existants

### Création / import bâtiment
1. **Page** : `BuildingCreateEditPage` (multi-step)
2. **Service** : `services/building_naming.py` réconcilie un import MAJIC avec :
   - Une recherche IGN par adresse (`fetchBuildingNamingDataset`)
   - Une recherche OSM par bbox géographique
   - Une confirmation utilisateur visuelle via `BuildingNamingMap`
3. **Persistance** : création du `Building` avec tous les `*_source_id` (traçabilité)

### Liste cartographique
- `BuildingsLandingPage` : vue globale carte + filtres
- `BuildingsListPage` : tableau triable
- `BuildingPortfolioMap` : Leaflet avec popups

## Pistes baux locataires (1.2)

À discuter avec utilisateur. Hypothèses de schéma :

**Option A** — Étendre `Local` :
```python
class Local(Base):
    # ... champs existants
    is_rented: Mapped[bool] = mapped_column(Boolean, default=False)
    lease_start: Mapped[date | None]
    lease_end: Mapped[date | None]
    landlord_name: Mapped[str | None]
    lease_pdf_path: Mapped[str | None]
    monthly_rent_eur: Mapped[float | None]
```
✅ Simple. ❌ Mélange propriétaire et locataire dans le même modèle.

**Option B** — Table dédiée `Lease` (relation N-1 vers Local ou Building) :
```python
class Lease(Base):
    __tablename__ = "leases"
    id: Mapped[int]
    building_id: Mapped[int]
    local_id: Mapped[int | None]  # null si bail global sur le bâtiment
    start_date, end_date, landlord_name, monthly_rent, pdf_filename, ...
```
✅ Propre, gère bien les renouvellements. ❌ Plus de complexité immédiate.

**Recommandation par défaut** : Option B (table dédiée). Permet l'historique des baux.

### Parser PDF bail
- Réutiliser l'architecture `services/bpu.py` (pdftotext + regex tolérante + OCR fallback)
- Champs à extraire : nom bailleur, dates, loyer mensuel, surface, adresse
- Stocker `raw_text` pour re-parsing futur (pattern du BPU)

## Routes API

| Méthode | Route | Service |
|---|---|---|
| GET | `/api/buildings` | `list_buildings` |
| GET | `/api/buildings/{id}` | `get_building` |
| POST | `/api/buildings` | `create_building_from_naming` |
| PATCH | `/api/buildings/{id}` | `update_building` |
| POST | `/api/buildings/import/preview` | `preview_building_import_file` |
| POST | `/api/buildings/import/execute` | `execute_building_import_file` |
| GET | `/api/buildings/{id}/locals` | `list_building_locals` |
| POST | `/api/buildings/{id}/locals` | `create_local` |
| GET | `/api/cities` | `list_cities` |
