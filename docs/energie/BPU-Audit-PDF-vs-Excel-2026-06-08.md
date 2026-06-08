# Audit BPU électricité — PDF source ↔ Excel canonique

tags: #energie #BPU #audit #qualite-donnees

> Objectif : vérifier ligne à ligne que `extraction_tarifs_electricite_BPU.xlsx`
> (onglet `Prix_detailles`, 173 lignes / 17 PDF) reflète **exactement** les valeurs
> des PDF source de `saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/`.
> Toute anomalie → valeur exacte saisie dans le xlsx.
>
> Sauvegarde xlsx avant édition : `extraction_tarifs_electricite_BPU.BACKUP-2026-06-08.xlsx`
> Méthode : PDF texte → `extract_text(extraction_mode="layout")` ; PDF scannés → lecture image extraite.

## Suivi par PDF (17)

| # | PDF | Lignes | Type | Statut | Anomalies |
|---|-----|--------|------|--------|-----------|
| 1 | LOT3 BPU V2_MS3_N°20-28_EDF 2021-2022 prix ferme | 14 | scan 2p | ✅ vérifié | GO 0,56 indicatif p1 (volume ENR=0) — à arbitrer |
| 2 | EDF_MS1_LOT_1_AVENANT_6_BPU_2025 | 19 | texte | ✅ vérifié | aucune (19/19 exact) |
| 3 | EDF_MS1_LOT_2_AVENANT_5_BPU_2025 | 3 | texte | ✅ vérifié | aucune (3/3 exact) |
| 4 | EDF_MS1_LOT_3_AVENANT_5_BPU_2025 | 7 | texte | ✅ vérifié | aucune (7/7 exact) |
| 5 | 2025_18_MS1_BPU_ENGIE_LOT_1 | 17 | texte | ✅ vérifié | aucune (CEE 10,59 / GO 1,67 = cellules fusionnées uniques ; 2 « 0,00 » = artefacts colonne Fourniture) |
| 6 | 2025-19_MS_1_BPU_EDF_LOT 2 | 18 | scan 2p | ✅ vérifié | aucune (18/18 ; cap 0,49 confirmé au zoom ; MUDT HP/HC noircis = NaN correct) |
| 7 | BPU 2024 LOT 1 Elec | 19 | scan | ✅ vérifié | aucune (19/19 exact) |
| 8 | BPU 2024 LOT 2 Elec | 3 | scan | ✅ vérifié | aucune (3/3 exact) |
| 9 | BPU 2024 LOT 3 Elec | 7 | scan | ✅ vérifié | aucune (7/7 exact) |
| 10 | BPU MS n°1 lot n°1 EDF 2023 signé | 19 | scan | ✅ vérifié | aucune (19/19 ; C1 sans GO) |
| 11 | BPU MS n°1 lot n°2 EDF 2023 signé | 3 | scan | ✅ vérifié | aucune (3/3 exact) |
| 12 | BPU MS n°1 lot n°3 EDF 2023 signé | 7 | scan | ✅ vérifié | aucune (7/7 exact) |
| 13 | LOT1 BPU_MS3_N°19-20_EDF 2022 V2 | 18 | scan | ✅ vérifié | aucune (18/18 ; ENR 0,21 appliqué ; capacités négatives OK) |
| 14 | LOT2 BPU V2_MS3 N°19-21 EDF_2021-2022_achat clic | 6 | scan 2p | ✅ vérifié | aucune (6/6 ; ENR 0,21/0,021 Eclairage, Bornes vide) |
| 15 | LOT2 BPU_MS3_N°19-21_EDF 2022 V2 | 3 | scan | ✅ vérifié | aucune (3/3 exact) |
| 16 | LOT3 BPU_MS2_N°20-05_EDF 2022 V2 | 3 | scan | ✅ vérifié | aucune (3/3 exact) |
| 17 | LOT3 BPU_MS3_N°20-28_EDF 2021-2022 prix ferme | 7 | scan | ✅ vérifié | aucune (7/7 ; GO 0,56 indicatif bien saisi) |

Légende : ✅ vérifié · ⏳ en cours · ⬜ à faire

## Corrections au xlsx — ✅ APPLIQUÉES (2026-06-08)

**Audit terminé : 17/17 PDF vérifiés, 172/173 lignes = transcription exacte. 1 seule anomalie, corrigée.**

> ✅ Appliqué via openpyxl le 2026-06-08 (lignes Excel 151–157 de `Prix_detailles`) :
> `Option ENR / GO` 0 → **0,56** et `ENR/GO c€/kWh` → **0,056**, note ajoutée. Fichier intact
> (5 onglets, 173 lignes). Backup : `extraction_tarifs_electricite_BPU.BACKUP-2026-06-08.xlsx`.
> **Reste à faire côté app** : relancer l'import pour propager en base →
> `python -m app.scripts.import_bpu_xlsx --xlsx "<chemin>/extraction_tarifs_electricite_BPU.xlsx" --force`
> (sinon le tableau « Édition » continue d'afficher 0 sur ces 7 lignes jusqu'au ré-import).

| PDF | Site/typologie | Poste | Colonne | Valeur xlsx | Valeur PDF | Décision |
|-----|----------------|-------|---------|-------------|------------|----------|
| LOT3 BPU V2 MS3 2021-2022 (p.1) | C5 RAE Heures Creuses/Pleines | HPH | Option ENR / GO | 0 | 0,56 (indicatif, vol. ENR=0) | → 0,56 |
| idem | C5 RAE Heures Creuses/Pleines | HCH | GO | 0 | 0,56 | → 0,56 |
| idem | C5 RAE Heures Base | Base | GO | 0 | 0,56 | → 0,56 |
| idem | C5 RAE 4 cadrans | HPH | GO | 0 | 0,56 | → 0,56 |
| idem | C5 RAE 4 cadrans | HPB | GO | 0 | 0,56 | → 0,56 |
| idem | C5 RAE 4 cadrans | HCH | GO | 0 | 0,56 | → 0,56 |
| idem | C5 RAE 4 cadrans | HCB | GO | 0 | 0,56 | → 0,56 |

> Justification : le PDF imprime « surcoût Enr 0,56 €/MWh, à titre indicatif car Volume ENR à 0 ».
> Le fichier jumeau non‑V2 (PDF #17) a été saisi à 0,56 → on aligne pour cohérence + valeur exacte.
> Note à ajouter dans la colonne « Notes / observations » : « ENR 0,56 indicatif (Volume ENR à 0) ».
> ⚠️ Application en attente : fermer Excel (lock file `~$` présent).

## Détail des vérifications

## Suite — Branchement BPU → Facturation (anti double-saisie)

`/energie/facturation` (vérification de factures) stockait ses prix `BillingBpuLine` **en double**
de l'historique BPU (table `bpu_*` + template codé en dur `bpu_templates.py`). Branchement ajouté :

- **Source = le xlsx audité** (et non les tables `bpu_*`, qui écrasent la dimension tarifaire :
  ENGIE est importé sous un seul segment « BATIMENT »). Le xlsx garde la colonne Tension/TURPE.
- `services/billing_bpu_sync.py` : `build_lines_for_lot(n)` lit le **document le plus récent du lot**
  (Lot 1 → ENGIE 2026 ; Lot 2 → EDF 2026 « 2025-19_MS_1 »), mappe Tension/TURPE → tarif billing
  (CU/CU4/MU4/MUDT/LU/EP/C4/C2), normalise en €/MWh, et upsert `BillingBpuLine` (year=NULL).
- Validé contre la vérité terrain (`bpu_templates`) : **lot1 identique (21/21)**, **lot2 identique
  (22/22)** sauf les 2 lignes MUDT noircies (cee/go vides côté xlsx — plus fidèle que le template).
  Tests : `tests/test_billing_bpu_sync.py` (5/5).
- Endpoint `POST /billing/configs/{id}/bpu-lines/sync?apply=` (aperçu/écriture) + bouton vert
  « ↻ Reprendre les prix depuis le BPU » dans l'étape BPU de `/energie/facturation`.
- **Pas de suppression** : `/energie/facturation` reste nécessaire (plages HP/HC, mapping
  fournisseur→lot→PRM, moteur de contrôle de factures). Seule la **double saisie des prix** disparaît.

### PDF 1 — LOT3 BPU V2 MS3 2021-2022 prix ferme ✅
Fourniture 14/14 exact · CEE 14/14 exact · Capacité 14/14 exact (4 zéros réels postes 4 cadrans HCH/HCB).
GO : page 2 sans colonne ENR (vide légitime) ; page 1 ENR 0,56 €/MWh **indicatif** « car Volume ENR à 0 » → xlsx a stocké 0 (coût effectif). Seul arbitrage en suspens.
</content>
