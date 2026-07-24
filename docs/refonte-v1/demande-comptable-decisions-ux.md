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
  - DALKIA : suppression `MONTANT HT`, `VALEUR DE BASE`, `REVISION HT`. **3 colonnes
    additives au niveau ligne** : `MONTANT BASE TTC` + `MONTANT REVISION TTC` =
    `MONTANT TTC`. Révision = dont-révision = montant × (révisé − base) / révisé (TTC) ;
    base = montant − révision (calcul par différence → égalité au centime). Le forfait
    révisé trimestriel a été retiré (maille différente = source de confusion).
  - ENGIE / EDF : `MONTANT HT` → `MONTANT TTC` ; suppression `OPERATION`.
  - TotalEnergies gaz : `MONTANT HT`, `TVA` supprimées (TTC déjà présent).
- Chantier ultérieur (hors périmètre immédiat) : basculer **toutes** les données
  plateforme en TTC (demande explicite de l'utilisateur, étape séparée).

### 5 — Matrice `MATRICE_DALKIA-COMPATBILITE V2.xlsx` + page `/refonte-v1/matrices`

**Diagnostic (2026-07-24) :**

a) **Le parsing V2 est correct.** Simulation sur le vrai fichier : 75 sites,
   en-têtes bien normalisés, `operation_code = None` pour les 75 sites (la feuille
   « Sites vers codes » du V2 n'a aucune colonne opération). Donc le `98004` vu par
   la comptable **ne vient pas du V2**.

b) **La donnée prod est périmée.** Exemple `VDS-BAM 08` (Centre Technique Municipal) :
   - V2 (correct) : service **MABA**, fonction **020**, antenne **CTM**, pas d'opération.
   - Prod (faux) : service **ATBA**, fonction **28**, opération **98004**.
   Le site est dans le V2 (rapproché par `code_site`), donc **un réimport V2 corrige
   tout** — le rapport lit ces axes en direct depuis `CpeAccountingSiteMapping`.
   - **Décision** : réimporter le V2 en prod. Voie auditée = page `/cpe`, bouton
     d'import codification (`POST /cpe/accounting/import-codification`, upsert par
     `code_site`, aucune suppression). Vérifier ensuite le rapport (ligne CTM).
   - Réserve : upsert sans purge → si la ligne facture pointe vers un mapping résiduel
     sous un autre `code_site`, re-vérifier le lien `CpeFinanceLine.accounting_site_id`.

c) **Deux systèmes de matrice déconnectés** (à cadrer séparément) :
   - Système A = `AccountingMatrixRule`/`Version` + snapshots → c'est ce que montre
     `/refonte-v1/matrices` (`MatrixAdminPageV1`), éditeur générique versionné.
   - Système B = `CpeAccountingSiteMapping` + `CpeAccountingNatureRule` (issu du V2)
     → **seul** à alimenter le rapport comptable (LC, antenne, nature).
   - A ne pilote pas le rapport. La page « plus cohérente » attendue = le référentiel
     DALKIA legacy (système B). Chantier : rebrancher `/refonte-v1/matrices` sur B.
