# DPGF base vs budget révisé (DALKIA) — analyse & prise en compte dans l'atterrissage

> Rapport « fil du dev » — 2026-07-03. Analyse du fonctionnement de `/cpe/dalkia-import` (dossier de
> marché CPE) et vérification, poste par poste, de la révision dans l'atterrissage `/refonte-v1/marches`.
> Déclenche le correctif P1 (voir §5). Complète [[p1-gaz-dalkia-decisions.md]].

## 1. Fonctionnement de `/cpe/dalkia-import`

Page = dossier de marché CPE (`CpeDalkiaPage`), 2 phases :
- **Données & référentiel** : Imports, Sites, Matrice, **Références** (DPGF), **Formules et indices**.
- **Contrôle** : **Factures** (suivi marché *prévu vs reçu*), Petits travaux P3, Contrôle factures.

Le référentiel maître (acte d'engagement, `cpe_dalkia_ref_*`) fixe par poste/année les montants **DPGF de
base** : `CpeDalkiaRefP2P3.p2_total_ht`/`p3_total_ht` (+ sous-parts `p2_4_ht`/`p3_4_ht`),
`CpeDalkiaRefP1Gaz.p10_total_ht`, `CpeDalkiaRefP1Elec.p10_total_ht`. C'est le **prévu** du suivi marché
(`cpe_market_tracking._collect`).

## 2. Base DPGF vs révisé — mécanisme par poste

| Poste | Base DPGF | Révision DALKIA |
|---|---|---|
| P2 / P2.4 | forfait P20 (dont `p2_4_ht`) | indexation **ICHT-IME / FSD2** (coef sur forfait) |
| P3 / P3.4 | forfait P30 (dont `p3_4_ht`, APE) | indexation **ICHT-IME / BT40** |
| **P1 gaz** | P10 (Annexe 6) | **DPGF P1 révisé séparé** (`cpe_dpgf_p1_*`), 3 niveaux : `contrat` → `rev_temp` (T°) → **`rev_temp_prix` (T° + prix OS3)** = révisé officiel |
| P1-ELEC (piscines Lot 2) | P10 élec | **non révisé** |

**DPGF P1 révisé** (`CpeDpgfP1Line`, niveau `rev_temp_prix`) : livré par DALKIA à chaque OS impactant le prix
gaz, lignée d'import séparée. Exposé par `get_dpgf_p1_levels` → bloc `p1_dpgf` du suivi marché, mais
**purement informatif** : docstring `_dpgf_p1_block` = *« n'entre PAS dans le calcul prévu/reçu ; le prévu P1
reste au niveau contrat »*.

## 3. Prise en compte dans l'atterrissage `/refonte-v1/marches` (état AVANT correctif)

| Poste | Révisé dans l'atterrissage ? | Source |
|---|---|---|
| P2 / P2.4 | ✅ | base × **coefficient observé** factures (`_revision_coef_by_market`, Σrévisé/Σbase dernier trim.) |
| P3 / P3.4 | ✅ | idem coef P3 |
| **P1 gaz** | ⚠️ oui mais par **reconstitution** (conso attendue DJU × OS3, PR #40) — **PAS** le DPGF `rev_temp_prix` officiel | `cpe_p1_gaz_revise` |
| P1-ELEC | ✅ non révisé (correct) | budget base |

## 4. Vérifications (recommandations #2 et #3)

- **Coefficient P2/P3** = ratio prix révisé/base **observé sur les factures** (`CpeFinanceLine`), pas les indices
  ICHT/FSD/BT40 saisis manuellement. C'est un **contrôle**, pas une saisie → correct. Les « Saisie Po2 »
  n'influencent pas ce coefficient.
- **P2.4 / P3.4 (APE)** : sous-parts extraites des totaux P2/P3, révisées via le **même coefficient P2/P3**
  (mapping `P2-4→P2`, `P3-4→P3`). ⚠️ Hypothèse à confirmer contre le contrat : les forfaits APE suivent-ils
  strictement la même indexation que P2/P3 ? (Pas un bug code, une question contractuelle.)

## 5. Correctif décidé (recommandation #1) — P1 gaz

Le budget révisé P1 doit privilégier la **source faisant foi** :
1. **DPGF P1 `rev_temp_prix`** (montant officiel DALKIA) quand un DPGF P1 révisé est importé pour l'année ;
2. **reconstitution conso × OS3** (mon moteur `cpe_p1_gaz_revise`) **en repli** (projection) sinon.

Implémentation : helper `_p1_budget_override(db, city_id, year, lot)` dans `accounting_contract_budget` —
lit `get_dpgf_p1_levels(...)["rev_temp_prix"][year]` d'abord, sinon `compute_p1_gaz_budget().total`. Le poste
P1 de l'atterrissage utilise cet override (avec `revision_detail` indiquant la source). P1-ELEC inchangé.

## 6. Reste ouvert
- Confirmer l'indexation APE P2.4/P3.4 contre le contrat.
- (Plus tard) exposer le niveau `rev_temp` (T° seule) comme variante d'atterrissage ?
