# Demande comptable — audit P1 et fonction dans la LC

Date : 2026-07-29
Page : `/refonte-v1/factures` → **Demande comptable**
Classeur contrôlé : `saas/energie/DALKIA/COMPTABILITE/rapport-controle-comptable-2026-07-24 (2).xlsx`

## 1. Existant vérifié

### Classeur réel

- Feuille `DALKIA` : 468 lignes de données + total.
- Filtre `POSTE FACTURE = P1/P1.EL` : 43 lignes, dont 41 P1 gaz et 2 P1.EL.
- Les 43 lignes ont une LC non vide.
- Exemple Vallon, ligne 324 :
  - facture `0001E2607QRY6` ;
  - source : `835,37 EUR HT`, TVA `20 %`, prix de base `74,17`,
    prix/forfait révisé `3 341,49` ;
  - rapport : base `22,25 EUR TTC`, révision `980,19 EUR TTC`,
    total `1 002,44 EUR TTC` ;
  - LC actuelle : `BATI-60621-XSCO-ALSH`.

### Backend

- Génération : `saas/backend/app/services/comptable_report.py`,
  fonction `_write_dalkia_comptable_sheet`.
- Formule actuelle pour toutes les lignes :
  `dont révision = montant × (révisé - base) / révisé`.
- Cette formule est valide pour P2/P3, où base et révisé sont deux forfaits
  annuels comparables.
- Elle est invalide pour P1 :
  - `base_price` est un prix unitaire gaz en EUR/MWhPCS ;
  - `revised_price` est un forfait annuel révisé ;
  - le ratio mélange donc deux unités différentes.
- La fonction comptable est volontairement exclue de `_cpe_report_lc` depuis le
  commit `a6afc66`, en application du retour du 2026-07-24 désormais contredit.

### Frontend et API

- Le frontend transmet seulement les worklists au endpoint
  `POST /api/billing/comptable/rapport-controle.xlsx`.
- Ni le drawer ni l'API ne transforment les montants ou la LC.
- Le défaut est donc localisé dans le service backend de génération XLSX.

### Production en lecture seule

- Les 41 lignes P1 gaz du classeur ont toutes une référence contractuelle P1
  active par site et année.
- Exemple Vallon :
  - prix de base porté par la facture : `74,17 EUR HT/MWhPCS` ;
  - quantité contractuelle : `38 MWhPCS` ;
  - part fixe OS3 : `668,11 EUR HT` ;
  - base annuelle effective OS3 : `74,17 × 38 + 668,11 = 3 486,57 EUR HT` ;
  - forfait annuel révisé de la ligne facture : `3 341,49 EUR HT` ;
  - montant facturé trimestriel : `835,37 EUR HT`.
- Décomposition cohérente et additive :
  - base TTC proratisée : `1 045,97 EUR` ;
  - révision TTC : `-43,53 EUR` ;
  - total TTC : `1 002,44 EUR`.
- La première proposition à `1 210,82 / -208,38 EUR` utilisait à tort la base
  du marché initial (`4 036,07 EUR HT`) ; elle est remplacée par la base OS3.
- Les deux lignes P1.EL sont non révisées : base = total et révision = 0.
- La matrice de production contient la fonction `331` pour le Vallon.

## 2. Décisions confirmées

- **D1.** P2/P3 : conserver la décomposition actuelle, fondée sur deux forfaits
  annuels comparables.
- **D2.** P1 gaz : reconstruire la base annuelle effective OS3 avec le prix de
  base porté par la facture, la quantité contractuelle du référentiel maître et
  la part fixe du DPGF P1 actif (`rev_temp_prix`) ; proratiser cette base au
  montant facturé via `montant_ht / revised_price`, puis calculer la révision
  par différence.
- **D3.** P1.EL : base TTC = montant TTC, révision TTC = 0.
- **D4.** Si une référence P1 gaz manque, ne pas produire de faux montant :
  laisser base/révision vides et signaler la référence manquante dans
  `POINT A CORRIGER`.
- **D5.** Réintroduire la fonction dans la LC DALKIA immédiatement après le
  gestionnaire. Exemple : `BATI-331-60621-XSCO-ALSH`.
- **D6.** Ne pas modifier la LC ENGIE/EDF dans ce correctif.

## 3. Confirmation utilisateur

Validation reçue le 2026-07-29 pour les trois points :

1. base P1 gaz proratisée au montant facturé ;
2. fonction ajoutée dans toutes les LC DALKIA, immédiatement après le gestionnaire ;
3. révision P1 négative autorisée lorsque le forfait révisé est inférieur à la base.

Après contre-vérification, l'utilisateur confirme explicitement que l'OS n°3
doit servir de base pour P1 ; cette précision remplace la base du marché initial.

## 4. Implémentation et tests

- P1 gaz avec référence : calcul base/révision/total et égalité additive.
- P1.EL : base = total, révision = 0.
- P1 gaz sans référence : cellules vides + point à corriger.
- LC DALKIA : fonction placée après le gestionnaire ; opération toujours limitée
  à P3/P3.4.
- Non-régression P2/P3 et génération complète du rapport.
- Résultat : `17 passed` sur `tests/test_comptable_report.py` le 2026-07-29.
