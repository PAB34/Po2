# Demande comptable — décisions UX (retours comptable, 2026-07-24)

Page : `/refonte-v1/factures` → bouton **Demande comptable** (drawer → rapport XLSX
`/billing/comptable/rapport-controle.xlsx`). Moteur : `app/services/comptable_report.py`.
Branche de travail : `feat/comptable-report-fixes` (depuis `main`).

Retours issus du point avec la comptable. Une feuille par tiers facturant
(DALKIA / ENGIE / EDF / TotalEnergies) + Synthèse.

## Sujets & décisions

### 1 + 4 — Opération d'investissement dans la LC (FAIT)
Cas remonté : LC `BATI-28-6156-98004-ATBA-CTM` sur une ligne **maintenance (nature 6156)**.
- Diagnostic : « ATBAT » n'est pas une antenne — c'est le segment service `ATBA`.
  Le vrai défaut = le n° d'**opération 98004** (investissement) qui fuit dans la LC
  d'une ligne P2.
- **Décision** : le numéro d'opération n'apparaît **que pour DALKIA et uniquement
  sur un poste P3 / P3.4**. Ailleurs (P1/P2 DALKIA, ENGIE, EDF, gaz) : jamais.
- Fait : `_cpe_report_lc` gate l'opération sur `_is_cpe_p3_line` ;
  `_energy_report_lc` ne contient plus d'opération. Test : `test_dalkia_p2_line_excludes_operation_from_lc`.
- Reste (sujet 2/3) : retirer la colonne `OPERATION` explicite des feuilles ENGIE/EDF.

### 2 + 3 — Tout en TTC, suppression du HT (EN COURS)
- **Décision** : la comptable travaille en **TTC**. Aucune colonne HT visible.
  TTC calculé depuis le HT + la TVA en vigueur.
- **TTC ligne = HT ligne × (1 + TVA facture)** (taux global de la facture appliqué
  à chaque ligne ; énergie : `total_ttc/total_ht`).
- Colonnes supprimées dans chaque feuille tiers :
  - DALKIA : suppression `MONTANT HT`, `VALEUR DE BASE`, `REVISION HT`. Colonnes TTC
    retenues : `MONTANT TTC`, `PRIX REVISE TTC` (forfait révisé du trimestre) et
    `MONTANT REVISION TTC` = **part de révision comprise dans le facturé** (dont
    révision = montant × (révisé − base) / révisé, puis TTC).
  - ENGIE / EDF : `MONTANT HT` → `MONTANT TTC` ; suppression `OPERATION`.
  - TotalEnergies gaz : `MONTANT HT`, `TVA` supprimées (TTC déjà présent).
- Chantier ultérieur (hors périmètre immédiat) : basculer **toutes** les données
  plateforme en TTC (demande explicite de l'utilisateur, étape séparée).

### 5 — Matrice `MATRICE_DALKIA-COMPATBILITE V2.xlsx` + page `/refonte-v1/matrices` (À CADRER)
- La matrice doit constituer l'écriture comptable de la ville en reprenant tous les
  axes (service, fonction, nature, opération si investissement, **antenne** = colonne J
  « Antenne » de la feuille « Sites vers codes »).
- Suspicion de parsing / de désalignement de la page `/refonte-v1/matrices` avec le
  besoin (relier élément facturé ↔ écriture comptable ville). À auditer séparément.
- Question ouverte : la donnée d'antenne vue en prod (« ATBAT ») provient probablement
  d'un import antérieur ≠ V2 ; vérifier le réimport V2 en prod.
