# 2026-07-02 - Budget révisé gaz (fixe / variable)

> IA : Claude Code. Suite de `2026-07-02 - Indices variables marches staging.md`.
> Reprise après galère Codex. Décision user : **laisser PR #38 de côté** (indices & variables, front « correct »),
> attaquer directement le **budget révisé fixe/variable**.

## Objectif livré
1er incrément du budget révisé fiable : moteur **FIXE / VARIABLE** par **PCE**, marché **gaz TotalEnergies**.
Généralise le patron CPE `accounting_contract_budget` (coefficient global) en vraie décomposition.

## Décisions user (avant code)
- Périmètre = **gaz TotalEnergies** (le mieux outillé, patron réutilisable ENGIE/EDF).
- Conso attendue (part variable) = **extrapolation DJU** (profil Sète), base historique N-1.
- Maille = **PCE** (agrégation site/bâtiment + total).
Doc « fil du dev » : `docs/refonte-v1/budget-revise-gaz-decisions.md`.

## Méthode (par PCE, année Y ; calcul à la volée, aucune migration)
- FIXE = abo + ATRD/ATRT fixe + CTA (N-1, tenu à plat v1).
- VARIABLE = conso attendue × prix réf : conso = kWh N-1 × (DJU_normal/DJU_N-1, `energie.get_dju_monthly`) ;
  fourniture révisée PEG (`load_revisable_prices`, ratio moy Y/N-1) ; accise/ATRD var/indexation tenus /kWh.
- Réalisé = Σ total_hors_tva factures Y ; Atterrissage = réalisé + reste projeté DJU (formule `cpe_atterrissage`).
Rien recodé côté prix/contrôles : on **branche** `GasInvoice`, PEG, DJU.

## Livrables (branche `feat/gas-budget-revise`)
- `app/services/gas_budget_revise.py`, `app/schemas/gas_budget.py`, route `GET /api/marches/gas-budget-revise?year=`
  (module `app/api/routes/gas_budget.py`, prefix `/marches` — pas de collision avec la future PR #38).
- Front : segment « Budget révisé gaz (fixe/variable) » sur `/refonte-v1/marches`
  (`GasBudgetReviseV1.tsx` + hook + `api.ts`).
- Tests `tests/test_gas_budget_revise.py` : **5 passed** (variable+DJU+PEG, atterrissage partiel, fixe pur,
  sans N-1, PEG indisponible). Workaround poste : `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 DATABASE_URL=sqlite:///./test.db python -m pytest -p no:cacheprovider`.

## État Git / PR
- **PR #39 (draft)** : https://github.com/PAB34/Po2/pull/39 — CI backend+front **verte**.
- Staging déployé (run 28596373072, success), health 200. **Pas mergé prod** (attente validation user).

## Gotchas
- CSV DJU non versionnés (seulement en prod) → moteur gère l'absence (fallback), tests injectent les DJU.
- Bug **préexistant** repéré : `test_cpe_atterrissage.py` monkeypatche `energie.get_dju_monthly` alors que le
  service lit `aggregate_dju_monthly` → tests inopérants/échouent en local. Tâche séparée créée (hors PR #39).

## Prochaine décision
1. Relire staging `/refonte-v1/marches` → « Budget révisé gaz », valider les chiffres sur données réelles.
2. Si OK : PR #39 ready → merge main (prod auto) → surveiller deploy + health.
3. Suite : parts fixes révisées par tarif versionné ; décompo thermosensible/base ECS ; **généralisation ENGIE/EDF**.
