# 2026-06-09 - Controle factures ENGIE BPU canonique

> IA : Codex GPT-5
> Duree approximative : 1h
> Precedente session : `[[Sessions/2026-06-09 — Analyse et scaffolding API GRDF ADICT]]`

## Objectif de la session

Clarifier les nombreuses erreurs de controle facture observees sur
`saas/energie/ENGIE/FACTURES/MesFactures_20260609132103.xlsx`, avec comme reference BPU opposable
`saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/extraction_tarifs_electricite_BPU.xlsx`, afin de fiabiliser
la future fiche de liaison au service finance.

## Ce qui a ete fait

### PO2-FACT-001 - Controle BPU ENGIE

- Lecture de `docs/00-Index.md`, `docs/Backlog.md`, `docs/04-Etat-actuel-du-dev.md`.
- Diagnostic local sur le XLSX ENGIE du 2026-06-09 :
  - 185 bordereaux ;
  - 1 267 sites ;
  - BPU courant ENGIE 2026 = `2025_18_MS1_BPU_ENGIE_LOT_1.pdf`, Lot 1, depuis `extraction_tarifs_electricite_BPU.xlsx` ;
  - 5 996 lignes tarifaires controlees ;
  - 0 ecart prix BPU ;
  - 0 reference manquante.
- Conclusion : les nombreuses erreurs observees etaient des faux positifs de referentiel/mapping, pas des erreurs ENGIE averees sur les prix unitaires.
- Fichiers principaux touches :
  - `saas/backend/app/services/billing_bpu_sync.py`
  - `saas/backend/app/services/invoice_analysis.py`
  - `saas/backend/app/api/routes/bpu.py`
  - `saas/backend/tests/test_billing_bpu_sync.py`
  - `saas/backend/tests/test_invoice_analysis_bpu_mapping.py`

## Details techniques

- Ajout d'un mapping BPU courant par fournisseur : `ENGIE -> Lot 1`, `EDF -> Lot 2`.
- Le controle facture charge les lignes courantes depuis le xlsx canonique avant les lignes configurees manuellement, afin d'eviter un faux controle contre un ancien lot ou un mauvais lot.
- Le resume BPU expose le document canonique utilise.
- Le cache du BPU courant est vide apres reimport du xlsx via `/api/bpu/import-xlsx`.
- Le mapping tarifaire facture verrouille les cas dominants de l'export :
  - `C5` + `CU` + lignes 4 postes -> `CU4` ;
  - `C5` + `CU` + base seule -> `CU` ;
  - `C2` -> `C2` meme sans libelle tarif d'acheminement.

## Validation

```bash
cd saas/backend
python -m compileall app
python -m pytest tests/test_billing_bpu_sync.py tests/test_invoice_analysis_bpu_mapping.py
```

Resultat : 9 tests passes. Un warning pytest cache local sans impact.

## Handoff suivant

1. Deployer les changements.
2. Reimporter `MesFactures_20260609132103.xlsx` avec l'option de mise a jour forcee.
3. Verifier dans `/energie/factures` que les erreurs `BPU_PRICE_MISMATCH` massives disparaissent.
4. Tester la fiche liaison finance sur quelques bordereaux representatifs :
   - un bordereau C5/CU4 multi-postes ;
   - un bordereau C4 ;
   - un bordereau C2 ;
   - un bordereau avec avoir ou facture negative si disponible.

## Notes et decisions

- Decision durable : pour le controle facture electricite courant, la reference opposable est le xlsx canonique
  `extraction_tarifs_electricite_BPU.xlsx`, pas une configuration UI qui peut rester sur le mauvais lot.
- Les controles TURPE, consommation ENEDIS et puissance restent visibles mais ne doivent pas etre confondus avec
  le controle prix BPU contractuel quand la fiche finance valide/refuse la facture.

## Pour la prochaine IA - entree en matiere

```
J'ai lu :
- docs/00-Index.md
- docs/Backlog.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-06-09 - Controle factures ENGIE BPU canonique.md

Je sais que le poste utilisateur est verrouille entreprise : je ne demanderai aucune installation locale.
Je comprends que la priorite 1 est de deployer puis reimporter le XLSX ENGIE avec force_update pour rejouer les controles.
Je propose de commencer par verifier le statut git, commit/push si demande, puis suivre le deploy et recontroler `/energie/factures`.
```
