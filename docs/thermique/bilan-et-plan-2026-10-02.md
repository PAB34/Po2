# Outil thermique — bilan et plan d'objectifs (2026-10-02)

Document de recentrage demandé par le thermicien. **C'est la boussole des prochaines sessions** : chaque lot
proposé doit servir un objectif ci-dessous, dans l'ordre.

## 1. Où en est-on

thermique.patrimoineaucarre.com : métré thermique d'un bâtiment à partir de plans PDF aplatis (lus comme des
images), validé par le thermicien, en vue d'études de déperditions. Projet d'essai : projet 1 (médiathèque),
niveau de travail **R+1** ; R+2 analysé automatiquement (mauvais), autres niveaux non faits.

## 2. Forces

1. **Le socle de données tient.** Tout geste du thermicien s'écrit dans le relevé brut (jamais dans le dessin),
   chaque enregistrement crée une version de l'étude : rien ne se perd, tout se rejoue.
2. **Les gestes manuels fiables existent** et ont été validés à l'usage :
   - calage des niveaux « comme AutoCAD » (validé par le thermicien) ;
   - hauteurs mesurées dans une coupe et posées sur les locaux (un, plusieurs, tout le niveau) ;
   - menuiseries : modèles mesurés en élévation, capture, bibliothèque, pose au clic, exposition au nord,
     morceaux réunis ;
   - murs : ligne de métré + composition validée mur par mur, suppression en un geste.
3. **Un parcours par étapes** (Planche, Analyse, Locaux et hauteur, Parois, Menuiseries, Ponts) avec un
   compteur de ce qui reste, et une fenêtre « Coupes et élévations » sans IA.
4. **Une méthode de travail** : fichier de décisions avant de coder (D1 → D244), tests automatiques (≈ 217 écran,
   plusieurs centaines serveur), mise en production à chaque modification testée.
5. **Le référentiel normatif est posé** : ponts thermiques NF EN ISO 14683, normes du dossier NORMES (pas de
   Th-Bât).

## 3. Faiblesses (dites franchement)

1. **La détection automatique n'est pas fiable.** La passe globale de l'IA rend 23 à 36 objets sur le R+2 contre
   130 au R+1 (fait en session interactive), elle coûte cher et toute la chaîne en hérite. La lecture IA des
   coupes ne servait à rien (retirée).
2. **Trop d'allers-retours d'interface.** Plusieurs fonctions ont été ajoutées puis retirées en quelques jours
   (traits de coupe à placer, lecture IA des coupes, pinceau, retracé, « Affecter aussi à »). Elles restent dans le
   serveur : dette, et risque de confusion.
3. **Je ne teste pas à la souris.** Mes tests vérifient la logique, pas le parcours réel : le thermicien découvre
   des défauts (ex. erreur 422 du mur retracé, oubli à la porte d'entrée du serveur).
4. **Le modèle du mur est incomplet** : relevé découpé par tronçons de façade, murs atypiques (couches non
   parallèles, mur sur plusieurs pans) pas encore représentables.
5. **Les bibliothèques sont dispersées et non validées** : catalogue des composants lu par l'IA (par niveau),
   bibliothèque normée des menuiseries, modèles mesurés du projet, ponts types. Aucune ne porte encore, de bout
   en bout, les valeurs thermiques (U, Uw, ψ) validées par le thermicien.
6. **L'interface est encore chargée** : panneaux, alertes et informations d'anciennes étapes visibles là où
   elles ne servent pas.
7. **Le livrable n'existe pas encore** : surfaces × compositions → déperditions par local (NF EN 12831-1) et
   export ne sont pas faits. Le R+1 lui-même n'est pas fini (3 locaux validés sur 30 au dernier relevé).

## 4. Plan d'objectifs, dans l'ordre

Chaque objectif a un **critère de sortie** vérifiable. On ne passe au suivant que quand il est atteint.

### Objectif 1 — R+1 parfait (en cours)

Critère : sur le R+1, **100 %** des locaux validés avec leur hauteur ; **100 %** des murs avec une composition
validée ; **100 %** des menuiseries avec un modèle mesuré (hors murs-rideaux) ; **100 %** des ponts jugés ; contrôle
de cohérence sans anomalie bloquante ; chiffres de référence du R+1 figés dans `04-Etat-actuel-du-dev.md`.

- 1a. Murs atypiques (lot B, `mur-ligne-de-metre-decisions.md`) : redessiner la ligne de métré, couches non
  parallèles, mur sur plusieurs pans — après réponse aux 3 questions.
- 1b. Coupes et élévations du projet : toutes les vues créées et orientées, hauteurs d'étage mesurées, tous les
  modèles de menuiserie mesurés et capturés.
- 1c. Recette à la souris par le thermicien, étape par étape ; chaque défaut corrigé avec un test qui passe par
  le même chemin que le site.

### Objectif 2 — Interface allégée, étape par étape

Critère : à chaque étape, l'écran ne montre que ce qui sert à cette étape (dessin, panneau, boutons, alertes) ;
aucune fonction retirée ne subsiste ni à l'écran ni dans le serveur.

- 2a. Inventaire, étape par étape, de ce qui s'affiche → liste « garder / replier / supprimer » validée par le
  thermicien avant de coder.
- 2b. Nettoyage du serveur : traits de coupe tracés, lecture IA des coupes et relais associé, pinceau et retracé,
  « Affecter aussi à », passe globale automatique — supprimés ou mis à part, tests ajustés.

> Proposé en parallèle de l'objectif 1 : un écran allégé accélère la consolidation du R+1.

### Objectif 3 — Bibliothèques fiables

Critère : une **bibliothèque du projet** unique où chaque composant (mur, menuiserie, pont) a une composition ou
des dimensions validées **et** ses valeurs thermiques (U, Uw, ψ) avec leur source normative ; réutilisable d'un
niveau à l'autre.

- 3a. Audit des bibliothèques existantes (catalogue IA, bibliothèque menuiseries normée, modèles mesurés, ponts
  types) → fichier de décisions.
- 3b. Fusion en une bibliothèque projet ; validation par le thermicien ; lien depuis chaque mur, menuiserie, pont.

### Objectif 4 — Les autres niveaux

Critère : chaque niveau atteint les critères de l'objectif 1, **sans** passe globale automatique.

- 4a. Report du relevé du R+1 sur un autre niveau par le calage, sans IA (`report-entre-niveaux-decisions.md`,
  D233–D237) : repris / écarté / à relever.
- 4b. Détection « par l'exemple » des menuiseries répétées (on montre une fenêtre, l'outil retrouve ses copies).
- 4c. IA seulement en lecture ciblée, à la demande, sur les morceaux « à relever ».

### Objectif 5 — Le livrable thermique

Critère : pour chaque local, surfaces de parois et de menuiseries × valeurs de la bibliothèque + ponts →
déperditions (NF EN 12831-1), et un export exploitable par une entreprise CVC.

## 5. Règles de conduite (pour ne pas se disperser)

1. Un lot à la fois, au service d'un objectif ci-dessus ; fichier de décisions avant de coder.
2. Après chaque lot : test du thermicien à la souris avant d'en ouvrir un autre.
3. Une fonction retirée de l'écran est retirée du serveur dans le même lot (ou notée pour l'objectif 2b).
4. Pas de lancement d'IA coûteux sans accord ; pas de passe globale automatique.
5. Tout test d'un nouveau geste passe aussi par la porte d'entrée du serveur (schéma de l'API).
