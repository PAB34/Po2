# 13 - Matrice routes, fonctionnalites et refonte API

> Document genere par `python -m app.scripts.build_api_catalog`.
> Ne pas editer les tables endpoint a la main : corriger le generateur ou les annotations source.

## 1. Objectif

Attacher chaque endpoint existant a son code, sa fonctionnalite actuelle, son domaine cible et son prefixe cible.
Cette matrice sert a preparer la refonte progressive de l'API et de l'UX sans perdre ce qui a deja ete developpe.

## 2. Synthese par routeur

| Routeur actuel | Endpoints | Domaine cible dominant | Prefixe cible dominant | Fonctionnalite actuelle |
|---|---:|---|---|---|
| `auth` | 5 | Administration / socle | `/api/auth` | connexion, profil, mot de passe |
| `billing` | 38 | Energie / finance | `/api/energie/factures` | factures fournisseurs, controles, decisions, export finance |
| `bpu` | 22 | Energie / referentiels | `/api/energie/prix` | BPU, TURPE, prix contractuels |
| `buildings` | 31 | Patrimoine | `/api/patrimoine` | sites, batiments, locaux, rattachements |
| `cities` | 1 | Administration / socle | `/api/admin/villes` | ville et tenant |
| `cpe` | 56 | Marches & contrats | `/api/marches/cpe-dalkia` | CPE DALKIA, finances, controles, consommations |
| `cpe-dalkia` | 21 | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` | referentiel contractuel DALKIA |
| `cvc` | 20 | Technique | `/api/technique/cvc` | inventaire CVC, matching, F-Gaz, ESP |
| `energie` | 13 | Energie | `/api/energie/consommations` | consommations, PRM, DJU, preconisations |
| `energie-async` | 6 | Administration / connecteurs | `/api/admin/connecteurs/enedis/async` | jobs async ENEDIS |
| `energie-sync` | 11 | Energie / admin donnees | `/api/energie/distributeurs/enedis` | acquisition ENEDIS et DJU |
| `engie` | 24 | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` | proxy API ENGIE potentiel |
| `equipment` | 8 | Technique | `/api/technique/equipements` | referentiel SYPEMI et equipements |
| `grdf` | 8 | Energie gaz | `/api/energie/distributeurs/grdf` | PCE, consommations gaz, GRDF |
| `health` | 1 | Administration / diagnostics | `/api/admin/diagnostics` | sante technique |
| `internal` | 1 | Technique interne | `/api/internal` | authentification interne |
| `pronostics` | 13 | Hors produit | `(hors plateforme)` | jeu hors plateforme, ne pas integrer |

## 3. Matrice detaillee

### `auth`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `POST /api/auth/change-password` | `saas/backend/app/api/routes/auth.py:77` | auth, building_naming, cities | connexion, profil, mot de passe | Administration / socle | `/api/auth` |
| `POST /api/auth/login` | `saas/backend/app/api/routes/auth.py:50` | auth, building_naming, cities | connexion, profil, mot de passe | Administration / socle | `/api/auth` |
| `GET /api/auth/me` | `saas/backend/app/api/routes/auth.py:62` | auth, building_naming, cities | connexion, profil, mot de passe | Administration / socle | `/api/auth` |
| `PUT /api/auth/me` | `saas/backend/app/api/routes/auth.py:67` | auth, building_naming, cities | connexion, profil, mot de passe | Administration / socle | `/api/auth` |
| `POST /api/auth/register` | `saas/backend/app/api/routes/auth.py:22` | auth, building_naming, cities | connexion, profil, mot de passe | Administration / socle | `/api/auth` |

### `billing`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `POST /api/billing/accounting/import-codification` | `saas/backend/app/api/routes/billing.py:672` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/accounting/nature-rules` | `saas/backend/app/api/routes/billing.py:746` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `POST /api/billing/accounting/nature-rules` | `saas/backend/app/api/routes/billing.py:754` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `DELETE /api/billing/accounting/nature-rules/{rule_id}` | `saas/backend/app/api/routes/billing.py:778` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `PATCH /api/billing/accounting/nature-rules/{rule_id}` | `saas/backend/app/api/routes/billing.py:764` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/accounting/site-mappings` | `saas/backend/app/api/routes/billing.py:700` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `POST /api/billing/accounting/site-mappings` | `saas/backend/app/api/routes/billing.py:708` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `POST /api/billing/accounting/site-mappings/bootstrap` | `saas/backend/app/api/routes/billing.py:691` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `DELETE /api/billing/accounting/site-mappings/{mapping_id}` | `saas/backend/app/api/routes/billing.py:732` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `PATCH /api/billing/accounting/site-mappings/{mapping_id}` | `saas/backend/app/api/routes/billing.py:718` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/configs` | `saas/backend/app/api/routes/billing.py:97` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `PUT /api/billing/configs/supplier/{supplier}` | `saas/backend/app/api/routes/billing.py:114` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `DELETE /api/billing/configs/{config_id}` | `saas/backend/app/api/routes/billing.py:144` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `PATCH /api/billing/configs/{config_id}` | `saas/backend/app/api/routes/billing.py:132` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/configs/{config_id}/bpu-lines` | `saas/backend/app/api/routes/billing.py:202` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `PUT /api/billing/configs/{config_id}/bpu-lines` | `saas/backend/app/api/routes/billing.py:213` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `POST /api/billing/configs/{config_id}/bpu-lines/sync` | `saas/backend/app/api/routes/billing.py:225` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/configs/{config_id}/hphc-slots` | `saas/backend/app/api/routes/billing.py:179` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `PUT /api/billing/configs/{config_id}/hphc-slots` | `saas/backend/app/api/routes/billing.py:190` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/configs/{config_id}/prices` | `saas/backend/app/api/routes/billing.py:156` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `PUT /api/billing/configs/{config_id}/prices` | `saas/backend/app/api/routes/billing.py:167` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/invoices/batches` | `saas/backend/app/api/routes/billing.py:308` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `POST /api/billing/invoices/batches` | `saas/backend/app/api/routes/billing.py:330` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/invoices/batches/{batch_id}` | `saas/backend/app/api/routes/billing.py:317` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/invoices/consumption-monthly` | `saas/backend/app/api/routes/billing.py:262` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `DELETE /api/billing/invoices/imports` | `saas/backend/app/api/routes/billing.py:633` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/invoices/imports` | `saas/backend/app/api/routes/billing.py:253` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `POST /api/billing/invoices/imports` | `saas/backend/app/api/routes/billing.py:374` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `POST /api/billing/invoices/imports/edf-csv` | `saas/backend/app/api/routes/billing.py:511` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `POST /api/billing/invoices/imports/xlsx` | `saas/backend/app/api/routes/billing.py:389` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `DELETE /api/billing/invoices/imports/{invoice_import_id}` | `saas/backend/app/api/routes/billing.py:620` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/invoices/imports/{invoice_import_id}` | `saas/backend/app/api/routes/billing.py:340` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `POST /api/billing/invoices/imports/{invoice_import_id}/analyze` | `saas/backend/app/api/routes/billing.py:654` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/invoices/imports/{invoice_import_id}/codification` | `saas/backend/app/api/routes/billing.py:792` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `PATCH /api/billing/invoices/imports/{invoice_import_id}/decision` | `saas/backend/app/api/routes/billing.py:353` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/invoices/imports/{invoice_import_id}/liaison.xlsx` | `saas/backend/app/api/routes/billing.py:820` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/supplier-groups` | `saas/backend/app/api/routes/billing.py:88` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |
| `GET /api/billing/turpe/versions` | `saas/backend/app/api/routes/billing.py:106` | billing, billing_bpu_sync, edf_csv_import, energie_accounting, engie_xlsx_import, invoices, turpe | factures fournisseurs, controles, decisions, export finance | Energie / finance | `/api/energie/factures` |

### `bpu`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `POST /api/bpu/charges` | `saas/backend/app/api/routes/bpu.py:739` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `DELETE /api/bpu/charges/{charge_id}` | `saas/backend/app/api/routes/bpu.py:772` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `PATCH /api/bpu/charges/{charge_id}` | `saas/backend/app/api/routes/bpu.py:755` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `POST /api/bpu/components` | `saas/backend/app/api/routes/bpu.py:667` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `DELETE /api/bpu/components/{component_id}` | `saas/backend/app/api/routes/bpu.py:720` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `PATCH /api/bpu/components/{component_id}` | `saas/backend/app/api/routes/bpu.py:687` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `GET /api/bpu/documents` | `saas/backend/app/api/routes/bpu.py:171` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `DELETE /api/bpu/documents/{document_id}` | `saas/backend/app/api/routes/bpu.py:225` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `GET /api/bpu/documents/{document_id}` | `saas/backend/app/api/routes/bpu.py:203` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `PATCH /api/bpu/documents/{document_id}` | `saas/backend/app/api/routes/bpu.py:533` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `GET /api/bpu/editable-rows` | `saas/backend/app/api/routes/bpu.py:460` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `GET /api/bpu/formula` | `saas/backend/app/api/routes/bpu.py:154` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `POST /api/bpu/import` | `saas/backend/app/api/routes/bpu.py:353` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `POST /api/bpu/import-xlsx` | `saas/backend/app/api/routes/bpu.py:417` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `POST /api/bpu/periods` | `saas/backend/app/api/routes/bpu.py:611` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `DELETE /api/bpu/periods/{period_id}` | `saas/backend/app/api/routes/bpu.py:648` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `PATCH /api/bpu/periods/{period_id}` | `saas/backend/app/api/routes/bpu.py:631` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `POST /api/bpu/segments` | `saas/backend/app/api/routes/bpu.py:555` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `DELETE /api/bpu/segments/{segment_id}` | `saas/backend/app/api/routes/bpu.py:592` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `PATCH /api/bpu/segments/{segment_id}` | `saas/backend/app/api/routes/bpu.py:575` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `GET /api/bpu/timeline` | `saas/backend/app/api/routes/bpu.py:244` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |
| `GET /api/bpu/turpe-evolution` | `saas/backend/app/api/routes/bpu.py:335` | billing_bpu_sync, bpu, turpe | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix` |

### `buildings`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `DELETE /api/buildings` | `saas/backend/app/api/routes/buildings.py:198` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings` | `saas/backend/app/api/routes/buildings.py:207` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings` | `saas/backend/app/api/routes/buildings.py:276` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/import/preview` | `saas/backend/app/api/routes/buildings.py:158` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings/locals` | `saas/backend/app/api/routes/buildings.py:223` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/lookup/free-address` | `saas/backend/app/api/routes/buildings.py:137` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings/meters/matching` | `saas/backend/app/api/routes/buildings.py:466` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/meters/matching/apply` | `saas/backend/app/api/routes/buildings.py:475` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings/naming/dataset` | `saas/backend/app/api/routes/buildings.py:87` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/naming/selection` | `saas/backend/app/api/routes/buildings.py:185` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings/naming/{unique_key}` | `saas/backend/app/api/routes/buildings.py:124` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings/sites` | `saas/backend/app/api/routes/buildings.py:215` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/sites` | `saas/backend/app/api/routes/buildings.py:232` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `DELETE /api/buildings/sites/{site_id}` | `saas/backend/app/api/routes/buildings.py:254` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `PUT /api/buildings/sites/{site_id}` | `saas/backend/app/api/routes/buildings.py:242` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/sites/{site_id}/reclassify` | `saas/backend/app/api/routes/buildings.py:265` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `DELETE /api/buildings/{building_id}` | `saas/backend/app/api/routes/buildings.py:308` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings/{building_id}` | `saas/backend/app/api/routes/buildings.py:286` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `PUT /api/buildings/{building_id}` | `saas/backend/app/api/routes/buildings.py:296` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/{building_id}/geo-attachment` | `saas/backend/app/api/routes/buildings.py:330` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/{building_id}/ign-attachment` | `saas/backend/app/api/routes/buildings.py:345` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings/{building_id}/locals` | `saas/backend/app/api/routes/buildings.py:404` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/{building_id}/locals` | `saas/backend/app/api/routes/buildings.py:414` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `DELETE /api/buildings/{building_id}/locals/{local_id}` | `saas/backend/app/api/routes/buildings.py:440` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `PUT /api/buildings/{building_id}/locals/{local_id}` | `saas/backend/app/api/routes/buildings.py:426` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/{building_id}/locals/{local_id}/reclassify` | `saas/backend/app/api/routes/buildings.py:453` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings/{building_id}/meters` | `saas/backend/app/api/routes/buildings.py:485` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/{building_id}/meters` | `saas/backend/app/api/routes/buildings.py:495` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `DELETE /api/buildings/{building_id}/meters/{meter_link_id}` | `saas/backend/app/api/routes/buildings.py:507` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `GET /api/buildings/{building_id}/nearby-dgfip` | `saas/backend/app/api/routes/buildings.py:357` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |
| `POST /api/buildings/{building_id}/reclassify` | `saas/backend/app/api/routes/buildings.py:319` | building_naming, buildings, cities, meter_matching | sites, batiments, locaux, rattachements | Patrimoine | `/api/patrimoine` |

### `cities`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `GET /api/cities` | `saas/backend/app/api/routes/cities.py:11` | cities | ville et tenant | Administration / socle | `/api/admin/villes` |

### `cpe`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `POST /api/cpe/accounting/import-codification` | `saas/backend/app/api/routes/cpe.py:205` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/accounting/nature-rules` | `saas/backend/app/api/routes/cpe.py:223` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/accounting/nature-rules` | `saas/backend/app/api/routes/cpe.py:232` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `DELETE /api/cpe/accounting/nature-rules/{rule_id}` | `saas/backend/app/api/routes/cpe.py:258` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `PATCH /api/cpe/accounting/nature-rules/{rule_id}` | `saas/backend/app/api/routes/cpe.py:244` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/accounting/site-mappings` | `saas/backend/app/api/routes/cpe.py:318` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/accounting/site-mappings` | `saas/backend/app/api/routes/cpe.py:327` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `DELETE /api/cpe/accounting/site-mappings/{mapping_id}` | `saas/backend/app/api/routes/cpe.py:353` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `PATCH /api/cpe/accounting/site-mappings/{mapping_id}` | `saas/backend/app/api/routes/cpe.py:339` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/bilan/{annee}` | `saas/backend/app/api/routes/cpe.py:765` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/bilan/{annee}/atterrissage` | `saas/backend/app/api/routes/cpe.py:807` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/bilan/{annee}/calculer` | `saas/backend/app/api/routes/cpe.py:732` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/bilan/{annee}/elec-performance` | `saas/backend/app/api/routes/cpe.py:791` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/bilan/{annee}/p24-objective` | `saas/backend/app/api/routes/cpe.py:775` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/consommations/synthese/{annee}` | `saas/backend/app/api/routes/cpe.py:183` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/contract-references` | `saas/backend/app/api/routes/cpe.py:271` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/contract-references` | `saas/backend/app/api/routes/cpe.py:280` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `DELETE /api/cpe/contract-references/{reference_id}` | `saas/backend/app/api/routes/cpe.py:305` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `PATCH /api/cpe/contract-references/{reference_id}` | `saas/backend/app/api/routes/cpe.py:291` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/dju/{annee}` | `saas/backend/app/api/routes/cpe.py:717` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/batches` | `saas/backend/app/api/routes/cpe.py:419` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/finances/controls/recalculate` | `saas/backend/app/api/routes/cpe.py:568` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/controls/report` | `saas/backend/app/api/routes/cpe.py:558` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/controls/report.xlsx` | `saas/backend/app/api/routes/cpe.py:578` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/finances/evidences/{evidence_id}/apply-declared-indices` | `saas/backend/app/api/routes/cpe.py:542` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `DELETE /api/cpe/finances/history` | `saas/backend/app/api/routes/cpe.py:438` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/finances/import` | `saas/backend/app/api/routes/cpe.py:366` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/invoices` | `saas/backend/app/api/routes/cpe.py:428` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `PATCH /api/cpe/finances/invoices/{invoice_id}` | `saas/backend/app/api/routes/cpe.py:649` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/invoices/{invoice_id}/controls` | `saas/backend/app/api/routes/cpe.py:623` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/finances/invoices/{invoice_id}/controls/recalculate` | `saas/backend/app/api/routes/cpe.py:636` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/finances/invoices/{invoice_id}/evidence-pdf` | `saas/backend/app/api/routes/cpe.py:519` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/invoices/{invoice_id}/liaison.xlsx` | `saas/backend/app/api/routes/cpe.py:663` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/invoices/{invoice_id}/lines` | `saas/backend/app/api/routes/cpe.py:447` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/market-tracking` | `saas/backend/app/api/routes/cpe.py:592` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/market-tracking.xlsx` | `saas/backend/app/api/routes/cpe.py:605` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/p3-devis` | `saas/backend/app/api/routes/cpe.py:398` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/finances/p3-devis/atterrissage` | `saas/backend/app/api/routes/cpe.py:408` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/finances/p3-devis/import` | `saas/backend/app/api/routes/cpe.py:384` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/finances/preview` | `saas/backend/app/api/routes/cpe.py:193` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/import/csv` | `saas/backend/app/api/routes/cpe.py:167` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/prix-gaz` | `saas/backend/app/api/routes/cpe.py:699` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/prix-gaz/{annee}` | `saas/backend/app/api/routes/cpe.py:683` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/revision-evidences` | `saas/backend/app/api/routes/cpe.py:491` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/revision-evidences` | `saas/backend/app/api/routes/cpe.py:500` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/revision-indices` | `saas/backend/app/api/routes/cpe.py:460` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/revision-indices` | `saas/backend/app/api/routes/cpe.py:470` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/revision-observations` | `saas/backend/app/api/routes/cpe.py:482` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/sites` | `saas/backend/app/api/routes/cpe.py:69` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/sites` | `saas/backend/app/api/routes/cpe.py:79` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/sites/{site_id}` | `saas/backend/app/api/routes/cpe.py:91` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `PATCH /api/cpe/sites/{site_id}` | `saas/backend/app/api/routes/cpe.py:103` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/sites/{site_id}/bilan/{annee}/calculer` | `saas/backend/app/api/routes/cpe.py:751` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/sites/{site_id}/consommations` | `saas/backend/app/api/routes/cpe.py:132` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `GET /api/cpe/sites/{site_id}/releves` | `saas/backend/app/api/routes/cpe.py:119` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |
| `POST /api/cpe/sites/{site_id}/releves` | `saas/backend/app/api/routes/cpe.py:152` | cpe, cpe_accounting, cpe_atterrissage, cpe_finance_preview, cpe_import, cpe_market_tracking, cpe_p3_devis | CPE DALKIA, finances, controles, consommations | Marches & contrats | `/api/marches/cpe-dalkia` |

### `cpe-dalkia`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `GET /api/cpe/dalkia-ref/active-summary` | `saas/backend/app/api/routes/cpe_dalkia.py:295` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `POST /api/cpe/dalkia-ref/confirm` | `saas/backend/app/api/routes/cpe_dalkia.py:211` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `POST /api/cpe/dalkia-ref/dpgf-p1/confirm` | `saas/backend/app/api/routes/cpe_dalkia.py:506` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/dpgf-p1/imports` | `saas/backend/app/api/routes/cpe_dalkia.py:560` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/dpgf-p1/imports/all` | `saas/backend/app/api/routes/cpe_dalkia.py:569` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `PATCH /api/cpe/dalkia-ref/dpgf-p1/imports/{import_id}/acte` | `saas/backend/app/api/routes/cpe_dalkia.py:543` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/dpgf-p1/imports/{import_id}/diff` | `saas/backend/app/api/routes/cpe_dalkia.py:322` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `POST /api/cpe/dalkia-ref/dpgf-p1/preview` | `saas/backend/app/api/routes/cpe_dalkia.py:480` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/imports` | `saas/backend/app/api/routes/cpe_dalkia.py:240` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/imports/all` | `saas/backend/app/api/routes/cpe_dalkia.py:285` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `PATCH /api/cpe/dalkia-ref/imports/{import_id}/acte` | `saas/backend/app/api/routes/cpe_dalkia.py:249` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/imports/{import_id}/ape` | `saas/backend/app/api/routes/cpe_dalkia.py:383` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/imports/{import_id}/bpu` | `saas/backend/app/api/routes/cpe_dalkia.py:425` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/imports/{import_id}/cibles` | `saas/backend/app/api/routes/cpe_dalkia.py:368` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/imports/{import_id}/diff` | `saas/backend/app/api/routes/cpe_dalkia.py:310` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/imports/{import_id}/p2p3` | `saas/backend/app/api/routes/cpe_dalkia.py:354` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/imports/{import_id}/recap` | `saas/backend/app/api/routes/cpe_dalkia.py:396` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `GET /api/cpe/dalkia-ref/imports/{import_id}/sites` | `saas/backend/app/api/routes/cpe_dalkia.py:333` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `POST /api/cpe/dalkia-ref/imports/{import_id}/sync-p1-reference` | `saas/backend/app/api/routes/cpe_dalkia.py:579` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `POST /api/cpe/dalkia-ref/preview` | `saas/backend/app/api/routes/cpe_dalkia.py:165` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |
| `POST /api/cpe/dalkia-ref/sync-cpe-sites` | `saas/backend/app/api/routes/cpe_dalkia.py:439` | cpe_dalkia_db, cpe_dalkia_diff, cpe_dalkia_import, cpe_dpgf_p1 | referentiel contractuel DALKIA | Marches & contrats / admin expert | `/api/marches/cpe-dalkia/referentiel` |

### `cvc`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `GET /api/cvc/buildings/{building_id}` | `saas/backend/app/api/routes/cvc.py:150` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `DELETE /api/cvc/buildings/{building_id}/items` | `saas/backend/app/api/routes/cvc.py:176` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `POST /api/cvc/import` | `saas/backend/app/api/routes/cvc.py:79` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `GET /api/cvc/imports` | `saas/backend/app/api/routes/cvc.py:102` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `GET /api/cvc/imports/{import_batch}/items` | `saas/backend/app/api/routes/cvc.py:110` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `POST /api/cvc/imports/{import_batch}/recompute-references` | `saas/backend/app/api/routes/cvc.py:119` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `PATCH /api/cvc/imports/{import_batch}/site-mappings` | `saas/backend/app/api/routes/cvc.py:137` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `GET /api/cvc/imports/{import_batch}/site-matches` | `saas/backend/app/api/routes/cvc.py:128` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `DELETE /api/cvc/items/{item_id}` | `saas/backend/app/api/routes/cvc.py:187` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `PATCH /api/cvc/items/{item_id}` | `saas/backend/app/api/routes/cvc.py:160` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `POST /api/cvc/match-buildings` | `saas/backend/app/api/routes/cvc.py:70` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `POST /api/cvc/preview` | `saas/backend/app/api/routes/cvc.py:58` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `GET /api/cvc/refrigerants/dashboard` | `saas/backend/app/api/routes/cvc.py:220` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `POST /api/cvc/refrigerants/import` | `saas/backend/app/api/routes/cvc.py:199` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `GET /api/cvc/refrigerants/imports` | `saas/backend/app/api/routes/cvc.py:212` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `GET /api/cvc/refrigerants/imports/{import_batch}/items` | `saas/backend/app/api/routes/cvc.py:228` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `PATCH /api/cvc/refrigerants/items/{item_id}` | `saas/backend/app/api/routes/cvc.py:237` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `GET /api/cvc/source-building-mappings` | `saas/backend/app/api/routes/cvc.py:253` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `PATCH /api/cvc/source-building-mappings/{mapping_id}` | `saas/backend/app/api/routes/cvc.py:263` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |
| `GET /api/cvc/technical-report` | `saas/backend/app/api/routes/cvc.py:279` | buildings, cvc | inventaire CVC, matching, F-Gaz, ESP | Technique | `/api/technique/cvc` |

### `energie`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `GET /api/energie` | `saas/backend/app/api/routes/energie.py:39` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/data-audit` | `saas/backend/app/api/routes/energie.py:52` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/data-ranges` | `saas/backend/app/api/routes/energie.py:47` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/dju/monthly` | `saas/backend/app/api/routes/energie.py:57` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/preconisations` | `saas/backend/app/api/routes/energie.py:64` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/{prm_id}` | `saas/backend/app/api/routes/energie.py:89` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/{prm_id}/annual-profile` | `saas/backend/app/api/routes/energie.py:117` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/{prm_id}/daily-consumption` | `saas/backend/app/api/routes/energie.py:125` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/{prm_id}/dju-performance` | `saas/backend/app/api/routes/energie.py:134` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/{prm_id}/dju-seasonal` | `saas/backend/app/api/routes/energie.py:142` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/{prm_id}/load-curve` | `saas/backend/app/api/routes/energie.py:108` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/{prm_id}/max-power` | `saas/backend/app/api/routes/energie.py:100` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |
| `GET /api/energie/{prm_id}/preconisation` | `saas/backend/app/api/routes/energie.py:75` | energie, power_real_costs, power_recommendations | consommations, PRM, DJU, preconisations | Energie | `/api/energie/consommations` |

### `energie-async`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `POST /api/energie/sync/async/backfill-full` | `saas/backend/app/api/routes/enedis_async.py:178` | enedis_async | jobs async ENEDIS | Administration / connecteurs | `/api/admin/connecteurs/enedis/async` |
| `GET /api/energie/sync/async/jobs` | `saas/backend/app/api/routes/enedis_async.py:210` | enedis_async | jobs async ENEDIS | Administration / connecteurs | `/api/admin/connecteurs/enedis/async` |
| `GET /api/energie/sync/async/jobs/summary` | `saas/backend/app/api/routes/enedis_async.py:236` | enedis_async | jobs async ENEDIS | Administration / connecteurs | `/api/admin/connecteurs/enedis/async` |
| `GET /api/energie/sync/async/jobs/{job_id}` | `saas/backend/app/api/routes/enedis_async.py:302` | enedis_async | jobs async ENEDIS | Administration / connecteurs | `/api/admin/connecteurs/enedis/async` |
| `POST /api/energie/sync/async/poll-now` | `saas/backend/app/api/routes/enedis_async.py:314` | enedis_async | jobs async ENEDIS | Administration / connecteurs | `/api/admin/connecteurs/enedis/async` |
| `POST /api/energie/sync/async/start` | `saas/backend/app/api/routes/enedis_async.py:119` | enedis_async | jobs async ENEDIS | Administration / connecteurs | `/api/admin/connecteurs/enedis/async` |

### `energie-sync`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `POST /api/energie/sync/customer/start` | `saas/backend/app/api/routes/enedis_sync.py:190` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `GET /api/energie/sync/customer/status` | `saas/backend/app/api/routes/enedis_sync.py:185` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `GET /api/energie/sync/diagnostics/{source}` | `saas/backend/app/api/routes/enedis_sync.py:212` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `POST /api/energie/sync/dju/start` | `saas/backend/app/api/routes/enedis_sync.py:170` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `GET /api/energie/sync/dju/status` | `saas/backend/app/api/routes/enedis_sync.py:165` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `POST /api/energie/sync/load-curve/start` | `saas/backend/app/api/routes/enedis_sync.py:138` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `GET /api/energie/sync/load-curve/status` | `saas/backend/app/api/routes/enedis_sync.py:133` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `POST /api/energie/sync/max-power/start` | `saas/backend/app/api/routes/enedis_sync.py:101` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `GET /api/energie/sync/max-power/status` | `saas/backend/app/api/routes/enedis_sync.py:96` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `POST /api/energie/sync/start` | `saas/backend/app/api/routes/enedis_sync.py:78` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |
| `GET /api/energie/sync/status` | `saas/backend/app/api/routes/enedis_sync.py:73` | dju_sync, enedis_customer_sync, enedis_sync | acquisition ENEDIS et DJU | Energie / admin donnees | `/api/energie/distributeurs/enedis` |

### `engie`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `GET /api/engie/consommations` | `saas/backend/app/api/routes/engie.py:179` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/consommations/foisonne` | `saas/backend/app/api/routes/engie.py:205` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/consommations/site/{site_id}/index` | `saas/backend/app/api/routes/engie.py:275` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/consommations/site/{uid}/courbe-de-charge` | `saas/backend/app/api/routes/engie.py:229` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/consommations/site/{uid}/energie-reactive` | `saas/backend/app/api/routes/engie.py:245` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/consommations/site/{uid}/puissance-souscrite` | `saas/backend/app/api/routes/engie.py:260` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/contrats` | `saas/backend/app/api/routes/engie.py:153` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/contrats/{uid}/sites` | `saas/backend/app/api/routes/engie.py:165` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/demandes` | `saas/backend/app/api/routes/engie.py:368` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/demandes/categories` | `saas/backend/app/api/routes/engie.py:381` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/demandes/{uid}` | `saas/backend/app/api/routes/engie.py:390` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/factures` | `saas/backend/app/api/routes/engie.py:295` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/factures/{uid}` | `saas/backend/app/api/routes/engie.py:321` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/factures/{uid}/details` | `saas/backend/app/api/routes/engie.py:335` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/factures/{uid}/fichier` | `saas/backend/app/api/routes/engie.py:349` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/groupes` | `saas/backend/app/api/routes/engie.py:130` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/groupes/{uid}` | `saas/backend/app/api/routes/engie.py:139` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/profil` | `saas/backend/app/api/routes/engie.py:38` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/profils` | `saas/backend/app/api/routes/engie.py:47` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/sites` | `saas/backend/app/api/routes/engie.py:61` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/sites/{uid}` | `saas/backend/app/api/routes/engie.py:83` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/sites/{uid}/details` | `saas/backend/app/api/routes/engie.py:92` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/sites/{uid}/details-v2` | `saas/backend/app/api/routes/engie.py:101` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |
| `GET /api/engie/sites/{uid}/programmation-horaire` | `saas/backend/app/api/routes/engie.py:110` | engie_client | proxy API ENGIE potentiel | Administration / connecteurs en attente | `/api/admin/connecteurs/engie` |

### `equipment`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `GET /api/equipment/buildings/{building_id}` | `saas/backend/app/api/routes/equipment.py:56` | buildings, equipment | referentiel SYPEMI et equipements | Technique | `/api/technique/equipements` |
| `POST /api/equipment/buildings/{building_id}` | `saas/backend/app/api/routes/equipment.py:67` | buildings, equipment | referentiel SYPEMI et equipements | Technique | `/api/technique/equipements` |
| `POST /api/equipment/buildings/{building_id}/bulk` | `saas/backend/app/api/routes/equipment.py:82` | buildings, equipment | referentiel SYPEMI et equipements | Technique | `/api/technique/equipements` |
| `GET /api/equipment/buildings/{building_id}/summary` | `saas/backend/app/api/routes/equipment.py:128` | buildings, equipment | referentiel SYPEMI et equipements | Technique | `/api/technique/equipements` |
| `DELETE /api/equipment/buildings/{building_id}/{equipment_id}` | `saas/backend/app/api/routes/equipment.py:113` | buildings, equipment | referentiel SYPEMI et equipements | Technique | `/api/technique/equipements` |
| `PUT /api/equipment/buildings/{building_id}/{equipment_id}` | `saas/backend/app/api/routes/equipment.py:97` | buildings, equipment | referentiel SYPEMI et equipements | Technique | `/api/technique/equipements` |
| `GET /api/equipment/references` | `saas/backend/app/api/routes/equipment.py:32` | buildings, equipment | referentiel SYPEMI et equipements | Technique | `/api/technique/equipements` |
| `GET /api/equipment/summaries` | `saas/backend/app/api/routes/equipment.py:41` | buildings, equipment | referentiel SYPEMI et equipements | Technique | `/api/technique/equipements` |

### `grdf`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `POST /api/grdf/conso/backfill` | `saas/backend/app/api/routes/grdf.py:85` | gas_analytics, grdf_conso, grdf_contractuel, grdf_gda | PCE, consommations gaz, GRDF | Energie gaz | `/api/energie/distributeurs/grdf` |
| `GET /api/grdf/conso/monthly` | `saas/backend/app/api/routes/grdf.py:152` | gas_analytics, grdf_conso, grdf_contractuel, grdf_gda | PCE, consommations gaz, GRDF | Energie gaz | `/api/energie/distributeurs/grdf` |
| `GET /api/grdf/conso/status` | `saas/backend/app/api/routes/grdf.py:80` | gas_analytics, grdf_conso, grdf_contractuel, grdf_gda | PCE, consommations gaz, GRDF | Energie gaz | `/api/energie/distributeurs/grdf` |
| `POST /api/grdf/conso/sync` | `saas/backend/app/api/routes/grdf.py:96` | gas_analytics, grdf_conso, grdf_contractuel, grdf_gda | PCE, consommations gaz, GRDF | Energie gaz | `/api/energie/distributeurs/grdf` |
| `POST /api/grdf/contractuel/enrich` | `saas/backend/app/api/routes/grdf.py:107` | gas_analytics, grdf_conso, grdf_contractuel, grdf_gda | PCE, consommations gaz, GRDF | Energie gaz | `/api/energie/distributeurs/grdf` |
| `GET /api/grdf/pces` | `saas/backend/app/api/routes/grdf.py:56` | gas_analytics, grdf_conso, grdf_contractuel, grdf_gda | PCE, consommations gaz, GRDF | Energie gaz | `/api/energie/distributeurs/grdf` |
| `POST /api/grdf/pces/sync` | `saas/backend/app/api/routes/grdf.py:69` | gas_analytics, grdf_conso, grdf_contractuel, grdf_gda | PCE, consommations gaz, GRDF | Energie gaz | `/api/energie/distributeurs/grdf` |
| `GET /api/grdf/rapprochement-p1/{year}` | `saas/backend/app/api/routes/grdf.py:165` | gas_analytics, grdf_conso, grdf_contractuel, grdf_gda | PCE, consommations gaz, GRDF | Energie gaz | `/api/energie/distributeurs/grdf` |

### `health`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `GET /api/health` | `saas/backend/app/api/routes/health.py:8` | - | sante technique | Administration / diagnostics | `/api/admin/diagnostics` |

### `internal`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `GET /api/internal/basic-auth` | `saas/backend/app/api/routes/internal_auth.py:12` | auth | authentification interne | Technique interne | `/api/internal` |

### `pronostics`

| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible |
|---|---|---|---|---|---|
| `GET /api/pronostics/admin/model-feed` | `saas/backend/app/api/routes/pronostics.py:211` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `POST /api/pronostics/admin/sync-scores` | `saas/backend/app/api/routes/pronostics.py:203` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `POST /api/pronostics/forgot-password` | `saas/backend/app/api/routes/pronostics.py:94` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `POST /api/pronostics/login` | `saas/backend/app/api/routes/pronostics.py:86` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `GET /api/pronostics/matches` | `saas/backend/app/api/routes/pronostics.py:150` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `GET /api/pronostics/me` | `saas/backend/app/api/routes/pronostics.py:118` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `PATCH /api/pronostics/me` | `saas/backend/app/api/routes/pronostics.py:123` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `POST /api/pronostics/me/password` | `saas/backend/app/api/routes/pronostics.py:135` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `GET /api/pronostics/participants` | `saas/backend/app/api/routes/pronostics.py:197` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `PUT /api/pronostics/predictions` | `saas/backend/app/api/routes/pronostics.py:182` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `GET /api/pronostics/ranking` | `saas/backend/app/api/routes/pronostics.py:191` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `POST /api/pronostics/register` | `saas/backend/app/api/routes/pronostics.py:73` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |
| `POST /api/pronostics/reset-password` | `saas/backend/app/api/routes/pronostics.py:108` | football_data, pronostics | jeu hors plateforme, ne pas integrer | Hors produit | `(hors plateforme)` |

## 4. Regles d'utilisation

- Ne pas renommer les endpoints en masse.
- Utiliser cette matrice pour decider parcours par parcours.
- Commencer par les endpoints du controle facture, de la decision et de l'export finance.
- Creer des facades cible si necessaire, puis migrer le front progressivement.
- Supprimer seulement les endpoints confirmes sans usage produit, sans script, sans front et sans cible.
