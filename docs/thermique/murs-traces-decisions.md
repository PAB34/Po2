# Murs tracés librement, suppression immédiate, départ à zéro du R+1 (D248 à D253)

Date : 2026-10-02. Objectif 1 de la boussole (R+1 parfait). Remplace le lot B de
`mur-ligne-de-metre-decisions.md` (D245 à D247), dont les questions sont absorbées ici.

## Ce que veut le thermicien (2026-10-02)

1. Cliquer une ligne de mur → ses **deux extrémités** apparaissent ; les **étirer, raccourcir, déplacer
   librement**, sans rester dans le sens de la ligne d'origine.
2. « Supprimer ce mur » → le mur **disparaît aussitôt du plan**, sans « Enregistrer les corrections » ; la
   suppression est aujourd'hui **trop longue**.
3. **Clic droit → « Créer un mur »** : tracer une ligne libre.
4. **Reprendre la planche du R+1 à zéro**, en gardant tout le travail fait jusqu'ici, en sauvegarde réutilisable.
5. Un point complet sur la détection : `detection-composants-bilan-2026-10-02.md`.

## Existant vérifié

- Un mur est aujourd'hui un **morceau du relevé de la façade** : un tronçon (le guide calculé sur l'image), une
  abscisse de début et de fin le long de ce tronçon, et des nus mesurés perpendiculairement. Sa ligne de métré
  (D242) est **calculée par le serveur** à partir de ces nombres. Il ne peut donc pas sortir de la direction de
  son tronçon : c'est ce qui bloque la demande 1.
- **Pourquoi la suppression est lente et ne se voit pas** : le geste est gardé dans l'écran
  (`useStudyElements`) ; la ligne de métré, elle, n'existe qu'après un **recalcul complet du niveau** par le
  serveur (relevé → réunion des morceaux → exposition → pièces → ponts → fiches → reprojection), déclenché par
  « Recalculer » ou « Enregistrer ». Plusieurs secondes sur le R+1, pour un seul mur.
- Une seule étude par planche ; ses versions gardent les pièces et le relevé ; on peut revenir à une version
  (`restaurer`). Planche, échelle, calage, nord, vues de coupe et modèles de menuiserie sont rangés **hors** de
  l'étude.

## Décisions proposées

- **D248 — Un mur devient un objet tracé.** Un mur = une **ligne de métré libre** (face intérieure) : deux points
  ou plus sur le plan, en coordonnées du PDF, plus sa composition, son côté extérieur et sa provenance (tracé,
  repris du relevé de l'IA, reporté d'un autre niveau). Il n'est plus attaché à un tronçon de façade. Sa
  longueur est celle de la ligne. Le relevé de l'IA n'est plus la source des murs.
- **D249 — Poignées.** Mur désigné : un rond à chaque extrémité. On le **glisse où l'on veut** ; **aimant** sur
  les extrémités et lignes des autres murs, pour fermer les angles ; **Maj** maintenue = sans aimant. Longueur
  affichée pendant le glissement. Un clic droit sur la ligne **ajoute un sommet** : le mur à plusieurs pans
  (D247) se fait ainsi.
- **D250 — Créer un mur.** Clic droit sur le plan → « Créer un mur » → un clic par sommet, double-clic ou
  Entrée pour finir, Échap pour annuler. Le mur prend la **dernière composition validée**, à changer dans la
  fiche.
- **D251 — Côté extérieur.** Les couches se posent du côté opposé au local chauffé le plus proche ; bouton
  « Inverser le côté » dans la fiche. Le dessin montre l'épaisseur en ombre légère de ce côté.
- **D252 — Gestes enregistrés aussitôt.** Créer, déplacer, supprimer un mur ou valider sa composition :
  **visible à l'instant** à l'écran, **enregistré en arrière-plan** par une petite requête qui ne recalcule pas
  tout le niveau. Plus de bouton « Enregistrer » pour les murs ; Ctrl+Z annule. Le calcul complet (surfaces,
  ponts) se fait plus tard, à la demande.
- **D253 — Repartir de zéro.** Bouton « Repartir de zéro » sur le niveau, avec confirmation. (1) L'étude actuelle
  est **sauvegardée en entier** sous un nom daté (« R+1 relevé IA — 2026-10-02 »), rangée dans le projet et
  téléchargeable en JSON. (2) Le niveau repart **vide**. (3) Restent : planche, échelle, calage, nord, vues de
  coupe, modèles de menuiserie et bibliothèque. (4) Plus tard, depuis la liste des sauvegardes : « Reprendre ses
  locaux », « Afficher ses murs en calque de suggestions » ou « Tout restaurer ».

## Ce que cela change ailleurs (à traiter dans le même lot ou noté)

- **Découpage pièce par pièce (D18 à D20) : on le garde.** Il coupe aujourd'hui les intervalles d'un tronçon. Il
  s'appliquera à la **ligne du mur tracé**, avec la même règle : sondage à 30 cm à l'intérieur de la ligne ;
  coupe là où la pièce derrière change ; recalage sur l'about de cloison à moins de 30 cm. Un mur tracé d'un
  seul trait sur trois bureaux donne donc trois morceaux, un par bureau, sans que vous le coupiez. Cela suppose
  que les **locaux** existent avant les murs : c'est l'enjeu de la question 1.
- **Menuiseries** : elles restent posées comme aujourd'hui. Leur surface sera retirée du mur qu'elles
  coupent au moment du calcul (objectif 5).
- **Ponts thermiques** : les angles se déduiront des rencontres entre murs tracés. Lot à part, après les murs.
- **Ancien relevé** : la fusion à 6 cm, le pinceau, le retracé et le découpage par tronçon ne servent plus aux
  murs → nettoyage, objectif 2b.

## Ordre proposé

1. **Lot C1** : sauvegarde complète et « Repartir de zéro » (D253).
2. **Lot C2** : murs tracés (D248, D250), poignées (D249), enregistrement immédiat et suppression instantanée
   (D252).
3. **Lot C3** : côté extérieur (D251) et rattachement aux locaux. Votre recette à la souris suit chaque lot.

## Questions

1. **Que garde le niveau quand on repart de zéro ?** a) tout vide, locaux compris (vous retracez tout) ; b) les
   **locaux** restent (contours, noms, hauteurs), seuls murs, menuiseries et ponts repartent de zéro ; c) autre.
2. **Les murs de l'IA après le départ à zéro** : a) disparus (vous tracez tout) ; b) affichés en **calque de
   suggestions** grisé, un clic pour en accepter un et l'éditer.
3. **Aimant** : sur les extrémités et lignes des autres murs, **Maj** pour le couper. Ça vous va ?
4. **Murs intérieurs** (refends, cloisons sur local non chauffé) : traçables aussi dès ce lot, avec un type
   « extérieur / sur local non chauffé / intérieur » ? Ou l'enveloppe seulement pour commencer ?
5. **Couches non parallèles** (ancienne question) : une épaisseur au début et une à la fin de chaque couche
   vous suffit-elle ?
