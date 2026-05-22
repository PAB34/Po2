# Module — Contrats de maintenance

> Gestion des contrats de maintenance, prestataires, lots techniques, échéances, coûts et bâtiments/équipements couverts.

## Périmètre

| Fonctionnalité | Statut |
|---|---|
| Référentiel contrats | 🔴 Todo |
| Upload PDF / pièces contractuelles | 🔴 Todo |
| Affectation multi-référents patrimoine | 🔴 Todo |
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

Le contrat ne doit pas fabriquer sa propre liste de sites. Il doit viser le référentiel patrimoine maître défini dans [[Decisions/008-referentiel-patrimoine-et-rapprochements]].

La V1 peut commencer par les bâtiments si le premier lot de données le justifie, mais le cadrage métier attendu est :

- contrat applicable à un `Site` complet ;
- contrat applicable à un `Building` précis ;
- contrat applicable à un `Local` si le périmètre est fin ;
- équipement couvert en complément quand le module technique l'exige.

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
- héritage visible si un contrat est affecté au `Site` parent ;
- lien vers les pièces PDF ;
- visibilité sur les lots couverts et non couverts.

## MVP conseillé

1. S'appuyer sur l'ADR référentiel patrimoine puis trancher le premier lien technique : `Site`, `Building`, `Local` ou table de scope polymorphe.
2. Migration `maintenance_contracts` + table de liaison.
3. Routes CRUD backend.
4. Page frontend `/maintenance` ou onglet dans gestion technique.
5. Affectation à plusieurs bâtiments.
6. Alertes simples sur contrats arrivant à échéance dans 90 jours.

## Dépendances

- `Building` existant ;
- module gestion technique pour rattachement futur aux équipements ;
- stockage de documents déjà utilisé par les factures énergie.
