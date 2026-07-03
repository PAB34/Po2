# Budget révisé EDF éclairage public — décisions (fixe / variable, maille PRM)

> Rapport « fil du dev » — 2026-07-03. Jumeau de `engie-elec-revise-decisions.md` : même moteur élec
> (fixe/variable, BPU + TURPE, réalisé + atterrissage), appliqué au tier **EDF**. Écrit AVANT de coder.

## 1. État des lieux (audit staging 2026-07-03)
- EDF = **81 factures / 402 PRM**, années **2023→2026** (import CSV `edf_csv_import`). Donc le **N-1 existe**
  (contrairement à ENGIE) → la « prévision de référence » sera enfin significative.
- Segments : **C5 = 365 PRM** (éclairage public + petits sites), C4 = 31, C2 = 6.
- Codes de lignes EDF 2025 : `supply`, `cspe`, `network_fixed_total`, `cee`, `cta`, `subscription`,
  `capacity`, `network_overrun`. **Aucune anomalie soutirage** (le bug prix/montant était propre au
  fichier XLSX ENGIE feuille C5).

## 2. Décisions actées (validées utilisateur)

### D1 — Réutiliser le moteur élec (généralisation, pas duplication)
Le moteur ENGIE (`engie_elec_budget_revise`) devient **générique** (`supplier` + `conso_model`), avec deux
entrées : `build_engie_elec_budget_revise` (inchangée) et `build_edf_elec_budget_revise`. BPU/TURPE, réalisé
fixe/variable, agrégats (regroupement, bâtiment), atterrissage : **identiques**. Filtre = `supplier=EDF`.

### D2 — Conso attendue = N-1 reconduit + **profil saisonnier photopériode** (pas de DJU)
L'éclairage public **n'est pas thermosensible** (il suit la durée de nuit, pas le chauffage). Donc :
- **annuel** = conso N-1 reconduite (ENEDIS N-1 si dispo, sinon kWh facturés N-1) — parc ~stable d'une année sur l'autre ;
- **mensuel** (pour la projection d'atterrissage) = `annuel × poids_photopériode[mois]`, où le poids ∝ **heures
  de nuit du mois** (profil ~Sète, lat. 43,4°N) → plus de conso en hiver, moins en été.
- `conso_method` = `photoperiod` (ou `photoperiod_n1` sans ENEDIS). `thermo_share` = 0 (non applicable).

### D3 — Part fixe réseau : `network_fixed_total` conditionnel
EDF ne fournit **que** `network_fixed_total` (pas les composantes gestion/comptage/soutirage fixe). Or, pour
ENGIE, `network_fixed_total` **duplique** ces composantes (donc ignoré). Règle robuste **par PRM** :
- si des composantes fixes réseau existent (ENGIE) → on **ignore** `network_fixed_total` ;
- sinon (EDF) → `network_fixed_total` **compte** comme part fixe réseau.
→ Marche pour les deux fournisseurs sans code spécifique par supplier.

### D4 — Prix de référence, réalisé, atterrissage : identiques à ENGIE
Prix dérivés du N-1 par PRM, révisés BPU (fourniture, `load_historical_bpu_prices(db,"EDF")`) + TURPE
(réseau). Réalisé = lignes EDF année Y (fixe/variable). Atterrissage = réalisé + reste projeté sur les mois
NON couverts (conso mensuelle attendue photopériode × prix de référence).

## 3. Livrables
1. Généralisation `engie_elec_budget_revise.py` : `supplier` + `conso_model` + `network_fixed_total`
   conditionnel + profil photopériode + `build_edf_elec_budget_revise`.
2. Route `GET /api/marches/edf-elec-budget-revise?year=` (schéma réutilisé).
3. Front : composant élec générique (`supplier` en prop) branché sur les tiers ENGIE **et** EDF (remplace le
   dernier `ComingSoon`).
4. Tests ciblés (sqlite) : conso photopériode (répartition mensuelle), `network_fixed_total` compté pour EDF /
   ignoré pour ENGIE, réalisé partiel→atterrissage EDF.

## 4. Hors périmètre v1
- Modèle astronomique fin (on garde un profil mensuel statique approché pour Sète).
- Extinction nocturne partielle / télégestion (impact conso non modélisé).
