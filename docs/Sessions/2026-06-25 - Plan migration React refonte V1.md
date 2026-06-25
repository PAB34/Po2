# 2026-06-25 - Plan migration React refonte V1

## Contexte

Après validation du prototype V1 et des contrats d’écran Cockpit, Factures, Fluides et Sites 360°, cadrage du passage vers le vrai frontend React.

## Réalisé

- Lecture de `saas/frontend/src/App.tsx` pour comprendre les routes et la navigation actuelles.
- Lecture du début de `saas/frontend/src/lib/api.ts` pour confirmer le rôle central du fichier API.
- Création de `docs/37-Plan-migration-React-refonte-V1.md`.
- Mise à jour de l’index, du backlog et de l’état actuel.

## Décision

Migration progressive en parallèle de l’existant. La V1 ne remplace pas brutalement les pages historiques ; elle démarre avec tokens, composants communs, shell, mocks typés, puis raccordement réel.

## Handoff suivant

Démarrer l’incrément 1 : créer `src/design-system`, `src/app/AppShellV1.tsx` et une première route/surface V1 sans casser les routes existantes. Validation minimale : build frontend.
