# Moteur métier « référentiels des marchés » — décisions avant code

> Doc « fil du dev » — 2026-07-06. Fait suite à l'audit
> [`moteur-metier-referentiels-marches-audit.md`](moteur-metier-referentiels-marches-audit.md).
> Objet : figer les décisions structurantes AVANT de coder l'onglet « Référentiel » de
> `/refonte-v1/marches`. Base de travail : `origin/main` (worktree `feat/moteur-metier-referentiels`).

## 0bis. ⚠️ PIVOT 2026-07-06 (après 1re livraison T1) — remplace une partie du §1

Après avoir vu le stub à l'écran, l'utilisateur a recadré : **ne pas réécrire ce qui marche déjà**.
Décisions qui **remplacent Q3 et la structure** :

- **Q3 → EMBARQUER l'existant** (et non réécrire). Les pages legacy `CpeDalkiaImportPage` et
  `EnergieBpuPage` sont complètes (import + révisions + diff + journal) et **sans paramètre d'URL**
  → montées telles quelles dans le shell refonte. Réécriture DS V1 abandonnée (harmonisation cosmétique
  différée, incrémentale).
- **Structure → HUB CENTRAL unique** (et non un onglet par tier). Le moteur BPU est déjà **unifié tous
  fournisseurs** (EDF/ENGIE/TotalE dans une seule page) → on ne le duplique pas par tier. Nouvelle entrée
  nav **« Référentiels marchés »** (`/refonte-v1/referentiels`, section « Référentiels & admin »),
  2 sous-onglets : **DPGF DALKIA** + **BPU Hérault Énergies**.
- **Gate fidélité (§4bis) → allégée** : l'utilisateur fait confiance au moteur existant et n'a pas de
  documents sources à fournir. **Comparaison poste-par-poste abandonnée.** Restent 2 items d'hygiène
  **optionnels** (non bloquants) : ENGIE peu fourni (1 doc), actes DPGF non qualifiés.
- **T1 stub retiré** : l'onglet « Référentiel » par tier + `MarketReferentielV1` + hooks + fetchers front
  ont été supprimés (revert). Les **guard tests backend** (`test_marches_referentiel_read.py`) sont
  **conservés** (les endpoints restent ceux utilisés par les pages embarquées).
- **Q1/Q5 caducs à court terme** : plus de regroupement sous « Marchés & contrats » (c'est un hub dédié) ;
  renommage API `/api/marches/...` **différé** (les pages legacy tapent les anciens préfixes, ça marche).

> Ce qui suit (§1 à §4) reflète le plan INITIAL, conservé pour trace mais **supplanté par ce §0bis**.

## 1. Décisions tranchées (2026-07-06) — INITIAL, voir §0bis pour l'état retenu

| # | Question (audit §6) | Décision |
|---|---|---|
| **Q1** | Où regrouper DPGF **et** BPU ? | **Tout sous « Marchés & contrats »** (`/refonte-v1/marches`). Onglet « Référentiel » par tier ; fin des adresses éparpillées `/cpe/dalkia-import` et `/energie/bpu`. |
| **Q2** | Consultation seule ou import ? | **Import dès le départ.** La brique Référentiel expose consultation **+** import/mise à jour du référentiel dans le shell refonte. |
| **Q3** | Embarquer le legacy ou réécrire ? | **Réécrire au design-system V1.** Nouveaux composants `features/marches/`, on ne réutilise que le **backend** (pas les pages `CpeDalkiaImportPage` / `EnergieBpuPage`). |
| **Q5** | Renommer l'API maintenant ? | **Renommer `/api/marches/...` maintenant, avec alias** vers les anciens préfixes (`/api/cpe/dalkia-ref`, `/api/bpu`) pour ne rien casser. |

**Conséquence de périmètre** : ce n'est plus un simple « branchement UX » mais un chantier réel
(réécriture DS + import + renommage API). → **découpage en sous-tranches** (§4) pour livrer et valider
sur staging par incréments, pas d'un bloc.

## 2. Question encore ouverte

- **Q4 — SPIE / SUEZ** : type de référentiel (BPU maintenance ?) non cadré. **Hors périmètre de cette
  tranche.** Les tiers `dalkia | gaz | engie | edf` suffisent pour V1 ; la grille sera étendue plus tard.

## 3. Cible retenue (rappel audit §4, confirmée)

Sous `/refonte-v1/marches`, chaque tier expose la même grille d'onglets, avec **« Référentiel » en tête** :

```
/refonte-v1/marches  →  [tier: DALKIA | TotalEnergies(gaz) | ENGIE | EDF]
   ├─ Référentiel      ← NOUVEAU (DPGF pour DALKIA ; BPU pour la fourniture)
   ├─ Atterrissage     (déjà en prod)
   ├─ Cible conso      (DALKIA seulement, déjà en prod)
   └─ Indices & variables (déjà en prod)
```

- **DALKIA** → référentiel **DPGF** (P1/P2/P3, cibles NB) — backend `cpe-dalkia-ref`.
- **gaz / engie / edf** → référentiel **BPU** (fourniture) — backend `bpu` (+ `gas_bpu` pour le lot 7 gaz).

## 4. Découpage technique proposé (sous-tranches, validation staging entre chaque)

Point d'ancrage front : `saas/frontend/src/features/marches/MarketsBudgetPageV1.tsx`
(type `SubView`, tableaux `subs` de chaque `TierConfig`, bloc de rendu conditionnel).

- **T1 — Squelette onglet « Référentiel » (front, consultation)**
  - Ajouter `"referentiel"` à `SubView` et en 1re entrée de `subs` pour les 4 tiers.
  - Nouveau composant `MarketReferentielV1` qui dispatche : DPGF (dalkia) vs BPU (gaz/engie/edf).
  - Vues **lecture** : liste des DPGF/BPU importés (dernier en vigueur + journal), branchées sur les
    endpoints existants (`/api/cpe/dalkia-ref/*`, `/api/bpu/*`) — hooks `use…V1` dans `features/marches/`.
  - Tests : `npx tsc -b` (CI).

- **T2 — Import dans le shell refonte (Q2) — EXIGENCE : état initial ET révisions**
  L'import doit couvrir explicitement, pour chaque référentiel, **la version initiale ET ses révisions**
  (question fondamentale user 2026-07-06). Mécanismes de versionnement existants à exposer :
  - **BPU (fourniture)** : un `BpuDocument` par (fournisseur × année × lot × **avenant**) — champs
    `valid_year`, `valid_from/to`, `amendment_number/label`, `market_subsequent`. Import via
    `POST /bpu/import` (PDF) ou `/bpu/import-xlsx`. → initial = avenant nul ; révisions = avenants /
    nouvelles années. ⚠️ **extraction OCR/parse** (`extraction_status`, `extraction_confidence`) : cf. gate §4bis.
  - **DPGF DALKIA** : deux mécanismes distincts, tous deux à couvrir :
    1. **Référentiel maître** `cpe_dalkia_ref_*` (base P1/P2/P3) versionné par **imports maîtres** +
       **journal des actes** (`acte_type`/`acte_label`/`date_effet`, `is_active`) + moteur de diff.
    2. **DPGF P1 gaz révisé séparé** `cpe_dpgf_p1_*`, **3 niveaux** : `contrat` → `rev_temp` (T°) →
       `rev_temp_prix` (T° + prix OS3) = révisé officiel, livré par DALKIA à chaque OS
       (cf. `dpgf-base-vs-revise-analyse.md`). Ligne d'import dédiée.
    (P2/P3 : révision = indexation calculée ICHT-IME/FSD2/BT40, pas un import.)
  - Tests : parcours import à blanc sur staging + tsc + guard backend versionnement.

- **T3 — Renommage API `/api/marches/...` + alias (Q5)**
  - Nouveaux préfixes `/api/marches/cpe-dalkia/referentiel` et `/api/marches/herault-energie/bpu`
    montés en parallèle des anciens (alias conservés). Front bascule sur les nouveaux.
  - Tests backend ciblés sur le routage/alias (pytest), non-régression des anciens préfixes.

> On peut s'arrêter et livrer après T1 (valeur immédiate : consultation centralisée) avant d'engager T2/T3.

## 4bis. Gate FIDÉLITÉ des données (remarque fondamentale user 2026-07-06)

> « Vérifier que les données affichées correspondent bien au BPU de base fourni. »

L'onglet Référentiel n'invente rien : il affiche ce qui est en base. **Mais le contenu BPU provient d'une
extraction PDF/OCR** (champ `extraction_status` ∈ {ok, ocr_ok, ocr_review, manual, pending, error},
`extraction_confidence`) → **la fidélité au document source n'est pas garantie automatiquement**. C'est
précisément le risque signalé. Il existe déjà un antécédent : `docs/energie/BPU-Audit-PDF-vs-Excel-2026-06-08.md`.

**Gate (bloquant avant de considérer le référentiel « fiable ») :**
1. Sur staging (copie prod), lister par tier les documents et leur `extraction_status` ; prioriser
   `ocr_review` / `manual` / `error`.
2. Pour un échantillon, **comparer poste par poste** les valeurs affichées aux **documents sources**
   (BPU PDF/Excel fournis, DPGF maître). Source de vérité à confirmer par l'utilisateur (emplacement des
   fichiers de référence).
3. Afficher dans l'UI Référentiel un **indicateur de fiabilité** (statut d'extraction + date) pour que
   l'utilisateur voie d'un coup d'œil ce qui est vérifié vs à revoir. (déjà : colonne « Extraction » côté BPU élec).

## 5. Garde-fous (workflow)

- Worktree isolé `feat/moteur-metier-referentiels` basé sur `origin/main`.
- Ne pas toucher `PRONO/*` ni `knockout_mc.py` (Codex). Commits sur pathspecs explicites.
- Pas de merge `main` sans accord explicite → validation staging d'abord.
- Ne pas confondre référentiel **DPGF** et cotation **OS3** du P1 (invariant gaz 2026-05-22 :
  la cotation OS3 reste dans le module CPE, ne pas la fusionner avec la référence BPU TotalEnergies).

## 6. À confirmer avant de coder

1. Les 4 décisions §1 (Q1/Q2/Q3/Q5) sont-elles bien celles retenues ?
2. OK pour le **découpage T1→T3** avec arrêt possible après T1 ?
3. On démarre par **T1 (consultation)** même si Q2 = import dès le départ, pour livrer vite, puis T2 ?
   (ou tu veux T1+T2 groupés dès la 1re PR ?)
