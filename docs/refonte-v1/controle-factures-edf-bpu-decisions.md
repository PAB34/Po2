# Contrôle de factures EDF au BPU — décisions (avant code)

> Doc « fil du dev » — 2026-07-07. Après le re-import BPU + recalcul, le contrôle BPU **ENGIE** est actif
> (143/185 factures, 2941 lignes, 4 écarts). Mais **EDF reste à 0/81** : la fourniture éclairage public /
> petits sites n'est **pas contrôlée** contre le BPU. Objectif : combler cette lacune.

## 1. Diagnostic (tracé sur vraies factures EDF prod, read-only)
Deux causes cumulées, dans le **résolveur partagé** `resolve_historical_bpu_price` :
1. **Poste vide** : les lignes fourniture EDF ont `poste = None` → `POSTE_TO_BPU_PERIOD.get("")` = None →
   la résolution s'arrête (pas de période). (Mono-poste : l'éclairage public / petits sites n'ont pas de
   ventilation HP/HC.)
2. **Vocabulaire de candidats** : les sites EDF sont des **bâtiments C5** (CONSERVATOIRE, FOYER…) →
   `historical_segment_code_for_site` renvoie `BATIMENT`, candidats `{BATIMENT, BATIMENT_BT36}`. Or c'est
   le **vocabulaire ENGIE** ; les prix bâtiment **EDF** sont sous `C5_BAT_1/2/4` (ancien marché) → absents
   des candidats → aucun match.

**Fait notable** : les factures EDF émises en 2026 portent la conso **2025** (décalage de facturation) →
`billed_on = 2025` → grilles EDF 2025 (dont `C5_BAT_1` BASE). Cohérent.

## 2. Fix retenu (additif, ne casse pas ENGIE)
Dans `invoice_bpu.py` (résolveur partagé, utilisé par le contrôle) :
1. **Poste vide → BASE** : si `poste` est vide, période = `BASE` (fourniture mono-poste).
2. **Candidats bâtiment EDF** : pour un site C5 bâtiment (`base == "BATIMENT"`), ajouter le vocabulaire
   ancien marché **`C5_BAT_1/2/4/BASE`** (en plus de `BATIMENT_BT36` pour ENGIE). Match EXACT, ADDITIF.

**Sûreté** :
- ENGIE inchangé : les lignes ENGIE ont un poste (jamais le branch vide) ; ENGIE n'a pas de prix
  `C5_BAT_*` (charge supplier-scopée) → nouveaux candidats sans effet.
- Pas d'ambiguïté à `BASE` : sur une année donnée, une seule variante bâtiment porte un prix BASE
  (2021 `C5_BAT_BASE`, 2022+ `C5_BAT_1`) → un seul match. Les variantes RAE (auto-conso, prix différent)
  **ne sont PAS ajoutées** pour éviter un faux double-match.

## 3. Validation empirique (avant code)
Simulation sur 56 lignes fourniture EDF réelles : **54/56 résolues** avec candidats `C5_BAT_*` + BASE
(billed_on = 55×2025, 1×2026). Les 2 restants = cas 2026 (grille EDF 2026 = seulement `ECLAIRAGE_PUBLIC`).

## 4. Plan
Code (2 modifs `invoice_bpu.py`) → tests (EDF résout, ENGIE non régressé) → validation lecture seule prod
avec le VRAI résolveur (contrôle recalculé) → staging → merge prod → **recalcul EDF**.

## 5bis. ⚠️ CORRECTION (2026-07-08) — la vraie cause = le PARSEUR, pas la donnée

Fausse piste initiale : « EDF non contrôlable car pas de prix unitaire ». **Faux.** En revérifiant le CSV
brut (`20260708_..._080726.csv`), la fourniture EDF est **entièrement détaillée** :
- kWh par poste : `consommation_kwh_base/hp/hc/hpsb/hcsb/hpsh/hcsh/pointe` ;
- montants par poste : `montant_htva_base/hp/hc/...` ; total : `total_fourniture_elec_ht_euros`.
- Vérif : FOYERS DES PECHEURS (C5) → base 937 kWh / 99,19 € = **105,9 €/MWh = BPU C5_BAT_1** ; THEATRE (C4)
  HPH → **107,96 €/MWh = BPU C4**.

**Le coupable = le parseur** `invoice_parsers/edf_csv.py` (ligne 125) : il émettait **une seule** ligne
fourniture (montant total), sans poste/quantité/prix unitaire → le contrôle sautait la ligne (`unit_price_ht`
absent).

**Fix parseur (`_supply_lines`)** : émettre une **ligne fourniture par poste** (quantité kWh + prix unitaire
= montant/kWh). Mapping saison : HPSB/HCSB → HPE/HCE (été), HPSH/HCSH → HPH/HCH (hiver). Repli BASE =
total fourniture / conso totale (sites sans détail poste, ex. certains C4). + le fix résolveur §2
(candidats `C5_BAT_*`).

**Validation end-to-end prod (read-only)** : re-parse + contrôle → EDF passe de **0 à 9 / 7 lignes BPU**
contrôlées par facture (quelques écarts à revoir). **Bonus** : l'atterrissage EDF gagne les vrais kWh/poste.

**Reste** : merge → **re-analyser** les factures EDF prod (le recompute doit RE-PARSER, pas seulement
rebâtir le contrôle depuis l'ancien parsed) → recalcul.

## 5. Question ouverte
- Q1 — Les sites EDF vraiment « éclairage public » (nom explicite) → segment `C5_EP` / `ECLAIRAGE_PUBLIC`.
  Les « petits sites bâtiment » → `C5_BAT_*`. La détection actuelle (nom contient « éclairage ») peut
  sous-classer certains ÉP en bâtiment. Acceptable en v1 (le prix fourniture bâtiment vs ÉP reste proche) ;
  à affiner si les 4 écarts ENGIE / EDF révèlent des désalignements.
