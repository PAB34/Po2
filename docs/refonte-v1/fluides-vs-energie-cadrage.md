# Cadrage — `/refonte-v1/fluides` vs `/energie` (multi-fournisseurs)

> Doc « fil du dev » — 2026-07-07. Chantier à prévoir. L'utilisateur trouve **`/energie` plus pertinente**
> que `/refonte-v1/fluides`, **mais** `/energie` ne travaille que sur **ENGIE**.

## 1. Le sujet
- `/energie` (legacy) : vue énergie riche/pertinente, mais **mono-fournisseur (ENGIE)**.
- `/refonte-v1/fluides` : nouvelle vue **multi-fluides** (électricité/gaz/eau), jugée moins pertinente.
- Question de fond : **quelle vue devient la cible**, et comment lui donner à la fois la **pertinence de
  `/energie`** ET le **multi-fournisseurs / multi-fluides** ?

## 2. À faire en premier — AUDIT (avant toute décision)
Comparer concrètement les deux pages (fil du dev : auditer l'existant back ET front) :
- `/energie` : quelles infos/pertinences précises l'utilisateur apprécie (détail PRM, préconisations,
  courbes, contrôle…) ? Qu'est-ce qui est **ENGIE-only** (source de données, filtres, hypothèses) ?
- `/refonte-v1/fluides` : que couvre-t-elle déjà, qu'est-ce qui manque vs `/energie` ?

## 3. Options (à départager après audit)
- **A — Étendre `/energie`** au multi-fournisseurs (EDF, TotalEnergies…) : garde la pertinence, mais
  dé-« ENGIE-ise » la source de données.
- **B — Porter les qualités de `/energie` dans `/fluides`** : la refonte devient la cible unique.
- **C — Hybride** : `/fluides` comme hub, embarquant/renvoyant vers la vue détaillée façon `/energie` par
  fluide/fournisseur.

## 4. Questions à trancher (après audit)
- Q1 — Quelle vue est la **cible pérenne** (on en abandonne une) ?
- Q2 — Qu'est-ce qui, dans `/energie`, est **précisément** « plus pertinent » (à préserver) ?
- Q3 — Le multi-fournisseurs suppose des **données comparables** (ENEDIS/factures par PRM tous
  fournisseurs) : déjà en place pour l'atterrissage, à confirmer pour cette vue.
