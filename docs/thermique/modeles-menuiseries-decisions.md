# Modèles de menuiserie mesurés et posés sur le plan (D218 à D222)

Date : 2026-10-01. Suite de `coupes-elevations-fenetre-decisions.md` (D213–D217), après le test du R+1.

## Constats du test (2026-10-01)

1. Poser une hauteur : il manque « appliquer à **tous** les locaux du niveau ».
2. Mesure d'une menuiserie : la recherche « baie du projet à ± 5 cm » échoue souvent. Cause : deux
   menuiseries accolées de même composant, sans rien entre elles, sont **réunies en une baie** (D199) dont la
   largeur est la somme ; un morceau mal relevé donne aussi une largeur fausse.
3. Le **nom de composant lu par l'IA n'est pas fiable** : un même « M1 » couvre des largeurs très
   différentes. « Pour toutes les M1 » appliquerait une hauteur à des menuiseries d'un autre modèle.
4. Le thermicien veut une **capture** de chaque modèle mesuré, pour qu'un agent relève plus tard cadre et
   vitrage, et une **bibliothèque des modèles** du projet.
5. Le trait de la menuiserie sur le plan doit **hériter** du modèle réellement mesuré : sa cote de largeur
   affichée devient celle du modèle.

## Existant vérifié

- `thermique_menuiseries.py` : baies = éléments contigus de même composant ; hauteur par composant ou par
  baie (confirmations gardées dans `lecture_json["menuiseries"]` de la vue) ; `proposer` à ± 5 cm.
- `thermique_elements.py` : corrections d'éléments (`element_corriger`), enregistrées par `saveStudy`, qui
  recalcule l'étude.
- Le plan ne montre aujourd'hui aucune cote de menuiserie : seulement le trait (`StudyMetrics`).
- Rendu PDF : pypdfium2 sous `VERROU_PDFIUM`, fichiers du projet sous `thermique_storage_dir/projet_<id>/`.

## Décisions

- **D218 — Hauteur à tout le niveau.** Le bandeau de pose propose aussi « Appliquer à tous les locaux du
  niveau » (remplace les hauteurs déjà données, après confirmation).
- **D219 — Le modèle de menuiserie, unité mesurée.** Deux coins sur une coupe ou une élévation donnent
  largeur et hauteur ; le thermicien nomme le **modèle** (proposé : composant le plus proche + dimensions,
  ex. « M1 120×215 ») ou reprend un modèle existant (une nouvelle mesure du même nom le remplace). Le modèle
  est gardé avec la vue (`lecture_json["menuiseries"]`, champ `modele`) avec ses coins et sa capture.
  On mesure **la baie entière, d'un tableau à l'autre**, cadre compris.
- **D220 — Le modèle se pose en cliquant les menuiseries du plan.** Comme pour les hauteurs : la
  menuiserie désignée reçoit le modèle tout de suite, puis chaque menuiserie cliquée ; un raccourci
  « Appliquer aux menuiseries de même largeur (± 2 cm) » sur le niveau. Le modèle s'écrit sur l'élément du
  relevé (champ corrigeable `modele`) : le nom de composant de l'IA ne décide plus de rien. Deux éléments de
  modèles différents ne sont plus réunis en une baie.
- **D221 — Le trait hérite du modèle.** Une baie posée prend la largeur et la hauteur du modèle
  (`largeur_retenue_cm`, `surface_m2`) ; sur le plan, à l'étape des parois et menuiseries, chaque menuiserie
  porte sa cote : « modèle · L × H » si posée, sinon la largeur relevée. Un écart de plus de 5 cm entre le
  plan et le modèle est signalé (baie double, morceau).
- **D222 — Capture et bibliothèque des modèles.** À l'enregistrement, le serveur découpe la vue autour des
  deux coins (marge de 30 %) en PNG (`projet_<id>/modeles/`). La bibliothèque du projet liste chaque modèle :
  vignette, nom, L × H, vue de mesure, nombre de menuiseries posées. La relecture du cadre et du vitrage par
  un agent viendra plus tard.

## Reporté

- Couper une baie réunie à tort en deux menuiseries (proposé le 2026-10-01, non retenu dans ce lot).
- Relevé du cadre et du vitrage par un agent sur les captures.
