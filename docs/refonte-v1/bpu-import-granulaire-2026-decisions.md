# Task #1 — import granulaire des typologies 2026 (résidu ~3 %) : audit + décisions

> Doc « fil du dev » — 2026-07-07. Objectif : supprimer le résidu d'imprécision de la révision BPU élec
> (PR #46) dû au **collapse** des typologies « Bâtiment » 2026 sous un seul `segment_code = BATIMENT`.
> Touche l'import BPU **et** le résolveur partagé avec le contrôle de factures → prudence.

## 1. Rappel du problème
`import_bpu_xlsx._normalize_segment` teste `Bâtiment` AVANT la tension → les 6 variantes 2026 (HTA / BT>36 /
BT≤36 profils) sont écrasées sous `BATIMENT` (contrainte unique `(document_id, segment_code)`). Il ne reste
que 8 postes « mélangés ». Côté atterrissage, on résout via `BUILDING_ANY` (grille collapse).

## 2. Gain réel quantifié (avant de décider)
Le collapse a, par chance, conservé un prix par poste issu de profils DISTINCTS (BASE←SDT CU, HP/HC←MUDT,
4-saisons←CU4, POINTE←HTA). Donc :
- **C5 (BT≤36) bâtiments = majorité des PRM** : `BUILDING_ANY` renvoie déjà les prix BT≤36 → **résidu 0**.
- **C2/C4 (HTA/BT>36) bâtiments = 67 PRM sur 267** : leur prix 2026 devrait venir de la grille HTA/BT>36,
  mais `BUILDING_ANY` renvoie le profil survivant → écart **~3 % par poste** sur la fourniture.
- Impact total estimé : fourniture ≈ 60 % du variable × 3 % × (67/267 PRM) ≈ **< 0,5 % de l'atterrissage
  ENGIE**. Réel mais faible.

## 3. Contrainte : résolveur PARTAGÉ avec le contrôle de factures
`resolve_historical_bpu_price` (utilisé par `invoice_analysis`) matche par **`segment_code` EXACT** via
`historical_segment_code_for_site` (retourne `BATIMENT` pour un site bâtiment C5). Si l'import produit
`BATIMENT_BT36`, le match exact échoue → le contrôle **perd la couverture** des factures bâtiments 2026
(pas de crash, mais `historical_checked_lines` chute). **Régression silencieuse à éviter.**

## 4. Approche retenue (robuste, additive) — à valider
Rendre la résolution **par typologie canonique** au lieu d'un `segment_code` exact, dans le résolveur
partagé, de façon **additive** (n'enlève aucun match existant, en ajoute) :
1. **Import** : `_normalize_segment` produit `BATIMENT_HTA/BT/BT36` (et `ECLAIRAGE_PUBLIC_*`) selon la
   colonne Tension (helper `_tension_bucket` : `HTA` / `>36`→BT / sinon `36`→BT36).
2. **Résolveur partagé** : `resolve_historical_bpu_price` matche si la **typologie canonique** de la
   référence == celle du site (HTA / BT_SUP36 / BT_INF36 / EP / BORNE), au lieu de l'égalité stricte de
   `segment_code`. Mutualiser la fonction `canonical_typology` (déjà dans `engie_elec_budget_revise`).
   Conserver la logique de désambiguïsation existante (année/avenant).
3. **Atterrissage** : déjà compatible (`_canonical_typology` gère `BATIMENT_HTA/BT/BT36`) → bénéficie
   automatiquement de la granularité, `BUILDING_ANY` devient un simple repli.
4. **Re-import BPU** sur prod (idempotent, recrée les segments avec les nouveaux codes).

## 5. Garde-fous / tests
- **Tests contrôle factures** : `test_invoice_analysis*` — vérifier que `historical_checked_lines` ne
  RÉGRESSE pas (idéalement augmente) sur un échantillon ENGIE/EDF 2026. Ajouter un test canonical match.
- Validation lecture seule prod AVANT re-import : simuler le nouvel index et comparer le nb de lignes
  contrôlées + le nouvel atterrissage (écart attendu < 0,5 %).
- Re-import prod = écriture : le faire hors heures, vérifier les comptes de segments avant/après.

## 6. Questions ouvertes
- Q1 — Le gain (< 0,5 %) justifie-t-il le refactor du résolveur partagé + re-import ? (utilisateur a
  demandé « précision maximale » → oui, mais acter le coût/risque).
- Q2 — Désambiguïsation canonique : si plusieurs références partagent la typologie (ex. C5_BAT_1/2/4, même
  prix), prendre la plus récente / n'importe laquelle (prix identiques) — à confirmer sur données.

## 7. Recommandation
Approche §4 (canonique, additive) = la seule qui supprime le résidu SANS casser le contrôle. Coût modéré,
gain faible mais réel. Procéder avec les tests §5 comme filet. Sinon, statu quo assumé (résidu < 0,5 %).
