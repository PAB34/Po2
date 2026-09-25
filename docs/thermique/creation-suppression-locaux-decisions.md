# Créer et supprimer un local au clic droit — décisions

Date : 2026-09-25

## Demande

Pouvoir créer ou supprimer un local par un simple clic droit sur le plan.

## Existant vérifié

- Hors édition, le clic droit sur un local permet déjà de l'ouvrir, de changer sa nature, de reprendre
  son contour ou de le couper en deux.
- Le clic droit dans une zone vide ne propose actuellement aucune action.
- Le moteur d'édition sait modifier, couper et fusionner des locaux, mais il n'existe pas encore
  d'opération serveur explicite de création ou de suppression d'un local.
- Les éléments thermiques, côtés, objets d'enveloppe et liaisons sont dérivés ou rattachés aux locaux :
  une suppression silencieuse pourrait donc modifier le métré au-delà du seul contour visible.

## Orientation proposée

**D132 — Créer part du point cliqué.** Un clic droit dans une zone sans local propose « Créer un local
ici ». Le clic ouvre un tracé de contour vide dont le premier point est le point cliqué ; l'utilisateur
pose les autres sommets puis confirme le local, son nom et sa nature.

**D133 — Supprimer est proposé sur le local visé.** Un clic droit dans un local propose « Supprimer ce
local ». L'action demande une confirmation explicite mentionnant le nom du local et les conséquences
calculées avant toute écriture.

**D134 — « Supprimer » écarte le local sans effacer sa trace.** Comme pour un élément d'enveloppe, le
local reste dans l'étude avec un état `exclu` et un motif, sort des métrés actifs, apparaît en grisé et
peut être réactivé. La surface libérée est signalée comme non affectée. Cette solution préserve la
traçabilité et évite une cascade irréversible sur les composants associés.

**D135 — Création et suppression sont enregistrées côté serveur.** Elles produisent une nouvelle version
de l'étude, comme les autres éditions géométriques. Le Ctrl+Z local des corrections d'éléments ne traverse
pas cette frontière dans le premier lot.

## Questions à valider avant développement

**Q2.** Pour créer un local, valides-tu le parcours proposé : clic droit dans le vide, premier point posé
automatiquement, tracé des autres points, puis saisie du nom et de la nature avant confirmation ?

**Q3.** Pour supprimer un local, valides-tu le garde-fou proposé : confirmation obligatoire, puis local
écarté et grisé mais récupérable, plutôt qu'un effacement irréversible avec ses composants rattachés ?
