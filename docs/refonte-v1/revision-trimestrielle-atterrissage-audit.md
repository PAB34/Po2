# Révision trimestrielle des prix → atterrissage budget contractuel — audit

> Rapport « fil du dev » (lecture seule) — 2026-07-02. Fait suite à la demande : intégrer la **révision
> trimestrielle des prix** dans l'atterrissage « budget contractuel » (PR #36), car la révision gonfle le
> montant réellement dû → le budget contractuel (et donc l'atterrissage) doit être **révisé**, pas resté
> au montant DPGF « nu ». Question posée : **sur quels postes s'applique le calcul de révision ?**

## 0. TL;DR

- La révision existe déjà, **calculée et contrôlée** dans l'export « Fiche liaison finance »
  (`GET /cpe/finances/invoices/{id}/liaison.xlsx` → `build_detailed_finance_liaison_workbook`).
- **DALKIA fournit** dans son export, par ligne, `prix_de_base` (annuel) et `prix_ou_forfait_revise`
  (annuel révisé = base × coefficient trimestriel). On ne recalcule pas la révision : on la **contrôle**
  contre les formules d'indices. La colonne « Révision appliquée » = `_line_revision_breakdown(line)`.
- **Postes concernés par une révision** : **P2**, **P3** (indices), et **P1 gaz** (mécanisme propre gaz).
  **P1-ÉLEC** : pas de révision par indices dans le code.
- **Impact atterrissage (le vrai sujet)** : mon `build_contract_budget_landing` prend comme budget le
  **prévu DPGF = montant de BASE** (non révisé), alors que le **réalisé = factures = déjà révisé**.
  → base de comparaison incohérente : il faut **réviser le budget contractuel**.

## 1. Sur quels postes s'applique la révision (réponse à la question)

Source : `services/cpe_accounting.py`, dispatch dans `recompute_finance_invoice_controls` (l.2260-2314).
`revision_lines = lignes dont market ∈ {P2, P3}`.

| Poste | Révision ? | Formule / mécanisme | Fonction de contrôle |
|---|---|---|---|
| **P2** (maintenance, hors P2.4) | ✅ indices | `P2 = P20 × (0,15 + 0,70·ICHT-IME/ICHT-IME0 + 0,15·FSD2/FSD20)` | `_control_revision_p2` |
| **P2.4** (intéressement) | ✅ (même marché P2) | révision P2 + gate objectifs (`_control_p2_4_objectives`) | `_control_revision_p2` + P2.4 |
| **P3** (gros entretien, hors P3.4) | ✅ indices | `P3 = P30 × (0,15 + 0,30·ICHT-IME/ICHT-IME0 + 0,55·BT40/BT400)` | `_control_revision_p3` |
| **P3.4** (travaux APE) | ✅ (même marché P3) | révision P3 par indices (⚠ le contrat dit APE = forfait non révisable — **à lever**, cf. Q4) | `_control_revision_p3` |
| **P1 gaz** (acompte + conso) | ✅ mécanisme propre | prix gaz OS3/PEG (Annexe 6) + acompte vs DPGF ; **pas** ICHT/FSD/BT40 | `_control_p1_gaz_pu_os3`, `_control_p1_gaz_acompte_against_dpgf` |
| **P1-ÉLEC** (Lot 2 piscines) | ❌ pas de révision par indices | P10 élec = total (Annexe 6.2) ; aucun contrôle de révision dédié | — |

**Indices** : stockés dans `CpeRevisionIndex` (city, year, quarter, index_code, value). Bases de
référence éditables : `ICHT_IME0`, `FSD20`, `BT400` (défauts `ICHT_IME_BASE`/`FSD2_BASE`/`BT40_BASE`).
Coefficients **observés** (revised/base) reconstruits depuis les factures : `list_revision_observations`
(⚠ **P2/P3 uniquement**, ne couvre pas P1).

## 2. Comment le montant de révision est calculé (mécanique exacte)

`_line_revision_breakdown(line)` (l.1263) :
- `base` = `line.base_price` (annuel DPGF), `revised` = `line.revised_price` (annuel révisé DALKIA),
  `amount` = `line.amount_ht` (acompte de la période, souvent 1/4 de l'annuel).
- `base_share = base × (amount / revised)` → quote-part hors révision de l'acompte.
- `revision_share = amount − base_share` → **le montant de la révision** de la période.
- Gère les acomptes /4, les prorata partiels et les lignes à la consommation (PU × quantité).

Autrement dit : **coefficient de révision du poste = revised / base** (annuel), et il varie par trimestre.

## 3. Le problème pour l'atterrissage (PR #36)

`build_contract_budget_landing` (mergé) construit le budget contractuel à partir de
`cpe_market_tracking` → `prevu`, qui vient des **montants DPGF de référence** :
`CpeDalkiaRefP2P3.p2_total_ht / p3_total_ht`, `CpeDalkiaRefP1Gaz.p10_total_ht` — ce sont des montants
**de BASE (P20/P30/P10 nus)**, **non révisés**.

Or dans le même écran :
- `realise` = `recu` = `amount_ht` des factures CPE = **déjà révisé** (inclut la révision DALKIA).
- `budget_contractuel` = prévu DPGF = **base non révisée**.

Conséquence : on compare un réalisé révisé à un budget non révisé. L'atterrissage sous-estime le budget
contractuel dès qu'il y a inflation (coefficient > 1). **Corriger = réviser le budget contractuel**, ce qui
le gonfle mécaniquement (exactement ce que vous décrivez).

## 4. Options pour intégrer la révision dans le budget contractuel

- **Option A — coefficient observé (réutilise l'existant).** Appliquer au prévu DPGF (base) le
  **coefficient observé** du trimestre le plus récent de l'année (`list_revision_observations`, = revised/base)
  par poste (P2, P3). Simple, aucune saisie d'indices requise ; mais **P2/P3 seulement** (pas P1) et dépend
  d'avoir ≥ 1 facture révisée dans l'année.
- **Option B — coefficient recalculé depuis les indices.** Recalculer le coefficient via les formules
  P2/P3 à partir de `CpeRevisionIndex` pour le trimestre courant, appliqué au prévu base. Plus « propre »,
  mais nécessite les indices saisis + une **formule P1 gaz distincte** (OS3/PEG) à brancher.
- **Option C — réel écoulé + extrapolation (le plus fidèle).** Trimestres écoulés : révisé **réel** des
  factures ; trimestres à venir : dernier coefficient connu × prévu base. Mélange réalisé + estimation,
  cohérent avec la logique d'atterrissage (réalisé à date + reste-à-venir estimé).

Recommandation provisoire : **Option A** en v1 (rapide, réutilise `list_revision_observations`), en
affichant explicitement « budget contractuel révisé (coef. Tn observé) » + le budget base en regard, puis
**Option C** en v2 pour la fidélité.

## 5. Questions ouvertes (numérotées — à trancher avant de coder)

1. **Périmètre de la révision du budget** : on révise **P2 + P3** (là où l'existant sait le faire), et on
   traite **P1 gaz** à part (coefficient propre) ? Ou P2/P3 seulement en v1 et P1 plus tard ?
2. **Source du coefficient** : **observé** (revised/base des factures, Option A) ou **recalculé** depuis
   les indices `CpeRevisionIndex` (Option B) ? (l'observé est dispo tout de suite, l'indiciel est « officiel »).
3. **Quel trimestre fait référence** pour un budget annuel : dernier coefficient connu de l'année ? moyenne
   des trimestres écoulés ? coefficient par trimestre puis somme (Option C) ?
4. **P3.4 APE** : le contrat dit **forfait global non révisable** (deadline 2029), mais le code applique la
   révision P3 (indices) à toute ligne market=P3, **y compris P3.4**. Faut-il **exclure P3.4 de la révision**
   dans le budget contractuel (le laisser au forfait) ? (probable oui — à confirmer).
5. **Affichage** : montrer 2 colonnes « budget base » et « budget révisé » + le coefficient appliqué, ou
   remplacer directement le budget par le révisé ? (transparence compta vs simplicité).
6. **P1-ÉLEC** : confirmer qu'il n'y a **pas** de révision (donc budget = base) côté Lot 2 piscines.

## 6. Fichiers concernés (probables)
- Lecture/réutilisation : `services/cpe_accounting.py` (`_line_revision_breakdown`,
  `list_revision_observations`, formules P2/P3, contrôles P1 gaz), `services/cpe_market_tracking.py`
  (prévu base), `services/accounting_contract_budget.py` (mon service à faire évoluer),
  `models/cpe_dalkia.py` (`CpeDalkiaRefP2P3`, `CpeDalkiaRefP1Gaz`), `models/cpe.py` (`CpeRevisionIndex`).
- Évolution probable : `accounting_contract_budget.build_contract_budget_landing` (ajout d'un budget
  **révisé** par poste + coefficient), schéma + front (colonne/badge « révisé »). Calcul à la volée, sans migration.

## 7. Ce que je NE fais pas sans validation
- Choisir le périmètre (Q1), la source du coefficient (Q2) et la maille trimestre (Q3).
- Exclure ou non P3.4 de la révision (Q4) — impact contractuel.

## 8. Décisions validées (2026-07-02)

- **Q1/Q2/Q3 — Source & maille** : **Option C** (réel écoulé + extrapolation). Trimestres écoulés = révisé
  réel des factures ; trimestres à venir = **dernier coefficient connu** appliqué au budget base.
  Implémentation v1 : coefficient **observé par marché** (P1/P2/P3) = `Σ prix_révisé / Σ prix_base` du
  **dernier trimestre écoulé avec données**, appliqué au budget base du poste. Poste→marché : P1/P1-ELEC→P1,
  P2/P2-4→P2, P3/P3-4→P3. Défaut coef = 1,0 si aucune facture révisée.
- **Q5 — Affichage** : **base + révisé + coefficient** (3 infos : budget base DPGF, budget contractuel
  révisé, coefficient appliqué), pour la traçabilité compta.
- **Q4 — P3.4** : **révisé** dans la vue trimestrielle (travaux programmés obligatoires facturés au ¼ du
  P30 révisé, formule OUV11 confirmée `06-Facturation-et-indices.md`). L'**APE** (forfait global non
  révisable, `01-Structure-du-marché.md`) est une **enveloppe pluriannuelle distincte**, hors de cette vue
  (chantier « réalisé vs programme APE » séparé). → aucun changement pour exclure P3.4 : comportement correct.
- **Correctif 2026-07-02 (revue staging)** : le coefficient Σrévisé/Σbase n'a de sens que pour **P2/P3**
  (base/révisé = forfaits annuels). Pour **P1 gaz**, `prix_de_base`/`prix_révisé` sont des **prix unitaires
  du gaz (€/MWh)** sur des lignes de conso → un ratio agrégé donnait un coefficient aberrant (bug observé
  ≈ 300). **P1 gaz est donc exclu** de la révision par coefficient (budget = base) : sa révision propre
  (prix gaz OS3/PEG) est un mécanisme distinct à intégrer séparément. La **formule d'extrapolation** est
  désormais affichée en petit sous la ligne du poste (`revision_detail`). L'extrapolation se **recale
  automatiquement** à chaque nouvel import de factures (dernier trimestre connu, calcul à la volée).
- **Suite (noté)** : construire un **tableau de suivi des indices/variables** (indices de révision, prix
  gaz PEG/OS3, TURPE…) avec graphiques, nouvelle entrée sur `/refonte-v1/marches`. Transversal aux marchés
  (DALKIA/ENGIE/EDF), à cadrer plus tard. Voir mémoire `project_suivi_indices_variables`.
