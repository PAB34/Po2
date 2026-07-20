# Fluides V1 — refonte page `/refonte-v1/fluides` : décisions UX

> Date : 2026-07-09 · Statut : **cadrage, à décider AVANT de coder** (fil du dev)
> Objectif : une vraie page Fluides qui **atterrit sur une vue globale (tous fluides)** puis
> donne accès au **détail par fluide** (ENEDIS élec · GRDF gaz · SUEZ eau à venir).
> Références lues : `docs/34-Contrat-ecran-Fluides-V1.md` (contrat d'écran complet F01–F04),
> `docs/prototype-refonte-v1/` (maquette front-only), page réelle `/energie`.

## 1. Existant vérifié

### Front

| Élément | Fichier | État réel |
|---|---|---|
| Page refonte `/refonte-v1/fluides` | `pages/RefonteV1FluidsPage.tsx` → `features/fluids/FluidsPortfolioPageV1.tsx` | **100 % mock** (`fluids.mock.ts`). KPI + dérives + table « abonnements à recalibrer ». **Pas d'onglets, pas de graphe, pas d'atterrissage, aucun accès détail par fluide.** |
| Page énergie réelle | `pages/EnergiePage.tsx` | **Bien construite, données réelles** : perf DJU saisonnière, KPI parc, bandes de puissance, camembert fournisseurs, calibrage, top consommateurs, référentiel contractuel, couverture/audit, panneau collecte ENEDIS. Recharts. |
| Page gaz réelle | `pages/EnergieGazPage.tsx` | Existe (détail GRDF/gaz). À relire en détail avant réutilisation. |
| Design-system dispo | `design-system/` | `Button, Card, DataTable, Drawer, FilterBar, KpiCard, SegmentControl, StatusBadge`. Recharts déjà utilisé ailleurs. |
| Prototype Fluides | `docs/prototype-refonte-v1/app.js` (`renderFluids`) | **Maquette riche** : onglets Tous/Élec/Gaz/Eau, bandeau sources, 4 KPI, courbe réel/référence/prévision + fourchette, cartes saison hiver/été, dérives, anneau de confiance, panneau abonnements + drawer calibration, table sites. **C'est la référence à reprendre.** |

### Back (endpoints réels)

- **Électricité (ENEDIS)** : `GET /api/energie` (overview parc), `/data-ranges`, `/data-audit`, `/dju/monthly`, `/preconisations`, `/{prm}` (+ `/max-power`, `/load-curve`, `/annual-profile`, `/daily-consumption`, `/dju-performance`, `/dju-seasonal`). **Riche et réel.**
- **Gaz (GRDF)** : `GET /api/grdf/pces`, `/conso/monthly` (filtrable `id_pce` **ou `building_id`**), `/conso/status`, `/rapprochement-p1/{year}`. Agrégation mensuelle par site partiellement possible.
- **Eau (SUEZ)** : **aucun module backend**. Confirme « à construire ».
- **Manquant (doc 34 §9)** : endpoint **portefeuille multi-fluides agrégé** (conso/€/atterrissage tous fluides), moteur d'atterrissage physique central/bas/haut, conversion financière, détection dérives courbe de charge.

## 2. Constat

La page refonte actuelle ne fait qu'afficher des maquettes statiques. Toute la donnée réelle vit
dans `/energie` (élec) et `/energie/gaz` (gaz), qui sont **hors du DS refonte** mais fonctionnels.
La valeur neuve attendue = **la vue globale « atterrissage tous fluides » qui n'existe nulle part**.

## 3. Proposition d'UI/UX (parti pris à valider)

### 3.1 Arborescence

```
/refonte-v1/fluides                → VUE GLOBALE (neuve) : synthèse tous fluides + atterrissage + 3 cartes d'accès
   ├── carte Électricité (ENEDIS)  → détail = page /energie EMBARQUÉE dans AppShellV1
   ├── carte Gaz (GRDF)            → détail = page /energie/gaz EMBARQUÉE
   └── carte Eau (SUEZ)            → carte pédagogique « À construire » (pas de données)
```

Parti pris majeur : **ne pas réécrire les détails**. On embarque les pages legacy `/energie` et
`/energie/gaz` (pattern déjà validé en prod pour le hub Référentiels, PR #42). Le **neuf = la vue
globale uniquement**. Détails = données réelles immédiates, zéro régression.

### 3.2 Contenu de la vue globale — **révisé après retour du 2026-07-09**

La vue globale est **recentrée sur le climat (DJU)** — facteur explicatif dominant des consommations —
et **ne projette AUCUN impact financier**. Tout ce qui est spécifique à un distributeur (dérives de
courbe de charge, surveillance des contrats, qualité par source) descend **dans le détail du fluide**.

1. **En-tête** : « Fluides & consommations », période (2026/2025), fraîcheur sources (ENEDIS/GRDF/DJU), export.
2. **Bandeau sources** : point live + couverture globale.
3. **EN TÊTE — un seul graphe climatique + la carte performance** (retour du 2026-07-09, posture analyste) :
   - **Trajectoire climatique** (courbes) montrant **DJU chauffage ET froid ensemble** (2 couleurs :
     bleu = chauffage, ambre = froid), chacun avec **2026 / N-1 / moyenne** (plein / tirets / pointillés).
     + **indicateurs chiffrés** chaud & froid : cumul DJU + Δ vs N-1 + Δ vs moyenne. (L'ancien graphe en
     barres chaud/froid est **supprimé**, remplacé par celui-ci.)
   - **Carte « Performance énergétique »** (remplace l'ancienne carte) headline **thermosensibilité
     kWh/DJU** + **son évolution vs N-1 en gros** (indicateur n°1) + mini **signature énergétique**
     (droite conso~DJU N-1 vs 2026) + part thermosensible / **talon** (et son évolution) + pentes chauffage/clim.
4. **Accès détail par distributeur** (3 cartes cliquables ENEDIS/GRDF/SUEZ, mini-KPI + « Ouvrir le détail »).
5. **4 KPI conso (SANS €)** : Conso observée (brute), **Corrigée du climat** (évolution réelle vs N-1),
   **Talon non climatique** (part + évolution), Couverture données.
6. **Cartes saison** hiver / été.

### 3.2bis Posture analyste énergie (cadre retenu)

Ordre d'importance des indicateurs, qui structure la page :
1. **Signature énergétique** = droite conso ~ DJU. Pente = **thermosensibilité** (impact/°C) ;
   ordonnée = **talon** (conso non climatique : nuit, week-end, veilles).
2. **Évolution de la pente vs N-1** = performance intrinsèque, à climat égal (↑ = dégradation,
   ↓ = gains). **Indicateur de pilotage n°1**, mis en tête de la carte performance.
3. **Conso corrigée du climat** (DJU-normalisée) pour comparer les années équitablement.

### 3.3ter Fenêtres distributeurs (maquettées de la même manière)

- **ENEDIS (élec)** : hero distributeur + KPI (dont thermosensibilité +Δ N-1), **signature énergétique**
  (nuage conso/DJU + régressions N-1/2026), calibrage, **dérives de courbe de charge**, **surveillance
  des contrats** + **drawer calibration**.
- **GRDF (gaz)** : hero + KPI, **conso mensuelle + courbe DJU superposée**, **rapprochement P1 DALKIA**,
  surveillance des contrats (CAR/profil) + drawer.
- **SUEZ (eau)** : hero « À construire » + KPI grisés + **sections prévues** (volumes m³, détection de
  fuites/talon, couverture, surveillance) — aucun câblage.
- ✅ **Implémentation (décidé 2026-07-09 — Option A)** : en v1, **embarquer** les pages `/energie` et
  `/energie/gaz` telles quelles (réel, pas de réécriture). La **vue globale climat/performance** est le
  **seul chantier neuf**. Les maquettes distributeurs = **cible de reskin phase 2** (non planifiée).

## 6. Plan d'implémentation (Option A)

Branche : `feat/fluides-vue-globale` (worktree neuf off `origin/main`). Staging city_id=303.

- **Incrément 1 — structure & embed (front, sans back)** : sous-routes `/refonte-v1/fluides/electricite|gaz|eau`
  dans `App.tsx` ; pages qui embarquent `EnergiePage` / `EnergieGazPage` dans `AppShellV1` ; eau = placeholder
  « À construire ». Vue globale : cartes d'accès + KPI conso composés depuis `GET /api/energie` (réel).
  Typecheck `npx tsc -b`.
- ✅ **Incrément 2 — climat & performance FAIT** : endpoint `GET /api/energie/fluids/climate`
  (`get_fluids_climate`) = DJU chauffage/**froid** multi-années (N/N-1/moyenne, cumuls + Δ) +
  **thermosensibilité** (régression conso~DJU), **talon**, **évolution vs N-1** (indicateur n°1) + R².
  Front : trajectoire recharts (6 courbes chaud/froid × N/N-1/moy) + chips Δ + carte **performance**
  (signature énergétique, part thermosensible/talon) + KPI Rigueur climatique & Thermosensibilité réels.
  Thermosensibilité v1 = **élec** (gaz en calque ultérieur). `tests/test_fluids_climate.py` 5/5 ; `tsc -b` OK.
- ✅ **Incrément Acquisition FAIT** : bande « Sources » → bouton **« Gérer la collecte »** → **tiroir
  Acquisition** (DS `Drawer`) listant ENEDIS / GRDF / SUEZ avec l'**état réel** (fraîcheur via
  `data-ranges`, gaps « Puissance max/CDC absentes » et « Conso GRDF non chargée » via
  `grdf/conso/status`) ; chaque ligne ouvre la **fenêtre de collecte** du distributeur. ENEDIS = nouvelle
  sous-route `/refonte-v1/fluides/electricite/collecte` embarquant `EnergieDataOpsPage` (retire la page
  isolée `/energie/donnees`). GRDF = collecte déjà dans la fenêtre gaz. SUEZ = placeholder. C'est le
  **levier** des étapes C (puissance max) et D (gaz) du §7. `tsc -b` OK.
- **Incrément 3 — surveillance & drawer** : brancher la préconisation réelle (`/energie/{prm}/preconisation`)
  dans le drawer des détails (déjà côté /energie ; à exposer dans la trame refonte le cas échéant).

⚠️ Ne pas toucher `PRONO/*` ni `knockout_mc.py`. `git status` + pathspecs explicites, jamais de force-push.

## 7. Audit données & backend (2026-07-10, sondage staging réel)

### Données réellement disponibles (staging, city_id=303)

| Donnée | Couverture réelle | Verdict |
|---|---|---|
| **DJU chauffage & froid** | 2015→2026 (139 mois) ; chaud OK, **froid OK** (53 mois>0, base 22) ; 2026 jusqu'à juillet | ✅ excellent |
| **Conso élec (ENEDIS)** | 2023-05 → 2026-06, 422 700 lignes jour (2023 partiel) | ✅ bon (N/N-1 OK) |
| **Conso gaz (GRDF `gas_consumptions`)** | **0 ligne**, 10 PCE, 0 rattaché bâtiment | ❌ **non chargé** |
| **Puissance max ENEDIS** | **0 ligne** | ❌ absent |
| **Courbe de charge ENEDIS** | **0 ligne** | ❌ absent |
| **Eau (SUEZ)** | néant | ❌ à construire |

### Backend réutilisable

- Climat/perf : `get_fluids_climate` (nouveau), `_dju_monthly_index`, `_parc_elec_by_month`, `get_prm_dju_seasonal/performance`.
- Élec : `_consumption_by_month`, `get_data_ranges`/`get_data_audit`, détail PRM.
- Gaz : `gas_analytics.monthly_series` (DB, kWh PCS, **agrégeable parc**), `reconcile_p1` — **mais table vide**.
- Calibrage/préco : `power_recommendations` (`get_power_recommendations`, `get_prm_power_recommendation`) — **dépend max power / CDC** (vides).

### Constats / risques

1. ⚠️ **Bug méthodo thermosensibilité N-1** : on compare la pente 2026 (6 mois, hiver) à la pente 2025
   (12 mois) → **+73 % artefact**. Correctif = régresser N-1 sur **les mêmes mois** que l'année en cours
   (comparaison à période homogène) + garde-fou nb mois. **Prioritaire** (KPI affiché faux sur staging).
2. **Gaz bloqué** : `gas_consumptions` vide → thermosensibilité gaz, graphe conso gaz et KPI gaz
   impossibles tant que la **collecte GRDF (Phases 2-5)** n'alimente pas la table.
3. **Calibrage / drawer inc 3 / dérives CDC / surveillance abonnements bloqués** : max power + CDC vides.
   Prérequis = **collecter la puissance max** (chemin léger ENEDIS via panneau collecte), puis CDC si profils fins.
4. **Élec = seul fluide complet** aujourd'hui (conso + DJU). Enrichissable sans nouvelle donnée
   (conso **corrigée du climat** DJU-normalisée : données présentes).

### Étapes à venir (repriorisées)

- ✅ **A. Thermosensibilité FAIT** : passée en **fenêtre glissante 12 mois** (courante vs 12 mois
  précédents) → saisonnalité complète, pente robuste. Sur staging : **+13,2 %** (07/2025–06/2026 vs
  07/2024–06/2025, r² 0,64) au lieu de l'artefact +73 % de la comparaison d'années civiles partielles.
- **B. Consolider l'élec** (données prêtes) : conso corrigée du climat (DJU-normalisée), éventuel drill par site.
- **C. Débloquer calibrage/CDC** : collecter **max power** ENEDIS → calibrage + drawer inc 3 + dérives.
- **D. Débloquer le gaz** : alimenter `gas_consumptions` (GRDF Phases 2-5) → thermosensibilité gaz + graphe + P1 réel.
- **E. Eau** : à l'obtention d'une source SUEZ réelle.

Priorité immédiate : **A** ; puis **B** (valeur, données prêtes) ; **C** et **D** = dépendances collecte à planifier.

**Sortis de la vue globale → déplacés dans le détail du fluide :** dérives de courbe de charge
(ENEDIS), **surveillance des contrats / abonnements à recalibrer** (sous-section de chaque fluide),
anneau de qualité par distributeur.

### 3.3 Indicateur thermosensibilité (validé exploitable)

- **Thermosensibilité = pente kWh/DJU** (1 DJU = 1 °C d'écart à 18 °C sur 1 jour) → « impact conso par °C ».
- À compléter par **part thermosensible %** + **talon non climatique**. Déjà à moitié calculé sur
  `/energie` (ratios kWh/DJU, cible, écart) → agrégat parc réaliste.
- **À calculer là où c'est physique** : chauffage gaz/élec + climatisation ; pas sur l'élec non
  thermosensible (éclairage…).
- ✅ **DJU chauffage ET climatisation/froid disponibles** — le moteur d'acquisition DJU existe déjà
  (confirmé 2026-07-09). Les deux séries s'affichent avec comparaison historique 2026/N-1/moyenne.

### 3.4 Données v1 (incrémental)

- KPI/cartes élec = composés depuis `GET /api/energie` (réel) ; gaz = GRDF `conso/monthly` agrégé.
- DJU 2026/N-1/moyenne = `dju/monthly` + série pluriannuelle (`dju_seasonal`).
- Thermosensibilité = agrégée depuis les ratios kWh/DJU existants.
- **Aucune projection financière** sur cette page (décision du 2026-07-09).

## 4. Questions à décider (numérotées)

**Décidé le 2026-07-09 :**
1. ✅ **Navigation détails** → **embarquer** `/energie` (élec) et `/energie/gaz` (gaz), pas de réécriture.
2. ✅ **Périmètre v1** → **réel d'abord** (élec `/api/energie` + gaz GRDF composés) ; **atterrissage /
   prévision / impact € = phase 2** (endpoint agrégé + moteur à construire), étiquetés « estimation »
   ou masqués en v1.
5. ✅ **Routes détail** → **sous-routes dédiées** `/refonte-v1/fluides/electricite|gaz|eau`
   (cartes cliquables, URL partageable).

**Décidé le 2026-07-09 (retour maquette v2) :**
4. ✅ **Surveillance des contrats / abonnements** → **sous-section de chaque détail** fluide
   (ENEDIS / GRDF / SUEZ), plus dans la vue globale.
6. ✅ **Impact financier** → **supprimé** de cette page (elle n'a pas vocation à projeter l'€).
   Dérives de courbe de charge → également descendues dans le détail (spécifique ENEDIS).

**Décidé le 2026-07-09 (retour maquette v3) :**
3. ✅ **Eau / SUEZ** → carte « À construire » seule, **aucun câblage**.
7. ✅ **Drawer calibration** → oui dès la v1 : `Drawer` du DS + préconisation réelle
   (`/energie/{prm}/preconisation`), courbe/pente, étapes du calcul, actions (instruire / demande fournisseur).
8. ✅ **DJU froid disponible** (moteur d'acquisition existant) → série climatisation affichée avec
   comparaison historique, comme le chauffage.

**Toutes les questions de cadrage sont tranchées.** Prochaine étape = maquette validée → code.

## 5. Prochaine étape

Après réponses (au moins Q1, Q2, Q5) : produire une **maquette HTML cliquable** (artifact) de la
vue globale + d'un accès détail, en repartant du prototype, pour valider le parti pris **avant** de
coder. Puis worktree neuf off `origin/main`, incréments testés sur staging.
