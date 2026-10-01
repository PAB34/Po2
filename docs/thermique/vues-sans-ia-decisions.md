# Coupes et élévations sans lecture IA ; menuiseries mesurées visibles (D230 à D232)

Date : 2026-10-01. Suite de `etapes-parois-menuiseries-decisions.md` (D227–D229).

## Constat du thermicien

« Le travail de l'agent sur les planches de coupes et d'élévations ne sert à rien en l'état, et son rendu est
absent après avoir chargé les JSON. » Les hauteurs se mesurent désormais à la main (D211, D215) et les
menuiseries par modèles (D219) : la lecture des pièces et des niveaux d'une coupe par l'IA n'a plus d'usage, et
ses cadres de vues étaient faux (D205). Il veut aussi **voir sur l'élévation les menuiseries déjà mesurées**
pour savoir où il en est.

## Existant vérifié

- `thermique_travaux._lectures_de_coupes` : « Analyser » met en file la lecture des planches de coupes et de
  façades (COUPES), la relecture des vues (VUES) et les traits de coupe des plans (TRAITS).
- `thermique_lecture_coupes` : vues enregistrées par import d'une lecture ; corrigées par `corriger_vue`.
- Les modèles mesurés gardent leurs deux coins dans `lecture_json["menuiseries"]` de la vue (D219).

## Décisions

- **D230 — Plus de lecture IA des coupes et élévations.** « Analyser » ne met plus en file ni les planches de
  coupes et de façades, ni les traits de coupe des plans (inutiles depuis D216). « Faire lire par l'IA » est
  retiré de l'écran. L'import manuel d'une lecture reste possible (D204) ; les vues déjà là restent.
- **D231 — Une vue se crée à la main.** Sur une planche de coupes ou d'élévations : « Ajouter une vue », deux
  clics pour le cadre, puis nom, nature (coupe / élévation) et haut du dessin tel qu'on le voit. Elle est
  aussitôt utilisable dans la fenêtre « Coupes et élévations ». Le parcours de la planche : Planche à l'échelle,
  puis **Vues** (« N vues cadrées »).
- **D232 — Les menuiseries mesurées se voient.** Dans la fenêtre « Coupes et élévations » et sur la planche,
  chaque modèle mesuré est dessiné à sa place (rectangle de ses deux coins) avec son nom ; la liste des vues
  dit combien de modèles chaque vue porte.
