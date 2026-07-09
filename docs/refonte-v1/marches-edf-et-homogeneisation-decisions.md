# Décisions — page /refonte-v1/marches : EDF (cohérence + factures bloquées), renommage, homogénéisation colonnes

> Doc « fil du dev » — 2026-07-09. Existant audité (front + back + **données réelles staging**,
> city_id=303 Sète) AVANT toute modif. 4 sujets remontés par l'utilisateur. Branche de travail à créer.

## Contexte — structure actuelle de la page (vérifié)

`/refonte-v1/marches` = `MarketsBudgetPageV1` : 4 tiers × sous-vues.

| Tier | Composant atterrissage | Sous-vues |
|---|---|---|
| DALKIA CPE | `ContractBudgetLandingV1` | atterrissage · cible · indices |
| Gaz TotalEnergies | `GasBudgetReviseV1` | atterrissage · indices |
| ENGIE (élec) | `ElecBudgetReviseV1 supplier=ENGIE` | atterrissage · indices |
| EDF (élec) | `ElecBudgetReviseV1 supplier=EDF` | atterrissage · indices |

Back atterrissage élec = `services/engie_elec_budget_revise.py` (générique ENGIE/EDF ;
EDF = conso « photopériode », ENGIE = « thermo DJU »).

---

## Sujet #1 — EDF « incohérent » dans l'atterrissage

### Constats sur données staging (EDF, city 303)
- **96 factures EDF** importées : 71 en `review`, 25 `valid`.
- Répartition par année de période : 2023 = 2 · 2024 = 4 · **2025 = 57 (186 k€)** · **2026 = 8 (8,4 k€)** ·
  **25 factures SANS période** (`period_start` NULL, total ≈ −559 € → avoirs/rééditions).
- La vue atterrissage s'ouvre par **défaut sur l'année courante = 2026**, or 2026 n'a que **8 factures**
  (facturation très partielle / décalée). Le « réalisé à date » est donc minuscule et l'atterrissage est
  presque entièrement une **projection** du N-1 (2025) reconduit par photopériode.
- `SUPPLIER_CONTRACT_MISMATCH` massif (voir #4) = PRM EDF rattachés à un autre fournisseur dans le
  référentiel ENEDIS → risque de conso attendue / rattachement bâtiment incohérents par PRM.

### Hypothèses de l'incohérence (à confirmer avec l'utilisateur)
1. L'utilisateur regarde **2026** (défaut) où la donnée est très partielle → chiffres « faux » alors que
   c'est un problème de **période affichée**, pas de calcul.
2. Les **25 factures sans période** (avoirs) ne sont rattachées à aucune année → soit ignorées, soit mal
   comptées → écart.
3. Mismatch référentiel ENEDIS (PRM EDF vus ENGIE) → conso attendue / prévision de référence biaisées.

### Questions #1
- **Q1.1** — Quelle **année** regardais-tu (2026 par défaut, ou 2025) et quel chiffre précis t'a semblé
  incohérent (atterrissage total ? un PRM ? la prévision de référence ?) ? *(oriente le diagnostic)*
- **Q1.2** — Défaut d'année : garder l'**année courante**, ou basculer sur la **dernière année avec des
  factures « significatives »** (ex. 2025) tant que l'année en cours est trop partielle ?
- **Q1.3** — Traitement des **avoirs / factures sans période** dans l'atterrissage : les rattacher à
  l'année d'émission, ou les exclure explicitement avec un compteur visible ?

---

## Sujet #2 — la page s'appelle « Marchés » mais ne traite qu'atterrissage + indices

### Constat
Titre actuel : « **Marchés — budget, atterrissage et indices** ». En réalité il n'y a **pas de gestion de
budget de marché** en tant que telle : uniquement **atterrissage** (réalisé + projeté), **cible conso**
(DALKIA), et **indices & variables**. Le mot « budget » induit en erreur.

### Questions #2
- **Q2.1** — Nouveau titre/eyebrow. Proposition : eyebrow « Suivi des marchés », titre « **Atterrissage &
  indices par marché** ». OK, ou autre libellé ?
- **Q2.2** — Faut-il aussi renommer l'entrée de nav (aujourd'hui « Marchés & contrats » → « Vue d'ensemble »)
  ou seulement le titre de la page ?

---

## Sujet #3 — homogénéiser les colonnes entre marchés

### Constat (colonnes actuelles par tier)
- **Élec (ENGIE/EDF)** — maille PRM : Bâtiment/PRM · Réalisé (fixe/var/mois) · Conso attendue · **Prix réf.** ·
  Atterrissage · Prévision réf. · Écart/réf. · Méthode.
- **Gaz (TE)** — maille PCE : PCE/site · Réalisé · Conso attendue · Atterrissage · Prévision réf. · Écart/réf. ·
  Méthode. *(≈ élec, sans « Prix réf. » ni détail fixe/variable)*
- **DALKIA CPE** — maille poste : Poste · Budget base (DPGF) · Coef. révision · Budget révisé · Réalisé ·
  Atterrissage · Reste à facturer · Écart réalisé/budget · Taux fact. · Méthode. *(modèle **différent** :
  budget contractuel, pas de conso)*

→ **Gaz et Élec sont déjà quasi homogènes** ; **DALKIA est structurellement différent** (budget DPGF vs
projection conso). Une homogénéisation « colonne à colonne » totale des 4 n'a pas de sens (pas de conso ni
de prix chez DALKIA ; pas de budget DPGF chez élec/gaz).

### Questions #3
- **Q3.1** — Périmètre d'homogénéisation : (a) **Gaz + ENGIE + EDF uniquement** (même jeu de colonnes,
  même ordre, mêmes libellés — DALKIA laissé à part) ; ou (b) forcer aussi un **socle commun minimal**
  sur DALKIA (Réalisé · Atterrissage · Écart · Méthode aux mêmes places) ?
  *(reco : a)*
- **Q3.2** — Pour Gaz, ajoute-t-on les colonnes élec manquantes (**« Prix réf. »** et **détail fixe/variable**
  du réalisé) pour un alignement total, ou garde-t-on Gaz plus sobre ?
- **Q3.3** — Cible technique : extraire un **composant/tableau commun** (colonnes partagées) réutilisé par
  élec + gaz, ou juste aligner libellés/ordre sans refactor lourd ? *(reco : factoriser les colonnes conso
  dans un module partagé)*

---

## Sujet #4 — beaucoup d'erreurs → statut « bloqué » sur les factures EDF (/factures)

### Constats sur données staging (issues EDF, agrégées)
| Code | Sévérité | Occurrences | Nature |
|---|---|---:|---|
| `SUPPLIER_CONTRACT_MISMATCH` | warning | **451** | PRM rattaché à un autre fournisseur (référentiel ENEDIS) → **bloqué** |
| `FIXED_CHARGE_PERIOD_NOT_APPLICABLE` | explained | 142 | ligne fixe sans conso (neutralisé) |
| `PERIOD_MISSING` | warning | 127 | période incomplète → **bloqué** |
| `CONSUMPTION_REFERENCE_MISSING` | warning | 127 | conso/période incomplète → **bloqué** |
| `DUPLICATE_EXPORT_OR_REISSUE` | explained | 41 | doublon export (neutralisé) |
| `CONSUMPTION_ENEDIS_MISMATCH` | anomaly | 25 | à expliquer |
| `MISSING_REGROUPEMENT` | warning | 24 | → **bloqué** |
| `DOUBLE_BILLING_PERIOD` | anomaly | 16 | à expliquer |

### Analyse
Le « bloqué » EDF est **dominé par `SUPPLIER_CONTRACT_MISMATCH` (451)** : l'éclairage public EDF a ses PRM
rattachés à un **autre fournisseur dans le référentiel ENEDIS** — c'est **structurel EDF**, pas une anomalie
de facturation. Idem `PERIOD_MISSING` / `CONSUMPTION_REFERENCE_MISSING` (lignes fourniture EDF sans quantité).
Ces codes noient les vraies anomalies (`CONSUMPTION_ENEDIS_MISMATCH`, `DOUBLE_BILLING_PERIOD`).

Rappel principe utilisateur (mémoire) : **« contrôle ≠ anomalie de facturation → supprimer, pas reclasser ».**

### Questions #4
- **Q4.1** — Pour EDF (éclairage public), `SUPPLIER_CONTRACT_MISMATCH` doit-il être **supprimé du contrôle**
  (non pertinent : le PRM éclairage public n'est pas censé matcher le fournisseur du référentiel), plutôt que
  compté en « bloqué » ? *(reco : supprimer pour EDF)*
- **Q4.2** — `PERIOD_MISSING` / `CONSUMPTION_REFERENCE_MISSING` sur les lignes fourniture EDF sans quantité :
  même traitement (supprimer / marquer non applicable EDF) ?
- **Q4.3** — Portée du correctif : **EDF seulement**, ou revoir plus largement la liste des codes comptés en
  « bloqué » vs « à expliquer » sur toute la file factures ?

---

## Implémenté (2026-07-09, branche `feat/marches-edf-fixes`)

- **#4** — `invoice_analysis.py` : `_suppress_supplier_specific_controls` retire pour **EDF** les codes
  `SUPPLIER_CONTRACT_MISMATCH`, `PERIOD_MISSING`, `CONSUMPTION_REFERENCE_MISSING` avant classement.
  Test `test_edf_control_suppression.py`. ⚠ **Nécessite un « Recalculer les contrôles »** (reanalyze) pour
  s'appliquer aux factures EDF déjà importées.
- **#1** — `engie_elec_budget_revise.py` : `_years_overview` → `available_years` + `recommended_year`
  (année la plus récente couvrant ≥ 6 mois). `year` devient optionnel (routes EDF/ENGIE + schéma).
  Front `ElecBudgetReviseV1` ouvre sur l'année recommandée + bandeau explicatif. Test
  `test_elec_budget_default_year.py`.
- **#2** — `MarketsBudgetPageV1` : eyebrow « Suivi des marchés », titre « Atterrissage & indices par marché ».
- **#3** — `GasBudgetReviseV1` aligné sur `ElecBudgetReviseV1` : ajout colonne **« Prix réf. »** (PEG),
  ratio climat isolé sous la conso, même titre/eyebrow de section. ENGIE/EDF partageaient déjà le composant.

## Suivi (2026-07-09) — auto-validation & « expliqué »

Question soulevée : compter une facture « expliquée » comme « OK » est-il judicieux ?
- Constat code : `control_status == valid` ignore les « expliqués » → une facture avec uniquement
  des anomalies expliquées était **auto-validée** (ADR 012, `_auto_validate_if_clean`).
- **Décision (option b)** : on garde l'auto-validation des expliqués **sauf** le doublon exact
  (`DUPLICATE_EXPORT_OR_REISSUE`) = risque de double paiement → reste `to_review` (à confirmer par un
  humain). Implémenté via `_AUTO_VALIDATION_HOLD_CODES`. Test `test_auto_validate_holds_on_exact_duplicate`.
- L'affichage garde « Expliquée » distinct de « Sans écart » (inchangé).
- ⚠ Effet **à partir de maintenant** : les factures déjà auto-validées avec un doublon avant ce
  correctif restent `approved` (l'auto-validation n'écrase jamais une décision existante).

## Ordre proposé
1. **#4** (factures EDF bloquées) — diagnostic terminé, correctif ciblé, fort impact ressenti.
2. **#1** (EDF atterrissage) — dépend des réponses Q1.1–Q1.3 pour trancher bug vs affichage.
3. **#2** (renommage) — rapide, sans risque.
4. **#3** (homogénéisation colonnes) — refacto UI, à faire après #1 (mêmes composants touchés).
