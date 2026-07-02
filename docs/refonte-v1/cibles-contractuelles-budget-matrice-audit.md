# Cibles contractuelles CPE → budget de la matrice — audit & décisions

> Rapport « fil du dev » (lecture seule) — 2026-07-02. Branche `feat/cibles-contractuelles` (worktree,
> basée sur `origin/main`). Objectif de la session : brancher les **cibles/budgets contractuels CPE
> (DALKIA)** sur l'axe de la **matrice comptable** pour un atterrissage « budget contractuel − réalisé »,
> conformément à `atterrissage-strategie-front.md` §5bis. **Écrit AVANT de coder** (règle 05-Conventions §2).

## 0. Ce que dit la stratégie (§5bis)

`budget contractuel (référence) − réalisé (snapshots matrice) = atterrissage vs contrat`, où le budget
n'est **pas** une saisie prévisionnelle Ville mais le **montant contractuel** (pièces qui nous lient au
tiers). Le module Budget par marché (PR #33) reste, mais **sa source de budget bascule** de « saisie
manuelle » à « référence contractuelle ».

## 1. Existant — les briques (auditées dans le code)

### 1.1 Axe « budget par marché » (PR #33) — la cible à alimenter
- **Modèle** `AccountingBudgetLine` (`app/models/accounting_budget.py`) : clé
  `(city_id, matrix_contract_id, year, operation_number)` → `amount_budget` (**saisi manuellement**).
- **Service** `accounting_budget.py` :
  - `compute_suivi()` : budget vs réalisé vs atterrissage (**pro-rata temporel v1**), par `operation_number`.
  - `compute_realized_by_operation()` : le **réalisé** = somme des `amount_allocated` des
    `invoice_accounting_snapshots` figés (`validated/manual_override/exported`), **groupés par
    `imputation.operation`**. Année résolue seulement pour sources `cpe_dalkia` et `energy_import`.
- **Axe de rattachement** = `operation_number`, porté par `AccountingMatrixRule.operation_number` et
  recopié dans le snapshot au moment de l'`apply`.

### 1.2 Le « marché » = `AccountingMatrixContract`
- `(domain, supplier, contract_code, lot_label)`. Pour DALKIA CPE : `contract_code` = `C00190116O`
  (Lot 1) / `C00190155J` (Lot 2). **C'est le pont naturel** avec le monde CPE (même `contract_code`).

### 1.3 Sources du « budget contractuel » — ⚠️ HÉTÉROGÈNES (découverte clé)
La stratégie §5bis suppose que **tous** les postes vivent dans `cpe_contract_references`. **C'est faux.**
En réalité les montants contractuels DALKIA sont éclatés :

| Poste contractuel | Où il vit réellement | Accès |
|---|---|---|
| **P1 gaz acompte** | `cpe_contract_references` (kind `p1_gaz_acompte`) | `annual_amount_ht` / `expected_amount_ht` |
| **P2 / P2.4 / P3 / P3.4** (forfaits & provisions) | **`cpe_dalkia_ref_p2p3`** (table `CpeDalkiaRefP2P3`, imports DALKIA) | agrégé par `cpe_market_tracking` |
| **Cible élec** (Annexe 5.2) | référentiel cibles élec | `resolve_cible_elec_for_year` |
| **Cible gaz NB/N'B/NC** | référentiel cibles | `resolve_nb_for_year*` |
| **Périmètre / lot** | `cpe_contract_references` (kind `cpe_contract_scope`, billed_item `CPE_VILLE_LOT_1`) | `_contract_lot_map` |

### 1.4 `cpe_market_tracking.build_market_tracking()` — le budget contractuel **déjà calculé**
- Route **`GET /cpe/finances/market-tracking?year_from=&year_to=`** (`CpeMarketTrackingOut`).
- Produit déjà, **par poste** `P1 / P1-ELEC / P2 / P2-4 / P3 / P3-4` **et par année**, un couple
  `{prevu, recu, ecart, taux}` : `prevu` = **budget contractuel** (référentiel), `recu` = réalisé factures CPE.
- **C'est déjà « budget contractuel vs réalisé » pour DALKIA**, mais sur l'**axe poste CPE**, pas sur
  l'axe `operation_number` de la matrice. Grosse réutilisation possible — ne rien recoder du calcul du prévu.

## 2. Le vrai problème = réconcilier DEUX axes

- **Axe matrice / compta Ville** : `operation_number` (+ service/fonction/antenne/nature).
- **Axe contractuel / CPE** : poste `P1/P2/P2.4/P3/P3.4` + cibles élec/gaz.

Le budget contractuel est nativement **par poste** ; le réalisé de la matrice est **par opération**.
Pour poser « budget contractuel − réalisé » sur le **même** axe, il faut une **correspondance
poste CPE ↔ operation_number** (ou nature). Deux mondes à marier — c'est LE point de design.

## 3. Options d'architecture (à trancher)

- **Option A — côté matrice (mapping poste→opération).** Ajouter une table de correspondance
  `poste CPE → matrix_contract + operation_number`, et remplir `AccountingBudgetLine.amount_budget`
  (ou une colonne `amount_budget_contractuel` dérivée) à partir du prévu de `market_tracking`. Le module
  Budget existant continue de tourner, sa colonne budget devient « contractuelle ». **Réutilise
  compute_suivi tel quel.** Le réalisé reste celui des snapshots matrice.
- **Option B — côté CPE (exposer l'atterrissage par poste, sans passer par operation_number).** Un
  nouveau service `cpe_atterrissage_contractuel` qui, par poste, fait `prevu − recu → atterrissage`
  (pro-rata pour P2/élec, DJU pour gaz, engagé/provision pour P3). N'utilise PAS l'axe matrice ; la
  matrice ne sert que d'imputation comptable. Plus simple, mais ne « branche » pas réellement sur la matrice.
- **Option C — hybride.** Le budget contractuel par poste (Option B pour le calcul) est **projeté** sur
  l'axe matrice via la correspondance (Option A) uniquement pour l'affichage « par opération » quand la
  compta le demande. Plus de travail.

Recommandation provisoire : **Option A** — c'est ce que §5bis décrit littéralement (« la colonne budget
du module PR #33 prend le montant contractuel »), et ça réutilise `compute_suivi` + `market_tracking`.

## 4. Questions ouvertes (numérotées — à trancher avant de coder)

1. **Maille du budget contractuel.** On le pose par `operation_number` (axe matrice actuel, Option A) ou
   par **poste CPE** P1/P2/P3… (Option B) ? Si Option A : qui définit la correspondance poste→opération
   (table éditable ? déduction depuis les `AccountingMatrixRule.scope` p1/p2/p3 existantes ?).
2. **Réalisé : lequel fait foi ?** Le réalisé « snapshots matrice » (`compute_realized_by_operation`) ou
   le réalisé « factures CPE par poste » (`market_tracking.recu`) ? Les deux existent et peuvent diverger
   (périmètre, statut figé vs toutes lignes). Un seul doit être la source de vérité de l'atterrissage.
3. **P1 gaz : atterrissage pro-rata ou DJU ?** Le budget P1 est thermosensible. On garde le pro-rata
   simple de `compute_suivi`, ou on branche l'extrapolation **DJU** (`cpe_atterrissage`) pour le poste gaz ?
   (la stratégie §2 dit DJU pour le thermosensible).
4. **Périmètre v1.** On se limite à **DALKIA** (2 contrats, budget 100 % contractuel) pour cette session,
   en laissant ENGIE (cible élec = ENEDIS) et EDF (cible à définir) pour des tranches suivantes ? (recommandé).
5. **Modèle de données.** Nouvelle colonne `amount_budget_source` + `amount_budget_contractuel` sur
   `accounting_budget_lines`, ou **table dédiée** `accounting_contract_budget` (référence → opération),
   ou **calcul à la volée** sans persistance (dérivé de market_tracking à chaque appel) ? (le calcul à la
   volée évite une migration et la désync, cf. le choix « réalisé jamais stocké » déjà fait §1.1).
6. **P3.4 (APE).** Hors périmètre v1 (pluriannuel, moteur à construire) — confirmé ?
7. **Front.** On livre d'abord l'**API** (budget contractuel vs réalisé vs atterrissage) et on branche le
   front refonte (maquette `prototype-refonte-v1`) dans une tranche suivante ? Ou front minimal en même temps ?

## 5. Fichiers concernés (probables)
- Lecture/réutilisation : `services/cpe_market_tracking.py`, `services/accounting_budget.py`,
  `services/cpe_atterrissage.py`, `models/accounting_matrix.py`, `models/accounting_budget.py`,
  `models/cpe.py` (`CpeContractReference`), `api/routes/cpe.py`.
- Création probable : un service `accounting_contract_budget.py` (+ éventuelle table/migration selon Q5),
  une route sous `/api/accounting-budget/*` ou `/cpe/finances/*`, schémas Pydantic.

## 6. Tests ciblés probables
- `pytest tests/test_accounting_budget*.py` (existant, à retrouver) + nouveau test du service contractuel.
- `pytest tests/test_cpe_market_tracking*.py` si on touche l'agrégat prévu.
- ⚠️ `tests/test_cpe_atterrissage.py` a **3 tests rouges dépendants de la date** (déjà signalé dans
  `atterrissage-sourcing-existant.md`) — ne pas les confondre avec une régression.
- Front : `npx tsc -b` (via CI, npm absent en local).

## 7. Ce que je NE fais pas sans validation
- Choisir la maille (Q1) et la source de réalisé (Q2) — ce sont des décisions structurantes.
- Créer une migration (Q5) avant d'avoir tranché persistance vs calcul à la volée.
- Toucher EDF/ENGIE (hors périmètre v1) ni P3.4.
