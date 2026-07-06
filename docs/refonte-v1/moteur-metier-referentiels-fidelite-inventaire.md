# Gate fidélité — inventaire des référentiels en base (staging)

> 2026-07-06. Étape 1 de la « gate fidélité » (cf. `moteur-metier-referentiels-decisions.md` §4bis).
> Inventaire **lecture seule** de la base staging (copie prod) : que contient réellement chaque
> référentiel, et quel est son statut d'extraction. La comparaison **poste par poste aux documents
> sources** (fournis par l'utilisateur) reste à faire.

## Bonne nouvelle : pas d'OCR incertain sur le BPU élec
Les 17 documents BPU élec (EDF/ENGIE) sont tous en `extraction_status = manual`, confiance 1.000 →
**saisie/validation manuelle, pas d'extraction OCR devinée**. Le risque « OCR faux » est donc faible ;
le risque résiduel = erreur de transcription humaine (à contrôler par échantillon vs source).

## BPU électricité (bpu_documents) — 17 docs
- **EDF** : 16 docs, années 2021→2026, lots 1/2/3 ; avenants présents (2025 : L1 av6, L2 av5, L3 av5).
  Composantes de prix présentes (10 à 76 par doc).
- **ENGIE** : **1 seul doc** (2026, lot 1, 32 composantes). Très pauvre — vérifier si d'autres
  années/lots manquent.
- ⚠️ **Doublons potentiels** : EDF 2021 lot 3 (×2), EDF 2022 lot 3 (×2) — soit avenants non distingués,
  soit imports dupliqués. À lever lors de la comparaison aux sources.

## BPU gaz lot 7 (gas_bpu_prices) — 2026 seulement
- 4 profils (T1–T4), tous avec `fourniture_ht_mwh`. Pas d'historique d'années. Vérifier si normal.

## DPGF DALKIA base (cpe_dalkia_ref_imports)
- **Lot 1** : 1 version active (72 sites) + 2 remplacées conservées. Fichier
  `01_24BT039_L1_AE_ANNEXES_OFFRE_FINALE.xlsx`.
- **Lot 2** : 1 version active (4 sites, `..._MISE_AU_POINT.xlsx`) + 4 remplacées.
- ⚠️ **Actes non qualifiés** : `acte_type` / `date_effet` **vides sur tous les imports** → le journal
  montre les versions mais pas leur nature (avenant n°X, date d'effet). L'onglet Référentiel affichera
  « — » en colonne Acte tant que ce n'est pas renseigné. À enrichir (patch acte a posteriori existe déjà :
  `PATCH /cpe/dalkia-ref/imports/{id}/acte`).

## DPGF P1 gaz révisé (cpe_dpgf_p1_lines) — complet
- **3 niveaux tous présents** : `contrat` (522) → `rev_temp` (522) → `rev_temp_prix` (522). Révision
  officielle (T° + prix OS3) bien chargée. 1 import.

## Reste à faire (comparaison aux sources)
Comparer, sur un échantillon, les valeurs affichées aux **documents de référence fournis par
l'utilisateur** : prioriser (1) les doublons EDF, (2) le doc ENGIE isolé, (3) quelques postes DPGF base
Lot 1/2, (4) les 3 niveaux P1 gaz vs DPGF P1 révisé DALKIA.
