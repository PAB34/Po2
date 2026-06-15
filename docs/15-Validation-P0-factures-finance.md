# 15 - Validation P0 factures, decisions et export finance

> Date : 2026-06-15.
> Objectif : certifier progressivement le parcours prioritaire
> `facture -> controle -> decision -> matrice comptable -> export XLSX finance`.

Ce document accompagne la matrice [[13-Matrice-routes-fonctionnalites-refonte-api]].
La matrice contient maintenant deux colonnes de preuve :

- `Statut validation`
- `Preuve`

## 1. Echelle de validation

| Statut | Sens |
|---|---|
| `inventorié` | Endpoint repere, pas encore prouve fonctionnellement. |
| `import app OK` | L'application FastAPI importe et enregistre la route. |
| `test service OK` | Une ou plusieurs briques service sont couvertes par des tests versionnes. |
| `test endpoint HTTP OK` | Un test HTTP appelle l'endpoint. |
| `validé front` | Le parcours a ete verifie depuis l'interface. |
| `validé prod` | Le parcours a ete verifie en production. |
| `à corriger` | Une preuve locale montre un probleme a traiter. |

Regle importante :

```text
Un endpoint ne doit monter de statut que si la preuve existe.
```

## 2. Tests cibles executes

Commande executee depuis `saas/backend` :

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
python -m pytest tests/test_energie_accounting.py tests/test_engie_xlsx_parser.py tests/test_invoice_batches.py tests/test_invoice_analysis_bpu_mapping.py tests/test_billing_bpu_sync.py
```

Resultat :

```text
21 passed
```

Avertissement non bloquant :

```text
PytestCacheWarning sur .pytest_cache
```

## 3. Perimetre energie fournisseurs

### 3.1 Import factures ENGIE XLSX

| Endpoint | Statut actuel | Preuve |
|---|---|---|
| `POST /api/billing/invoices/imports/xlsx` | `test service OK` | `test_engie_xlsx_parser.py` couvre le parsing ENGIE XLSX. |
| `GET /api/billing/invoices/batches` | `test service OK` | `test_invoice_batches.py` couvre les lots et archives. |
| `POST /api/billing/invoices/batches` | `test service OK` | `test_invoice_batches.py` couvre les lots et archives. |

Limite :

```text
La preuve est service/parser, pas encore endpoint HTTP ni front.
```

### 3.2 Controle BPU / analyse facture

| Endpoint | Statut actuel | Preuve |
|---|---|---|
| `POST /api/billing/invoices/imports/{invoice_import_id}/analyze` | `test service OK` | `test_invoice_analysis_bpu_mapping.py` + `test_billing_bpu_sync.py` couvrent des briques BPU. |
| `/api/bpu/*` | `test service OK` | `test_billing_bpu_sync.py` valide le mapping BPU XLSX vers prix courants. |

Limite :

```text
Le controle complet facture -> ecart -> decision doit encore avoir un test bout-en-bout.
```

### 3.3 Matrice comptable energie

| Endpoint | Statut actuel | Preuve |
|---|---|---|
| `POST /api/billing/accounting/import-codification` | `test service OK` | `test_energie_accounting.py` couvre import codification. |
| `GET /api/billing/accounting/site-mappings` | `test service OK` | `test_energie_accounting.py` couvre mappings PRM/site. |
| `GET /api/billing/accounting/nature-rules` | `test service OK` | `test_energie_accounting.py` couvre regles nature comptable. |
| `GET /api/billing/invoices/imports/{invoice_import_id}/codification` | `test service OK` | `test_energie_accounting.py` couvre resolution de codification. |

Limite :

```text
Le parametrage est teste au niveau service. Il faut ajouter un test HTTP et verifier l'ecran front.
```

### 3.4 Export XLSX finance energie

| Endpoint | Statut actuel | Preuve |
|---|---|---|
| `GET /api/billing/invoices/imports/{invoice_import_id}/liaison.xlsx` | `test service OK` | `test_energie_accounting.py::test_build_liaison_workbook` + `::test_liaison_is_tier_agnostic_and_marks_export`. |

Increment P0-a (2026-06-15) livre :

```text
- Liaison tier-agnostique : titre + nom de fichier suivent le fournisseur (ENGIE/EDF/TotalEnergies)
  via supplier_registry, au lieu d'un "ENGIE" code en dur. Meta inclut deja HT et TTC.
- Tracabilite : nouveau champ EnergyInvoiceImport.finance_exported_at (migration 0055), pose a l'export
  (mark_energy_liaison_exported, parite avec mark_finance_liaison_exported cote DALKIA).
- Front : "Transmise finance le ..." sur le detail facture + compteur "X/N transmises" sur l'etape Liaison.
```

Limite :

```text
Pas encore de test HTTP ni de validation front ; export consolide par periode (P0-c) et historique de
decision (P0-b) restent a faire.
```

### 3.5 Decision facture energie

| Endpoint | Statut actuel | Preuve |
|---|---|---|
| `PATCH /api/billing/invoices/imports/{invoice_import_id}/decision` | `import app OK` | Route chargee par l'application, mais test de decision a creer. |

Action suivante :

```text
Creer un test service + HTTP pour valider une facture, bloquer une facture, puis verifier l'historique et l'export.
```

## 4. Perimetre CPE DALKIA

Le CPE DALKIA est dans le coeur P0, mais il ne doit pas etre marque comme certifie tant que les echecs connus ne
sont pas traites.

| Endpoint | Statut actuel | Preuve |
|---|---|---|
| `POST /api/cpe/accounting/import-codification` | `à corriger` | `test_cpe_accounting_import.py::test_enriched_codification_matches_finance_export_lines` echoue : 2047 lignes attendues, 0 matchee. |
| `GET /api/cpe/bilan/{annee}/atterrissage` | `à corriger` | `test_cpe_atterrissage.py` echoue sur DJU/interessement. |
| `GET /api/cpe/dju/{annee}` | `à corriger` | Donnees DJU a corriger selon tests CPE. |
| `GET /api/cpe/finances/market-tracking` | `à corriger` | `test_cpe_market_tracking.py` echoue : bloc DJU sans donnees. |

Conclusion :

```text
Le moteur CPE existe et porte beaucoup de valeur, mais la certification P0 doit commencer par corriger
codification enrichie, DJU et atterrissage avant validation front/prod.
```

## 5. Prochaine etape technique

Ordre recommande :

1. Ajouter des tests HTTP pour le parcours energie :
   - import ou consultation import facture ;
   - analyse facture ;
   - decision ;
   - codification ;
   - export `liaison.xlsx`.
2. Ajouter un test front minimal ou une verification Browser du parcours.
3. Corriger les tests CPE rouges.
4. Seulement ensuite, proposer des routes cible/facades sous `/api/energie/factures`.

