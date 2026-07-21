# Fluides refonte — reste à faire (backlog priorisé)

> Statut : backlog actif, mis à jour 2026-07-21. Branche `integ/fluides-on-main` (déployée sur staging).
> Contexte : la vue globale `/refonte-v1/fluides` et le détail `/refonte-v1/fluides/electricite`
> sont faits (KPI, référentiel contractuel, calibrage×fournisseur, tableau compteurs triable/filtrable,
> graphes conso vs moyenne, kWh/DJU, DJU historique+projection, part conso fournisseur).

## Décidé
- **Impact financier : ÉLEC d'abord, gaz plus tard.**
- **Ne pas fabriquer de chiffre financier** : l'impact € dépend d'un prix €/kWh TTC projeté qui n'existe
  pas encore de façon exploitable → il faut d'abord le **BPU « Perspective »**.

## 1. BPU « Perspective » (élec) — PRÉREQUIS de l'impact financier
Dans `/refonte-v1/referentiels` → section « BPU — Hérault Énergies », ajouter un bouton **« Perspective »**
(à côté d'« Évolution ») : **projection tarifaire +5 et +10 ans** basée sur l'historique, **graphe + tableau**.
- Assembler un **€/kWh TTC** = fourniture (BPU) + réseau (**TURPE**, `fetchBpuTurpeEvolution` = historique réel
  d'évolution %) + **taxes** (accise/CSPE, CTA, TVA).
- Projeter chaque composante par régression sur l'historique → prix TTC +5/+10 ans (+ % d'évolution).
- Exposer ces valeurs projetées via un endpoint réutilisable (pour l'impact financier).
- Front : nouvelle vue « Perspective » (courbes + tableau), sur le modèle de la vue « Évolution » existante
  (`EnergieBpuPage.tsx`, `fetchBpuTimeline` / `fetchBpuTurpeEvolution`).

## 2. Cadre « Impact financier » (élec) — après (1)
Cadre **collé à droite** de la projection DJU sur `/refonte-v1/fluides`, intégrant ÉLEC (gaz plus tard) :
- **Conso projetée** = part thermosensible (kWh/DJU × DJU projeté de `djuOutlook`) + talon non climatique.
- **Prix projeté** = €/kWh TTC issu du BPU « Perspective » (1).
- **Chiffre à 5 ans et 10 ans** = conso projetée × prix projeté (€/an), affiché avec les hypothèses visibles.
- Gaz : `MWh/DJU × prix gaz TTC projeté` — **en attente** (voir 4 et 5).

## 3. Cartes « Performance » sous « Trajectoire climatique »
Dans `FluidsClimateSectionV1`, passer la carte perf **sous** le graphe trajectoire, et ajouter **2 cartes** :
- **Élec** : signature énergétique / thermosensibilité (déjà codée).
- **Gaz** : même gabarit, **placeholder** « données gaz à venir » (pas de données GRDF pour l'instant).

## 4. BPU gaz (manquant) — chantier données
Le gaz est **absent des BPU** de `/refonte-v1/referentiels`. Importer/modéliser le BPU gaz (prix fourniture,
ATRD/acheminement, taxes) pour disposer d'un **€/MWh TTC gaz** projetable → débloque le prix gaz de (1)/(2).

## 5. Impact financier gaz — après (4) + collecte GRDF
Nécessite : conso gaz réelle (GRDF, cf. secret SMS en attente) + BPU gaz (4). `MWh/DJU × prix gaz TTC projeté`.

## 6. Dérives réelles (courbe de charge ENEDIS)
Module de **détection** (talon nocturne, conso week-end, ruptures) sur `enedis_load_curve.csv` (**prod**, 994 Mo),
lecture **par PRM** (garde-fou OOM). Alimente : le compteur **« dérives »** de la carte d'accès élec (vue globale)
et le panneau « Dérives prioritaires » du détail élec (actuellement en aperçu).

## 7. Calibrage / préconisations sur staging
`enedis_max_power.csv` **absent du volume staging** → calibrage×fournisseur et préconisations = 0 sur staging
(OK en prod, 393 905 lignes). Pour un aperçu complet staging : (a) lancer la sync puissance max, ou
(b) copier le fichier prod dans le volume staging. Non bloquant pour la prod.

## 8. Mise en prod
Merge `integ/fluides-on-main` → `main` → déploiement prod (calibrage/préconisations/dérives s'y peuplent).
Puis **GRDF** (câblage dès réception du secret SMS) → débloque le gaz (2/5).

---
### Ordre proposé
**(1) BPU Perspective élec → (2) Impact financier élec → (3) cartes perf → (6) dérives réelles →
(4) BPU gaz → (5) impact gaz.** Mise en prod (8) possible à tout moment sur ce qui est prêt.
