# Deux étapes : Parois, puis Menuiseries (D227 à D229)

Date : 2026-10-01. Suite de `menuiseries-reunies-exposition-decisions.md` (D223–D226).

## Constat

À l'étape « Parois et menuiseries », le trait du mur, celui de la menuiserie et le contour de la pièce se
superposent : viser une menuiserie pour lui poser son modèle est pénible. La fiche d'une menuiserie montre
aussi des gestes qui ne servent plus (« Affecter aussi à… », lecture de l'IA, corrections) et brouillent la
lecture.

## Existant vérifié

- `parcours.ts` : étape `enveloppe` « Parois et menuiseries », `vueDeLEtape` règle familles dessinées, clic,
  liste des éléments ; `StudyMetrics` épaissit les menuiseries à cette étape (`accentMenuiseries`).
- `ElementPanel.tsx` : fiche d'un élément (lecture de l'agent, écarts, exposition, modèle, baie, affectation,
  confirmer, corriger, écarter).

## Décisions

- **D227 — Six étapes.** Planche, Analyse, Locaux et hauteur, **Parois**, **Menuiseries**, Ponts.
  - Parois : seuls les murs (et poteaux, garde-corps) sont épais et attrapables ; les menuiseries sont
    estompées. Compteur : parois à vérifier.
  - Menuiseries : seules les menuiseries sont dessinées, très épaisses, avec leur cote ; murs et contours des
    pièces très estompés ; un clic n'attrape qu'une menuiserie. Compteur : menuiseries sans modèle (hors
    murs-rideaux, dont la hauteur est celle du local). « Coupes et élévations » et la bibliothèque des modèles
    y sont.
- **D228 — Fiche d'une menuiserie allégée.** En tête : type, exposition, modèle mesuré, baie retenue, mesure.
  Lecture de l'IA, écarts, correction et « Écarter » passent dans un bloc replié « Corriger le relevé ».
- **D229 — « Affecter aussi à… » retiré de l'écran.** Le champ `pieces_en_plus` reste lu par le serveur (D217) ;
  plus rien ne l'écrit depuis l'écran.
