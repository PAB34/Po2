# Atterrissage — stratégie & documentation pour le futur front

> Décidé avec le service comptabilité (2026-07-01). Ce document fixe **la stratégie d'atterrissage
> par tiers facturant** pour la refonte, en s'appuyant sur les **pièces contractuelles + cibles**,
> et cartographie l'existant (code) et la **maquette** à réutiliser.
> Sourcing détaillé de l'existant : `atterrissage-sourcing-existant.md`.

## 0. Décision stratégique (le virage)

- **La matrice comptable va « au plus loin » côté compta Ville** (imputation service/fonction/antenne/
  nature/opération) → **puis on s'arrête** côté compta. Le budget **prévisionnel** ligne à ligne pour
  dire « où en est la conso du budget » est jugé **trop compliqué** par la compta : on ne s'appuie pas
  dessus pour l'atterrissage.
- **L'atterrissage se base sur les pièces contractuelles** qui nous lient aux tiers **et sur les cibles
  définies** (contractuelles ou, à défaut, fixées par nous depuis l'historique). Pas sur un budget
  prévisionnel saisi.
- Conséquence : le module **Budget par marché** (PR #33, budget vs réalisé pro-rata) reste utile comme
  vue comptable, mais **n'est pas le moteur d'atterrissage**. L'atterrissage = projection **vs cibles**.

## 1. Maquette de référence (à réutiliser pour la refonte)

- **Prototype HTML autonome** : `docs/prototype-refonte-v1/` (`index.html` + `app.js` + `styles.css`,
  `ouvrir-prototype.cmd`). Sans backend, données simulées. Couvre déjà : budget, fluides, cockpit,
  **atterrissage**, DALKIA, maintenance, P2/P3, ENGIE, EDF, marché, cible. Doc :
  `docs/29-Prototype-frontend-V1-sans-backend.md`.
- **Labo React** monté en prod : `/refonte-v1/*` (`saas/frontend/src/features/{cockpit,fluids,sites,
  invoices,matrices}`). `cockpit/fluids/sites` affichent l'atterrissage **mocké** (`*.mock.ts`).
- **Contrats d'écran** : `docs/34-Contrat-ecran-Fluides-V1.md` (§F04 atterrissage), `36-Cockpit-Sites`.

→ Le front cible reprend la maquille HTML pour l'UX et branche les vrais calculs ci-dessous.

## 2. Principe commun d'atterrissage

Pour chaque poste sous cible : `atterrissage = réalisé à date + reste-à-venir estimé`, comparé à la
**cible contractuelle**. L'estimation du reste-à-venir dépend de la nature :
- **thermosensible (gaz/chauffage)** → extrapolation **climatique DJU** (moteur existant, cf. §3) ;
- **non thermosensible (électricité)** → **pro-rata de la période** (cible annuelle × mois/12), pas de DJU ;
- **travaux (P3/P3.4)** → engagé (devis) vs provision.

## 3. DALKIA

Marché CPE (2 contrats : Lot 1 `C00190116O`, Lot 2 `C00190155J` — cf. périmètre CPE).

### 3.1 Énergétique (gaz / chauffage) — ✅ **existe, à rebrancher**
- **Cibles contractuelles** : NB (révisé chaque année par les travaux APE) et cible via `NC/N'B`.
  Lecture : `resolve_nb_for_year*` (import `cpe_dalkia_ref_cibles`).
- **Moteur d'atterrissage** : `cpe_atterrissage.build_atterrissage()` — extrapolation **DJU**, projette
  NC/N'B + **intéressement/pénalité** contractuels. API `GET /cpe/bilan/{annee}/atterrissage?trimestre=`.
- **Front** : existe (`CpeDalkiaPage`), à reprendre dans la maquette refonte.

### 3.2 Maintenance P2 / P3
- **P2** = **forfait annuel contractuel** (montant fixe connu). Atterrissage = le forfait lui-même
  (pas de projection climatique). *Prévu ?* → oui au sens « montant contractuel connu » ; il reste à
  **exposer le forfait P2** comme cible et à afficher réalisé (acomptes) vs forfait. Pas de moteur
  dédié aujourd'hui, mais trivial (montant contractuel).
- **P3** = **provision annuelle** ; atterrissage = **engagé (devis) vs provision**. ✅ existe :
  `cpe_p3_devis.build_p3_atterrissage()` → `engage_total`, `reste_provision`, `taux_engagement`.
  API `GET /cpe/finances/p3-devis/atterrissage`.

### 3.3 Travaux de performance énergétique = P3.4 (élec) — ✅ **base existe**
- **Cible ELEC** contractuelle (Annexe 5.2) par site/année : `resolve_cible_elec_for_year`.
- **Suivi/atterrissage** : `build_elec_performance()` (IPMVP option B) = cible **au pro-rata de la
  période** vs conso réelle ; gate objectif global **P2.4** (`build_p24_objective`). API
  `GET /cpe/bilan/{annee}/elec-performance` et `/p24-objective`.
- *Prévu ?* → oui, cible contractuelle existante ; à rebrancher dans le front refonte.

## 4. ENGIE — fourniture électricité **bâtiments**

- **Périmètre** : marché ENGIE **désormais limité aux bâtiments** (avant il incluait l'éclairage public,
  désormais chez EDF).
- **Point clé** : c'est un **marché que nous avons avec ENGIE** (fourniture élec), **mais** DALKIA est
  **intéressé/pénalisé sur les consommations d'électricité que ENGIE nous facture** (CPE élec). Donc :
  - l'**atterrissage de la performance** de ces consommations se suit **côté DALKIA** (même moteur
    `build_elec_performance` / cible élec Annexe 5.2, §3.3) ;
  - mais le **front doit l'afficher en précisant « marché ENGIE »** (fourniture) distinct de l'
    **intéressement DALKIA** (performance). Ne pas laisser croire que la performance est « ENGIE ».
- **À construire** : rattacher les PRM ENGIE (bâtiments) aux sites CPE pour que la conso facturée ENGIE
  alimente le suivi de cible élec DALKIA. La matrice comptable (antenne = bâtiment) aide au rapprochement.

## 5. EDF — marché **éclairage public**

- **Cible** : **aucune cible existante**. Décision : **définir nos propres cibles à partir de
  l'historique** de consommation (éclairage public), puis établir un atterrissage.
- **À construire (nouveau)** :
  1. calcul d'une **cible EDF par périmètre** (point lumineux / armoire / secteur) depuis l'historique
     (moyenne N-1/N-2, éventuellement corrigée saison si pertinent) ;
  2. **atterrissage = réalisé à date + reste estimé (pro-rata / profil saisonnier éclairage) vs cible** ;
  3. pas d'intéressement tiers (c'est un marché de fourniture EDF, pas un CPE) → l'atterrissage sert au
     **pilotage interne** (dérive de conso, budget éclairage public).
- Réutilisable : la logique `build_elec_performance` (cible pro-rata vs conso) peut servir de patron,
  avec une **cible auto-définie** au lieu de la cible contractuelle DALKIA.

## 6. Ce qui manque / à construire (synthèse)

| Tiers / poste | Cible | Moteur atterrissage | État |
|---|---|---|---|
| DALKIA gaz (énergétique) | NB/N'B/NC contractuel | DJU (`cpe_atterrissage`) | ✅ existe, à rebrancher front |
| DALKIA P2 maintenance | forfait annuel | trivial (forfait) | à exposer (cible + acomptes) |
| DALKIA P3 travaux | provision | engagé vs provision (`build_p3_atterrissage`) | ✅ existe |
| DALKIA P3.4 / élec perf | cible élec Annexe 5.2 | pro-rata (`build_elec_performance`) + gate P2.4 | ✅ existe |
| ENGIE élec bâtiments | cible élec DALKIA | idem élec perf, **libellé marché ENGIE** | rattachement PRM→site CPE à faire |
| EDF éclairage public | **à définir (historique)** | à construire (cible auto + pro-rata) | ❌ nouveau |

## 7. Recommandations pour le front refonte

1. **Reprendre la maquette HTML** (`prototype-refonte-v1`) comme référence UX pour les écrans
   atterrissage / cockpit / fluides.
2. **Rebrancher l'existant CPE** (atterrissage gaz, élec perf, P2.4, P3) — ne rien recoder.
3. **Un écran « Atterrissage par marché/tiers »** qui, par tiers, affiche : cible (source :
   contractuelle ou auto-définie), réalisé à date, reste estimé, atterrissage, écart à la cible ;
   avec le **libellé du marché** (ENGIE/EDF/DALKIA) distinct de **qui porte l'intéressement** (DALKIA).
4. **EDF** = le seul vrai chantier neuf : moteur de cible depuis l'historique + atterrissage éclairage public.
5. Le **moteur DJU** (`dju_profiles` / `cpe_atterrissage`) est le socle réutilisable pour toute
   estimation de reste-à-venir thermosensible.

## 8. Questions ouvertes

- **DALKIA P2** : veut-on afficher le forfait P2 comme « cible » avec suivi des acomptes, ou le
  laisser hors atterrissage (montant fixe non pilotable) ?
- **ENGIE** : la conso facturée ENGIE (bâtiments) doit-elle alimenter **la même** cible élec DALKIA que
  la part élec déjà suivie, ou une cible distincte ? (dépend du périmètre exact de l'intéressement élec).
- **EDF** : maille de cible éclairage public (global ville / par armoire / par secteur) et méthode
  (moyenne N-1, N-2, correction saison) ?
