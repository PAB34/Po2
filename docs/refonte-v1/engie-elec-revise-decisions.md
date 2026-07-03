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
- Décomposition **froid/climatisation** (DJU_froid) : seule la thermosensibilité **chauffage** est prise en v1.
- EDF éclairage public (autre cible de conso, autre maille).
- Table de suivi des indices TURPE/BPU (onglet « Indices & variables » déjà posé).
- Calque **cible DALKIA** (conso objectif / intéressement) — incrément suivant.

## 5. Ce que je NE fais pas sans validation
- Toucher le périmètre EDF (élec aussi, mais cible et maille différentes).

---

## 6. État de réalisation (2026-07-03)

Backend **fait et testé** (6 tests sqlite verts) : `engie_elec_budget_revise.py`, `schemas/engie_budget.py`,
`routes/engie_budget.py` → `GET /api/marches/engie-elec-budget-revise?year=`. Front à faire (§8).

## 7. Détail du calcul (référence)

> Objectif : comprendre chaque nombre de la page sans lire le code. Tout est **calculé à la volée**
> (aucune table, aucune migration). Sources = factures ENGIE importées (réalisé + prix N-1), conso ENEDIS
> (attendue), tables BPU/TURPE (révision).

### 7.1 Périmètre et maille
- On prend toutes les lignes de factures **`supplier = ENGIE`, `energy_type = electricity`** de la ville.
- Clé de calcul = **PRM** (`EnergyInvoiceSite.prm_id`). Chaque PRM est ensuite rattaché à un **bâtiment**
  via `BuildingMeterLink(fluid="ELECTRICITE")` ; les PRM sans lien sont regroupés en « Non affecté ».
- Une ligne est datée par sa **période** (`period_start` → sinon `period_end`) : année N-1 = base de prix,
  année Y = réalisé.

### 7.2 Classification des lignes (fixe / variable)
Chaque ligne a un `normalized_code` (produit par le parser ENGIE). On les range ainsi, **en excluant les
lignes « total »** (`supply_total_ht`, `network_fixed_total`, `network_total_ht`, `tax_total`, …) qui
agrègent déjà d'autres lignes → sinon double comptage.

| Nature | Codes | Rôle |
|---|---|---|
| **VARIABLE** | `supply` (fourniture), `network_variable` (soutirage variable), `capacity`, `cee`, `contribution`, `green_energy`, taxes /kWh (`cspe`, `ticfe`, taxes communale/départementale), + pénalités `network_overrun*` | conso × prix |
| **FIXE** | `network_management` (gestion), `network_counting` (comptage), `network_withdrawal`/`soutirage_fixed` (soutirage fixe), `cta`, `subscription` | termes fixes |

> Les **pénalités de dépassement** comptent dans le réalisé variable mais **pas** dans le calcul des prix
> unitaires (elles ne sont pas proportionnelles à la conso).

### 7.3 Prix unitaires de référence (dérivés du N-1, par PRM)
À partir des lignes **N-1** du PRM :
```
pu_fourniture  = Σ montant(supply)          / Σ kWh(supply)
pu_reseau_var  = Σ montant(network_variable) / Σ kWh(supply)
pu_autres_var  = Σ montant(autres variables) / Σ kWh(supply)
fixe_reseau    = Σ montant(gestion + comptage + soutirage fixe)
fixe_autre     = Σ montant(cta + abonnement)
```

### 7.4 Révision des prix (ce qui rend le budget « révisé »)
- **Ratio BPU** (fourniture) : pour chaque poste (BASE/HP/HC…), prix BPU ENGIE de l'année Y ÷ prix BPU N-1
  (`resolve_historical_bpu_price`), pondéré par les kWh du poste. Si non résolu (segment/poste manquant) →
  **1,0** (prix N-1 tenu), `bpu_available = false`.
- **Ratio TURPE** (réseau variable + fixe) : indice cumulé des évolutions moyennes HTA-BT
  (`TURPE_EVOLUTION_EVENTS`) à mi-Y ÷ mi-N-1. Si aucune évolution → **1,0**, `turpe_available = false`.
```
pu_variable = pu_fourniture × ratio_BPU  +  pu_reseau_var × ratio_TURPE  +  pu_autres_var
fixe        = fixe_reseau  × ratio_TURPE  +  fixe_autre
```

### 7.5 Conso attendue (N-1 ENEDIS + DJU thermosensible)
Régression linéaire sur l'historique **ENEDIS** mensuel du PRM (mois complets, année Y exclue) :
```
kWh_mois ≈ base + pente × DJU_chauffage_mois           (régression moindres carrés)
conso_mensuelle_attendue[m] = base + pente × DJU_normal[m]
conso_attendue_an           = Σ_m conso_mensuelle_attendue[m]
```
- `DJU_normal[m]` = moyenne historique du DJU chauffage du mois calendaire m (hors année Y).
- **Seule la part `pente × DJU` est climatique** ; la `base` (éclairage, bureautique, ventilation, froid
  alimentaire) est tenue → **pas de surcorrection** (≠ ratio DJU global du gaz).
- `part thermosensible = (Σ pente × DJU_normal) / conso_attendue_an` (affichée).
- **Fallbacks** : pente ≤ 0 ou historique trop court/plat → conso = somme ENEDIS N-1 (`conso_method = enedis_flat`) ;
  aucun ENEDIS → kWh facturés N-1 (`no_enedis`).

### 7.6 Prévision de référence, réalisé, atterrissage
```
variable_prevision   = conso_attendue_an × pu_variable
prevision_reference  = variable_prevision + fixe            (repère, PAS un budget contractuel)

realise              = Σ lignes fixe+variable des factures Y du PRM
mois_couverts        = mois réellement facturés en Y

atterrissage :
  - aucun réalisé Y            → = prevision_reference           (landing_method = prevision)
  - année Y close (today > Y)  → = realise                       (realise_complet)
  - sinon (année en cours)     → = realise
                                   + Σ conso_mensuelle_attendue[mois NON couverts] × pu_variable
                                   + (fixe_réalisé / mois_couverts) × nb_mois_restants   (mensuel)
ecart = atterrissage − prevision_reference
```
La projection du reste utilise la **conso mensuelle attendue** (modèle thermo) des mois non facturés →
cohérent, sans surcorrection climatique. Base = **mois réellement couverts** (le décalage de facturation
ne fausse pas le prorata).

### 7.7 Totaux et agrégat bâtiment
Totaux marché = somme des PRM. Agrégat bâtiment = somme des PRM d'un même `building_id`
(prévision / réalisé / atterrissage + nb PRM), PRM sans lien → « Non affecté ».

### 7.8 Signaux de fiabilité exposés
`enedis_available`, `bpu_available`, `turpe_available`, `conso_method`, `thermo_share`, `has_history`,
et par PRM le rattachement bâtiment — pour que l'utilisateur sache **à quel point** chaque chiffre est
révisé vs tenu à plat.

## 8. Proposition front (à valider avant code)
Voir la proposition détaillée en conversation (2026-07-03) : page `EngieBudgetReviseV1.tsx` clonée du gaz,
avec bascule **maille PRM / bâtiment**, colonnes conso attendue (thermo %) + prix réf (ratios BPU/TURPE),
bandeau de fiabilité (ENEDIS/BPU/TURPE), et emplacement réservé au **calque cible DALKIA**.
