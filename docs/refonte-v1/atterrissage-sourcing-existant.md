# Sourcing — Atterrissage financier & énergétique développé AVANT la refonte front

> Rapport d'audit (lecture seule) demandé le 2026-07-01. Objectif : recenser tout ce qui existe
> déjà dans le code/docs sur le calcul d'atterrissage (projection fin d'année), avant le travail
> de refonte du front, pour ne pas le reconstruire.

## TL;DR — 3 familles

1. **Atterrissage ÉNERGÉTIQUE / performance CPE DALKIA** = **construit et fonctionnel** (backend + ancien
   front `/cpe`). Projette l'**intéressement/pénalité** de fin d'année par extrapolation **DJU**.
2. **Atterrissage FINANCIER des Fluides (ENGIE/EDF, doc 34 §F04)** = **spécifié mais NON construit**.
   Seulement **mocké** dans le labo refonte (`fluids.mock.ts`, `cockpit.mock.ts`).
3. **Atterrissage FINANCIER par marché (budget)** = **construit récemment** (cette session, PR #33), en
   **pro-rata temporel simple** — la v1 volontairement légère de la famille 2.

---

## 1. Atterrissage énergétique / intéressement CPE (CONSTRUIT)

Le cœur historique. Répond aux **réunions trimestrielles DALKIA** : « vu le réalisé T1(+T2…), où
atterrit-on au 31/12 ? ».

**Backend**
- `saas/backend/app/services/cpe_atterrissage.py` → `build_atterrissage(db, annee, trimestre)`.
  Méthode (v1, docstring du fichier) : la conso chauffage ∝ DJU ; extrapolation **climatique** (pas
  pro-rata temporel — l'hiver pèse plus) :
  - `DJU_projeté_annuel = DJU_réel(mois écoulés) + DJU_normal(mois restants)` (profil normal = moyenne
    historique du CSV DJU Open-Meteo hors année en cours) ;
  - `NC_projeté = NC_réalisé × (DJU_projeté / DJU_réel_écoulé)` ;
  - `N'B_projeté = NB × (DJU_projeté / 1426)` ;
  - intéressement/pénalité projetés via la **formule contractuelle** `calcul_interessement`.
  ⚠️ Modèle pur-DJU (ignore la part non thermosensible) — à caler sur le tableau DALKIA.
- `saas/backend/app/services/cpe.py` : socle de calcul — `calcul_n_prime_b`, `calcul_nc`,
  `calcul_interessement`, `get_bilan_annuel` (cumul depuis le 1er janvier, ≠ projection),
  `DJU_REFERENCE = 1426`, `resolve_nb_for_year*`.
- `saas/backend/app/services/dju_profiles.py` : moteur DJU (profil DALKIA, agrégation mensuelle,
  mois de chauffe), alimenté par un CSV DJU.

**API** (`saas/backend/app/api/routes/cpe.py`)
- `GET /cpe/bilan/{annee}/atterrissage?trimestre=` → projection intéressement/pénalité.
- `GET /cpe/bilan/{annee}` → bilan cumulé.
- `POST /cpe/bilan/{annee}/calculer`, `POST /cpe/sites/{id}/bilan/{annee}/calculer`.

**Front (ancien, réel)** : `saas/frontend/src/pages/CpeDalkiaPage.tsx` consomme
`fetchCpeAtterrissage` / `fetchCpeBilan` (`saas/frontend/src/lib/api.ts`, types `CpeAtterrissage*`,
`CpeBilanAnnuel`).

**Tests** : `tests/test_cpe_atterrissage.py` (⚠️ 3 tests actuellement rouges car dépendants de la date
du jour — repérés cette session, non liés à nos modifs).

---

## 2. Performance & objectifs électriques CPE (CONSTRUIT, connexe)

Suivi de la trajectoire élec vs cible (le volet élec du CPE, IPMVP B).

**Backend** (`cpe.py`) : `build_elec_performance(db, annee)` (cible vs conso réelle par site, IPMVP B),
`build_p24_objective(db, annee)` (gate objectif global P2.4), `resolve_cible_elec_for_year`.

**API** : `GET /cpe/bilan/{annee}/elec-performance`, `GET /cpe/bilan/{annee}/p24-objective`.

**Front** : `fetchCpeElecPerformance`, type `CpeElecPerf*` ; consommé par `CpeDalkiaPage`.

---

## 3. Atterrissage P3 (travaux DALKIA) (CONSTRUIT, connexe)

**Backend** : `saas/backend/app/services/cpe_p3_devis.py` → `build_p3_atterrissage(db, year)` :
confronte le **cumul des devis engagés** (in-scope) à la **provision P3** → `engage_total`,
`reste_provision`, `taux_engagement`.
**API** : `GET /cpe/finances/p3-devis/atterrissage`.

C'est un atterrissage **budgétaire de travaux** (engagé vs provision), pas climatique.

---

## 4. Atterrissage FINANCIER des Fluides — SPÉCIFIÉ, NON CONSTRUIT

Le vrai « atterrissage financier » énergie (ENGIE/EDF/eau) est **cadré mais pas codé**.

**Spec** : `docs/34-Contrat-ecran-Fluides-V1.md` **§F04 — Atterrissage et scénarios** (route cible
`/fluides/atterrissage`). Formule :
- `réalisé distributeur + consommation restante estimée = atterrissage physique` ;
- `atterrissage physique × prix variables + parts fixes prévues = atterrissage financier` ;
- **scénarios central / bas / haut**, écart au budget, versionné (une correction crée une version).

**État réel** : **aucun service backend** ne l'implémente. Il n'existe **que mocké** dans le labo React :
- `saas/frontend/src/features/fluids/fluids.mock.ts`, `features/cockpit/cockpit.mock.ts`,
  `features/sites/sites.mock.ts` (valeurs d'atterrissage simulées) ;
- affiché par `FluidsPortfolioPageV1.tsx` (données mockées).

**Pré-requis manquants** (pourquoi pas construit) : conso distributeur ENEDIS/GRDF « à date » +
conso restante estimée (moteur DJU/saisonnalité côté fluides) + **prix contractuels versionnés** (BPU).

---

## 5. Atterrissage FINANCIER par marché (budget) — CONSTRUIT cette session (PR #33)

`saas/backend/app/services/accounting_budget.py` → `compute_suivi` : budget vs réalisé (snapshots
factures) vs **atterrissage = pro-rata temporel simple**. Route `/api/accounting-budget/*`, front
`/refonte-v1/marches`. C'est la **v1 légère** de la famille 4 ; le moteur physique→financier du §F04
reste la v2.

---

## 6. Synthèse : réutiliser quoi, construire quoi

| Brique | État | Réutilisable pour la refonte ? |
|---|---|---|
| Atterrissage intéressement CPE (DJU) | ✅ construit | Oui — à rebrancher dans le nouveau front CPE |
| Perf élec / P2.4 / atterrissage P3 | ✅ construit | Oui |
| Moteur DJU (`dju_profiles`) | ✅ construit | **Socle** réutilisable pour l'atterrissage physique Fluides (§F04) |
| Atterrissage financier Fluides §F04 | ❌ à construire (mocké) | Spec prête ; manque conso distributeur à date + BPU versionné |
| Atterrissage budget pro-rata | ✅ construit (PR #33) | Oui — à faire évoluer vers §F04 en v2 |

**Recommandation** : le moteur DJU d'extrapolation climatique du CPE (`cpe_atterrissage`) est
exactement la logique « consommation restante estimée » du §F04. Pour l'atterrissage financier Fluides,
**réutiliser ce moteur DJU** (généralisé aux PRM ENEDIS/PCE GRDF) + les **prix BPU** plutôt que repartir
de zéro. Ne pas confondre avec l'atterrissage **budgétaire pro-rata** (PR #33) qui est une autre maille
(marché/opération, pas physique).
