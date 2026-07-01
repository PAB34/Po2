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

### 3.3 P3.4 — Travaux de performance énergétique (APE) — ✅ **documenté (CCAP/CCTP/OUV11)**
> Correction : P3.4 n'est **pas** le suivi de perf élec — c'est un **poste de TRAVAUX**. Documentation
> complète déjà produite dans la base `docs/energie/CPE-DALKIA/` (lecture des pièces marché) :
> `01-Structure-du-marché.md` §P3/APE, `15-Formules-indices-et-travaux-P3.md`.
- **P3.4 = travaux programmés (obligatoires + APE)**. **APE = Actions de Performance Énergétique** :
  travaux d'efficacité énergétique, **montant global et forfaitaire** (non actualisable/révisable),
  **deadline 31/12/2029**, **CEE déduits** du montant des investissements, **suivi séparé du programme
  de travaux**. Révision P3.4 = formule OUV11.
- **Atterrissage P3.4** = suivi **pluriannuel réalisé vs programme forfaitaire APE** (avancement des
  travaux jusqu'à 2029), **pas** une projection conso-vs-cible annuelle. Proche de l'atterrissage P3
  (engagé vs enveloppe), mais sur l'enveloppe **APE forfaitaire**. À construire (le moteur P3 devis
  `build_p3_atterrissage` est le patron ; l'enveloppe = forfait APE, pas la provision annuelle).

### 3.4 Suivi de performance ÉLECTRIQUE (cible vs conso) — ✅ **base existe**
- **Cible ELEC** contractuelle (Annexe 5.2) par site/année : `resolve_cible_elec_for_year`.
- **Suivi/atterrissage** : `build_elec_performance()` (IPMVP option B) = cible **au pro-rata de la
  période** vs conso réelle ; gate objectif global **P2.4** (`build_p24_objective`). API
  `GET /cpe/bilan/{annee}/elec-performance` et `/p24-objective`.
- ⚠️ **Source de la conso réelle = ENEDIS (distributeur), PAS ENGIE (fournisseur).** Voir §4.

## 4. ENGIE / ENEDIS — électricité **bâtiments**

- **Distinguer fournisseur et distributeur** :
  - **ENGIE = fournisseur** (le marché de fourniture, qui nous **facture** l'électricité des bâtiments ;
    avant incluait l'éclairage public, désormais chez EDF).
  - **ENEDIS = distributeur** (qui **mesure et livre** ; **source de vérité de la consommation réelle**).
- **Correction (2026-07-01)** : le **suivi de performance / atterrissage** de DALKIA doit se baser sur
  les **consommations ENEDIS** (données compteur), **pas** sur les consos des factures ENGIE. ENGIE sert
  au **contrôle de facturation** (BPU/TURPE) et à l'imputation comptable ; **ENEDIS** sert au **calcul de
  performance** (conso réelle vs cible élec Annexe 5.2).
- **Intéressement** : DALKIA est intéressé/pénalisé sur ces consommations élec → suivi **côté DALKIA**
  (`build_elec_performance`), mais le front doit **libeller le marché « ENGIE »** (fourniture) distinct
  de **qui porte l'intéressement (DALKIA)**.
- **À construire** : rattacher les **PRM ENEDIS** (bâtiments) aux sites CPE pour alimenter la cible élec
  DALKIA depuis la conso **ENEDIS**. La plateforme dispose déjà d'un socle ENEDIS (module Énergie) et du
  rapprochement patrimoine ; la matrice comptable (antenne = bâtiment) aide au rapprochement.

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

## 5bis. Cible = **BUDGET CONTRACTUEL** branché à la matrice (idée utilisateur — VALIDÉE, réalisable)

> Proposition de l'utilisateur (que j'aurais dû suggérer) : une fois ce premier travail fait, **rattacher
> les cibles/atterrissages à la matrice comptable** pour que le « budget » de référence ne soit **pas le
> budget prévisionnel de la Ville** (jugé trop compliqué par la compta) mais le **budget CONTRACTUEL**
> (issu des pièces qui nous lient aux tiers). **Ce n'est pas une connerie — c'est la bonne cible d'archi.**

**Pourquoi c'est réalisable (les briques existent déjà) :**
- Le **réalisé par opération/nature** est déjà produit par la matrice (snapshots factures → module Budget).
- Le **budget contractuel** est déjà connu, poste par poste, dans les **références contractuelles**
  (`cpe_contract_references`, kinds `p1_gaz_acompte`, provision P3, forfait P2, cibles élec/gaz, forfait
  APE P3.4). Ce sont des **montants/cibles contractuels**, pas une saisie prévisionnelle.
- Il « suffit » donc de **relier chaque cible contractuelle à l'axe matrice** (opération/nature/marché) :
  le module Budget (PR #33) prend alors comme **colonne budget** le **montant contractuel** au lieu d'une
  saisie manuelle. `budget contractuel (référence) − réalisé (snapshots) = atterrissage vs contrat`.

**Conséquences / cadrage :**
- **DALKIA** : budget = P1 (acompte gaz révisé) + P2 (forfait) + P3 (provision) + P3.4 (forfait APE) +
  cibles élec/gaz → tout est **contractuel**, donc pas de saisie Ville.
- **ENGIE** : budget élec = la **cible élec DALKIA** (contractuelle) ; la conso mesurée = **ENEDIS**.
- **EDF** : **exception** — pas de cible contractuelle → on **définit la cible** depuis l'historique
  (§5), puis on la branche pareil à la matrice.
- Le module Budget existant reste, mais **sa source de budget bascule** de « saisie manuelle » à
  « référence contractuelle rattachée à la matrice ». C'est une **évolution**, pas un rejet, de la PR #33.

→ **Séquencement** : (1) finir la matrice comptable (en cours) ; (2) brancher les cibles contractuelles
existantes (CPE) sur l'axe matrice comme budget ; (3) construire la cible EDF (historique) ; (4) le front
affiche « budget contractuel vs réalisé vs atterrissage » par marché/tiers.

## 6. Ce qui manque / à construire (synthèse)

| Tiers / poste | Cible | Moteur atterrissage | État |
|---|---|---|---|
| DALKIA gaz (énergétique) | NB/N'B/NC contractuel | DJU (`cpe_atterrissage`) | ✅ existe, à rebrancher front |
| DALKIA P2 maintenance | forfait annuel | trivial (forfait) | à exposer (cible + acomptes) |
| DALKIA P3 travaux | provision annuelle | engagé vs provision (`build_p3_atterrissage`) | ✅ existe |
| DALKIA P3.4 (travaux APE) | **forfait global APE** (deadline 2029) | réalisé vs programme forfaitaire | ❌ à construire (patron = P3) ; **documenté** CCAP/CCTP |
| DALKIA perf ÉLEC | cible élec Annexe 5.2 | pro-rata (`build_elec_performance`) + gate P2.4 ; **conso = ENEDIS** | ✅ moteur existe ; source ENEDIS à brancher |
| ENGIE élec bâtiments | cible élec DALKIA | idem perf élec, **conso ENEDIS**, **libellé marché ENGIE** | rattachement PRM ENEDIS→site CPE à faire |
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
