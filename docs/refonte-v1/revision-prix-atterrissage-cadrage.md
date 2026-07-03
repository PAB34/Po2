# Révision des prix dans l'atterrissage DALKIA — cadrage (2 couches)

> Rapport « fil du dev » — 2026-07-03. Cadre la prise en compte des **variables de prix** (indices) dans
> l'atterrissage `/refonte-v1/marches`, en plus de l'évolution structurelle du marché (journal des actes).
> Suite de [[dpgf-base-vs-revise-analyse.md]]. Sources : `docs/energie/CPE-DALKIA/` 06, 12, 17.

## 1. Les deux couches (validé)

Le budget/atterrissage d'un poste DALKIA se construit sur **deux couches indépendantes** :

- **Couche A — évolution structurelle du marché** (« Journal du marché », `CpeDalkiaImportPage`) : avenants
  maîtres (entrée/sortie de bâtiments, renégociation, révision des **cibles/montants**) + révisions DPGF.
  → fait évoluer la **base** DPGF. Capté par l'atterrissage via l'**import actif** (`is_active`) : quand un
  avenant est importé/activé, le `prevu` par poste/année se met à jour automatiquement. ✅
- **Couche B — révision des prix par les variables** (indices, doc 06) : révise les **prix** entre deux
  versions. Formules contractuelles :
  - `P2 = P20 × (0,15 + 0,70·ICHT-IME/ICHT0 + 0,15·FSD2/FSD0)` (1er janvier)
  - `P3 = P30 × (0,15 + 0,30·ICHT-IME/ICHT0 + 0,55·BT40/BT400)`
  - `P1gaz = Pu0 × (a + b·PEG/PEG0 + c·TVD/TVD0 + d·CEE/CEE0 + e·TICGN/TICGN0)` (molécule OS3 figée 5 ans,
    mais TVD/CEE/TICGN restent variables)

## 2. État du code — couche B par poste

| Poste | Formule/variable | Déjà codé ? | Utilisé pour l'atterrissage ? |
|---|---|---|---|
| **P2 / P2.4** | `P2_REVISION_FORMULA` + bases `ICHT_IME_BASE=141,4`, `FSD2_BASE=169,8` | ✅ **facteur attendu calculé** dans `list_revision_observations` | ❌ non — l'atterrissage utilise le facteur **observé** (factures), pas l'attendu (formule) |
| **P3 / P3.4** | `P3_REVISION_FORMULA` + `BT40_BASE=128,4` | ✅ idem | ❌ idem |
| **P1 gaz (Lot 1)** | OS3 + Pugaz | ✅ DPGF `rev_temp_prix` / reconstitution OS3 (PR #40) | ✅ oui |
| **P1-ELEC (Lot 2 piscines)** | fourniture élec DALKIA (`cpe_dalkia_ref_p1_elec`, Annexe 6.2) | ⚠️ base présente, **révision prix élec non modélisée** | ❌ non révisé |

**Constat clé** : pour P2/P3, la mécanique **formule + indices existe** (elle sert au contrôle « facteur
attendu vs observé »). L'atterrissage, lui, lit le révisé **a posteriori sur les factures** (coef observé) :
tant qu'aucune facture révisée n'est arrivée, P2/P3 restent au **budget base (coef 1)**.

## 2bis. Décisions utilisateur (2026-07-03)

- **P2/P3 prospectif : ABANDONNÉ.** « On aura forcément les factures révisées » → le facteur **observé**
  (factures) suffit ; inutile de calculer le révisé par la formule avant facturation. On garde l'existant.
- **P1-ELEC Lot 2 piscines : REPORTÉ** (révision élec laissée de côté pour l'instant).
- Conséquence : la couche B est **considérée traitée** pour le besoin actuel (P1 gaz via DPGF/OS3 ; P2/P3
  via coef observé). Les §3/§4/§6 ci-dessous restent comme trace d'analyse, non planifiés.

## 3. Les trous à combler (couche B) — non planifiés (cf. §2bis)

1. **P2/P3 prospectif** : quand il n'y a pas encore de facture révisée pour l'année, piloter le budget avec
   le **facteur attendu (formule × indices)** au lieu de rester à coef 1. Les indices deviennent *moteurs*
   (pas seulement affichés dans « Indices & variables »). **Réutilise** le calcul existant.
2. **P1-ELEC Lot 2 piscines** : la fourniture élec DALKIA a sa propre révision de prix (analogue P1 gaz côté
   élec). Aujourd'hui = non révisé. À modéliser (OS élec ? BPU ? avenant seul ?). **À investiguer** — pas
   de source de prix élec révisé identifiée pour l'instant.

## 4. Décisions à prendre (numérotées)

1. **Priorité de la source P2/P3** : atterrissage = **observé (factures) si dispo, sinon attendu (formule)**
   — recommandé (le réel facturé fait foi, la formule comble le début d'année). OU formule toujours ?
2. **Source des indices** ICHT-IME / FSD2 / BT40 : d'où viennent les valeurs trimestrielles officielles
   (INSEE) et comment sont-elles alimentées (import vs saisie) ? Prérequis du prospectif — les « Saisie Po2 »
   purgées montrent que la saisie manuelle n'est pas fiable.
3. **P1-ELEC Lot 2** : quel mécanisme de révision du prix élec (existe-t-il un OS/prix élec, un BPU, ou la
   révision passe-t-elle uniquement par avenant sur `cpe_dalkia_ref_p1_elec`) ? À trancher avant de coder.
4. **P2.4/P3.4 (APE)** : confirmer contractuellement qu'ils s'indexent comme P2/P3 (déjà signalé §4
   de `dpgf-base-vs-revise-analyse.md`).

## 5. Ce que je NE fais pas sans validation
- Choisir la priorité observé/formule (Q1) — structurant.
- Coder le P1-ELEC révisé avant d'avoir identifié la source de prix élec (Q3).

## 6. Ordre de traitement proposé
1. **P2/P3 prospectif** (Q1) — petit, réutilise l'existant, gain immédiat en début d'année. Puis
2. **Fiabiliser la source des indices** (Q2) — sinon le prospectif s'appuie sur du fragile. Puis
3. **P1-ELEC Lot 2** (Q3) — après investigation de la source de prix élec.
