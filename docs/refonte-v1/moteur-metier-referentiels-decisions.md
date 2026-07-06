# Moteur métier « référentiels des marchés » — décisions avant code

> Doc « fil du dev » — 2026-07-06. Fait suite à l'audit
> [`moteur-metier-referentiels-marches-audit.md`](moteur-metier-referentiels-marches-audit.md).
> Objet : figer les décisions structurantes AVANT de coder l'onglet « Référentiel » de
> `/refonte-v1/marches`. Base de travail : `origin/main` (worktree `feat/moteur-metier-referentiels`).

## 1. Décisions tranchées (2026-07-06)

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

- **T2 — Import dans le shell refonte (Q2)**
  - Composants d'import DS V1 (upload/preview/confirm) réutilisant les endpoints d'import existants
    (DPGF : import/preview/confirm ; BPU : `import` / `import-xlsx`).
  - Tests : parcours import à blanc sur staging + tsc.

- **T3 — Renommage API `/api/marches/...` + alias (Q5)**
  - Nouveaux préfixes `/api/marches/cpe-dalkia/referentiel` et `/api/marches/herault-energie/bpu`
    montés en parallèle des anciens (alias conservés). Front bascule sur les nouveaux.
  - Tests backend ciblés sur le routage/alias (pytest), non-régression des anciens préfixes.

> On peut s'arrêter et livrer après T1 (valeur immédiate : consultation centralisée) avant d'engager T2/T3.

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
