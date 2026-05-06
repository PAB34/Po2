# Plan d'execution - Factures et decisions

Date : 2026-05-06

## Objectif

Transformer le module factures energie en outil de decision : une facture doit etre lisible, controlable, commentable, puis validee ou refusee depuis l'application.

## Phase 1 - Socle decision facture

Livrable attendu :

- page detail facture accessible depuis `/energie/factures` ;
- affichage de l'entete facture, des controles, des PRM/FIC et des lignes facture extraites ;
- statut de decision manuel : `a verifier`, `validee`, `refusee`, `contestation envoyee` ;
- commentaire de decision conserve avec la facture ;
- API dediee pour modifier la decision sans relancer l'analyse.

Cette phase ne tranche pas automatiquement la facture. Elle donne une decision assistee : le moteur signale, l'utilisateur arbitre.

## Phase 2 - Controle metier renforce

Ajouter les controles qui conditionnent une validation fiable :

- taxes et TVA ;
- coherence des periodes facturees ;
- comparaison kWh factures vs donnees ENEDIS ;
- puissance souscrite, puissance atteinte et depassements ;
- detail TURPE par composante et par PRM ;
- synthese des ecarts chiffres par famille de controle.

## Phase 3 - Preconisation abonnement chiffre

Faire converger factures controlees et donnees ENEDIS :

- scenarios prudent, equilibre, agressif ;
- niveau de confiance ;
- estimation annuelle lorsque les donnees TURPE et facture sont suffisantes ;
- fiche de preconisation exportable par PRM.

## Phase 4 - Automatisation Chorus

Brancher Chorus seulement apres stabilisation du moteur :

- compte connecteur ;
- jobs d'import ;
- rapprochement numero facture / fournisseur / periode ;
- conservation du fichier source Chorus ;
- generation d'un motif de refus exploitable.

## Phase 5 - Gaz et GRDF

Traiter le Lot 7 dans un moteur separe :

- referentiel BPU gaz ;
- donnees GRDF ;
- controles propres aux composantes gaz ;
- integration ensuite dans la meme experience de validation facture.
