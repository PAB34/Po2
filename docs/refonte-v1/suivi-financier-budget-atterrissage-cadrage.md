# Suivi financier — Budget / Réalisé / Atterrissage — Cadrage

> Date : 2026-06-29 · Statut : **étude / cadrage avant code** (rien n'est codé).
> But : situer le besoin (saisir un budget annuel par marché + page de suivi financier
> réalisé-à-date → atterrissage fin d'année) par rapport à l'existant, et choisir
> **où** inscrire le budget. À décider avec l'utilisateur avant implémentation.
> Renvois : `[[34-Contrat-ecran-Fluides-V1]]` (F04 atterrissage), `[[36-Contrat-ecran-Cockpit-Sites-V1]]`,
> `[[38-Modele-backend-matrices-comptables-versionnees]]`, `[[Decisions/010-matrices-comptables-versionnees]]`,
> `[[Decisions/011-assistant-matrices-et-decisions-factures-V1]]`.

## 1. Le besoin (reformulé)

1. Pouvoir **saisir le budget de l'année en cours pour un marché** (Hérault Énergie, DALKIA, SPIE…).
2. Une **page de suivi financier** : budget vs **dépenses réalisées à l'instant T** (issues des factures contrôlées) vs **atterrissage fin d'année** (projection).
3. S'appuyer sur ce qui existe déjà (matrice comptable, consommations, atterrissage CPE, maquettes).

## 2. Ce qui existe déjà

### 2a. Matrice comptable versionnée (backend complet, mergé `main`)
- Tables `accounting_matrix_*` + `invoice_accounting_snapshots` (modèle doc 38, ADR 010/011). API `/api/accounting-matrices/*`, front `/refonte-v1/matrices`.
- **`AccountingMatrixContract` = une matrice par contrat / lot / marché** (`domain` + `supplier` + `contract_code` + `lot_label`, city-scoped). ⭐ C'est déjà l'objet « marché concerné ».
- `AccountingMatrixRule` ventile chaque ligne de facture vers une **`accounting_nature`** (+ `operation_number`, `accounting_function`, `accounting_antenna`). → axe naturel d'un budget.
- `InvoiceAccountingSnapshot` (snapshot_json) = **l'imputation figée par facture** = la **source du « réalisé »**.
- ⚠️ Limite connue (chantier PO2-FIN-001) : les **extracteurs réels de lignes de facture par source** ne sont pas tous branchés sur `apply` (`invoice_lines: []` par défaut). Le « réalisé par nature » dépend de cette brique.

### 2b. Atterrissage CPE = intéressement (≠ financier)
- `app/services/cpe_atterrissage.py` + `/cpe/bilan/{annee}/atterrissage?trimestre=` : projette **NC / N'B / intéressement DALKIA** par **pro-rata DJU** (réunions trimestrielles). C'est de la **performance énergétique**, pas le budget financier du marché.

### 2c. Vision UX déjà cadrée + maquettée
- **Atterrissage financier spécifié** : doc 34 §F04 → `réalisé distributeur + conso restante estimée = atterrissage physique`, puis `× prix variables + parts fixes = atterrissage financier`, avec scénarios central/bas/haut et **écart au budget** comme KPI.
- Doc 36 (Cockpit) : KPI « budget opérationnel », « atterrissage annuel » ; chaîne de décision « Budget = engagé + facturé + atterrissage ».
- **Maquettes React (données simulées)** : `features/cockpit/` (`CockpitPageV1` + `cockpit.mock.ts`), `features/sites/` (`SitesPortfolioPageV1`, onglet Budget/PPT), `features/fluids/` (`FluidsPortfolioPageV1`). Le budget y est **mocké** (ex. « Budget opérationnel 8,42 M€ »).

## 3. Ce qui manque (donc à construire)

- **Aucune table « budget »** en base (vérifié : le budget n'existe que dans les `*.mock.ts`).
- **Aucune saisie** de budget annuel par marché.
- **Pas d'agrégat « réalisé par nature/opération »** exposé (dépend des extracteurs de lignes + snapshots).
- **Pas de moteur d'atterrissage financier** (le §F04 est dans la liste « à construire » du doc 34).

## 4. Deux « atterrissages » à ne jamais confondre

| | Atterrissage **intéressement** (existe) | Atterrissage **financier / budget** (à faire) |
|---|---|---|
| Objet | NC, N'B, prime/pénalité DALKIA | dépense € du marché vs budget |
| Méthode | pro-rata DJU (`cpe_atterrissage.py`) | réalisé factures + conso restante × prix |
| Périmètre | CPE/DALKIA performance | tous marchés (énergie, CPE, maintenance…) |

## 5. Où inscrire le budget — DÉCISION (2026-06-29)

**Choix utilisateur : module « Marchés » dédié, budget saisi à la maille OPÉRATION.**

- **Saisie (UX)** : une section **« Budget »** dans un **module « Marchés »** dédié (section cible de la nav refonte — cf. `[[project_moteurs_et_ux]]`/nav 4 sections), par **marché × année**, **ligne par opération** (`operation_number`).
- **Lien aux données existantes** (pour éviter le doublon malgré le module séparé) : chaque ligne de budget reste **rattachée à la matrice du marché** (`matrix_contract_id`) et à une **opération** ; c'est la matrice comptable qui produit le réalisé sur le même axe `operation_number`.
- **Modèle de données proposé** (à valider) : nouvelle table `accounting_budget_lines`
  `(id, city_id, matrix_contract_id, year, operation_number, label, amount_budget, comment, created/updated)`.
- **Réalisé** = agrégat des `invoice_accounting_snapshots` (validés/exportés) **par `operation_number`** pour l'année.
- **Atterrissage** = réalisé + reste-à-venir estimé (énergie : moteur Fluides §F04 ; CPE : croisement avec l'atterrissage intéressement ; défaut : pro-rata temporel ou DJU). Scénario central + fourchette.
- ⚠️ **Implication maille « opération »** : le réalisé ne se rapproche au budget que si `operation_number` est **réellement renseigné** dans les règles de matrice / snapshots. À vérifier sur les données réelles (sinon les lignes facturées tombent en « opération non affectée »).

### Alternatives écartées
- **Onglet « Budget » dans Matrices** (recommandé initialement) : écarté au profit d'un module Marchés plus lisible côté métier ; le rattachement `matrix_contract_id` conserve la cohérence.
- **Budget porté par le CPE** : trop étroit (besoin multi-marchés).

## 6. La page « Suivi financier » (concept cible)

Une page par marché (ou consolidée + filtre marché) :
- KPI : **budget**, **réalisé à date**, **engagé** (optionnel), **atterrissage central + fourchette**, **écart au budget**.
- Tableau par **nature comptable / opération** : budget · réalisé · % consommé · atterrissage · écart.
- Courbe budget vs réalisé cumulé vs trajectoire/atterrissage sur l'année.
- Lien vers les factures (drill-down via les snapshots) et vers les consommations (Fluides).
- Hébergement : **module « Marchés »** (saisie budget + page de suivi au même endroit). Routes candidates : `/refonte-v1/marches` (+ `/refonte-v1/marches/:marche/suivi`).

## 7. Questions à trancher avant de coder

- ~~Emplacement du budget~~ → **tranché** : module « Marchés » dédié (§5).
- ~~Maille du budget~~ → **tranché** : par **opération** (`operation_number`).
- **Granularité temporelle** : montant **annuel** seul, ou **réparti par mois/trimestre** (utile pour la trajectoire et l'écart à date) ?
- **Périmètre v1** : un seul marché pilote (Hérault Énergie ? DALKIA ?) ou tous d'emblée ?
- **Atterrissage v1** : pro-rata simple (rapide) ou brancher d'emblée le moteur physique→financier du doc 34 (plus lourd) ?
- **Engagé** : a-t-on une source d'« engagé » (commandes/marchés notifiés) ou seulement budget vs facturé pour la v1 ?
- **Référentiel des opérations** : d'où vient la liste des `operation_number` saisissables (matrice ? saisie libre ? import) ?

## 8. Dépendances / risques

- **Réalisé fiable ⇒ extracteurs de lignes par source** branchés sur `apply` (PO2-FIN-001) : sans ça, le réalisé par nature reste vide. **Pré-requis** de la page de suivi.
- **Atterrissage financier ⇒ prix contractuels versionnés** (BPU) + conso distributeur (Fluides « à construire »).
- **Doublon contact à surveiller** : `AccountingMatrixContract` porte déjà `contact_name/email` ; la tâche réclamation a créé `supplier_contacts` (par fournisseur). À réconcilier le moment venu (ne pas dupliquer la saisie).

## 9. Proposition de séquencement (si validé)

1. Trancher le reste du §7 (temporalité, périmètre v1, source des opérations).
2. Table `accounting_budget_lines` (maille opération) + API CRUD + **module « Marchés »** avec section « Budget ».
3. Endpoint « réalisé par `operation_number` / année » (agrégat snapshots) — **après** les extracteurs de lignes (PO2-FIN-001), pré-requis.
4. Page « Suivi financier » dans Marchés : budget vs réalisé (atterrissage = pro-rata v1).
5. Atterrissage financier moteur (doc 34 §F04) en v2.
