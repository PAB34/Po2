# Cadrage — charger le BPU gaz TotalEnergies (référentiels)

> Doc « fil du dev » — 2026-07-07. Chantier à prévoir. Faire apparaître **TotalEnergies** dans
> `/refonte-v1/referentiels` (BPU Hérault Énergies), aujourd'hui absent.

## 1. Constat (vérifié cette session)
- La vue référentiel BPU liste les fournisseurs **présents dans `bpu_documents`**. Il n'y a **aucun doc
  TotalEnergies** en base (prod et staging). Donc TE n'apparaît pas.
- Le classeur `extraction_tarifs_BPU_herault.xlsx` **contient** le BPU gaz TE (Lot 7, typologies **T1-T4**),
  mais l'import élec (`import_bpu_xlsx`) **ne sait pas le parser** : les lignes gaz ressortent en segment
  **`INCONNU`** avec **prix vides** (les colonnes de prix gaz diffèrent des colonnes élec). Test A/B
  documenté dans `bpu-import-granulaire-2026-decisions.md` §6ter.

## 2. À vérifier en préalable (audit)
- Le BPU gaz TE est-il **déjà exploité ailleurs** ? Le module **contrôle gaz TotalEnergies** existe
  (migrations 0057→0062, contrôle fourniture PEG/BPU lot 7). Utilise-t-il ses **propres références** (pas
  `bpu_documents`) ? → risque de **doublon** si on charge aussi dans `bpu_documents`.
- Où sont les **vraies grilles gaz** (T1-T4, prix €/MWh) et leur structure de colonnes ?

## 3. Cible (proposée)
Un **parseur gaz** (ou une extension de `import_bpu_xlsx`) qui mappe les lignes gaz TE (T1-T4, colonnes
prix gaz) vers `bpu_documents`/segments, pour qu'elles apparaissent dans le référentiel **et** soient
cohérentes avec le contrôle gaz existant.

## 4. Questions à trancher
- Q1 — **Unifier** le BPU gaz dans `bpu_documents` (référentiel commun) ou le garder **séparé** (module gaz) ?
- Q2 — Mapping **T1-T4** → segments/typologies gaz ; colonnes de prix gaz à lire.
- Q3 — Éviter la **double source de vérité** avec le contrôle gaz TotalEnergies existant.
