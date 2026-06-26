# 27 - Modele V1 de la plateforme operationnelle

> Date : 2026-06-24
> Statut : projection produit et UX a relire ; aucun developpement fonctionnel lance par ce document.

## Intention

La V1 n'est pas une nouvelle couche graphique posee sur les ecrans existants. Elle reorganise les capacites developpees autour des utilisateurs, de leurs decisions et des preuves necessaires. Elle reste editable dans l'atelier sans modifier le modele `Etat actuel`.

## Deux modeles dans l'atelier

- `Etat actuel - AS-IS` : photographie des fonctions, ecrans, lacunes et statuts constates ;
- `V1 - Plateforme operationnelle cible` : modele complet a construire et valider.

Les positions, commentaires, duplications et corrections sont independants entre les deux versions. L'export JSON contient les deux modeles.

## Composition de la V1

La V1 contient les 11 parcours metier projetes et trois parcours transversaux supplementaires :

1. cockpits par profil et files de travail ;
2. fiche Site 360 degres ;
3. design system et fondations produit.

Volume de conception : 16 diagrammes, 230 cadres et 259 relations. Les fonctions existantes reutilisables restent marquees `Developpe`. Les elements a livrer ou consolider sont marques `Specifie V1`.

## Experience cible

### Accueil par profil

Chaque utilisateur voit ses decisions prioritaires, alertes, echeances, anomalies et indicateurs. Les profils direction, finances, fluides, maintenance, technique et patrimoine ne recoivent pas le meme cockpit.

### Fiche Site 360 degres

Le site devient le pivot de navigation. Une meme fiche donne acces au patrimoine, locaux et occupations, PRM/PCE et consommations, contrats et couverture, factures et controles, CVC et conformite, budget/PPT, documents et historique.

### Workflow operationnel

Toute anomalie peut devenir une action affectee avec responsable, echeance, commentaire, preuve et statut. Les decisions sont horodatees et restent explicables.

### Pilotage complet

La V1 relie :

- factures contractuelles multi-fournisseurs et DALKIA ;
- consommations ENEDIS/GRDF, DJU et atterrissage kWh puis euros ;
- budget initial, realise, engagements, mandats et atterrissage ;
- inventaire CVC, criticite, conformite et PPT ;
- couverture DALKIA/SPIE et execution de la maintenance ;
- qualite, provenance, fraicheur, documents et audit.

## Fondations ajoutees au registre

- `UX-DS-01` : design system et composants metier ;
- `UX-HOME-01` : cockpits par profil ;
- `UX-SITE-360` : fiche site transversale ;
- `RBAC-01` : roles, permissions et perimetres ;
- `SEARCH-01` : recherche globale ;
- `NOTIF-01` : alertes et notifications ;
- `REPORT-01` : rapports et exports ;
- `ACCESS-01` : accessibilite, responsive et clavier ;
- UX-MEASURE-01 : tests utilisateurs et mesure de reussite ;
- INV-DEDUPE-01 : deduplication des reimports ;
- INV-HISTORY-01 : cycle nouvelle, traitee, archivee et reouverte ;
- INV-IMPORT-AUDIT-01 : rapport et historique des lots ;
- MARKET-CONTACT-01 : contacts entreprise par marche et lot ;
- CLAIM-01 : reclamations et suivi des echanges ;
- MAIL-DRAFT-01 : generation du destinataire, objet et message ;
- MAIL-SEND-01 : envoi direct futur.

## Ordre de conception recommande

1. Design system, navigation, permissions et contrats d'ecran.
2. Cockpits par profil et squelette Site 360 degres.
3. Dossier facture commun ENGIE/EDF/TotalEnergies/DALKIA.
4. Consommations, DJU, atterrissages et budget.
5. Couverture maintenance, CVC, conformite et PPT.
6. Files de travail, notifications, audit, rapports et accessibilite.

## Criteres de recette V1

- un nouvel utilisateur comprend son accueil et sa prochaine action sans formation longue ;
- chaque chiffre affiche sa periode, sa source, sa fraicheur et son niveau de couverture ;
- chaque anomalie permet un drill-down jusqu'a la preuve ;
- chaque decision possede un responsable, une date, un commentaire et un historique ;
- un site est consultable sans naviguer entre plusieurs silos techniques ;
- la direction compare budget, realise et atterrissage sur une matrice commune ;
- les sites non couverts par un contrat de maintenance sont visibles ;
- les parcours prioritaires sont utilisables au clavier, sur ecran reduit et avec les principaux etats d'erreur ;
- les tests utilisateurs sont realises avec chaque profil avant livraison.

## Hors perimetre

Le module de pronostics sportifs reste explicitement hors PatrimoineOp. Les fonctions futures eau, OPERAT, BACS et terrain sont visibles dans la V1 afin de proteger l'architecture, mais leur ordre de livraison doit etre arbitre.
## Contacts de marche et reclamations

Chaque marche et lot possede un contact principal et, si necessaire, un contact d'escalade : entreprise, nom, fonction, adresse e-mail, telephone, periode de validite et statut actif. Lorsqu'une anomalie de facturation est confirmee, la V1 selectionne le bon contact et genere une reclamation comprenant facture, periode, montants, ecarts, demande attendue et preuves.

La solution V1 recommandee est d'ouvrir la messagerie de l'utilisateur (`mailto:`), copier le message ou produire un fichier `.eml`. L'utilisateur relit puis envoie depuis son compte habituel et confirme l'envoi dans la plateforme. Cette approche evite de stocker un mot de passe SMTP et reduit les risques de delivrabilite.

L'envoi direct reste modelise comme option future, apres choix SMTP/API, gestion des secrets, SPF/DKIM, journalisation et validation du besoin reel.

Au 24 juin 2026, OVHcloud annonce une messagerie Starter 15 Go comprise avec chaque nom de domaine. L'offre E-mail Pro est affichee a 1,59 EUR HT/mois/compte. Verifier dans l'espace client que le domaine existant beneficie bien de la boite Starter avant toute commande.

## Cycle de vie des factures

La V1 accepte un export fournisseur portant sur une annee complete. Chaque facture ou avoir est rapproche de l'historique a l'aide d'une cle stable incluant le type de document. Une facture est consideree traitee lorsqu une decision horodatee et attribuee a un responsable a ete enregistree. Le resultat d'import distingue :

- nouvelle facture a traiter ;
- doublon strict ignore ;
- facture connue deja traitee, conservee dans l'historique ;
- facture connue mais modifiee, versionnee puis recontrolee ;
- facture en erreur ;
- facture reouverte avec un motif explicite.

Une mise a jour ne doit jamais effacer une decision, un commentaire, un responsable ou une preuve. Le rapport d'import indique les nombres crees, ignores, mis a jour et en erreur. La file quotidienne ne presente que les nouvelles factures et anomalies ; l'historique reste filtrable et consultable.

## Passe complete de couverture

La seconde passe confirme 66 capacites sur 66 representees dans l'atelier. Le modele actuel contient 11 diagrammes, 155 cadres et 171 relations. La V1 contient 16 diagrammes, 230 cadres et 259 relations. Les ajouts de cette passe sont Fluides/eau, contacts de marche, reclamations assistees, deduplication, historique et audit des imports.

## Arbitrages avant refonte

La V1 porte maintenant 26 questions utilisateur reliees aux cadres concernes : 13 arbitrages structurants (◆, rouge), dont la matrice comptable A26, et 13 choix de conception (◇, ambre). Apres la premiere relecture utilisateur, 17 decisions sont validees et 9 restent a completer. Une reponse validee devient ✓ verte. Le registre complet, les propositions de depart et la sequence d ateliers sont dans [[28-Questions-arbitrage-avant-refonte-V1]].
