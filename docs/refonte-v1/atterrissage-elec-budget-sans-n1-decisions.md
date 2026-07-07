# Atterrissage élec — budget de référence sans N-1 & réalisé partiel : audit + décisions

> Doc « fil du dev » — 2026-07-07. Fait suite à l'audit de l'atterrissage élec (après la révision BPU par
> typologie, PR #46 en prod). Deux constats à traiter (« option 2 »). Décider AVANT de coder.

## 1. Finding A — ENGIE : budget de référence ≈ 0 (marché démarré en 2026)

**Constat (prod, city 303)** : factures ENGIE présentes **uniquement en 2026** (268 PRM ; 0 en 2025).
La « prévision de référence » (`_build_point` / `_reference_from_lines`) dérive **prix unitaires + parts
fixes des lignes de factures N-1**. Sans facture 2025 → `ref["kwh"]=0`, `pu_fourniture=0`,
`fixe_reseau=0` → `prevision_reference ≈ 0` pour ~tous les PRM (total ~136 € pour 267 PRM), alors que le
réalisé 2026 est ~725 k€. L'« écart / référence » affiché (+930 k€) est donc **trompeur**.

**Nature** : limite de MODÈLE (le budget de référence suppose un historique de factures N-1), pas un
manque de données brutes — la conso ENEDIS N-1 existe pour ~176/267 PRM, et on a désormais le **BPU par
typologie** (PR #46).

**Piste (à valider)** : quand les factures N-1 sont absentes, bâtir la référence **sans N-1** :
- fourniture = **prix BPU du marché en vigueur** (grille par typologie/poste, déjà indexée par
  `build_bpu_fourniture_index`) × conso attendue ;
- réseau = TURPE (déjà dispo) ; taxes/part fixe = barèmes ou approximation ;
- conso attendue = **ENEDIS N-1** (déjà utilisée par `_expected_consumption`).
→ extension naturelle de la brique typologie B+C. Donne à ENGIE 2026 une vraie référence budgétaire.

**Questions ouvertes** :
- Q1 — Périmètre : ne déclencher le mode « BPU-référence » que si `ref["kwh"]==0` (pas de N-1) ? ou
  généraliser (cohérence avec les marchés qui ont un N-1) ?
- Q2 — Part fixe (abonnement/CTA/gestion) sans N-1 : barème BPU (`load_bpu_fixed_charges`) ou laisser 0 et
  ne chiffrer que le variable ? (impact modéré, le variable domine).
- Q3 — Que faire des PRM sans ENEDIS N-1 (91/267) : référence à 0 assumée + pastille, ou pro-rata du
  réalisé ?

## 2. Finding B — EDF : réalisé 2026 quasi vide (retard d'import)

**Constat** : EDF facturé 356 PRM en 2025, **7 seulement en 2026** ; dernière période importée =
2026-05-15. L'atterrissage EDF 2026 est donc ~100 % projection.

**Nature** : **opérationnel / données** (factures EDF éclairage public 2026 non importées), pas un bug de
code. L'atterrissage projette correctement ; il se remplira quand les factures 2026 seront chargées.

**Action** : importer les factures EDF 2026 (CSV éclairage public) via le flux existant
(`edf_csv_import`). Dépend de la **disponibilité des fichiers** côté utilisateur. Pas de code à écrire a
priori (sauf si le parseur bute sur un nouveau format).

**Question ouverte** :
- Q4 — Les factures EDF 2026 sont-elles disponibles (fichiers CSV) à importer, ou pas encore émises ?

## 3. Recommandation
- **A = chantier de code** à forte valeur (rend le budget ENGIE 2026 réel) → à cadrer/coder.
- **B = action données** (import) → dépend de fichiers utilisateur ; à confirmer (Q4) avant tout.
- Priorité : **A d'abord** (autonome, code), B en parallèle si les fichiers existent.
- Rappel : **Task #1 (import granulaire typologie 2026, résidu ~3 %)** reste à faire après.
