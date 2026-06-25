# Atelier BPMN Produit & UX

Atelier HTML autonome pour cartographier l'experience utilisateur de PatrimoineAuCarre sous forme de processus BPMN simplifie.

## Ouvrir l'atelier

Double-cliquer sur `ouvrir-atelier.cmd`. Le lanceur ouvre directement l'atelier autonome dans le navigateur, sans PowerShell, sans serveur local et sans installation.

## Versions du modele

Le menu en tete permet de choisir deux modeles independants :

- `Etat actuel - AS-IS` : photographie des fonctions et lacunes ;
- `V1 - Plateforme operationnelle cible` : projection complete avec 16 diagrammes.

Les modifications d'une version n'affectent pas l'autre. L'export JSON contient les deux modeles.
## Travailler et enregistrer

- glisser un cadre avec le clic gauche pour le deplacer ;
- utiliser la molette dans la carte pour zoomer ou dezoomer autour du pointeur ;
- maintenir le clic gauche sur le fond et deplacer la souris pour naviguer dans la carte ;
- double-cliquer un cadre ou une relation pour le commenter ;
- dupliquer un cadre depuis le panneau latéral ou sa fiche en conservant toutes ses propriétés ;
- utiliser `+ Liaison`, puis cliquer la source et la cible ;
- les modifications sont enregistrees automatiquement dans le navigateur, pour ce fichier local ;
- cliquer sur `Exporter JSON` pour creer un jalon durable, partageable et versionnable ;
- utiliser `Importer` pour restaurer un jalon.

L'enregistrement local est un brouillon de travail, pas une sauvegarde de depot. Exporter le JSON apres chaque seance importante.

## Synchronisation avec le developpement

L'atelier ne lit pas automatiquement le code : une fonctionnalite developpee ne suffit pas a determiner son bon parcours UX. Apres une livraison, demander a Codex :

> Synchronise l'atelier BPMN avec les derniers commits sans ecraser mes commentaires.

Les mises a jour versionnees ajoutent les nouveaux diagrammes, cadres et relations sans remplacer les positions, relations et commentaires deja enregistres.

## Fonctionnalites

- 11 diagrammes precharges L0, L1 et L2 couvrant les 50 capacites canoniques ;
- couloirs par acteur ;
- evenements, taches humaines/systeme, decisions, ecrans, donnees et capacites ;
- cadres deplacables et relations typees ;
- fiches specialisees par type de cadre : evenement, tache humaine, systeme, decision, ecran, donnee, capacite et annotation ;
- preremplissage expert des objectifs, regles, entrees/sorties, erreurs, etats UX, qualite des donnees et preuves ;
- details des relations : condition, information transportee, cadence et responsabilite ;
- filtres AS-IS / TO-BE et par acteur ;
- vues Registre et Couverture UX ;
- sauvegarde locale automatique ;
- import/export JSON.