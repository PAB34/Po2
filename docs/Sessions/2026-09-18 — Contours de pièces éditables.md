# 2026-09-18 — Contours de pièces éditables

> IA : Codex
> Précédente session : conversation Claude Code « Outil thermicien métré plans »

## Objectif de la session

Reprendre le travail interrompu sur les contours du R+1 : permettre le recalage manuel des sommets et
supprimer les zigzags, notamment dans le plus grand espace, sans déformer les formes réelles.

## Ce qui a été fait

### Contours de pièces

- Commit `af9dc199` : simplification adaptative et tests.
- L'éditeur existant a été audité : déplacement, ajout et suppression de sommets sont déjà raccordés à
  l'API, qui recalcule la surface et enregistre la correction comme géométrie manuelle.
- Le moteur essaie les quatre droites dominantes pour une pièce courante, puis nettoie seulement les
  petits zigzags pour un grand espace multi-côtés.
- Le contour brut est conservé dès qu'une simplification est appliquée.
- Les contours croisés, intersections lointaines et écarts de surface excessifs sont refusés.
- Commit `edef539e` : les contours très bruités sont ramenés à vingt sommets au plus ; avertissement
  au-delà de douze sommets et nouveau mode **Retracer par points** avec annulation du dernier clic.
- Validation finale : 13 tests backend ciblés, 4 tests front ciblés et typecheck TypeScript verts.
- Contrôle réel en lecture seule sur cinq clics du R+1 : 20 → 4 sommets sur le cas propre, 59 → 19
  sur le cas fuyant. La comparaison visuelle prouve que les écarts de surface restants viennent de
  menuiseries non désignées, donc de limites absentes en amont et non du simplificateur.

## Ce qui reste à faire / handoff

### Détection hybride des limites manquantes

- **Problème** : trois des cinq clics restent faux et un ne se ferme pas lorsque les menuiseries ne sont
  pas dans les calques désignés. Un post-traitement du polygone ne peut pas reconstruire une limite absente.
- **Suite** : proposer les limites sur un crop raster par IA/vision, puis aimanter les côtés proposés
  aux traits vectoriels proches avant de relancer la polygonisation.
- **Fichiers cibles** : nouveau moteur autonome de proposition locale, puis
  `saas/backend/app/services/thermique_pieces.py` et `PiecesPage.tsx`.
- **Commande locale de validation** :
  `python -m pytest tests/test_thermique_quadrilatere.py tests/test_thermique_pieces.py -p no:cacheprovider`.

## Notes & décisions

- ADR `[[Decisions/014-contours-pieces-simplification-adaptative]]`.
- Détail de l'audit : `thermique/contours-pieces-decisions.md`.

## Pour la prochaine IA — entrée en matière

```text
J'ai lu les trois documents de démarrage et la session « Contours de pièces éditables ».
Je comprends que les contours sont maintenant éditables et retracables, mais que les limites absentes
doivent ensuite être proposées par vision/IA puis aimantées sur le vectoriel.
Je commence par cadrer et tester ce moteur local sur les quatre échecs réels du R+1.
```
