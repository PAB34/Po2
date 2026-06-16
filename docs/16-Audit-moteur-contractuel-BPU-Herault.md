# 16 — Audit du moteur contractuel BPU (Hérault Énergie)

> Date : 2026-06-15. Premier des deux audits de moteurs contractuels (l'autre = DPGF DALKIA).
> Principe acté : **le contrôle de facturation ne vaut que par la référence contractuelle qu'il compare.**
> Le moteur BPU est la **référence de prix** des factures du marché fournisseurs (EDF, ENGIE, TotalEnergies gaz).
> Audit sur l'existant (code + base), sans nouveau fichier source.

## 1. Rôle

Le marché Hérault Énergie (centrale d'achat groupé) fixe les prix unitaires via des **BPU** (bordereaux de
prix), par lot / millésime / avenant. Ces prix sont la **vérité contractuelle** contre laquelle on contrôle
chaque ligne de facture fournisseur (`BPU_PRICE_MISMATCH`). Sans BPU fiable et complet, le contrôle prix est
aveugle.

## 2. Ce que le moteur extrait (acquis)

Structure normalisée 5 tables (`models/bpu.py`) :

```
BpuDocument (supplier, valid_year, MS, lot, avenant, validité, extraction_status)
 ├─ BpuSegment        (type tension | site C1–C5 | usage ; turpe_tariff ; usage_label)
 │   └─ BpuTimePeriod (BASE/HPH/HCH/HPE/HCE/POINTE/HP/HC)
 │       └─ BpuPriceComponent (fourniture/capacité/cee/cee_precarite/cpb/go ; prix + unité + €/MWh normalisé)
 └─ BpuFixedCharge    (abonnements, branchement provisoire…)
```

- **Source de vérité** = XLSX canonique saisi/audité (`scripts/import_bpu_xlsx`, `extraction_status=manual`,
  `confidence=1.0`) ; gaz lot 7 via `scripts/import_bpu_gas_lot7`. Parser PDF en pause (`raw_text` conservé).
- **Volume prod** (réf. doc 08) : 17 documents / 49 segments / 138 périodes / **523 composantes** / 36 frais fixes.
- **Édition** : `/energie/bpu` (onglet Édition) expose la modification des composantes ; Timeline + TURPE + Documents.
- Hétérogénéité d'unités gérée (c€/kWh EDF vs €/MWh ENGIE) → normalisation `price_value_eur_per_mwh`.

→ **Le moteur d'extraction/stockage est solide et complet.**

## 3. Ce que le contrôle en consomme réellement (`services/invoice_bpu.py`)

Le contrôle facture tente d'abord un **rapprochement historique exact** dans `bpu_*`, sinon **repli** sur la
grille courante `BillingConfig` / `BillingBpuLine` (`invoice_analysis.py`).

Clé de rapprochement historique (`resolve_historical_bpu_price`) :
`segment_code` × `period_code` × `component_type` × **date de facturation dans la validité du document**.
Prudence : si plusieurs documents revendiquent la même clé pour la même date → **abstention** (pas de faux contrôle).

## 4. Écarts & fragilités — le « gros travail »

| # | Constat (dans le code) | Conséquence | Gravité |
|---|---|---|---|
| 1 | **Gaz non branché au contrôle historique** : `normalize_bpu_supplier` ne renvoie que `EDF`/`ENGIE` (sinon `None`). Le **gaz lot 7 TotalEnergies est importé mais jamais lu** par `resolve_historical_bpu_price`. | Le contrôle des **factures gaz** (Hérault) n'a **pas** de référence BPU active par ce chemin. | **Élevée** (bloque le P0 gaz) |
| 2 | **Couverture segment partielle** : `historical_segment_code_for_site` ne mappe que `C1–C4` et `C5` **uniquement si « éclairage »** (`C5_EP`). | Le **C5 « bâtiment »** (gros du parc) n'est jamais rapproché en historique → repli systématique sur `BillingConfig`. | **Élevée** |
| 3 | **Deux sources de prix** : `bpu_*` (historique exact) vs `BillingConfig`/`BillingBpuLine` (courant, repli). Le contrôle utilise les deux. | On ne sait pas toujours **quelle référence a servi** ; risque d'incohérence et d'audit difficile. | Moyenne |
| 4 | **Composantes partielles** : mapping facture→BPU limité à `fourniture/capacité/cee/go`. **CEE précarité** et **CPB** non mappés. | Ces composantes ne sont pas contrôlées contre le BPU. | Moyenne |
| 5 | **Frais fixes non contrôlés** : `BpuFixedCharge` (abonnements) stockés mais pas confrontés aux factures. | L'abonnement facturé n'est pas vérifié vs contrat. | Moyenne |
| 6 | **Lisibilité de la référence** : pas de surface claire « cette ligne a été contrôlée avec tel BPU (doc/lot/avenant/date) ». | L'utilisateur/compta ne trace pas la preuve contractuelle du contrôle. | Moyenne |
| 7 | **Provenance** : tout repose sur la saisie XLSX canonique (parser PDF en pause). | Mise à jour = re-saisie XLSX ; pas d'ingestion auto d'un nouveau BPU. | Faible (assumé) |

## 5. Plan de renforcement proposé (priorisé)

**R1 — Brancher le gaz sur le contrôle BPU (P0). ✅ FAIT (commit 724db4d).**
`normalize_bpu_supplier` reconnaît désormais `TOTAL*` → `TOTALENERGIES` ; `historical_segment_code_for_site`
mappe les profils T1–T4 ; `INVOICE_COMPONENT_TO_BPU_COMPONENT` couvre `cee_precarite` et `cpb`.
`resolve_historical_bpu_price` est opérant pour TotalEnergies (T*/BASE). Fichier BPU historique unifié local
(`extraction_tarifs_BPU_herault.xlsx`) = élec + gaz lot 7.

**R2 — Couvrir le C5 « bâtiment ». ✅ FAIT (commit cc87b1d).**
`historical_segment_code_for_site` retourne `BATIMENT` pour tout C5 hors éclairage public → match avec le
segment_code stocké en base (ENGIE Lot 1 2026). L'éclairage public (C5_EP) reste inchangé.

**R3 — Clarifier les deux sources. ✅ FAIT.**
Le contrôle expose désormais `bpu.fallback_source` (`historical` / `canonical_xlsx` / `configured` / `mixed`)
+ `historical_documents` enrichis du fournisseur. Le détail de facture affiche « Référence prix BPU utilisée »
avec le nombre de lignes par source et la liste des documents historiques. `bpu_*` reste la source de vérité
prioritaire, `BillingConfig` le repli explicite et tracé.

**R4 — Compléter composantes + frais fixes. ✅ FAIT.**
- *Composantes* : `_bpu_component_field` mappe désormais `cee_precarite`/`cpb` → la chaîne de contrôle laisse
  passer ces composantes vers le BPU historique. Note : `BillingBpuLine` ne porte pas ces colonnes, donc le
  contrôle ne passe que par l'historique `bpu_*` ; côté **élec** ces composantes n'existent pas (gaz lot 7
  uniquement) → readiness sans impact ENGIE.
- *Frais fixes* : nouveau `load_bpu_fixed_charges` + `resolve_fixed_charge` (abstention si montants divergents,
  respect de la fenêtre de validité). `_check_bpu_fixed_charges` détecte par libellé les seuls frais fixes
  listés au BPU (branchement provisoire, contrat temporaire — pas l'« abonnement » générique = part fixe
  TURPE), compare le €/mois facturé (`BPU_FIXED_CHARGE_MISMATCH`, non bloquant) et **expose les frais fixes
  du contrat** (`fixed_charges.contract_charges`) pour la traçabilité.
  ⚠️ Détection par libellé à valider sur une vraie facture comportant un branchement provisoire.

**R5 — Traçabilité de la référence contractuelle. ✅ FAIT.**
`historical_documents` expose désormais `amendment_number`, `valid_from`, `valid_to`. Le détail de facture
affiche « <fournisseur> <année> lot <n> avenant <n> (valide du … au …) — <fichier> » par document mobilisé.

## 6. Arbitrages tranchés
1. **Ordre** : R1 gaz traité en premier (débloque le P0 gaz Hérault), puis R2, puis R3. ✅
2. **Convergence des 2 sources** : on garde le repli `BillingConfig` mais on le **trace explicitement** (R3) ;
   `bpu_*` reste prioritaire. Bascule vers source unique reportée tant que l'historique n'est pas exhaustif.
3. **Profils gaz lot 7** : confirmés T1–T4, composantes fourniture/CEE/CEE précarité/CPB/GO (cf. fichier source). ✅

> Suite : même audit pour le **moteur DPGF DALKIA** (doc 17), puis cadrage du **moteur eau SUEZ** (à créer).
