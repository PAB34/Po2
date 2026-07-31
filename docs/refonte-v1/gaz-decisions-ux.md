# Page /energie/gaz (GRDF ADICT) — décisions UX

Statut : refonte visuelle v1 déployée sur staging (branche `feat/gaz-page-refonte`, 2026-07-31).
Contexte : la page existait mais affichait des tableaux de chiffres bruts (mur de 49 tableaux
en mode « Tous les PCE »). Backend + données déjà en prod (49 PCE, 7,26 GWh, 2024→2026).

## Existant vérifié
- Composant `pages/EnergieGazPage.tsx` (KPI plats + bouton collecte + tableaux mensuels bruts).
- Design system : `kpi-row`/`kpi-card` (+ `--info/--warn/--alert`), `chart-section`, `badge-*`,
  `btn-primary/compact`, `data-table`, `page-header-row`, `page-subtitle`.
- **recharts 2.15.3 déjà installé et utilisé** (`EnergieDetailPage` → `AnnualProfileChart`,
  patron barres année/année réutilisé ici).
- API déjà exposées : `fetchGrdfPces`, `fetchGrdfMonthly`, `fetchGrdfConsoStatus`,
  `startGrdfBackfill`, `fetchGrdfReconcileP1` (+ types).

## Décisions (2026-07-31)
1. **Tableau de bord, pas tableur** : le graphe mensuel année/année (barres recharts) devient la
   pièce maîtresse ; le détail chiffré passe en bloc **repliable** (conservé pour export/contrôle).
2. **Graphe agrégé par défaut** (« Tous les PCE » = somme mensuelle) ; le sélecteur bascule sur un
   PCE précis. Évite le mur de tableaux.
3. **Bandeau KPI enrichi** : PCE référencés, droits actifs, collectables, **total consommé (GWh)**,
   **période couverte** (calculés à partir de la série « tous PCE »).
4. **Rapprochement P1 gaz DALKIA** inclus (validé) : table GRDF réel vs P1 DALKIA par PCE, avec
   écart % (rouge si |écart| > 5 %) et badge de statut (ok/écart/non rapprochable). Sélecteur d'année.
5. **Collecte** : bouton primaire + badge de statut dans l'en-tête (plus lisible que l'ancien texte).

## Questions ouvertes
- Q1. Unité d'affichage : tout en **MWh PCS** (choix actuel) ou proposer une bascule kWh/MWh/GWh ?
- Q2. Noms de sites vides (GRDF ne les fournit pas) → afficher le n° PCE en attendant la liaison au
  patrimoine ; faut-il un mapping manuel provisoire ?
- Q3. Faut-il un **export CSV/Excel** du détail mensuel et du rapprochement P1 ?
- Q4. Le graphe : garder des barres groupées par année, ou proposer une vue **cumulée annuelle** /
  **empilée par PCE** en option ?
