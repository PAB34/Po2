# Annuler une édition de contour — décisions

Date : 2026-09-25

## Existant vérifié

- La reprise d'un contour, la coupe et la création d'un local utilisent le même brouillon
  `useStudyEdition`.
- `reset()` sait déjà abandonner ce brouillon et son aperçu sans écrire côté serveur.
- Un bouton « Annuler » existe dans les panneaux d'édition et de création, mais son libellé ne précise
  pas clairement qu'il abandonne toute l'édition.
- La touche `Échap` efface actuellement les points des autres outils du plan, mais n'abandonne pas le
  brouillon d'édition.

## Décisions

**D136 — Échap abandonne tout le brouillon géométrique.** Pendant une reprise de contour, une coupe ou
la création d'un local, `Échap` appelle le même `reset()` que le bouton. Aucun appel serveur n'est fait et
le plan revient à la dernière version enregistrée.

**D137 — Le bouton est explicite.** Son libellé devient « Annuler l'édition » et son infobulle rappelle
le raccourci `Échap`. Il reste désactivé pendant un calcul en cours pour ne pas masquer une réponse
serveur encore attendue.

**D138 — Le raccourci est capturé au niveau de l'espace de travail.** Il fonctionne même si le focus est
dans le champ du nom du local. Il ferme aussi un éventuel menu contextuel et ne touche pas à l'historique
`Ctrl+Z` des corrections d'éléments.

## Question validée

**Q4 — Validée par la demande du 2026-09-25.** L'utilisateur demande explicitement `Échap` et un bouton
pour annuler une reprise de contour ou une action équivalente sur un local.

## Résultat du développement

- `Échap` abandonne désormais la reprise de contour, la coupe ou la création d'un local tant qu'aucun
  calcul serveur n'est en cours.
- Les deux panneaux affichent « Annuler l'édition » avec l'infobulle « Raccourci : Échap ».
- 12 fichiers et 93 tests frontend thermiques passent ; le typecheck et le build de production passent.
- Aucun calcul thermique n'a été modifié ; les repères chiffrés du R+1 ne sont donc pas affectés.
- Aucune recette authentifiée à la souris n'a été faite : aucun identifiant ni mot de passe n'a été
  demandé, affiché ou saisi.
