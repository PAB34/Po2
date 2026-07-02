# 2026-07-02 — Cibles contractuelles CPE → budget de la matrice (§5bis)

> IA : Claude Opus 4.8
> Précédente session : `[[Sessions/2026-07-01 - Merge PR32 factures et Budget par marche v1]]`

## 🎯 Objectif de la session

Brancher les **cibles/budgets contractuels CPE (DALKIA)** comme source de budget pour un atterrissage
« budget contractuel − réalisé » (stratégie `refonte-v1/atterrissage-strategie-front.md` **§5bis**), au
lieu d'un budget prévisionnel Ville. Périmètre v1 : DALKIA (ENGIE/EDF/P3.4 = tranches suivantes).

## ✅ Ce qui a été fait

### Chantier — Atterrissage budget contractuel par poste (PR #36, branche `feat/cibles-contractuelles`)

- **Audit « fil du dev » écrit AVANT de coder** : `refonte-v1/cibles-contractuelles-budget-matrice-audit.md`.
  Découverte clé : le budget contractuel est **hétérogène** (P1 dans `cpe_contract_references`, P2/P3 dans
  `cpe_dalkia_ref_p2p3`), mais `cpe_market_tracking.build_market_tracking` l'agrège **déjà** en prévu/reçu
  par poste. Le vrai chantier = marier l'axe **poste CPE** (P1/P2/P3…) et l'axe **`operation_number`** matrice.
- **Backend** : `services/accounting_contract_budget.py` (`build_contract_budget_landing`) + route
  `GET /api/cpe/finances/contract-budget-landing?year=&lot=` + schémas Pydantic. **Calcul à la volée, aucune
  migration.** 6 tests sqlite verts (`tests/test_accounting_contract_budget.py`).
- **Front** : onglet « Budget contractuel (poste) » dans `/refonte-v1/marches` (SegmentControl) —
  `features/marches/ContractBudgetLandingV1.tsx` + `useContractBudgetV1.ts` + `fetchContractBudgetLanding`
  dans `lib/api.ts`. KPIs + table par poste + projection optionnelle par opération.
- Commits : `fa37b1a` (doc audit), `b685943` (backend), `2d82d79` (front).

## 🚧 Ce qui reste à faire / handoff

### Priorité 1 — Valider et merger PR #36
- **CI verte** (typecheck front notamment, non exécutable en local sans node_modules) → puis merge = **déploiement prod auto**.
- Commande : `gh pr checks 36` ; puis `gh pr merge 36 --squash --delete-branch` sur feu vert utilisateur.

### Priorité 2 — Suites de l'atterrissage
- **ENGIE** : rattacher PRM ENEDIS → sites CPE pour alimenter la cible élec (conso = ENEDIS, pas ENGIE).
- **EDF** (éclairage public) : définir une cible depuis l'historique, puis atterrissage (pilotage interne).
- **P3.4 APE** : atterrissage réalisé vs enveloppe forfaitaire (patron = `cpe_p3_devis.build_p3_atterrissage`).

### Côté utilisateur — validations
- Confirmer la sémantique d'atterrissage v1 (montant contractuel fixe vs projection DJU pour le gaz).
- Décider du rejeu setup matrices en prod (hérité de la session précédente).

## 📝 Notes & décisions

- **Décisions validées** (dans l'audit) : **hybride** (calcul par poste + projection opération), **réalisé =
  factures CPE par poste** (`market_tracking.recu`, pas les snapshots matrice), **calcul à la volée** (pas de
  persistance/migration). Atterrissage v1 = montant contractuel fixe (pro-rata si budget inconnu), à **ne pas
  confondre** avec l'intéressement DJU (`cpe_atterrissage`).
- Pas d'ADR distincte : la décision durable (§5bis « budget = contractuel ») est déjà tracée dans
  `atterrissage-strategie-front.md` ; les choix d'implémentation sont dans l'audit daté.
- **Environnement** : node v24 portable présent, mais `node_modules` absent du worktree → typecheck front délégué à la CI.
- Tests rouges **préexistants** (non liés) : `test_cpe_market_tracking::test_dju_block_real_vs_reference` + 3 de
  `test_cpe_atterrissage.py` (fragilité DJU/date).
