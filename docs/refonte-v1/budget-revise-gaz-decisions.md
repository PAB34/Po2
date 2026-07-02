# Budget révisé gaz TotalEnergies — décisions (fixe / variable, maille PCE)

> Rapport « fil du dev » — 2026-07-02. Suite de `budget-revise-fixe-variable-sourcing.md`.
> 1er incrément du **budget révisé fiable** en reconstitution FIXE / VARIABLE. Écrit AVANT de coder.

## Décisions actées (validées utilisateur)

1. **Périmètre 1er incrément = gaz TotalEnergies** (Hérault Énergie, bâtiments Ville de Sète).
   Le mieux outillé : `GasInvoice` déjà décomposée fixe/variable + PEG mensuel + profil DJU Sète.
   Sert de **patron générique** réutilisable ensuite pour ENGIE puis EDF.
2. **Maille = PCE** (équivalent PRM pour le gaz), avec agrégation par site/bâtiment et total marché.
3. **Conso attendue (part variable) = extrapolation DJU** (profil Sète, `energie.get_dju_monthly`),
   corrigée du climat, base historique N-1. (Options N-1 brut et pro-rata écartées.)

## Le principe (rappel sourcing §0)

```
budget_révisé = Σ parts FIXES (révisées)  +  Σ (conso attendue × prix de référence)
atterrissage  = réalisé à date            +  reste estimé (mêmes prix de référence)
```

## Méthode v1 (par PCE, pour une année Y) — ce qu'on branche sans recoder

Références lues sur les factures **N-1** du PCE (`GasInvoice`, année Y-1) :

| Nature | Composantes GasInvoice | Prix / référence de révision |
|---|---|---|
| **FIXE** | `abonnement_fournisseur` + `atrt_terme_fixe` + `atrd_terme_fixe` + `montant_cta` | tenu à plat en v1 (termes ~constants ; révision tarif versionné = incrément suivant) |
| **VARIABLE** | `montant_conso_gaz` (fourniture) + `atrd_terme_variable` + `montant_ticgn` (accise) + `montant_indexation` | **fourniture révisée par PEG** (`GasSupplyRevisablePrice`, ratio moyenne Y / moyenne N-1) ; autres termes /kWh tenus |

- **Prix unitaires** dérivés du N-1 : `pu_fourniture = Σmontant_conso_gaz/Σkwh`,
  `pu_autres_var = Σ(accise+atrd_var+indexation)/Σkwh`.
- **PEG ratio** = moyenne `fourniture_eur_mwh` année Y / moyenne N-1 (= 1,0 si PEG indisponible → prix tenu).
- **Conso attendue** (correction climatique DJU) : `conso_attendue = kwh_N-1 × (DJU_normal_annuel / DJU_N-1_annuel)`
  où `DJU_normal[m]` = moyenne historique par mois calendaire (années ≠ Y). Formule du moteur
  `cpe_atterrissage` réutilisée. Fallback = 1,0 si pas de DJU (conso tenue au N-1).
- **Budget révisé** = `conso_attendue × (pu_fourniture×PEG_ratio + pu_autres_var)` + `fixe_N-1`.

**Réalisé** = `Σ total_hors_tva` des factures de l'année Y (déjà décomposées).

**Atterrissage** (réalisé + reste projeté DJU, prix de référence) :
- `conso_projetée_Y = kwh_réalisé_Y × (DJU_projeté_annuel / DJU_écoulé)` (comme `cpe_atterrissage`),
  `DJU_projeté_annuel = DJU_réel(mois écoulés) + DJU_normal(mois restants)` ;
- `atterrissage = réalisé + (conso_projetée − kwh_réalisé)×pu_variable_réf + fixe_mensuel×mois_restants`.
- Fallbacks : DJU écoulé nul → pro-rata temporel ; aucun réalisé Y → atterrissage = budget révisé.

## Réutilisation (rien recodé)

- `GasInvoice` (décompo) · `load_revisable_prices` (PEG) · `energie.get_dju_monthly` (DJU Sète) ·
  patron `accounting_contract_budget` (mise en forme budget/réalisé/atterrissage/écart).

## Livrables

1. `app/services/gas_budget_revise.py` — moteur (calcul à la volée, **aucune migration**).
2. `app/schemas/gas_budget.py` + route `GET /api/marches/gas-budget-revise?year=` (module `routes/gas_budget.py`).
3. Front : segment « Budget révisé (gaz) » sur `/refonte-v1/marches`.
4. Tests `tests/test_gas_budget_revise.py` (sqlite) : fixe pur, variable+DJU, réalisé partiel→atterrissage,
   PCE sans N-1 (fallback), PEG ratio.

## Hors périmètre v1 (incréments suivants)

- Révision des parts fixes par tarif versionné (ATRD/ATRT datés).
- Décomposition thermosensible / base ECS (modèle pur-DJU en v1, cf. avertissement `cpe_atterrissage`).
- Généralisation ENGIE / EDF (TURPE + BPU élec) — même moteur, autres sources de prix/conso.

## Questions restantes (mineures)

1. Part fixe : garder à plat en v1 ou brancher tout de suite le tarif ATRD/ATRT versionné ? (v1 = plat.)
2. Conso attendue quand pas de N-1 : tenir 0 (marqué « sans historique ») — OK v1.
