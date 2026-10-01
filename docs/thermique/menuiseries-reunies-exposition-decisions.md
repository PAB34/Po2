# Menuiseries réunies sur le plan et exposition au nord (D223 à D225)

Date : 2026-10-01. Suite de `modeles-menuiseries-decisions.md` (D218–D222).

## Constat

Sur le plan, des menuiseries apparaissent en plusieurs morceaux : la fusion d'office de D174 n'a été
appliquée qu'au calcul des baies (D199), le relevé gardant ses morceaux. Poser un modèle demande alors un
clic par morceau, et chaque morceau porte sa cote. Le thermicien veut aussi l'**exposition** de chaque
menuiserie, qui suive le nord quand on le change.

## Existant vérifié

- `thermique_menuiseries.baies_du_releve` : réunion des morceaux contigus (± 2 cm), au calcul seulement.
- `thermique_etude_edition.reconstruire` : appelé à chaque correction et à chaque pose du nord
  (`_rafraichir_orientations`) ; il relit le relevé brut.
- Tronçons du manifeste : `normale_ext` (repère image) ; `fiches_locaux.orientation(normale, nord_deg)` donne
  déjà l'orientation des côtés des locaux, en 8 secteurs.

## Décisions

- **D223 — Réunion physique dans le relevé.** À chaque recalcul, sur un même tronçon, deux menuiseries
  actives **de même composant et de même modèle**, séparées de **6 cm au plus** (réponse du 2026-10-01), sans
  autre élément entre elles qu'un « indéterminé », deviennent **une seule menuiserie** : bornes réunies, nus de
  fin repris du second morceau. L'indéterminé absorbé est écarté avec un motif. Les corrections sont gardées
  (confirmé si les deux l'étaient, corrigé si l'un l'était, modèle, pièces partagées) et les morceaux
  d'origine sont notés dans `morceaux_reunis`. Des composants différents ne sont jamais réunis d'office.
- **D224 — À la jonction de deux tronçons**, le relevé ne peut porter un seul élément : l'écran traite les
  morceaux d'une même baie comme un tout (une cote, un clic pose le modèle sur tous).
- **D225 — Exposition.** Chaque menuiserie porte son exposition, normale sortante de son mur par rapport au
  nord, en 8 secteurs (N, NE, E, SE, S, SO, O, NO) et en degrés. Le serveur l'écrit dans le relevé à chaque
  recalcul (`exposition`, `azimut_deg`), donc aussi quand le nord change ; l'écran la calcule en direct depuis
  la flèche du nord. Secteur sur la cote du plan, angle exact dans la fiche. Sans nord : « nord à caler ».
