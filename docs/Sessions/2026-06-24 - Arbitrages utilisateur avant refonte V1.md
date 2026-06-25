# Session - Arbitrages utilisateur avant refonte V1

> Date : 2026-06-24

## Objectif

Identifier les interrogations a fermer avant la refonte, concentrer le temps utilisateur sur les decisions metier et rendre ces questions visibles directement dans la carte V1.

## Realise

- creation de `docs/28-Questions-arbitrage-avant-refonte-V1.md` ;
- 26 questions avec proposition de depart, dont 12 structurantes et 14 de conception ;
- association de chaque question a un cadre precis de la V1 ;
- marqueurs `◆` rouge, `◇` ambre et `✓` vert ;
- filtres tous/requis/structurants/conception/valides ;
- champs d edition pour la question, la proposition ou reponse et l etat de validation ;
- affichage dans l inspecteur, le registre et la couverture UX ;
- migration non destructive `DATA_VERSION=7`.

## Validation

- `node --check` sur le script extrait : OK ;
- modele V1 : 16 diagrammes et 230 cadres ;
- 26 identifiants uniques A01-A26 ;
- repartition : 12 structurants, 14 conception ;
- preservation d une reponse utilisateur validee lors de la fusion : OK ;
- verification visuelle automatique non disponible car aucun onglet local n etait expose au navigateur integre pendant la session.

## Handoff suivant

1. Ouvrir l atelier puis selectionner `V1 - Plateforme operationnelle cible`.
2. Utiliser le filtre `◆ Structurants` et relire A01 a A12.
3. Double-cliquer chaque cadre, corriger la proposition si necessaire puis passer l etat a `Valide`.
4. Exporter le JSON apres la seance d arbitrage.
5. Demarrer les contrats d ecran du cockpit et du dossier facture seulement apres les arbitrages structurants correspondants.
## Consolidation apres reponses utilisateur

- conservation integrale des reponses brutes en annexe du registre ;
- normalisation en regles produit courtes et points restant a fermer ;
- 17 decisions validees, 9 a completer ;
- A26 Matrice comptable reclassee de conception vers structurant ;
- synchronisation de la carte V1 en `DATA_VERSION=8` ;
- migration non destructive : une reponse personnalisee deja saisie dans la carte reste prioritaire ;
- roles et parcours nouvellement explicites : CIRIL, deux profils comptables, ordre de service, depot tiers DALKIA P3 et controle BPU.

Validation : syntaxe JavaScript OK ; 16 diagrammes, 230 cadres, 17 arbitrages valides, 9 requis ; A26 structurant ; test de preservation des reponses carte OK.