# Module — Gestion technique

> Inventaire des équipements CVC, matériaux d'enveloppe, occupation et programmation.

## Périmètre

| Fonctionnalité roadmap | Statut |
|---|---|
| 2.1 CVC inventaire maintenance | 🟡 Partiel (référentiel + UI génériques, pas filtré CVC) |
| 2.2 Enveloppe inventaire technicien | 🟡 Partiel (même UI partagée avec 2.1) |
| 2.3 Occupation périodes des locaux | 🔴 Todo |
| 2.4 CVC température + programmation | 🔴 Todo |

## Données existantes

### Référentiel SYPEMI — `EquipmentReference`
- Fichier source : `saas/backend/data/durees_vie_powerbi_base_wide.csv` (310 lignes)
- Champs : `id_ligne`, `code_niveau_1`, `libelle_niveau_1`, ..., `code_niveau_5`, `equipement`, `sypemi_mini_annees`, `sypemi_reference_annees`, `sypemi_maxi_annees`, `fiche_cee`
- Import via : `python -m app.scripts.import_equipment_references <csv> --truncate`
- Hiérarchie : niveau 1 sépare CVC / Enveloppe / Électricité / ... → utiliser ce champ pour filtrer côté UI

### Assignations — `BuildingEquipment`
- Une ligne = un équipement installé dans un bâtiment, avec son état et sa quantité
- Champs : `building_id`, `equipment_ref_id`, `etat` (obsolete/degrade/moyen/neuf), `quantite` (faible/moyenne/elevee), `commentaire`, `duree_vie_restante` (calculée)
- Formule durée résiduelle : `sypemi_reference_annees × coefficient_etat`
- Coefficients état : obsolete=0.0, degrade=0.25, moyen=0.5, neuf=1.0 (cf. `schemas/equipment.py` ETAT_COEFFICIENTS)

### Score santé bâtiment
Implémenté dans `services/equipment.py::compute_building_equipment_summary`. Retourne `EquipmentStateCounts` (counts par état + total + `score_sante` 0-1).

## UI actuelle

- **Page** : `/buildings/technique` (`BuildingTechniquePage.tsx`, 627 lignes)
- **Composants** : tableau modal de sélection des équipements + édition inline état/quantité
- **Dark mode** : fixé en PR #10 (badges rgba translucides, fonds neutres)

## Pistes pour scinder CVC / Enveloppe (2.1 vs 2.2)

L'UI actuelle affiche TOUS les équipements ensemble. La grille fonctionnelle demande de séparer.

**Approche minimale** :
1. Ajouter un sélecteur en haut de `BuildingTechniquePage` : "CVC" / "Enveloppe" / "Tous"
2. Filtrer la liste sur `code_niveau_1` ou `libelle_niveau_1`
3. Adapter le titre de la page selon le filtre

**Approche complète** (plus longue) : 2 pages séparées avec deux URLs (`/buildings/technique/cvc` et `/buildings/technique/enveloppe`) et nav latérale.

## Occupation (2.3) — pistes

**Modèle proposé** :
```python
class BuildingOccupancy(Base):
    __tablename__ = "building_occupancies"
    id, building_id, local_id (nullable)
    day_of_week: int  # 0=lundi, 6=dimanche
    start_time: time, end_time: time
    period_label: str  # ex "Cours", "Restauration", "Inoccupé"
    season: str | None  # "hiver", "été", "toute saison"
    notes: str | None
```

**Liaison avec HC/HP** : `BillingHphcSlot` (déjà en BDD via migration 0006) a une structure proche → peut-être mutualiser.

**Insight métier** : croiser conso ENEDIS (par tranche horaire de la CDC) × créneaux d'occupation → repère les surconso "hors présence" (chauffage qui tourne le soir, etc.).

## Température + programmation (2.4) — pistes

Pas de connecteur GTB en France à intégrer en SaaS facilement. MVP envisageable :
- Upload Excel de programmation par bâtiment (consignes par horaire)
- Visualisation côté à côté avec la courbe de charge ENEDIS

À discuter avec utilisateur sur la priorité.

## Routes API

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/equipment/references` | Liste référentiel (310) |
| GET | `/api/equipment/summaries` | Score santé pour tous les bâtiments du tenant |
| GET | `/api/equipment/buildings/{id}` | Équipements d'un bâtiment |
| POST | `/api/equipment/buildings/{id}` | Ajouter un équipement |
| POST | `/api/equipment/buildings/{id}/bulk` | Ajout en masse |
| PUT | `/api/equipment/buildings/{id}/{equipment_id}` | Modifier |
| DELETE | `/api/equipment/buildings/{id}/{equipment_id}` | Supprimer |
| GET | `/api/equipment/buildings/{id}/summary` | Score santé d'un bâtiment |
