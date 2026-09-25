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
local ». L'action demande une confirmation explicite mentionnant le nom du local, la disparition de ses
contours et métrés dans la version courante, et la possibilité de restaurer une version antérieure.

**D134 — « Supprimer » efface réellement le local.** Choix explicite de l'utilisateur le 2026-09-25 :
pas de local grisé ni récupérable dans la version courante. L'objet `piece` est retiré de l'analyse, puis
le niveau entier est reconstruit. Les fiches, côtés, métrés et rattachements propres à ce local
disparaissent ; les éléments du relevé brut restent la source de vérité et sont réaffectés par le moteur
s'ils appartiennent encore à un local voisin. La version précédente de l'étude reste restaurable depuis
l'historique des versions.

**D135 — Création et suppression sont enregistrées côté serveur.** Elles produisent une nouvelle version
de l'étude, comme les autres éditions géométriques. Le Ctrl+Z local des corrections d'éléments ne traverse
pas cette frontière dans le premier lot.

## Questions à valider avant développement

**Q2 — Validée le 2026-09-25.** Clic droit dans le vide, premier point posé automatiquement, tracé des
autres points, puis saisie du nom et de la nature avant confirmation.

**Q3 — Tranchée le 2026-09-25.** Suppression totale demandée. Le local disparaît de la version courante
après confirmation ; la récupération reste possible uniquement en restaurant une version antérieure de
l'étude.

## Résultat du développement

- Le clic droit dans une zone vide propose « Créer un local ici » et pose immédiatement le premier
  point. Le panneau permet ensuite de renseigner le nom et la nature, de vérifier puis d'enregistrer.
- Le clic droit sur un local propose sa suppression définitive. Une confirmation nomme le local et
  rappelle que seule une version antérieure permet de le récupérer.
- Le backend accepte les opérations versionnées `local_ajouter` et `local_supprimer`, puis reconstruit
  l'intégralité des locaux, côtés, métrés, objets dessinés, liaisons et contrôles de couverture.
- Tests ciblés : 25 tests backend d'édition et 92 tests frontend thermiques réussis ; typecheck et build
  de production réussis.
- Garde-fou R+1 avant geste : 24 locaux, 227 éléments, 222 côtés, 170,12 m déperditifs, 289 formes et
  77 liaisons, strictement inchangés.
- Essais en mémoire sur le R+1 : création d'une gaine `piece-025` donnant 25 locaux ; suppression totale
  de `piece-015` donnant 23 locaux. Les 227 éléments sources et 77 liaisons restent présents ; les côtés
  et le linéaire du local supprimé sortent bien du métré actif.
- Aucune recette authentifiée à la souris n'a été faite : aucun identifiant ni mot de passe n'a été
  demandé, affiché ou saisi.
