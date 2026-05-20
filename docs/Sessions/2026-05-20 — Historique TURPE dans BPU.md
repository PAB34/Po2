# 2026-05-20 — Historique TURPE dans BPU

## Objectif

Retrouver ou la TURPE etait deja utilisee, puis integrer son evolution dans `/energie/bpu` pour que la page montre aussi le contexte reglemente d'acheminement qui impacte le prix complet de l'electricite.

## Constats code

- `saas/backend/app/services/turpe.py` contient le referentiel TURPE 7 detaille.
- `services/invoice_analysis.py` l'utilise pour controler les lignes d'acheminement des factures ENGIE.
- `services/power_recommendations.py` l'utilise pour chiffrer prudemment l'impact annuel d'un changement de puissance souscrite, limite a la part fixe TURPE.
- La page BPU suivait uniquement les composantes fournisseur (`fourniture`, `capacite`, `cee`, `go`), pas l'historique TURPE reglementaire.

## Sources retenues

Serie moyenne HTA-BT, issue des decisions CRE :

- 2021-08-01 : TURPE 6, +0,91 %
- 2022-08-01 : TURPE 6, +2,26 %
- 2023-08-01 : TURPE 6, +6,51 %
- 2024-11-01 : TURPE 6, +4,81 % (evolution 2024 decalee)
- 2025-02-01 : TURPE 6, +7,70 % (evolution exceptionnelle)
- 2025-08-01 : TURPE 7, -1,92 %

## Changements livres

- Backend :
  - ajout de `TURPE_EVOLUTION_EVENTS` et `list_turpe_evolution_events()` dans `services/turpe.py`;
  - ajout du schema `BpuTurpeEvolutionPoint`;
  - nouvel endpoint `GET /api/bpu/turpe-evolution`.
- Frontend :
  - ajout des types et de `fetchBpuTurpeEvolution()`;
  - nouvel onglet `TURPE` dans `EnergieBpuPage`;
  - graphe Recharts de l'indice TURPE base 100 au 2021-08-01;
  - tableau des points CRE avec liens sources.
- Docs :
  - backlog : `PO2-BPU-004` marque fait;
  - etat actuel : ligne BPU TURPE + rappel refresh 2026.

## Validation

- OK : `python -m compileall saas/backend/app/services/turpe.py saas/backend/app/api/routes/bpu.py saas/backend/app/schemas/bpu.py`
- Non fait localement : `npm run build`, car `npm` n'est pas installe sur le poste et `saas/frontend/node_modules` est absent.

## Handoff suivant

- Faire tourner le build frontend via GitHub Actions, Codespaces ou un environnement avec les dependances Node du projet.
- Au prochain refresh CRE 2026-08-01, ajouter le point 2026 dans `TURPE_EVOLUTION_EVENTS` et, si necessaire, le bareme detaille dans `TURPE_TABLES`.
