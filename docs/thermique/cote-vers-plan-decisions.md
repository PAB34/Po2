# Côté désigné, de la fiche au plan et retour — décisions (sujet 2)

Date : 2026-09-28

> « quand je clique sur une pièce dans le volet de droite s'affiche des éléments dans "Côtés et
> adjacences" j'aimerais pouvoir cliquer dessus qu'il se sélectionne dans le plan automatiquement »

## Existant vérifié

- La liste « Côtés et adjacences » est dans `StudyPanel.tsx` (`StudyRoomPanel`), alimentée par
  `room.fiche.cotes`. Chaque ligne est un `<article>` inerte ; elle contient aussi la liste des éléments
  d'enveloppe du côté (`EnvelopeItems`).
- Le plan dessine ces mêmes côtés dans `StudyMetrics.tsx` (composant `Cote`) à partir de `trace_pdf`.
  La couche des métrés est traversante (`pointer-events: none`, D79) : tout clic est routé par
  `onPick` dans `WorkspacePage.tsx`, qui cherche d'abord un pont, puis un élément d'enveloppe
  (`viserSurLePlan`), puis un local (`roomAt`).
- `TileSheetViewer` sait déjà amener le plan sur un point (`focus`, livré en F2 pour les ponts).
- **Mesuré sur le vrai R+1** (`banc.db`) : 24 locaux, **222 côtés, tous avec un tracé** ; le milieu du
  tracé est **sur le contour** du local (écart médian 0,00 pt, maximum 0,89 pt). Un côté se confond donc
  avec le trait du contour, et le mur qui le porte est au-delà, hors du local (le contour est le nu
  intérieur).

## Décisions

**D145 — Un côté désigné est un état partagé entre la fiche et le plan.** Il est tenu par
`WorkspacePage` : le local, le rang du côté dans `fiche.cotes`, et une empreinte (longueur + premier
point du tracé). Si le niveau est recalculé et que le côté à ce rang n'a plus la même empreinte, la
désignation tombe d'elle-même : mieux vaut ne rien surligner que surligner un autre côté.

**D146 — Dans la fiche, l'en-tête de chaque côté devient un bouton.** Un clic désigne le côté, un second
clic sur le même le relâche. La liste des éléments d'enveloppe reste hors du bouton (une liste dans un
bouton n'est pas du HTML valide). Un côté sans tracé reste affiché mais son bouton est désactivé et dit
pourquoi.

**D147 — Sur le plan, le côté désigné ressort et passe au-dessus des autres cotes.** Halo blanc, trait
épais, étiquette toujours affichée même quand le côté est court. Il est dessiné **après** toutes les cotes
— l'erreur déjà commise sur les éléments (dessiné avant, il disparaissait dessous) — mais **avant** les
pastilles de ponts, qui doivent rester lisibles.

**D148 — Le plan vient au côté.** Il se centre sur le milieu du tracé et zoome au moins à ×3 du plein
cadre, sans jamais dézoomer si l'on est déjà plus près.

**D149 — Réciproque : cliquer un côté sur le plan le désigne dans la fiche.** Un clic **à l'intérieur du
local ouvert**, à moins de 8 px d'un de ses côtés, désigne ce côté ; la fiche le surligne et le fait
défiler jusqu'à lui. Ordre de priorité du clic : **pont**, puis **côté** (dedans), puis **élément
d'enveloppe** (dehors, puisque le mur est au-delà du nu intérieur), puis **local**. Cliquer ailleurs dans
le local relâche le côté.

**D150 — Un côté et un élément ne sont jamais désignés ensemble.** Désigner un élément masque la fiche du
local (choix F4) : on relâche donc l'un quand on désigne l'autre. À l'étape « ponts thermiques », la fiche
n'est pas affichée : le clic sur un côté n'y est pas actif.

**D151 — Rien ne change dans le calcul.** Aucun appel serveur, aucun champ nouveau. Sur le R+1, 227
éléments, 222 côtés, 170,12 m déperditifs, 289 formes et 77 liaisons doivent rester identiques.

## Question tranchée au passage (sujet 4)

**Q7 — Valider un local exige-t-il que ses côtés et ses ponts aient été jugés ?** Réponse de
l'utilisateur, 2026-09-28 : **« NON : Uniquement côtes »** — les ponts ne conditionnent pas la validation
d'un local ; seuls ses côtés la conditionnent. Pas codé dans ce lot : aujourd'hui un côté n'a pas d'état
« jugé » propre (ce sont les éléments d'enveloppe qui en portent un). Le sens exact de « côtés jugés »
reste à préciser avant de coder — voir la fin de ce fichier.

## Résultat — 2026-09-28

- **Fiche → plan.** L'en-tête de chaque côté est un bouton : un clic surligne le côté sur le plan (halo
  blanc, trait bleu, étiquette forcée), l'amène au centre et zoome au moins à ×3 ; un second clic le
  relâche. La liste des éléments du côté reste en dessous, hors du bouton.
- **Plan → fiche.** Un clic à l'intérieur du local ouvert, près d'un côté, le désigne ; la ligne de la fiche
  s'encadre et défile jusqu'à la vue. Le plan ne bouge pas dans ce sens.
- **Mesuré sur le vrai R+1** (simulation du clic à 1,5 pt à l'intérieur du milieu de chaque tracé) :
  **207 côtés sur 222** sont désignés exactement. Les 15 autres sont tous courts (**1,84 m au plus**, la
  plupart sous 1 m), logés dans des redents où deux tracés se touchent presque (palier ascenseur,
  sanitaires, salle de pause) : le clic attrape le voisin ou rien. Ils restent désignables **depuis la
  fiche**, qui fonctionne pour les 222.
- Fichiers : `workspace/cotes.ts` (nouveau : côté visé, empreinte, prise au clic, milieu),
  `StudyMetrics.tsx`, `StudyPanel.tsx`, `WorkspacePage.tsx`, `elements.ts` (distance au segment
  exportée), `thermique.css`.
- Tests : 13 nouveaux (`cotes.test.tsx`), **108 tests frontend thermiques** au vert, typecheck et build de
  production réussis.
- **Aucun code serveur touché** : le métré du R+1 (227 éléments, 222 côtés, 170,12 m déperditifs,
  289 formes, 77 liaisons) est inchangé par construction.
- Aucune recette authentifiée à la souris : aucun identifiant n'a été demandé, affiché ni saisi.

## Q7 — Valider un local : tranchée et codée le 2026-09-28

Deux lectures étaient possibles ; l'utilisateur a choisi **(a) : tous les murs et menuiseries du local
sont tranchés (confirmés, corrigés ou écartés)**, plutôt qu'une coche « vu » par côté.

**Constat en codant — un défaut en production.** Depuis D139 (lot Codex), un recadrage se *conserve*
localement et l'enregistrement du lot se fait avec `valider: false` : **plus aucun geste ne validait un
local**. L'étape « Locaux » du parcours ne pouvait donc plus jamais passer à « fait ».

**D152 — La validation devient un geste à part.** Bouton « Valider ce local » sur la fiche, route
`POST /sheets/{id}/etude/locaux/{local_id}/valider` : pas de recalcul, le contenu n'est pas touché, une
version est créée (motif `validation_local`), puis la fiche enchaîne sur le premier local encore à valider
(D63).

**D153 — La règle est tenue par le serveur**, qui refuse (409) en disant combien de murs ou menuiseries
restent. L'écran applique la même règle pour griser le bouton et l'expliquer. Les **ponts ne comptent
pas** (Q7). Un élément que l'agent **n'a pas mis en doute est tenu pour acquis**, comme à l'étape
« parois et menuiseries » (D114) : seuls les éléments « à vérifier » doivent être tranchés. *Hypothèse
prise pour rester cohérent avec D114 ; l'exiger pour tous les éléments tient en une ligne
(`a_verifier` à retirer du filtre, serveur et écran).*

**D154 — Un travail en attente passe avant.** Contour en cours, corrections d'éléments ou modifications
de locaux non enregistrées : le bouton est grisé et dit quoi faire, car le serveur ne les connaît pas
encore.

**Mesuré sur le vrai R+1** : **11 locaux sur 24** sont validables tout de suite ; les 13 autres
totalisent **63** murs ou menuiseries à trancher, dont 28 dans le Pôle multimédia (64 à l'échelle du
niveau, un n'étant rattaché à aucun local). Tests : 6 backend (`test_thermique_etude_edition.py`, 31 au
vert), 7 frontend (`validation.test.tsx`, 115 tests thermiques au vert), typecheck et build.
