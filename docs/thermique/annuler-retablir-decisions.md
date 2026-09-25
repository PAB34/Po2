# Annuler / Rétablir — décisions

Date : 2026-09-25

## Existant vérifié

- `useStudyElements` conserve déjà, dans l'ordre, les opérations locales qui n'ont pas encore été
  enregistrées.
- `appliquerEnLocal(content, operation)` est une fonction pure : l'état courant peut donc être reconstruit
  en rejouant les opérations depuis le contenu de l'étude enregistré côté serveur.
- L'enregistrement envoie les opérations au serveur puis vide le brouillon local.
- Le recalcul remplace le contenu local par la réponse du serveur ; une annulation ultérieure doit revenir
  à l'état des corrections en attente et signaler qu'un nouveau recalcul est nécessaire.
- L'édition d'un contour utilise un brouillon distinct dans `useStudyEdition`.
- Les commandes de navigation de la passe des ponts existent déjà et ne font pas partie de ce lot.

## Décisions

**D123 — Les deux commandes sont « Annuler » et « Rétablir ».** Le choix a été confirmé par
l'utilisateur le 2026-09-25. Les boutons sont placés avec les actions d'enregistrement des corrections.
Le bouton d'annulation affiche le raccourci « Ctrl+Z » ; le rétablissement est également accessible par
« Ctrl+Maj+Z » et « Ctrl+Y ».

**D124 — Le premier lot couvre uniquement les opérations locales sur les éléments.** Il permet d'annuler
et de rétablir les confirmations, écarts, reclassements et autres corrections gérées par
`useStudyElements`. Il ne modifie pas le brouillon géométrique de `useStudyEdition`. Pendant l'édition
d'un contour, les raccourcis d'historique des éléments sont neutralisés afin d'éviter une action invisible
sur un autre contexte.

**D125 — L'historique est reconstruit, pas inversé.** Annuler retire la dernière opération active, la
place dans une pile de rétablissement, puis rejoue les opérations restantes depuis le contenu enregistré.
Rétablir replace la dernière opération annulée dans la liste active et rejoue l'ensemble. Cela évite de
maintenir une logique inverse différente pour chaque type d'opération.

**D126 — Un nouveau geste coupe la branche de rétablissement.** Après une annulation, toute nouvelle
correction vide la pile « Rétablir ». « Tout annuler », le changement d'étude et une sauvegarde réussie
vident les deux piles.

**D127 — L'enregistrement constitue une frontière.** Une opération déjà enregistrée côté serveur ne peut
pas être annulée par ces commandes. Après l'enregistrement, les boutons sont désactivés et les raccourcis
ne modifient rien. L'interface indique sobrement qu'il n'y a aucune correction locale à annuler.

**D128 — Le clavier respecte les champs de saisie.** L'écoute est installée en phase de capture pour être
fiable dans l'espace de travail, mais ne détourne jamais `Ctrl+Z`, `Ctrl+Maj+Z` ou `Ctrl+Y` quand la cible
est un `input`, un `textarea`, un `select` ou un élément `contenteditable`.

**D129 — Le recalcul reste explicite après une annulation.** Si le plan a été recalculé puis qu'une
correction est annulée ou rétablie, le bandeau revient à l'état « corrections en attente » et invite à
recalculer. Aucun résultat recalculé obsolète ne doit paraître encore valable.

**D130 — Les commandes montrent leur disponibilité.** « Annuler (Ctrl+Z) » et « Rétablir » sont
désactivés lorsque leur pile respective est vide. Une annonce accessible confirme l'action effectuée ou
explique qu'aucune action locale n'est disponible, sans multiplier les fenêtres modales.

**D131 — La non-régression est contrôlée à trois niveaux.** Les tests ciblés vérifient au minimum :
annulation simple, annulation puis rétablissement, coupure du rétablissement par une nouvelle action,
pile vide, protection des champs de saisie et remise en attente après recalcul. Le build TypeScript est
exécuté. Le jeu réel R+1 doit conserver 227 éléments, 222 côtés cotés, 170,12 m déperditifs, 289 formes
et 77 liaisons.

## Questions à valider

**Q1 — Validée le 2026-09-25.** L'utilisateur valide les décisions D123 à D131, notamment les
raccourcis de rétablissement `Ctrl+Maj+Z` et `Ctrl+Y`, et la limitation initiale aux corrections
d'éléments hors édition de contour.

## Résultat du développement

- Les deux boutons sont disponibles avec les corrections en attente ; « Rétablir » reste visible après
  l'annulation de la dernière correction.
- `Ctrl+Z`, `Ctrl+Maj+Z` et `Ctrl+Y` fonctionnent en phase de capture hors saisie et hors édition de
  contour.
- 12 fichiers de tests frontend thermiques, soit 91 tests, passent ; le typecheck et le build de
  production passent également.
- Le recalcul du R+1 réel reste strictement à 227 éléments, 222 côtés cotés, 170,12 m déperditifs,
  289 formes et 77 liaisons.
- La recette authentifiée à la souris n'a pas été faite : aucun identifiant ni mot de passe n'a été
  demandé, affiché ou saisi.
