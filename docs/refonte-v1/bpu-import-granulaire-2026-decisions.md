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

## 4bis. Vérif empirique prod (2026-07-07) → change l'approche
Test `resolve_historical_bpu_price` sur sites ENGIE : **C5 → matché 5/5** (code `BATIMENT`), **C2/C4 →
0/5** (codes `C2`/`C4`, absents des prix ENGIE qui n'ont que `BATIMENT`). Donc :
- ⚠️ Le **canonique par regroupement** (§4) fusionnerait C1/C2/C3 (prix DIFFÉRENTS : 54,8 / 84,5 / 90,6) →
  faux mismatches côté contrôle. **ABANDONNÉ.**
- Bon design = **jeu de codes candidats (match EXACT multiple, additif)** : le site propose {code actuel}
  ∪ {traduction classe→nouveau marché}. `BATIMENT_*` en plus, jamais en remplacement → **aucune
  régression** (C5 garde `BATIMENT`, gagne `BATIMENT_BT36`) et **gain** (C2→`BATIMENT_HTA`, C4→`BATIMENT_BT`
  désormais matchés). La précision C1/C2/C3 est préservée (pas de fusion).
- Atterrissage : **aucun changement de code** — `_canonical_typology` mappe déjà `BATIMENT_HTA/BT/BT36`,
  donc après re-import un PRM C2 tape `BATIMENT_HTA` (fin du repli collapse `BUILDING_ANY`).
- Éclairage public : **non granularisé** (mono-typologie) ; candidat {`C5_EP`, `ECLAIRAGE_PUBLIC`}.

## 4. Approche INITIALE (canonique) — abandonnée, voir §4bis
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

## 6bis. RÉALISÉ + VALIDATION STAGING (2026-07-07)

Code (branche `feat/bpu-import-granulaire`) : `_normalize_segment` + `_tension_bucket` (import granulaire
bâtiment 2026) ; `_segment_code_candidates` + match `in candidates` dans `resolve_historical_bpu_price`
(partagé). Atterrissage : aucun changement. 43 tests verts.

**Re-import = `import_xlsx(path, force=True)`** : `force=True` fait un **remplacement propre**
(delete doc existant + recreate) → pas de doublon, l'ancien `BATIMENT` collapse disparaît. **Fichier =
`extraction_tarifs_electricite_BPU.xlsx`** (EDF+ENGIE, **sans** TotalEnergies) → évite d'ajouter par
erreur le doc gaz TE (le fichier `_herault` l'ajouterait — écarté).

**Validation staging (code déployé + re-import elec)** :
- ENGIE segments : `BATIMENT` → **`BATIMENT_HTA` / `BATIMENT_BT` / `BATIMENT_BT36`** (collapse supprimé).
- Contrôle factures : **C2 0→4/5, C4 0→4/5, C5 5/5** (gain net, zéro régression ; le 5ᵉ poste = BASE
  absent des grilles 4-saisons HTA/BT, normal).
- Atterrissage ENGIE 2026 : 267/267 BPU appliqués, prév. réf. 1,152 M€ → **1,135 M€** (affinage ~1 %).
- EDF inchangé (16 docs). Aucun doc TE ajouté avec le fichier élec.

**Procédure prod (après merge du code)** : 1) merge → déploie le nouveau code ; 2)
`import_xlsx(extraction_tarifs_electricite_BPU.xlsx, force=True)` sur prod ; 3) vérifier segments +
contrôle + atterrissage. Fenêtre merge→reimport sans régression (C5 reste matché via `BATIMENT`).

## 7. Recommandation
Approche §4 (canonique, additive) = la seule qui supprime le résidu SANS casser le contrôle. Coût modéré,
gain faible mais réel. Procéder avec les tests §5 comme filet. Sinon, statu quo assumé (résidu < 0,5 %).
