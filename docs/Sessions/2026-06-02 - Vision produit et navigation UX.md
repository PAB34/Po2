# 2026-06-02 - Vision produit et navigation UX

> IA : Codex
> Session documentaire transversale
> Precedente session : `[[Sessions/2026-06-02 - Inventaire complet des fonctionnalites]]`

## Objectif

Transformer l'inventaire technique en cartographie produit claire pour preparer la refonte de l'interface
et de l'experience utilisateur.

## Ce qui a ete fait

- Lecture de la vision utilisateur, de l'inventaire transversal et de la navigation React actuelle.
- Constat UX : 14 liens plats dans la sidebar, avec melange entre entrees metier, imports et administration.
- Creation de `[[09-Vision-produit-et-navigation-UX]]`.
- Proposition de six domaines : Tableau de bord, Patrimoine, Energie, Contrats et CPE, Technique,
  Administration.
- Description des parcours prioritaires ENGIE, DALKIA et rapprochements patrimoine.
- Passage de `PO2-UX-001` a `En cours`.

## Handoff

### Arbitrages utilisateur

- Choisir la priorite du tableau de bord.
- Valider le nom du domaine CPE.
- Decider qui voit Administration.
- Choisir cascade patrimoine ou carte comme point d'entree.
- Choisir une file transverse `A traiter` ou des files par domaine.

### Implementation apres arbitrage

- Modifier la sidebar dans `saas/frontend/src/App.tsx`.
- Ajouter une sous-navigation contextuelle sans casser les routes existantes.
- Masquer les liens Connexion/Inscription lorsqu'une session est ouverte.
- Regrouper les imports experts dans Administration.

## Notes

- Aucun code frontend n'a ete modifie pendant ce cadrage.
- La console de rapprochement `PO2-PAT-003` reste structurante pour relier les domaines.

