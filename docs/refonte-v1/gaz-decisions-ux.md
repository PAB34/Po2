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

## v2 — alignement sur la page électricité (2026-08-17)

Demande : « que la page gaz reprenne le style graphique et les indicateurs de performance de
`/refonte-v1/fluides/electricite` mais adapté au gaz » + « un 2e graphique : le nombre de PCE peut
différer entre années et expliquer une baisse/hausse ».

6. **Composant dédié `features/fluids/FluidsGazDetailV1.tsx`**, monté sur `/refonte-v1/fluides/gaz`
   (au lieu d'embarquer la page legacy `EnergieGazPage`). Miroir exact de `FluidsElecDetailV1` :
   design system po2 (`po2-card`, `KpiCard`, `StatusBadge`, `po2-kpi-grid`, `po2-two-columns`),
   mêmes couleurs de séries (#3e6ea8 courant / #94a3b8 moyenne pointillée).
   `/energie/gaz` reste la vue legacy (inchangée).
7. **Biais de périmètre traité** (le parc GRDF grandit au fil des consentements) :
   - 2e graphe « **PCE actifs par mois** » (une ligne par année) ;
   - KPI « **Évolution à périmètre constant** » = mêmes PCE ∩ mêmes mois entre N et N-1 ;
   - KPI « **Effet périmètre** » = évolution brute − évolution à périmètre constant ;
   - bloc « ce qui explique l'écart » en 3 temps (brut → effet périmètre → évolution réelle).
   « PCE actif » = ayant consommé > 0 (un relevé à 0 ne compte pas comme site alimenté).
8. **Indicateur de performance adapté au gaz** : `MWh/DJU chauffage` (équivalent du kWh/DJU élec ;
   le gaz est quasi intégralement thermosensible). Calculé côté front en croisant
   `GET /energie/dju/monthly` avec les consos mensuelles — **aucun changement backend**.
   Mois sous 30 DJU écartés (ratio non significatif hors saison de chauffe).
9. **Tableau « Tous les PCE »** (recherche + tri + filtre droit), parité avec « Tous les compteurs ».
10. Le graphe principal (barres mensuelles par année) est **conservé** (jugé « intéressant »),
    seulement restylé dans le gabarit po2.

## Questions ouvertes
- Q1. Unité d'affichage : tout en **MWh PCS** (choix actuel) ou proposer une bascule kWh/MWh/GWh ?
- Q2. Noms de sites vides (GRDF ne les fournit pas) → afficher le n° PCE en attendant la liaison au
  patrimoine ; faut-il un mapping manuel provisoire ?
- Q3. Faut-il un **export CSV/Excel** du détail mensuel et du rapprochement P1 ?
- Q4. Le graphe : garder des barres groupées par année, ou proposer une vue **cumulée annuelle** /
  **empilée par PCE** en option ?
