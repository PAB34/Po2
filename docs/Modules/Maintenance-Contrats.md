# Module — Contrats de maintenance

> Gestion des contrats de maintenance, prestataires, lots techniques, échéances, coûts et bâtiments/équipements couverts.

## Périmètre

| Fonctionnalité | Statut |
|---|---|
| Référentiel contrats | 🔴 Todo |
| Upload PDF / pièces contractuelles | 🔴 Todo |
| Affectation multi-bâtiments | 🔴 Todo |
| Affectation optionnelle aux équipements | 🔴 Todo |
| Alertes échéance / préavis | 🔴 Todo |
| Vue bâtiment : contrats applicables | 🔴 Todo |

## Modèle cible

### Contrat

```python
class MaintenanceContract(Base):
    __tablename__ = "maintenance_contracts"
    id, city_id
    supplier_name: str
    contract_number: str | None
    title: str
    lot_code: str | None
    lot_label: str | None
    start_date: date | None
    end_date: date | None
    notice_date: date | None
    annual_amount_eur: float | None
    renewal_type: str | None
    pdf_path: str | None
    notes: str | None
```

### Affectations

```python
class MaintenanceContractBuilding(Base):
    __tablename__ = "maintenance_contract_buildings"
    contract_id: int
    building_id: int
```

Extension future :

```python
class MaintenanceContractEquipment(Base):
    __tablename__ = "maintenance_contract_equipments"
    contract_id: int
    building_equipment_id: int
```

## Lots métier possibles

- CVC ;
- plomberie / sanitaire ;
- électricité courant fort / faible ;
- ascenseurs / appareils élévateurs ;
- sûreté / sécurité ;
- portes automatiques / stores / volets ;
- facilities management ;
- multi-lots.

Ces lots doivent rester configurables : ne pas figer trop tôt une nomenclature fermée.

## UI cible

### Page contrats

- tableau des contrats ;
- filtres : prestataire, lot, échéance, bâtiment, statut ;
- bouton ajout / modification ;
- upload PDF ;
- badges échéance : actif, préavis proche, expiré.

### Fiche bâtiment

- bloc "Contrats de maintenance" listant les contrats applicables ;
- lien vers les pièces PDF ;
- visibilité sur les lots couverts et non couverts.

## MVP conseillé

1. ADR de schéma : contrat + N-N bâtiments.
2. Migration `maintenance_contracts` + table de liaison.
3. Routes CRUD backend.
4. Page frontend `/maintenance` ou onglet dans gestion technique.
5. Affectation à plusieurs bâtiments.
6. Alertes simples sur contrats arrivant à échéance dans 90 jours.

## Dépendances

- `Building` existant ;
- module gestion technique pour rattachement futur aux équipements ;
- stockage de documents déjà utilisé par les factures énergie.
