# Calque « cible conso & intéressement » DALKIA (page refonte /marches) — décisions

> Rapport « fil du dev » — 2026-07-03. Suite du cadrage ENGIE (la cible ne s'affiche que là où elle
> existe = sites DALKIA). Écrit AVANT de coder.

## 1. Audit : tout existe déjà côté calcul (front-only)
La comparaison **cible conso vs réalisé + intéressement/pénalité projetés** par site est **déjà calculée**
et exposée :
- Moteur : `services/cpe_atterrissage.build_atterrissage(db, annee, trimestre, city_id)` — par site :
  `nb_exercice` (cible NB), `n_prime_b_projete` (cible recalée climat), `nc_projete` (conso constatée
  projetée), `ecart_projete`, `type_resultat` (intéressement/pénalité), `montant_ht_projete` ; + totaux
  `total_interessement_projete`, `total_penalite_projete`, `net_projete`, DJU projeté. Modèle pur-DJU
  (extrapolation climatique), sert aux réunions trimestrielles DALKIA.
- Formules : `cpe.calcul_n_prime_b` (N'B), `cpe.calcul_nc` (NC), `cpe.calcul_interessement` (I/pénalité).
- Route : `GET /cpe/bilan/{annee}/atterrissage?trimestre=` → `CpeAtterrissageOut`.
- Client front : `fetchCpeAtterrissage(token, annee, trimestre)` → type `CpeAtterrissage` (déjà utilisé par
  la page legacy `CpeDalkiaPage`).

→ **Aucun backend à écrire.** Le calque = brancher cet endpoint dans la page refonte `/marches` (tier DALKIA).

## 2. Décisions actées

### D1 — Emplacement = nouveau sous-onglet DALKIA « Cible conso & intéressement »
Le tier DALKIA de `/refonte-v1/marches` a aujourd'hui 2 sous-vues (Atterrissage financier, Indices & variables).
On ajoute une **3ᵉ sous-vue** dédiée à l'axe **consommation** (distinct de l'axe € du financier). Uniquement
pour DALKIA (les autres tiers n'ont pas de cible).

### D2 — Contenu
- **Sélecteur de trimestre** (T1–T4, défaut = trimestre courant) + année (défaut = année courante).
- **KPI** : intéressement projeté · pénalité projetée · **net projeté** · (DJU projeté annuel en repère).
- **Tableau par site** (entêtes triables, cohérent avec ENGIE/EDF) : site (code + nom), tarif, **NB**
  (cible), **N'B projeté** (cible recalée climat), **NC projeté** (conso projetée), **écart**, **type**
  (intéressement/pénalité, badge), **montant projeté**, statut.
- Note méthode (pur-DJU, indicatif, à caler sur le tableau DALKIA).

### D3 — Périmètre v1 = GAZ (chauffage)
`build_atterrissage` s'appuie sur la cible **NB gaz** + DJU chauffage (le bien modélisé). La cible **élec**
(IPMVP B, gate P2.4 — cf. `project_cpe_electricite_scope`) n'est **pas** dans ce moteur → **hors v1**,
incrément suivant. On l'indique clairement dans la vue.

### D4 — Réutilisation
`fetchCpeAtterrissage` + type `CpeAtterrissage` existants. Composant refonte `CpeCibleConsoV1.tsx` +
sous-onglet dans `MarketsBudgetPageV1`. Zéro migration, zéro backend.

## 3. Livrables
1. Front : `CpeCibleConsoV1.tsx` (KPI + sélecteur trimestre + tableau triable) branché sur le tier DALKIA.
2. `MarketsBudgetPageV1` : sous-onglet « Cible conso & intéressement » (DALKIA uniquement).

## 4. Hors périmètre v1
- Cible **élec** IPMVP B / gate P2.4 (autre moteur).
- Refonte de la méthode DJU (pur-DJU indicatif conservé).
- Écriture/édition des cibles (lecture seule).
