# 2026-05-22 - References BPU historiques factures

## Objectif

Ouvrir le controle facture a l'historique EDF/ENGIE sans appliquer les prix
courants ENGIE a une facture ancienne.

## Livraison

- Nouveau service `saas/backend/app/services/invoice_bpu.py`.
- Le controle BPU facture cherche maintenant d'abord une ligne historique dans
  `bpu_*` avec un raccordement exact :
  - fournisseur BPU normalise `EDF` ou `ENGIE` ;
  - date de periode facturee ;
  - segment facture defendable (`C1` a `C4`, `C5_EP`) ;
  - poste horosaisonnier ;
  - composante prix.
- Si aucun raccordement historique exact n'est disponible, le controle reprend
  le comportement existant via `BillingConfig` et `BillingBpuLine`.
- Le resume BPU du rapport de controle expose maintenant le nombre de lignes
  controlees par reference historique, le nombre de lignes controlees par la
  grille configuree et les documents historiques utilises.

## Garde-fous

- Les BPU `ocr_review`, `pending` ou `error` ne servent pas de preuve de prix.
- Deux documents BPU concurrents pour la meme cle facture rendent le match
  historique ambigu : le controle ne tranche pas encore a leur place.
- Les C5 batiments restent volontairement hors resolution historique tant que
  le contexte lot / sous-typologie C5 n'est pas determine explicitement.

## Verification

- `compileall` passe sur le nouveau service, le controle facture et les tests
  ajoutes.
- `git diff --check` passe avec seulement l'avertissement CRLF habituel du
  worktree Windows.
- `pytest` ne peut pas etre execute dans ce shell : le runtime Python fourni
  ne contient pas le module `pytest`.

## Suite

1. Modeliser le contexte marche facture -> fournisseur attendu -> lot -> BPU.
2. Qualifier quelques factures EDF anciennes batiments et eclairage public.
3. Ajouter le parser EDF vers le modele facture normalise deja en place.
