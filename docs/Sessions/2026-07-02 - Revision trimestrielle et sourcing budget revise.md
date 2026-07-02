# 2026-07-02 — Révision trimestrielle + sourcing budget révisé (fixe/variable)

> IA : Claude Opus 4.8. Suite de `2026-07-02 - Cibles contractuelles CPE vers budget matrice`.
> Contexte : atterrissage « budget contractuel − réalisé » par marché (stratégie `atterrissage-strategie-front.md`).

## 🎯 Objectif de la session
Intégrer la **révision trimestrielle des prix** dans l'atterrissage budget contractuel, puis (sur relance
utilisateur) auditer l'existant pour un **budget révisé fiable** basé sur la décomposition **fixe/variable**
des factures, pour P1 gaz / ENGIE élec / EDF éclairage.

## ✅ Ce qui a été fait et MERGÉ EN PROD
- **PR #36 (mergée, prod)** — atterrissage budget contractuel par poste CPE (§5bis) :
  `services/accounting_contract_budget.py :: build_contract_budget_landing` + route
  `GET /api/cpe/finances/contract-budget-landing?year=&lot=` + onglet front « Budget contractuel (poste) »
  dans `/refonte-v1/marches` (`features/marches/ContractBudgetLandingV1.tsx` + `useContractBudgetV1.ts` +
  `fetchContractBudgetLanding` dans `lib/api.ts`). Réalisé = factures CPE par poste (`cpe_market_tracking`).
  Calcul à la volée, aucune migration. Hybride (projection par operation_number via règles matrice scope).

## 🟡 Ce qui est SUR STAGING, NON MERGÉ — PR #37 (branche `feat/revision-atterrissage`)
Budget contractuel **révisé** = budget base DPGF × coefficient de révision.
- Coef par marché (P2/P3 seulement) = Σrévisé/Σbase du **dernier trimestre facturé** (Option C), extrapolé.
  `_revision_coef_by_market` joint sur `CpeFinanceInvoice` (le code contrat est sur la facture, pas la ligne).
- **P1 gaz EXCLU** du coefficient (bug staging : coef ~300 car base/révisé = prix unitaires €/MWh sur conso,
  pas des forfaits). P1-ELEC non révisé. P3.4 révisé comme P3 (travaux programmés ¼ P30 révisé, OUV11) ;
  l'APE = forfait non révisable (hors vue trimestrielle).
- Sortie enrichie : `budget_base`, `coefficient_revision`, `revision_detail` (formule affichée en petit
  sous la ligne du poste), `budget_contractuel` (révisé). Front : colonnes base/coef/révisé + KPI base vs révisé.
- 9 tests sqlite verts (`tests/test_accounting_contract_budget.py`). CI verte. Déployé staging (santé 200).
- **Reste : validation staging utilisateur → merge (déclenche prod).** Lien :
  `https://staging.135-125-152-112.sslip.io/refonte-v1/marches` → onglet « Budget contractuel (poste) ».

## 🔍 Ce que l'audit a révélé (fil du dev — l'existant est DÉJÀ construit)
Le moteur des **prix/variables** existe pour tous ces marchés ; il manque la **couche budget révisé qui les
consomme**. La décomposition **fixe/variable** est déjà en base :
- **Gaz TotalEnergies** : `models/gas_invoice.py :: GasInvoice` entièrement décomposé — FIXE
  (`abonnement_fournisseur`, `atrd_terme_fixe`, `atrt_terme_fixe`, `montant_cta`) / VARIABLE
  (`prix_conso_gaz`×kWh, `atrd_terme_variable`, `montant_ticgn`). Réfs : `gas_revisable.py` (PEG mensuel
  €/MWh), `gas_bpu.py` (BPU lot 7), `gas_network_tariff.py` (ATRD), `gas_tax.py`. Service `gas_invoice.py`.
- **DALKIA P1 gaz** : prix **OS3** (`cpe_dpgf_p1.py`, `cpe_accounting._control_p1_gaz_pu_os3`), distinct du
  BPU TotalEnergies (invariant 04). P2/P3 = forfaits révisés par ICHT-IME/FSD2/BT40.
- **ENGIE / EDF élec** : `turpe.py` (tarifs **versionnés** + `list_turpe_evolution_events` ; part FIXE €/kVA
  vs VARIABLE soutirage×kWh), `bpu.py`/`invoice_bpu.py` (fourniture), `power_real_costs.py` (coût réel par PRM),
  imports `engie_xlsx_import.py` / `edf_csv_import.py`. Conso = **ENEDIS** (pas fournisseur). EDF : cible à définir.

Rapports produits : `docs/refonte-v1/revision-trimestrielle-atterrissage-audit.md`,
`docs/refonte-v1/budget-revise-fixe-variable-sourcing.md`.

## 🚧 Prochaines étapes (décidées avec l'utilisateur) — reprendre ICI
**Décisions actées** : (1) maille cible du budget révisé = **site/PRM** ; (2) 1er incrément V2 =
**table de suivi des indices/variables** (avec graphes), AVANT les moteurs.

### Priorité 1 — Table « Indices & variables » sur /refonte-v1/marches (plan prêt)
Plan détaillé : `docs/refonte-v1/indices-variables-suivi-plan.md`. **Plan validé par l'IA, en attente du GO
utilisateur** (il allait dire go mais a préféré documenter d'abord).
- Backend : endpoint d'agrégation `GET /api/marches/indices-variables?year_from=&year_to=` (calcul à la volée,
  no migration) normalisant les sources **déjà exposées** : `GET /cpe/revision-indices` + `/cpe/revision-observations`
  (ICHT/FSD/BT40 + coef observés), `GET /billing/gas/revisable` (PEG mensuel), `GET /bpu/turpe-evolution` +
  `/billing/turpe/versions`. Schéma Pydantic + tests sqlite.
- Front : 3e segment « Indices & variables » (SegmentControl) dans `MarketsBudgetPageV1.tsx` ; graphes
  **recharts (2.15.3 déjà présent** — suivre `components/BpuTimelineChart.tsx`/`PowerCalibrationChart.tsx`) +
  table par période. Lecture seule. Regroupement par famille (DALKIA/gaz/élec) ; ajouter la courbe du
  coefficient observé (révisé/base) recommandé.

### Priorité 2 — Généraliser le budget révisé en reconstitution fixe/variable (maille site/PRM)
Remplacer le coefficient global par : `budget révisé = Σ(fixe révisé) + Σ(conso attendue × prix de réf)`.
Commencer par le gaz TotalEnergies (le mieux outillé) ou fiabiliser P1 gaz DALKIA (OS3). Puis ENGIE
(TURPE+BPU+ENEDIS), puis EDF (définir la cible depuis l'historique).

### Priorité 3 — Coefficient directeur
Régression sur les coefficients trimestriels (table d'indices) → projeter T3/T4, remplacer « dernier connu ».

## 🛠️ Env / accès (rappels)
- **node v24 portable présent** (`/c/Users/pa.borja/AppData/Local/nodejs-portable/node-v24.18.0-win-x64`)
  mais `node_modules` absent des worktrees frais → typecheck front délégué à la CI. Backend : pytest via
  `DATABASE_URL=sqlite:///./test.db`.
- **Répertoire partagé Codex** : worktree isolé obligatoire (`git worktree add`), ne pas toucher `PRONO/*`
  ni `knockout_mc.py`, jamais force-push. Live dir = `feat/phase-5-drawer-actions` (modifs Codex non commitées).
- Merge `main` = **déploiement prod auto** (saas/**) → confirmer avant. Staging via
  `gh workflow run deploy-staging.yml -f ref=<branche>`. Preferer relecture staging AVANT prod.
- GH_TOKEN via `git credential fill`. VPS `~/.ssh/po2_vps2`.

## 📌 Pour reprendre en nouvelle conversation
1. Créer un worktree sur `origin/main` (contient PR #36). Si PR #37 pas encore mergée : la valider/merger d'abord.
2. Lire `docs/refonte-v1/indices-variables-suivi-plan.md` → coder Priorité 1 sur GO utilisateur.
3. Contexte complet : ce fichier + les 2 rapports d'audit ci-dessus + mémoire projet
   `project_cibles_contractuelles_atterrissage`, `project_suivi_indices_variables`.
