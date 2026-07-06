# Atterrissage élec — « BPU jamais résolu » : diagnostic + décisions (avant code)

> Doc « fil du dev » — 2026-07-06. Objet : le prix de référence de l'atterrissage électrique promet une
> **fourniture révisée par ratio BPU** (`engie_elec_budget_revise._bpu_fourniture_ratio`), mais sur la
> prod (Sète, city 303) `bpu_available = False` pour **100 % des PRM** (ENGIE + EDF, 2025 & 2026) → on
> tombe TOUJOURS sur le fallback « prix dérivés du N-1 ». Décider AVANT de coder.

## 1. Constat (validation lecture seule sur prod, 2026-07-06)

- ENGIE : 268 PRM (segments C2=11, C4=56, C5=201). EDF : 402 PRM (C2=6, C4=31, C5=365).
- `load_historical_bpu_prices` renvoie bien des prix (ENGIE 32, EDF 491) → **la donnée existe**.
- Pourtant `resolve_historical_bpu_price(...)` renvoie `None` sur tous les PRM tracés.

## 2. Causes racines (≠ un simple bug de matching)

Le ratio BPU = Σ(kWh × prix_Y) / Σ(kWh × prix_N-1) exige, par PRM : un `segment` mappé + un `poste`
mappé + des prix BPU **pour l'année Y ET l'année N-1**, au bon `segment_code`.

**ENGIE**
- **B1 — un seul millésime BPU** : les prix ENGIE ne couvrent que **2026** (`valid_year` = {2026: 32}).
  Le ratio Y/N-1 est donc **structurellement impossible** (2025 : ni 2025 ni 2024 ; 2026 : 2025 manquant).
- **B2 — segments manquants** : les 32 prix ENGIE sont tous `segment_code = BATIMENT`. Les PRM C2 (11) et
  C4 (56) — 67 PRM, souvent les plus gros — n'ont **aucun** prix BPU correspondant.
- (Les postes fourniture ENGIE — hph/hch/hpe/hce/base — sont bien mappés : ce n'est pas le blocage.)

**EDF**
- **B3 — lignes fourniture sans poste** : `poste = None` sur **les 425 lignes supply** EDF →
  `POSTE_TO_BPU_PERIOD.get("")` = None → `resolve` = None quoi qu'il arrive. La fourniture EDF
  (éclairage public) n'est pas ventilée HP/HC dans les factures.
- **B4 — vocabulaire de segment divergent** : `historical_segment_code_for_site` produit
  `BATIMENT` / `C5_EP`, alors que l'import BPU EDF a généré `C5_BAT_1/2/4`, `ECLAIRAGE_PUBLIC`,
  `C5_BORNES`, `C5_BAT_RAE_*`, `INCONNU`… → les codes ne se rencontrent jamais.

## 3. Lecture

Le moteur n'est pas « cassé » : le **fallback N-1 est une dégradation raisonnable**. Le vrai défaut est
que **l'UI/le libellé affirment « révisé par ratio BPU » alors que ça n'arrive jamais** (trompeur), et
que le mécanisme BPU-ratio ne peut pas fonctionner avec la **forme actuelle** des données BPU élec
(millésime unique ENGIE, segments manquants, poste absent EDF, vocabulaire divergent).

## 4. Options

- **A — Honnêteté d'abord (léger, sûr, sans dépendance donnée)** : rendre le fallback explicite. Le
  moteur renvoie déjà `bpu_available` par PRM et un agrégat ; on l'expose : libellé « prix de référence =
  dérivé N-1 (BPU non applicable : N ans d'historique / segment absent) » + pastille. Aucune promesse
  fausse. N'améliore pas la précision, mais dit vrai.
- **B — Réparer le vocabulaire de segment EDF (code, moyen)** : harmoniser
  `historical_segment_code_for_site` avec les `segment_code` réellement produits par `import_bpu_xlsx`
  (mapping C5_EP↔ECLAIRAGE_PUBLIC, BATIMENT↔C5_BAT_*). Débloque une partie des PRM EDF **si** B3 est aussi
  traité (poste). Ne débloque pas ENGIE (millésime unique).
- **C — Charger la donnée BPU manquante (données, lourd, hors code)** : millésimes ENGIE ≥ 2 ans +
  segments C2/C4 ; clarifier la ventilation poste EDF. Dépend de fichiers sources à fournir.
- **D — Assumer le N-1 pour l'élec** : acter que la révision fourniture élec se fait par **prix dérivés
  N-1** (comme aujourd'hui) et **retirer la promesse BPU** de l'UI élec ; garder le BPU pour le contrôle
  de factures, pas pour l'atterrissage. Le plus simple conceptuellement.

## 5. Questions ouvertes (à trancher avant de coder)

1. **Q1 — Cible** : veut-on vraiment que l'atterrissage élec soit **révisé par BPU**, ou le **N-1 dérivé
   suffit-il** (auquel cas → Option A ou D, on arrête de promettre le BPU) ?
2. **Q2 — Donnée ENGIE** : dispose-t-on (ou peut-on charger) des BPU ENGIE **multi-millésimes** et des
   **segments C2/C4** ? Sans ça, B2/B1 restent bloqués quoi qu'on code.
3. **Q3 — EDF poste** : la fourniture EDF éclairage public a-t-elle un sens ventilée HP/HC, ou est-elle
   mono-poste (BASE) ? (détermine si B3 est réparable côté mapping ou est une limite de la facture).
4. **Q4 — Périmètre v1** : livrer **Option A seule** (honnêteté, rapide, aucun risque) maintenant, puis
   décider B/C plus tard ? ou tenter B (vocab EDF) dans la foulée ?

## 6. Recommandation

**Q4 → Option A d'abord** : rendre la vue honnête (le libellé ne doit pas prétendre une révision BPU qui
n'a pas lieu), calcul déjà disponible (`bpu_available`), zéro risque, zéro dépendance donnée. Traiter B
(vocab EDF) et C (données ENGIE) comme des incréments séparés une fois Q2/Q3 clarifiés côté métier.
