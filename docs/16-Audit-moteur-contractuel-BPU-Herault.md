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

**R1 — Brancher le gaz sur le contrôle BPU (P0).**
Étendre `normalize_bpu_supplier` + le mapping segment/composante au gaz (profils T1–T4 du lot 7, composantes
fourniture ferme/CEE/CEE précarité/CPB/GO). Rendre `resolve_historical_bpu_price` opérant pour TotalEnergies.

**R2 — Couvrir le C5 « bâtiment ».**
Étendre `historical_segment_code_for_site` au C5 hors éclairage (mapping vers le bon segment BPU), pour sortir
ce parc du repli `BillingConfig`.

**R3 — Clarifier les deux sources.**
Décider la convergence `bpu_*` ↔ `BillingBpuLine` : faire de `bpu_*` la source unique de vérité, `BillingConfig`
ne servant qu'au calcul courant ; et **exposer dans le contrôle quelle référence (doc/lot/avenant) a servi**.

**R4 — Compléter composantes + frais fixes.**
Mapper CEE précarité / CPB ; ajouter le contrôle des abonnements (`BpuFixedCharge`) vs lignes d'abonnement facturées.

**R5 — Traçabilité de la référence contractuelle.**
Afficher sur la facture/le rapport la preuve : « contrôlé avec BPU <fournisseur> <lot> <avenant> valide du … au … ».

## 6. À arbitrer
1. **R1 gaz** : on attaque d'abord le branchement gaz (débloque le P0 gaz Hérault), ou d'abord R2 (C5 bâtiment, gros volume élec) ?
2. **R3 convergence des 2 sources** : on acte `bpu_*` comme source unique de vérité dès maintenant, ou on documente et on garde le repli encore un temps ?
3. **Profils gaz lot 7** : confirmer la grille (T1–T4, composantes) attendue pour le contrôle gaz Total.

> Suite : même audit pour le **moteur DPGF DALKIA** (doc 17), puis cadrage du **moteur eau SUEZ** (à créer).
