# 2026-06-02 - Inventaire complet des fonctionnalites

> IA : Codex
> Session documentaire transversale
> Precedente session : `[[Sessions/2026-06-01 - CPE pilotage financier et controle global]]`

## Objectif

Produire un inventaire complet des fonctionnalites developpees pour identifier ce qui est utile, ce qui se
recouvre et ce qui merite une revue avant retrait.

## Ce qui a ete fait

- Lecture du cockpit documentaire et cartographie du code reel.
- Constat : 201 routes FastAPI, 21 pages React, 50 modeles SQLAlchemy et 36 migrations.
- Integration des travaux recents Claude Code sur le moteur DALKIA issu des XLSX d'acte d'engagement :
  tables `cpe_dalkia_ref_*`, preview, RECAP, NB annuel, controles P2/P3 et sync P1.
- Creation de `[[08-Inventaire-fonctionnalites-developpees-2026-06-02]]`.

## Handoff

### Priorite 1 - Rapprocher les referentiels

- Implementer `PO2-PAT-003` : relier patrimoine, PRM/PCE et sites CPE/DALKIA sans ecraser les sources.

### Priorite 2 - Arbitrer les recouvrements

- Decider `bpu_*` vs `BillingBpuLine`.
- Decider `CvcInventoryItem` vs `BuildingEquipment`.
- Confirmer si le proxy `/api/engie/*` doit rester actif.

### Priorite 3 - Continuer le moteur DALKIA

- Rebrancher l'UI sur `/p2p3`, `/cibles`, `/ape`, `/recap`.
- Parser P3.4 detaille, BPU/DQE et coefficients restants.
- Creer le suivi operationnel APE.

## Notes

- Aucun code metier n'a ete modifie.
- Ne supprimer aucun recouvrement avant validation metier et verification en production.
- Les fichiers locaux non suivis `saas/energie/DALKIA/` et `saas/energie/Guide API.txt` restent intacts.

