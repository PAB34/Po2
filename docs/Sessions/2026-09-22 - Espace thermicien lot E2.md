# 2026-09-22 — Espace thermicien, lot E2

> IA : Codex
> Précédente session : passation `docs/thermique/passation-codex-E2.md`

## Objectif de la session

Importer dans l'espace de travail l'étude raster complète d'un niveau, afficher les locaux sur le plan, les lister
avec les locaux chauffés en premier et ouvrir une fiche détaillée en lecture seule.

## Ce qui a été fait

- Contrat portable `thermique.etude_niveau` produit par `run_etude_niveau.py`, sans appel d'agent supplémentaire.
- Validation stricte du PDF, de la page, de la rotation, des proportions, des identifiants et des contours ;
  conversion durable du repère normalisé en points PDF par inversion de la matrice pdfium.
- Migration 0083 : plan de référence serveur, étude courante et versions complètes.
- Routes authentifiées de lecture et d'import, avec confirmation obligatoire avant remplacement.
- Interface E2 : superposition et sélection synchronisées, liste triée, état des étapes et fiche en lecture seule.
- Données réelles R+1 assemblées dans
  `C:\Users\pa.borja\Documents\Codex\2026-09-18\tu\outputs\complement_R1\etude-R1.json`.

## Vérifications

- Backend : `123 passed, 547 deselected` sur `pytest tests -k thermique`.
- Frontend : `11 passed` sur `vitest run src/thermique`, puis `tsc -b` et build Vite réussis.
- Migration 0083 testée isolément en montée et en descente.
- R+1 réel : 24 locaux (17 chauffés, 5 circulations, 2 non chauffés), 230 éléments rattachés, 32 composants ;
  aucune cellule d'image ni chemin absolu dans le fichier portable.
- Reprojection réelle : erreur maximale de 0,0003 sur 1000 entre le contour normalisé et son retour raster.

## Ce qui reste à faire / handoff

- Faire relire le résultat E2 à l'utilisateur, puis pousser seulement après son accord explicite.
- Lot E3 : édition des sommets des locaux et des rattachements, remodélisation, validation pièce par pièce,
  enregistrement d'une nouvelle version et restauration/versionnement visible.
- Ne pas réintroduire de lecture vectorielle du PDF et ne pas lancer les agents depuis l'application.

## Notes et décisions

- Q1 à Q4 ont été validées le 2026-09-22 ; la source de vérité est
  `docs/thermique/etude-niveau-E2-decisions.md` (D53 à D58).
- Le fichier d'étude est la seule pièce importée ; les artefacts de contrôle restent sur le poste.
- Aucun push ni déploiement n'a été effectué pendant cette session.

## Pour la prochaine IA — entrée en matière

```text
Lis d'abord docs/thermique/etude-niveau-E2-decisions.md puis
docs/Sessions/2026-09-22 - Espace thermicien lot E2.md. E2 est implémenté et testé sur le vrai R+1.
Ne pousse rien sans accord explicite. La suite fonctionnelle est E3 : édition et validation pièce par pièce.
```
