# Factures & décisions V1 — décisions UX & contrôles (fichier de travail partagé)

> **À quoi sert ce fichier**
> Fichier commun, tenu à jour par Claude, pour la refonte de la page `/refonte-v1/factures`.
> Il recense **tous les contrôles / écarts** affichés, par **tiers facturant**, leur traitement
> décidé, et **toutes les questions ouvertes** à trancher avec Pierre‑André pour que l'interface
> reflète exactement ses attentes. Une ligne = un sujet. On édite ici **avant** de coder.
>
> Convention de verdict cible :
> - **A — Écart réel** : anomalie de facturation exploitable → badge rouge « ÉCART », compté en *Écarts*.
> - **C — Non contrôlable** : référence/donnée manquante côté plateforme → badge « N/C », compté en *Bloqués*.
> - **I — Info / alerte** *(à créer)* : information pertinente mais ni écart ni bloquant → discret (ex. triangle orange en bout de ligne), **non compté** en Écarts ni en Bloqués.
> - **Supprimé** : le contrôle n'est plus émis du tout.
>
> Page : [InvoicesDecisionPageV1.tsx](../../saas/frontend/src/features/invoices/InvoicesDecisionPageV1.tsx) ·
> Moteur énergie : [invoice_analysis.py](../../saas/backend/app/services/invoice_analysis.py) ·
> Moteur CPE : [cpe_accounting.py](../../saas/backend/app/services/cpe_accounting.py)

---

## 1. Décisions déjà prises (historique)

| Date | Sujet | Décision | Commit |
|---|---|---|---|
| 2026‑06‑28 | Faux écarts EDF (PRM/BPU) | Reclassés « non contrôlable » (set `NON_CONTROLABLE_CODES` élargi) | `7c90158` |
| 2026‑06‑28 | Contrôle **TURPE / acheminement** | **Supprimé** (faux positifs, réf. non alignées) | `7c90158` |
| 2026‑06‑29 | Recalcul EDF (.csv) | `_recompute_invoice_import` : recontrôle sur le parse stocké si fichier ≠ PDF | `8eb8e1b` |
| 2026‑06‑29 | `UNKNOWN_PRM`, `ENEDIS_CONSUMPTION_MISSING`, `ENEDIS_POWER_MISSING` | **Supprimés** (donnée externe absente ≠ écart) | `cea3c89` |
| 2026‑06‑29 | Contrôle **PUISSANCE** complet (`_check_power_controls`) | **Supprimé** : « Puissance atteinte… » n'a pas sa place dans le contrôle de facture | _(ce commit)_ |

**Principe directeur validé** : une **donnée externe absente** (référentiel ENEDIS non chargé, courbe de charge, etc.) **n'est jamais un écart de facturation** et ne doit pas bloquer la facture.

---

## 2. Inventaire des contrôles — Fluides (ENGIE / EDF, moteur énergie)

### 2.1 Vrais écarts (A) — à conserver
| Code | Message | Statut |
|---|---|---|
| `BPU_PRICE_MISMATCH` | Prix facturé ≠ prix BPU | A ✅ |
| `BPU_TARIFF_POSTE_INCONSISTENCY` | Prix cohérent mais mauvais poste/tarif | A ✅ |
| `TOTAL_TTC_MISMATCH` | Somme des FIC ≠ total facture | A ✅ |
| `LINE_AMOUNT_MISMATCH` | Ligne incohérente (qté × PU ≠ montant) | A ✅ |
| `VAT_TOTAL_MISMATCH` / `VAT_RECALC_MISMATCH` / `HT_TOTAL_MISMATCH` / `INVOICE_VAT_TOTAL_MISMATCH` | Incohérences HT/TVA/TTC | A ✅ |
| `PERIOD_INVALID` | Période incohérente (fin avant début) | A ✅ |
| `DUPLICATE_INVOICE_NUMBER` | N° de facture déjà importé | A ✅ |
| `MISSING_INVOICE_NUMBER` / `MISSING_TOTAL_TTC` | Donnée d'identité critique absente | A ✅ |
| `SUPPLIER_UNKNOWN` | Fournisseur non reconnu (hors ENGIE/EDF) | A ✅ |

### 2.2 Non contrôlable (C) — référence manquante
| Code | Message | Statut |
|---|---|---|
| `BPU_CONFIG_MISSING` / `BPU_LINES_MISSING` | Aucun BPU configuré | C ✅ |
| `BPU_REFERENCE_MISSING` / `BPU_PRICE_MISSING` | Pas de ligne/prix BPU pour ce tarif | C ✅ |
| `MISSING_MARKET_REFERENCE` / `MARKET_REFERENCE_MISMATCH` | Réf. marché (ENGIE only) | C ✅ |
| `MISSING_PRM` | PRM absent sur un site | C ✅ |
| `SUPPLIER_CONTRACT_MISMATCH` | PRM rattaché à un autre fournisseur ENEDIS | C ✅ |
| `TAX_TOTALS_MISSING` | Totaux HT/TVA/TTC incomplets | C ✅ |
| `MISSING_INVOICE_DATE` / `MISSING_REGROUPEMENT` | Donnée d'entête absente | C ✅ |

### 2.3 Supprimés (plus émis)
| Code | Ancien message | Raison |
|---|---|---|
| `UNKNOWN_PRM` | « PRM inconnu dans les donnees energie » | Donnée externe absente |
| `ENEDIS_CONSUMPTION_MISSING` | « Aucune consommation ENEDIS disponible… » | Donnée externe absente |
| `ENEDIS_POWER_MISSING` | « Aucune courbe de charge ni puissance max ENEDIS… » | Donnée externe absente |
| `TURPE_*` | Écarts d'acheminement | Réf. non alignées, faux positifs |
| `POWER_*` (toute la famille) | « Puissance atteinte… / souscrite / dépassement » | Hors périmètre contrôle facture |

### 2.4 ⚠️ À TRANCHER (actuellement comptés en *Bloqués*, ne devraient pas l'être)
| Code | Message | Situation actuelle | Proposition Claude | **Question** |
|---|---|---|---|---|
| `PERIOD_GAP` | « Trou de facturation detecte sur… » | C (Bloqué) | **I — info**, triangle orange en bout de ligne, non bloquant | Voir §3 Q1 |
| `PERIOD_OVERLAP` | « Chevauchement de periode sur… » | C (Bloqué) | **I — info** (idem PERIOD_GAP) | Voir §3 Q1 |
| `LINE_PERIOD_OUTSIDE_SITE_PERIOD` | « Ligne facturee hors periode FIC… » | C (Bloqué) | **I — info** ? ou supprimé ? | Voir §3 Q2 |
| `CONSUMPTION_REFERENCE_MISSING` | « Consommation facturee ou periode incomplete… » | C (Bloqué) | À clarifier (voir §3 Q3) | Voir §3 Q3 |
| `CONSUMPTION_ENEDIS_MISMATCH` / `CONSUMPTION_LOAD_CURVE_MISMATCH` | Conso facturée ≠ ENEDIS | C | **I — info** (écart d'estimation, pas de facturation) ? | Voir §3 Q4 |
| `ENEDIS_CONSUMPTION_PARTIAL` / `LOAD_CURVE_CONSUMPTION_PARTIAL` | Données ENEDIS partielles | C | Supprimé (bruit) ? | Voir §3 Q4 |

---

## 3. Questions ouvertes (à répondre par Pierre‑André)

**Q1 — `PERIOD_GAP` (trou) & `PERIOD_OVERLAP` (chevauchement).**
Pertinents mais **non bloquants, non écart**. Proposition : nouvelle catégorie **« Info »** affichée par un **triangle orange ⚠️ en bout de ligne** (tooltip au survol), + une section « Informations » dans le tiroir. N'entre ni dans *Écarts* ni dans *Bloqués*.
→ *Ce design te convient‑il ? Le triangle en bout de ligne suffit‑il, ou tu veux aussi un filtre dédié « factures avec trou de période » ?*

**Q2 — `LINE_PERIOD_OUTSIDE_SITE_PERIOD`** (« ligne facturée hors période FIC »).
→ *Info comme Q1, ou suppression pure ?*

**Q3 — `CONSUMPTION_REFERENCE_MISSING` — explication.**
Ce n'est **pas** un écart de prix. Il se déclenche quand, pour un site, la facture **n'a pas fourni** au moins l'un de : PRM, date de début, date de fin, **ou quantité de consommation** (kWh). Autrement dit : *le parseur n'a pas réussi à extraire une conso pour ce site*. Deux lectures possibles :
  - soit la facture ne porte effectivement pas de conso sur ce site (normal pour certaines lignes) → **à ignorer** ;
  - soit le **parseur** rate l'extraction (vrai sujet **technique**, à corriger côté parsing, pas à afficher comme écart).
→ *Veux‑tu (a) le supprimer de l'affichage, et (b) que je liste à part les sites où la conso n'est pas extraite, pour vérifier si c'est un trou de parsing ?*

**Q4 — Rapprochement conso ENEDIS** (`CONSUMPTION_ENEDIS_MISMATCH`, partiels).
C'est une comparaison conso facturée vs relevés ENEDIS (donnée externe, estimative).
→ *On garde en simple « Info », ou on supprime tout le rapprochement conso comme on l'a fait pour la puissance ?*

**Q5 — Dépassement de puissance réellement FACTURÉ.**
En supprimant la famille puissance, on a aussi retiré `POWER_OVERRUN_BILLED` qui détectait une **ligne de dépassement facturée en €**. C'était le seul contrôle puissance touchant un vrai montant.
→ *On le laisse supprimé, ou tu veux le réintroduire comme écart réel (A) « dépassement de puissance facturé : X € » ?*

---

## 4. Marché DALKIA (moteur CPE) — à passer en revue

Le moteur CPE distingue déjà nativement `ok` / `error` / `blocked`. À revoir ensemble si certains
`error` doivent devenir « Info », ou si des `blocked` polluent.

| control_type | Verdicts produits | À discuter ? |
|---|---|---|
| `invoice_total_ht` | ok / error | — |
| `invoice_period` / `invoice_timeline` / `invoice_type` | ok / error / blocked | timeline : dates édition/échéance, bloquant ? |
| `p1_gaz_pu_os3` / `p1_gaz_acompte_dpgf` / `p2p3_base_dpgf` | ok / error (/ blocked) | écart de révision = normal (cf. mémoire P1 DPGF) → Info ? |
| `revision_p2` / `revision_p3` / `p2_4_objectives` | ok / error / blocked | — |
| `accounting_nature` / `accounting_site` | ok / blocked | imputation comptable manquante = bloquant légitime ? |

**Question DALKIA (Q6)** : *passe‑t‑on en revue ces contrôles maintenant, ou après avoir figé les fluides ?*

---

## 5. SPIE & SUEZ (à venir)

Sources à ajouter (cf. backlog). À l'ajout, **repartir de ce tableau** : pour chaque contrôle,
décider A / C / I / Supprimé **par tiers**, car le périmètre diffère (ex. SPIE = maintenance CVC,
SUEZ = eau). Section à compléter quand les parseurs seront branchés.
