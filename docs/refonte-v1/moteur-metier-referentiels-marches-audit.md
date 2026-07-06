# Moteur métier « référentiels des marchés » (DPGF / BPU) — audit & cadrage

> Rapport « fil du dev » — 2026-07-03. **Recherche demandée** : le prochain gros chantier de la refonte
> front est le **moteur métier**, défini par l'utilisateur comme *« la centralisation des DPGF/BPU des
> marchés DALKIA / TotalEnergies, et à venir SUEZ, SPIE »*, avec un **objectif de cohérence des adresses**
> (routes) pour y atterrir. Ce doc cartographie l'existant (backend + frontend) et pose la cible.
> Écrit pour permettre de **repartir d'un contexte vide** dans une nouvelle conversation.

## 0. Réponse directe : les specs sont-elles documentées ?
**Partiellement.** Les briques existent et sont documentées séparément, mais **il n'y a PAS de spec unifiée**
du « moteur métier = centralisation des référentiels de marché ». Ce doc est ce point de départ.
Ce qui existe déjà comme doc :
- **Nav cible** : `saas/frontend/src/app/navigationV1.ts` + `docs/37-Plan-migration-React-refonte-V1.md`
  → section **« Moteurs métiers »** = { Énergie/Fluides, **Marchés & contrats**, Technique & CVC }.
- **Cohérence des adresses (API)** : `docs/13-Matrice-routes-fonctionnalites-refonte-api.md` — chaque routeur
  a déjà un **domaine cible** et un **préfixe cible** (voir §3).
- **DPGF DALKIA** : `docs/energie/CPE-DALKIA/11-Implémentation-Po2.md`, `18-Guide-utilisateur-moteur-DALKIA.md`,
  `docs/refonte-v1/dpgf-base-vs-revise-analyse.md`.
- **BPU** : `docs/Decisions/002-bpu-schema-normalise-5-tables.md`, `007-bpu-schema-on-read-vs-parser.md`,
  `docs/Chantiers/PO2-BPU-001-Parser-BPU-fiable.md`, `docs/energie/BPU-Audit-PDF-vs-Excel-2026-06-08.md`.

## 1. Définition retenue du « moteur métier »
Un **marché** (contrat fournisseur/prestataire) a un **référentiel contractuel** = les pièces de prix qui
servent de vérité pour contrôler les factures et reconstituer les budgets :
- **DPGF** (Décomposition du Prix Global et Forfaitaire) : pour le **CPE DALKIA** (P1/P2/P3, cibles NB/N'B).
- **BPU** (Bordereau de Prix Unitaires) : pour la **fourniture d'énergie** (marchés Hérault Énergies :
  ENGIE, EDF, TotalEnergies) et pour la **maintenance** (à venir : SPIE, SUEZ).

Le moteur métier = **centraliser la saisie/l'import + la consultation de ces référentiels au même endroit**,
avec des **adresses cohérentes**, et les relier aux moteurs déjà construits (atterrissage, contrôle facture).

## 2. Existant BACKEND (les référentiels sont déjà là, éclatés)

### 2.1 DPGF DALKIA — référentiel contractuel CPE
- **Routeur** : `cpe-dalkia` (21 endpoints), préfixe actuel `/api/cpe/dalkia-ref/*` (import/preview/confirm,
  imports, sites, prix). Cf. `saas/backend/app/api/routes/` (routeur cpe-dalkia) + `cpe.py` (56 endpoints,
  finances/contrôles/conso).
- **Services** : `cpe_dalkia_import.py`, `cpe_dalkia_db.py`, `cpe_dalkia_diff.py` (moteur de diff entre
  versions), `cpe_dpgf_p1.py` (DPGF P1 gaz révisé), `cpe.py`, `cpe_accounting.py`, `cpe_atterrissage.py`.
- **Modèles** : `models/cpe_dalkia.py`, `models/cpe.py`, `models/cpe_dpgf_p1.py`.
- **Cible doc 13** : domaine **Marchés & contrats**, préfixe **`/api/marches/cpe-dalkia/referentiel`**.

### 2.2 BPU — prix contractuels fourniture (Hérault Énergies : ENGIE/EDF/TotalEnergies)
- **Routeur** : `bpu` (22 endpoints), préfixe actuel `/api/bpu/*` : `documents`, `segments`, `periods`,
  `components`, `charges`, `timeline`, `formula`, `turpe-evolution`, `import` / `import-xlsx`, `editable-rows`.
- **Services** : `bpu.py` (parser PDF + schéma), `invoice_bpu.py` (résolution prix historique par
  site/poste/date), `billing_bpu_sync.py` (BPU XLSX → prix courants). TURPE lié : `turpe.py`.
- **Modèles** : `models/bpu.py` (5 tables : `BpuDocument`, `BpuSegment`, `BpuTimePeriod`,
  `BpuPriceComponent`, `BpuFixedCharge`). Un BPU = 1 PDF (fournisseur × année × marché × lot × avenant).
- **Cible doc 13** : domaine **Energie / referentiels**, préfixe **`/api/energie/prix`**.
- ⚠️ Il existe aussi des « BPU gaz lot 7 » côté TotalEnergies (`gas_bpu.py`) pour le contrôle gaz.

### 2.3 ⚠️ Tension à trancher (cœur du sujet)
La **doc 13 sépare** les deux référentiels dans deux domaines différents : BPU → *Energie/prix*, DPGF DALKIA
→ *Marchés/cpe-dalkia*. **La vision utilisateur les réunit** sous un même « moteur métier » (référentiels des
marchés). → **Décision structurante à prendre** : les référentiels marchés sont-ils regroupés sous
**Marchés & contrats** (vision user), ou le BPU reste-t-il sous Énergie ? (voir §6, Q1).

## 3. Existant FRONTEND — deux mondes parallèles

### 3.1 Pages LEGACY (les référentiels sont ici aujourd'hui)
| Page | Route actuelle | Rôle | Backend |
|---|---|---|---|
| `CpeDalkiaImportPage` | **`/cpe/dalkia-import`** | Import référentiel contractuel **DPGF DALKIA** | `/api/cpe/dalkia-ref/*` |
| `CpeDalkiaPage` | `/cpe` | Suivi conso / cibles / intéressement DALKIA (legacy) | `/api/cpe/*` |
| `EnergieBpuPage` | **`/energie/bpu`** | Historique **BPU** (Hérault Énergies, EDF/ENGIE/TotalE 2021–2026) | `/api/bpu/*` |
| `EnergieGazPage` | `/energie/gaz` | Contrôle gaz TotalEnergies | gas_invoice |
| `EnergieBillingPage` | `/energie/facturation` | Facturation/prix élec (configs, BPU lines) | `/api/billing/configs*` |
| `FacturesPage` | `/factures` | Factures & décisions (legacy) | `/api/billing/*` |

→ C'est là que se trouve le « Hérault Énergie regroupant ENGIE/EDF/TotalEnergies » que l'utilisateur
cherchait : **`/energie/bpu`** (page `EnergieBpuPage`).

### 3.2 Pages REFONTE V1 (`/refonte-v1/*`) — la cible en construction
Nav réelle (`navigationV1.ts`), rendue via `AppShellV1` :
- **Pilotage** : Cockpit (`/refonte-v1`), Factures & décisions (`/refonte-v1/factures`).
- **Patrimoine** : Sites 360° (`/refonte-v1/sites`), Compteurs & matching (`comingSoon`).
- **Moteurs métiers** : Énergie/Fluides (`/refonte-v1/fluides`), **Marchés & contrats
  (`/refonte-v1/marches`)**, Technique & CVC (`comingSoon`).
- **Référentiels & admin** : Matrices comptables (`/refonte-v1/matrices`), Administration (`comingSoon`).

**`/refonte-v1/marches`** (`MarketsBudgetPageV1`) = aujourd'hui **uniquement l'aval** : navigation par tier
(DALKIA CPE · Gaz TotalEnergies · ENGIE · EDF) × sous-onglets **Atterrissage** / **Cible conso** (DALKIA) /
**Indices & variables**. → **Il n'y a PAS encore d'onglet « Référentiel » (DPGF/BPU) : c'est le trou que le
moteur métier doit combler.**

## 4. Cible proposée (à valider)

### 4.1 Principe
Sous **Moteurs métiers → Marchés & contrats** (`/refonte-v1/marches`), chaque **tier/marché** expose un jeu
d'onglets **cohérent et identique** :
```
/refonte-v1/marches  →  [tier: DALKIA | TotalEnergies | ENGIE | EDF | (SUEZ) | (SPIE)]
   ├─ Référentiel      (DPGF pour DALKIA ; BPU pour fourniture ; BPU/DPGF maintenance pour SPIE/SUEZ)
   ├─ Atterrissage     (budget/révisé/réalisé — déjà fait)
   ├─ Cible conso      (là où il y a une cible — DALKIA fait)
   └─ Indices & variables (déjà fait)
```
La brique « Référentiel » **réutilise le backend existant** (cpe-dalkia-ref pour DPGF, bpu pour BPU) :
c'est un **portage/branchement UX**, pas un nouveau moteur.

### 4.2 Cohérence des adresses (le vrai objectif « où atterrir »)
- **Front** : tout passe par `/refonte-v1/marches?tier=<marché>&onglet=<referentiel|atterrissage|cible|indices>`
  (ou routes imbriquées équivalentes). Fin des adresses éparpillées `/cpe/dalkia-import` et `/energie/bpu`.
- **API** (doc 13) : converger vers `/api/marches/<marché>/...` (ex. `/api/marches/cpe-dalkia/referentiel`,
  et **décider** si le BPU devient `/api/marches/herault-energie/bpu` ou reste `/api/energie/prix`).
  Ces renommages peuvent être **différés** (alias) : la priorité est la cohérence FRONT.

## 5. Marchés & type de référentiel (périmètre cible)
| Marché / tier | Type | Référentiel | État |
|---|---|---|---|
| **DALKIA CPE** | Performance énergétique (chauffage) | **DPGF** P1/P2/P3 + cibles NB | Backend + page legacy OK ; à porter en refonte |
| **TotalEnergies** | Fourniture gaz (Hérault Énergies) | **BPU gaz** (lot 7) + PEG | Backend OK (gas_bpu) ; référentiel à exposer |
| **ENGIE** | Fourniture élec (Hérault Énergies) | **BPU élec** | Backend `bpu` OK ; page legacy `/energie/bpu` |
| **EDF** | Fourniture élec éclairage public | **BPU élec** | idem `bpu` |
| **SPIE** | Maintenance CVC (2e marché) | BPU/DPGF maintenance | Inventaire CVC fait (`/buildings/cvc-import`) ; référentiel prix à cadrer |
| **SUEZ** | À venir (eau/déchets ?) | À définir | Non commencé |

## 6. Écarts, risques et questions ouvertes
1. **Q1 (structurant)** : les référentiels marchés (DPGF **et** BPU) sont-ils tous regroupés sous
   **Marchés & contrats** (vision user), ou le BPU fourniture reste-t-il rattaché à **Énergie/Fluides** ?
   (La doc 13 penche pour séparer ; l'utilisateur pour réunir.)
2. **Q2** : granularité de la brique « Référentiel » en refonte = **consultation seule** d'abord (lecture des
   DPGF/BPU importés) puis **import** ? ou import dès le départ ?
3. **Q3** : réutiliser tel quel `/cpe/dalkia-import` (déjà refondu en « état en vigueur + journal des actes »,
   cf. `project_cpe_dossier_page`) et `EnergieBpuPage` en les **embarquant** dans le shell refonte, ou
   **réécrire** proprement avec le design-system V1 ?
4. **Q4** : SPIE/SUEZ — cadrer le type de référentiel (BPU maintenance ?) avant de généraliser la grille.
5. **Q5** : renommer les préfixes API (`/api/marches/...`) maintenant (avec alias) ou différer et ne
   travailler que la cohérence front ?

## 7. Pointeurs (pour repartir)
- Nav cible : `saas/frontend/src/app/navigationV1.ts` · `docs/37-Plan-migration-React-refonte-V1.md`.
- Cartographie API + préfixes cibles : `docs/13-Matrice-routes-fonctionnalites-refonte-api.md`.
- DPGF DALKIA : page `saas/frontend/src/pages/CpeDalkiaImportPage.tsx` ; services `cpe_dalkia_*`,
  `cpe_dpgf_p1.py` ; modèle `models/cpe_dalkia.py` ; docs `docs/energie/CPE-DALKIA/11,18` +
  `docs/refonte-v1/dpgf-base-vs-revise-analyse.md`.
- BPU : page `saas/frontend/src/pages/EnergieBpuPage.tsx` ; services `bpu.py`/`invoice_bpu.py`/
  `billing_bpu_sync.py` ; modèle `models/bpu.py` ; ADR `docs/Decisions/002,007`.
- Refonte marchés (aval déjà fait) : `saas/frontend/src/features/marches/MarketsBudgetPageV1.tsx` +
  `docs/refonte-v1/marches-budget-decisions-ux.md`, `engie-elec-revise-decisions.md`,
  `edf-elec-revise-decisions.md`, `dalkia-cible-conso-calque-decisions.md`.
- Mémoires liées : `project_moteurs_et_ux`, `project_reconstruction_v1`, `project_cpe_dossier_page`,
  `project_factures_refonte_spec`, `project_cpe_dalkia`, `project_cpe_electricite_scope`.
