---
read_policy: lire avant de coder le parcours par niveau (lot E3 bis de l'espace de travail thermique)
status: questions_ouvertes
---

# Parcours par niveau — décisions du lot E3 bis

Date : 2026-09-23. Demande de l'utilisateur après le premier usage réel d'E3 en production : les contours des
locaux nord et est ne s'arrêtent pas au bon endroit ; les métrés et les ponts thermiques doivent se lire **sur le
plan** ; les éléments détectés doivent pouvoir être isolés d'un clic ; et surtout le travail doit s'organiser en
**étapes successives par niveau**, et non pièce par pièce en une seule passe.

**Rien n'est codé tant que les questions du § 6 ne sont pas tranchées.**

## 1. Objectif repris et niveau de confiance

- Objectif compris : faire du recalage des contours une étape à part entière, menée niveau par niveau, précédée
  d'un calage automatique qui la rend courte, et suivie d'un recalcul unique puis du travail sur les éléments.
- Niveau de confiance : **élevé** sur le parcours et sur le calage (mesuré, § 2) ; **moyen** sur l'ergonomie des
  métrés dessinés sur le plan, qui demandera un aller-retour visuel avec vous.
- Hors lot : bibliothèque alimentée et association des ponts thermiques au référentiel (E4), hauteurs (E5).

## 2. Existant vérifié le 2026-09-23

### Le défaut de contour, mesuré

Sur `6.1.2 B.asst (1)`, côté nord : le contour est à **27 cm** du nu extérieur, alors que le relevé d'enveloppe
mesure **45 cm** de mur à cet endroit (tronçon T01, `nu_interieur_cm = -45` sur toute sa longueur). Écart d'environ
**18 cm**, et surtout un trait continu là où le relevé décrit des décrochements — 45 cm au droit des trumeaux,
26 cm au droit du mur-rideau (`nu_interieur_cm = -26` sur T02).

Autrement dit : **l'information exacte existe déjà dans l'étude**, elle n'est simplement pas utilisée pour poser
le contour. Le contour vient de `thermicien-plan` (qui lit des pixels), le nu intérieur vient de
`thermicien-enveloppe` (qui mesure bande par bande). Le second est bien plus précis que le premier.

### Ce que l'étude contient déjà

- Par côté de local : adjacence, voisin, longueur, épaisseur, orientation, caractère déperditif, et la liste des
  composants d'enveloppe rattachés avec leur linéaire.
- Par local : surface, périmètre, linéaire déperditif, répartition par adjacence, façade, parois, menuiseries,
  poteaux, linéaire sur local non chauffé, liaison plancher.
- Les **ponts thermiques sont comptés mais pas localisés** : la fiche donne
  `{"angle_sortant": 6.0, "angle_rentrant": 3.0, "about_refend": 0.5}` sans position.
- Le relevé brut porte, pour chaque élément, son tronçon et ses abscisses de début et de fin : de quoi calculer
  la position de chaque élément **et** de chaque liaison.
- **Régression à corriger** : en passant le contrat en version 2 (E3), le relevé reprojeté — qui portait le tracé
  de chaque élément en repère feuille — a été remplacé par le relevé brut. Le tracé est recalculé à chaque
  reconstruction mais n'est plus conservé : il faut le remettre pour pouvoir dessiner les éléments.

### Ce qu'E3 a livré et qu'il faut réorganiser

`Enregistrer et suivant` fait aujourd'hui trois choses d'un coup sur une seule pièce : enregistrer, recalculer
tout le niveau (10 à 15 s) et valider la pièce. Le parcours demandé sépare ces trois gestes ; l'attente cesse
d'être un problème puisqu'on ne recalcule plus qu'une fois par passe.

## 3. Décisions proposées

### D66 — Le calage des contours se fait sur le poste, à l'assemblage, jamais en silence au serveur

À la fin de la chaîne d'étude, avant d'écrire `etude-<niveau>.json`, chaque côté de local qualifié `exterieur`
(et, quand un élément le borde, `paroi`) est **projeté sur le nu intérieur relevé**, décrochements compris. Le
fichier arrive donc déjà calé : à l'import, il n'y a plus rien à corriger.

Ce choix découle de D54 (« import strict, sans correction silencieuse ») : le serveur ne doit pas retoucher une
géométrie à l'insu du thermicien. Le fichier porte `contours_cales: true` et, par local, le déplacement appliqué
à chaque côté, pour que vous puissiez voir ce qui a bougé.

Conséquence : l'étude du R+1 déjà importée en production **devra être réassemblée et réimportée**. C'est
quelques secondes, sans relancer le moindre agent, et l'ancienne étude reste en version.

### D76 — Analyser un projet entier depuis l'outil, par un relais local

Un bouton « Analyser avec Claude Code » met en file d'attente, côté serveur, tous les niveaux classés et à
l'échelle qui n'ont pas encore d'étude. Un petit programme lancé **sur le poste** vide cette file : pour chaque
niveau il télécharge le PDF et ses paramètres, lance `run_etude_niveau.py --mode cli`, puis importe le résultat
par la route d'import existante.

Le serveur ne peut pas démarrer un programme sur le poste : le relais est donc indispensable, et c'est lui qui
porte l'abonnement Claude. Première version **à la demande** (on lance la commande, elle vide la file et
s'arrête) ; le mode en veille (`--boucle`, tâche planifiée) viendra ensuite.

- **Ordre** : du niveau le plus bas au plus haut, le **catalogue validé passant d'un niveau au suivant**, pour
  que les composants gardent les mêmes identifiants dans tout le bâtiment.
- **Reprise** : la file survit à une coupure ; la chaîne repart où son journal s'est arrêté.
- **Garde-fou** : le relais **refuse** de remplacer une étude sur laquelle le thermicien a déjà travaillé
  (locaux validés ou contours retouchés) ; il le signale et passe au niveau suivant.
- **Identification** : le relais demande les identifiants du thermicien à sa première exécution et garde la
  session dans un fichier local, comme le fait le navigateur. Aucun secret n'entre dans le dépôt.

### D67 — Le parcours du niveau en cinq étapes

| Étape | Contenu | Portée |
|---|---|---|
| 1 | Plans : import, échelle, dénomination, classement | le projet |
| 2 | **Analyse** : envoi à Claude Code, traitement niveau par niveau, import automatique (D76) ; import manuel en secours | le projet |
| 3 | **Contours** : reprendre, couper, fusionner | une passe sur le niveau |
| 4 | **Recalcul** du niveau | le niveau |
| 5 | **Éléments** : voir, isoler, modifier, exclure, puis valider le local | pièce par pièce |

La colonne de gauche cesse d'être décorative : elle porte l'étape courante du niveau, son avancement, et
interdit de sauter une étape qui n'a pas de sens (pas d'éléments à traiter sans recalcul).

### D68 — L'édition n'appelle plus le calcul

Les retouches de contour d'une passe s'accumulent dans un **brouillon du niveau**, enregistré côté serveur sans
recalcul. On ne recalcule qu'à l'étape 4. Enregistrer devient instantané.

### D69 — Enregistrement libre en cours de niveau, obligatoire au changement de niveau

À tout moment pendant la passe, « Enregistrer le brouillon ». Si vous changez de planche ou de projet avec des
retouches non enregistrées, l'application le dit et demande quoi faire : enregistrer, ou abandonner les
retouches. Aucun départ silencieux.

### D70 — Recalcul automatique en fin de passe, et à la demande

Quand la passe contours est déclarée terminée, le recalcul part **automatiquement**. Il reste déclenchable à tout
moment sur le niveau, ou sur une seule pièce quand vous voulez vérifier un geste sans attendre la fin.

### D71 — La validation d'un local se déplace à l'étape 5

L'étape 3 enregistre sans juger. Un local passe à « validé » quand vous avez fini d'y travailler les éléments.
Les états restent : à vérifier, validé, à revoir (un voisin a changé).

### D72 — Les éléments détectés : voir, isoler, modifier, exclure

- **Isoler** : par défaut tous les éléments du local sont dessinés ; un clic sur un élément n'affiche que lui ;
  un second clic sur le même revient à tous ; un clic sur un autre n'affiche que ce nouvel élément.
- **Élargissements proposés** : cliquer un élément sur le plan le met en avant dans la liste ; Ctrl+clic pour en
  comparer plusieurs ; le survol éclaire sans figer la sélection.
- **Modifier** : composant de la bibliothèque, type, longueur, et pièce de rattachement.
- **Exclure** : l'élément sort du métré mais reste enregistré, avec le motif et la lecture d'origine de l'agent.
  Rien n'est effacé — c'est aussi ce qui permettra de mesurer la qualité des agents dans le temps.

### D73 — Les métrés dessinés sur le plan

Par défaut, sur le local sélectionné : les cotes des **côtés déperditifs** seulement, la surface au centre, et
les ponts thermiques en pastilles. Un réglage « tout montrer » affiche les cotes de tous les côtés. Les étiquettes
s'effacent quand le zoom ne permet plus de les lire.

### D74 — Les ponts thermiques sont localisés

Nouveau calcul : chaque liaison relevée (angle sortant, angle rentrant, about de refend, liaison plancher) reçoit
sa position à partir de son tronçon et de son abscisse, et son rattachement au local. Sans cela, D73 ne peut pas
les dessiner.

### D75 — Le tracé des éléments revient dans le fichier d'étude

Correction de la régression notée au § 2. Le contrat passe en `format_version: 3` : relevé brut **et** tracé
reprojeté des éléments, liaisons localisées, contours calés.

## 4. Découpage en livraisons

| Lot | Contenu | Pourquoi dans cet ordre |
|---|---|---|
| **F1** | Calage automatique des contours, liaisons localisées, tracé des éléments ; format v3 | réduit d'emblée le travail de l'étape 3 : moins de contours à reprendre à la main |
| **F0** | File d'attente et relais local (D76) | **après F1** : sinon le relais importerait automatiquement des études aux contours faux |
| **F2** | Parcours en cinq étapes, brouillon de niveau, enregistrement obligatoire au changement, recalcul en fin de passe | le squelette du travail quotidien |
| **F3** | Métrés et ponts dessinés sur le plan | lecture |
| **F4** | Éléments : isolement, modification, exclusion | le cœur de l'étape 5 |

E4 (bibliothèque alimentée, ponts associés au référentiel) et E5 (hauteurs) restent après.

## 5. Vérification prévue

1. Réassembler le R+1 en v3 et **mesurer** l'écart avant/après calage sur les bureaux nord et est : le côté nord
   de `6.1.2 B.asst (1)` doit passer de 27 cm à 45 cm du nu extérieur, avec les décrochements au droit des baies.
2. Vérifier que la surface totale des locaux et le taux de couverture s'améliorent, sans chevauchement nouveau.
3. Rejouer la coupe du plateau ouvert et le retour en arrière après la réorganisation du parcours.
4. Vérifier qu'un changement de planche avec brouillon non enregistré est bien retenu.
5. Contrôler sur le banc local, avec le vrai PDF, l'isolement des éléments et les cotes dessinées.
6. Tests ciblés serveur et interface, typage et construction.

## 6. Questions à valider avant le code

**Q1 — Ordre des lots.** Je propose de commencer par **F1** (le calage), parce qu'il réduit le travail manuel de
tous les lots suivants et qu'il répond directement à ce que vous avez observé. **Recommandation : oui.**

**Q2 — Votre étude du R+1 déjà en ligne.** Après F1, je réassemble le fichier en v3 et vous le réimportez sur la
même planche : l'étude actuelle devient une version antérieure, rien n'est perdu. **Recommandation : oui**, sinon
vous travailleriez sur des contours que l'on sait faux.

**Q3 — Les côtés intérieurs.** Le calage s'applique naturellement aux côtés sur l'extérieur, où le relevé
d'enveloppe a mesuré. Pour les cloisons intérieures, il n'y a pas de relevé : je les laisse tels quels.
**Recommandation : oui**, et c'est ce que l'étape 3 servira à corriger à la main.

## 7. Réponses de l'utilisateur du 2026-09-23

Q1 recalcul : **automatique à chaque fin de passe de niveau, et possible à tout moment**.
Q2 validation déplacée à l'étape éléments : oui.
Q3 suppression d'un élément : **exclusion avec trace**, pas d'effacement.
Q4 modification d'un élément : **composant, type, longueur et pièce de rattachement**.
Q5 métrés sur le plan : côtés déperditifs, surface, ponts en pastilles, réglage pour tout montrer.
Q6 calage : **pas un bouton** — il doit se faire automatiquement à la fin du travail des agents, pour que le
fichier importé soit déjà calé. D'où D66.

Second tour, sur le relais (D76) : version **à la demande** d'abord ; traitement **du plus bas au plus haut avec
le catalogue transmis** ; identifiants demandés **une seule fois** au relais et gardés localement.

Ordre des lots retenu : **F1 → F0 → F2 → F3 → F4**.
