# Édition locale par lot — décisions

Date : 2026-09-25

## Existant vérifié

- Une suppression ou un recadrage enregistré déclenche immédiatement `reconstruire()` sur tout le
  niveau. Sur le R+1 réel, cette reconstruction prend environ 10 à 15 secondes.
- Le bouton actuel « Enregistrer et suivant » mélange trois actions : terminer le brouillon, écrire au
  serveur et choisir le prochain local. Le thermicien ne peut donc pas enchaîner plusieurs contours.
- Les corrections d'éléments disposent déjà d'un modèle efficace : gestes locaux instantanés, puis un
  seul enregistrement/recalcul du lot.
- Les coupes, fusions et créations ont besoin d'une géométrie calculée par le serveur ; ce lot vise en
  priorité les recadrages et suppressions explicitement demandés.

## Décisions validées par la demande

**D139 — Un recadrage est d'abord conservé localement.** « Conserver la modification » ferme le
brouillon sans appel serveur, affiche immédiatement le nouveau contour et libère la sélection pour
passer à un autre local.

**D140 — Une suppression est instantanée dans le brouillon du niveau.** Après confirmation, le local
disparaît immédiatement de la liste et du zonage, mais l'écriture définitive attend l'enregistrement du
lot. « Tout annuler » le fait réapparaître.

**D141 — L'utilisateur choisit quand enregistrer.** Un bandeau permanent compte les modifications
géométriques en attente et propose « Enregistrer les modifications » et « Tout annuler ». Un seul appel
serveur rejoue le lot dans l'ordre et reconstruit le niveau une seule fois.

**D142 — Les métrés sont annoncés comme provisoires.** Avant l'enregistrement groupé, seuls les contours
et la présence des locaux sont mis à jour instantanément. Les côtés, surfaces thermiques, objets et ponts
restent ceux du dernier calcul ; le bandeau dit clairement qu'ils seront actualisés à l'enregistrement.

**D143 — Les opérations nécessitant le moteur restent séparées.** Une création, une coupe ou une fusion
demande d'abord d'enregistrer ou d'abandonner le lot local en attente. Leur comportement serveur actuel
reste inchangé dans ce lot pour ne pas simuler côté navigateur une géométrie complexe.

**D144 — Les sorties sont protégées.** Changer de niveau avec un lot en attente déclenche le même
garde-fou que les corrections d'éléments. `Échap` n'annule que le brouillon de contour actuellement
ouvert ; « Tout annuler » abandonne le lot accumulé.

## Questions validées

**Q5 — Validée par la demande du 2026-09-25.** Le thermicien veut pouvoir passer au local suivant sans
attendre un enregistrement serveur et enregistrer quand il le souhaite.

**Q6 — Validée par la demande du 2026-09-25.** La suppression doit paraître immédiate ; elle est donc
mise dans le même lot local que les recadrages, puis réellement appliquée lors de l'enregistrement choisi.

## Résultat du développement

- « Conserver la modification » remplace « Enregistrer et suivant » pour un recadrage : aucun appel
  serveur, le contour est immédiatement visible et la sélection est libérée.
- Les suppressions confirmées disparaissent immédiatement du brouillon du niveau et rejoignent le même
  lot ordonné que les recadrages.
- Le bandeau des locaux compte le lot et propose « Enregistrer les modifications » ou « Tout annuler ».
  Les métrés provisoires sont explicitement annoncés jusqu'au recalcul final.
- Un changement de niveau protège désormais à la fois les corrections d'éléments et les modifications
  géométriques en attente ; l'enregistrement doit réussir avant de quitter.
- Les créations, coupes, fusions et changements de nature restent bloqués tant que ce lot n'est pas
  enregistré ou abandonné.
- 13 fichiers et 95 tests frontend thermiques passent ; typecheck et build de production réussis.
- Aucun code de calcul thermique serveur n'a été modifié : le gain vient de la suppression des
  reconstructions intermédiaires, pas d'un calcul approximatif.
- Aucune recette authentifiée à la souris n'a été faite : aucun identifiant ni mot de passe n'a été
  demandé, affiché ou saisi.
