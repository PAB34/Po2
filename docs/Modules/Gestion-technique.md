# Module — Gestion technique

> Inventaire des équipements CVC, matériaux d'enveloppe, occupation et programmation.

## Périmètre

| Fonctionnalité roadmap | Statut |
|---|---|
| 2.1 CVC inventaire maintenance | 🟡 Partiel (référentiel + UI génériques, pas filtré CVC) |
| 2.2 Enveloppe inventaire technicien | 🟡 Partiel (même UI partagée avec 2.1) |
| 2.3 Occupation périodes des locaux | 🔴 Todo |
| 2.4 CVC température + programmation | 🔴 Todo |
| 2.5 GTB / décret BACS / NF EN ISO 52120 | Futur |
| 2.6 Rattachement compteurs fluides aux bâtiments | 🔴 Todo |
| N.2 Contrats de maintenance | 🔴 Todo |

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

### Inventaire CVC terrain — source utilisateur
- Fichier source : `saas/CVC/listing materiels V2.xlsx` (1301 lignes)
- Colonnes observées : `SITE`, `BATIMENT`, `NIVEAU`, `LOCAL`, `DESIGNATION`, `STATUT`, `ETAT SANTE`, `QTE QTE RELEVEE`, `FAMILLE`, `MARQUE`, `MODELE`, `DATE MES`
- Usage cible : enrichir `BuildingEquipment` ou créer une table d'inventaire terrain plus fine avant rapprochement avec le référentiel SYPEMI.
- Attention : le rattachement `SITE` / `BATIMENT` doit être rapproché du `Building` métier avec score de confiance, pas importé aveuglément.

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

## Fiche bâtiment centrale — vision cible

La gestion technique ne doit pas rester un module isolé. Elle alimente la fiche bâtiment centrale avec :

- les équipements et matériaux ;
- les compteurs fluides associés au bâtiment ;
- les plannings d'occupation et de nettoyage ;
- les consignes et programmations CVC ;
- les contrats de maintenance ;
- les indicateurs réglementaires futurs (OPERAT, BACS/GTB).

Ordre recommandé : rattacher les compteurs -> importer l'occupation -> importer/fiabiliser l'inventaire CVC -> saisir la programmation CVC -> ouvrir le portail usagers -> calculer BACS/GTB.

## Rattachement compteurs fluides (2.6) — pistes

**Objectif** : chaque bâtiment peut être relié à un ou plusieurs compteurs électricité, gaz et eau. Le modèle doit aussi accepter le cas inverse : un compteur alimente plusieurs bâtiments.

**Modèle proposé** :
```python
class BuildingMeterLink(Base):
    __tablename__ = "building_meter_links"
    id, city_id, building_id
    fluid: str  # electricity, gas, water
    meter_identifier: str  # PRM/PDL, PCE, compteur eau
    meter_label: str | None
    usage_label: str | None  # bâtiment, logement, chaufferie, éclairage, annexe...
    share_ratio: float | None  # si compteur partagé
    valid_from: date | None
    valid_to: date | None
    confidence: str  # certain, probable, a_verifier
    validation_status: str  # draft, validated, rejected
    source: str | None  # ENEDIS, facture, terrain, import
```

**Points de vigilance** :
- ne jamais supposer "1 bâtiment = 1 compteur" ;
- gérer les compteurs partagés et les dates de validité ;
- afficher dans la fiche bâtiment les compteurs rattachés, les compteurs orphelins et les bâtiments sans compteur.

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

**Source MVP** : `saas/CVC/PF - Annexe n°9 - Occupation des bâtiments.xlsx` (78 lignes).

Colonnes source :
- `Code`, `Nom du site`, `Lot`, `Occupation`, `Nettoyage`, `Fermetures`, `Responsable`, `Tel`, `Mail`.

**Vision cible portail usagers** :
- les responsables/usagers de bâtiments peuvent proposer ou modifier les plannings ;
- chaque modification conserve un historique, une date d'effet et un commentaire ;
- un statut de validation évite que la donnée opérationnelle parte directement en production ;
- un tiers final/référent patrimoine-énergie reçoit une alerte en cas de modification.

**Liaison avec HC/HP** : `BillingHphcSlot` (déjà en BDD via migration 0006) a une structure proche → peut-être mutualiser.

**Insight métier** : croiser conso ENEDIS (par tranche horaire de la CDC) × créneaux d'occupation → repère les surconso "hors présence" (chauffage qui tourne le soir, etc.).

## Température + programmation (2.4) — pistes

Pas de connecteur GTB en France à intégrer en SaaS facilement. MVP envisageable :
- Upload Excel de programmation par bâtiment (consignes par horaire)
- Visualisation côté à côté avec la courbe de charge ENEDIS

À discuter avec utilisateur sur la priorité.

**Données à prévoir** :
- température confort/réduit ;
- température de départ chaudière ou réseau ;
- loi d'eau si disponible ;
- horaires de chauffe/refroidissement/ventilation ;
- équipement ou zone desservie ;
- saison/période de validité ;
- source et niveau de confiance.

## GTB / BACS / NF EN ISO 52120 — futur

Source : `saas/CVC/TABLEAU 6 NORME NF EN ISO 52120.pdf` (11 pages).

Objectif futur : transformer le tableau 6 en référentiel de données. Quand l'utilisateur sélectionne une typologie de régulation pour une fonction donnée, Po2 doit pouvoir déterminer la contribution à la classe GTB/BAC du bâtiment vis-à-vis du décret BACS.

**Schéma conceptuel cible** :
```python
class BacGtbReferenceFunction(Base):
    __tablename__ = "bac_gtb_reference_functions"
    id
    domain: str  # chauffage, refroidissement, ventilation, ECS, eclairage...
    function_code: str  # ex 1.1, 1.3, 1.4
    function_label: str
    regulation_level: str
    residential_class: str | None  # A/B/C/D si applicable
    non_residential_class: str | None
    applicability_rule: str | None
```

**Principe d'évaluation** :
- un bâtiment n'est pas pénalisé pour une fonction non applicable ;
- la preuve peut venir de l'inventaire CVC, d'un DOE, d'une visite, d'un contrat ou d'une GTB ;
- le résultat doit afficher une classe estimée et un niveau de confiance, pas une certification.

**Priorité** : ne pas démarrer avant d'avoir fiabilisé le rattachement bâtiments/compteurs, l'inventaire CVC terrain et la programmation CVC.

## Contrats de maintenance — pistes

Voir aussi [[Maintenance-Contrats]].

**Modèle proposé** :
```python
class MaintenanceContract(Base):
    __tablename__ = "maintenance_contracts"
    id, city_id
    supplier_name: str
    contract_number: str | None
    lot_label: str | None  # CVC, plomberie, électricité, ascenseurs...
    start_date, end_date, notice_date
    annual_amount_eur: float | None
    renewal_type: str | None
    pdf_path: str | None
```

**Affectations** :
- relation N-N avec `Building` pour les contrats couvrant plusieurs bâtiments ;
- option future : relation N-N avec `BuildingEquipment` pour rattacher un contrat aux équipements couverts.

**MVP conseillé** :
1. CRUD contrats + upload PDF ;
2. affectation à un ou plusieurs bâtiments ;
3. vue des contrats arrivant à échéance / préavis ;
4. affichage dans la fiche bâtiment.

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
