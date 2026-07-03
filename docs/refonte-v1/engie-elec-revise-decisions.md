# Budget révisé ENGIE électricité — décisions (fixe / variable, maille PRM/site)

> Rapport « fil du dev » — 2026-07-03. Suite de `budget-revise-fixe-variable-sourcing.md` (§1.4, §2),
> `budget-revise-gaz-decisions.md` (patron gaz TE) et `p1-gaz-dalkia-decisions.md`.
> Généralise le moteur fixe/variable au 1er marché **élec** (ENGIE). Écrit AVANT de coder.

## 1. Audit du rattachement conso ENEDIS ↔ sites/PRM (la dépendance à cadrer)

Chaîne de données vérifiée (lecture code, worktree `origin/main`) :

| Maillon | Source | État |
|---|---|---|
| **Réalisé** ENGIE par PRM | `EnergyInvoice(supplier="ENGIE", energy_type="electricity")` → `EnergyInvoiceSite.prm_id` → `EnergyInvoicePeriod` → `EnergyInvoiceLine.amount_ht/normalized_code` (import `engie_xlsx_import.py`) | ✅ en base, par PRM |
| **Périmètre marché** | `EnergyInvoice.supplier` (indexé, distinct ENGIE / EDF, tous deux élec) ; PRM du marché = `prm_id` distincts des factures ENGIE | ✅ discriminant fiable |
| **Conso ENEDIS par PRM** | `energie._consumption_by_month()` → `{prm_id: {YYYY-MM: kWh}}` et `_rolling_annual_kwh(prm_id)` (source `enedis_data.csv`, journalier) | ✅ dispo, maille PRM |
| **Rattachement PRM → bâtiment/site** | `BuildingMeterLink(fluid="ELECTRICITE", meter_identifier=PRM)` → `building_id` ; alimenté par `meter_matching.py` (suggestion + validation manuelle) | 🟡 table + moteur OK, **taux de couverture/validation à vérifier sur prod** |
| **Prix référence VARIABLE** | fourniture `bpu.py`/`invoice_bpu.py` (timeline prix marché Hérault) ; acheminement `turpe.py` (`find_turpe_table(on_date)` → soutirage €/kWh) | ✅ moteurs existants |
| **Prix référence FIXE** | abonnement fourniture (BPU) ; TURPE fixe (€/kVA/an, gestion, comptage) × `subscribed_power_kva` (`EnergyInvoicePeriod`) | ✅ moteurs existants |

**Conclusions de l'audit :**
- Le socle est complet : conso ENEDIS **est** disponible par PRM (mensuel + annuel glissant), les factures
  ENGIE **sont** par PRM, les moteurs de prix (BPU/TURPE) existent.
- ⚠️ Piège OOM (`project_load_curve_oom`) : on lit la **conso journalière** (`_consumption_by_month`,
  index par PRM, volume maîtrisé), **jamais la courbe de charge 30 min** (index global dégradé au-delà de
  150 Mo). Aucun besoin de la courbe de charge ici.
- **Seul maillon à finaliser = le rattachement PRM → bâtiment** (`BuildingMeterLink` élec) : le code est là,
  mais la **couverture réelle** (combien de PRM ENGIE validés vers un bâtiment) doit être mesurée en
  **lecture seule sur prod** (cf. `feedback_test_avant_push`). Les CSV ENEDIS et la table vivent hors git.
  → Si couverture faible : la maille **PRM** reste fonctionnelle (label = `site_name` de la facture),
  l'agrégation par bâtiment est un enrichissement, pas un bloquant.

## 2. Décisions actées (validées utilisateur 2026-07-03)

### D1 — Maille = PRM + agrégat bâtiment ✅
Clé = PRM (naturelle facture + ENEDIS + TURPE), **agrégation par bâtiment** via `BuildingMeterLink`
quand le lien existe (sinon PRM autonome, label = `site_name`), + total marché. Symétrique du gaz.

### D2 — Conso attendue = N-1 ENEDIS + **correction DJU thermosensible** ✅
Pas de ratio DJU global (surcorrige l'élec : la base éclairage/bureautique/ventilation/froid n'est pas
thermosensible). On applique une **régression `kWh_mois = base + pente × DJU_mois` par PRM**, puis
`conso_attendue = base×12 + pente × DJU_normal`. On corrige **seulement** la part chauffage/clim.
→ Réutilise la machinerie existante `get_prm_dju_performance` / `_build_dju_side` / `_linear_trend`
(kWh/DJU chauffage + froid) + `_dju_monthly_index`. Fallbacks : pente non significative → conso N-1 tenue ;
pas d'historique ENEDIS → conso reconstituée des kWh facturés N-1 (marqué « sans ENEDIS »).

### D3 — Prix de référence = **BPU (fourniture) + TURPE (soutirage var + fixe versionné)**, fallback N-1 ✅
- VARIABLE : fourniture via `bpu`/`invoice_bpu` (prix marché Hérault) + acheminement `turpe.find_turpe_table(on_date)` (soutirage €/kWh).
- FIXE : abonnement fourniture (BPU) + TURPE fixe (€/kVA/an, gestion, comptage) × `subscribed_power_kva` (`EnergyInvoicePeriod`).
- **Fallback par PRM** : prix dérivés des factures ENGIE N-1 quand BPU/TURPE ne résolvent pas
  (option tarifaire ou puissance manquante). À confirmer au codage : résolution par PRM de l'option
  tarifaire + puissance souscrite depuis `EnergyInvoiceSite/Period`.

### D4 — Périmètre = **tous les PRM facturés ENGIE** ; cible DALKIA = **calque comparatif** ✅
Budget/atterrissage = prévisionnel N-1 sur tous les PRM ENGIE (`supplier="ENGIE"`, énergie élec),
indépendamment de l'appartenance à un marché DALKIA. La **cible DALKIA** (conso, intéressement/pénalités,
y compris sites sans P1 fourniture — cf. `cpe_electricite_scope`) s'affiche **en comparaison là où elle
existe** (conso cible vs conso attendue vs réalisé), **sans** entrer dans le calcul de coût. Patron
`cibles-contractuelles-atterrissage`. Branchement de la donnée cible = incrément suivant (calque optionnel v1).

### D5 — Réalisé & atterrissage
Réalisé = Σ `amount_ht` des lignes factures ENGIE année Y par PRM. Atterrissage = réalisé à date +
reste projeté (conso restante × prix réf variable + fixe × mois restants), base = **mois réellement
couverts** (fix repris des moteurs gaz TE / P1).

### D6 — Front
Cloner `GasBudgetReviseV1.tsx` → `EngieBudgetReviseV1.tsx`, remplacer le `ComingSoon` du tier ENGIE
dans `MarketsBudgetPageV1.tsx`.

## 3. Livrables prévus (après GO)

1. `app/services/engie_elec_budget_revise.py` — moteur par PRM (+ agrégat bâtiment/marché), calcul à la
   volée, **aucune migration**. Réutilise `energie._consumption_by_month`/`_rolling_annual_kwh`,
   `turpe`, `bpu`, `power_real_costs`/`EnergyInvoice*`, `BuildingMeterLink`.
2. `app/schemas/engie_budget.py` + route `GET /api/marches/engie-elec-budget-revise?year=`
   (clone `routes/gas_budget.py`).
3. Front : `EngieBudgetReviseV1.tsx` dans le tier ENGIE de `/refonte-v1/marches`.
4. Tests ciblés (sqlite) : variable BPU/TURPE, fixe TURPE×kVA, réalisé partiel→atterrissage,
   PRM sans ENEDIS (fallback), PRM sans lien bâtiment (maille PRM seule).

## 4. Hors périmètre v1
- Correction thermosensible / décomposition base-thermo de l'élec.
- EDF éclairage public (autre cible de conso, autre maille).
- Table de suivi des indices TURPE/BPU (onglet « Indices & variables » déjà posé).

## 5. Ce que je NE fais pas sans validation
- Q2 (source conso attendue) et Q3 (BPU/TURPE vs dérivé N-1) — structurants.
- Toucher le périmètre EDF (élec aussi, mais cible et maille différentes).
