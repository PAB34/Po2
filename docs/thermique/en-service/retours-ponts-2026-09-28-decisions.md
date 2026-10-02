# Second retour d'usage sur les ponts thermiques — décisions et questions

Date : 2026-09-28, après la mise en production de `5f133139`. Six remarques de l'utilisateur (P1 à P6).
Répondez sous chaque question par une ligne `REPONSE : …`.

---

## P1 — Voir le croquis du pont type, en grand, au moment de réattribuer

> « j'aurais aimé avoir la picture du pont thermique et de manière assez zoomée pour choisir le pont
> thermique en pouvant bien visualiser la constitution des éléments »

**Existant.** « Réattribuer… » propose une liste de codes (C1, IW3…) avec leur description et leurs ψ,
et renvoie à la page du PDF de la norme. Aucune image. À l'étape des ponts, le plan se centre sur le pont
en cours, zoomé ×5.

**Piste.** À côté de la liste, une grande vignette du pont type choisi (mur, isolant, dalle, dormant), qui
change quand on parcourt la liste ; et, au-dessus, une **vignette zoomée du plan** à l'endroit du pont, pour
comparer les deux côte à côte.

**Q19 — D'où viennent les croquis ?**
- (a) **Les croquis de la norme eux-mêmes**, découpés dans votre PDF de la NF EN ISO 14683. Fidèles, mais
  c'est une reproduction du document CSTB sous licence nominative : à réserver à votre bureau d'études.
- (b) **Nos propres schémas**, dessinés par l'outil pour chaque pont type (même lecture : mur, isolant à
  l'extérieur / au centre / à l'intérieur / mur léger, dalle, dormant), sans rien reprendre du document.
  Utilisables par tous les bureaux d'études.
- (c) Les deux : nos schémas partout, le croquis de la norme en plus pour votre bureau.

**Q20 — La vignette zoomée du plan dans le panneau vous est-elle utile**, en plus du plan lui-même ?
(a) oui (b) non, le zoom du plan suffit s'il est plus fort.

## P2 — À l'étape des ponts, cliquer un local pour ne voir que ses ponts

> « si je clique sur un local je ne vois que les ponts thermiques associés à ce local, mais j'aimerais les
> voir pour être sûr que le pont thermique est bien le bon associé au local »

**Existant.** À l'étape des ponts, le clic ne vise que les ponts (D156) ; un clic ailleurs ne fait rien.
Chaque pont n'est rattaché qu'à **un** local sur le plan, même un about partagé à 50/50.

**Piste.** Clic dans un local → le local est surligné, **seuls ses ponts restent sur le plan** (ceux
partagés avec un voisin compris, marqués « ½ »), et le panneau affiche « Ponts de « Bureau » : 4 » avec
leur liste. Clic hors de tout local → retour au niveau entier.

**Q21 — Et la passe ?**
- (a) Elle se limite au local ouvert : « Pont 2 sur 4 », puis on passe au local suivant.
- (b) Elle reste sur tout le niveau ; le local ouvert ne filtre que le plan et la liste.

## P3 — Un pont entre deux pièces compte-t-il 0,5 ou 1 ?

**Mesuré sur le R+1 aujourd'hui.**
- Abouts de refend : **9 sur 13 sont bien partagés 0,5 + 0,5** entre les deux pièces qu'ils séparent ; les
  4 autres ont la même pièce des deux côtés. Le total du niveau reste juste : 13.
- Angles sortants et rentrants : **les 64 comptent 1 dans une seule pièce**, celle qui est derrière le
  milieu de l'angle. Le partage des angles est le **sujet 3** de `reprise-sujets-ouverts.md`, demandé et
  **pas encore fait**.
- Un pont posé à la main compte 1 dans la pièce qui contient son point.

**Décision proposée — D163.** Un angle qui tombe à la jonction de deux pièces (une cloison qui arrive dans
le coin) est partagé 0,5 + 0,5, détecté en sondant de part et d'autre du coin. Le total du niveau ne change
pas ; seule la répartition entre pièces bouge.

**Q22 — En plus de la détection, voulez-vous pouvoir choisir à la main les pièces qui se partagent un
pont** (« partagé avec… » dans sa fiche) ? (a) oui (b) non, la détection suffit.

## P4 — Au clic droit, les ponts les plus courants du plan d'abord

> « par défaut s'affichent les ponts thermiques les plus courants du plan et avoir la possibilité d'en
> choisir dans la liste complète »

**Existant.** Le clic droit propose les trois types (angle sortant, rentrant, about) ; le pont type se donne
ensuite avec « Réattribuer… ».

**Piste.** Le menu propose les **ponts types les plus employés sur ce niveau** (« C1 — angle sortant, isolant
à l'extérieur · 18 sur ce niveau »), puis « Autre pont type… », qui ouvre la liste complète du catalogue
dans le panneau. Tant qu'aucun pont type n'est posé sur le niveau, on retombe sur les trois types.

**Q23 — Combien de ponts par défaut, et comptés où ?** (a) les 5 plus employés sur ce niveau (b) les 5 plus
employés sur tout le projet (c) autre.

## P5 — L'ajout d'un pont est long : est-ce le même problème qu'avant ?

**Oui, c'est la même cause.** L'ajout demande au serveur de recalculer tout le niveau pour savoir sur quel
tronçon tombe le pont, soit quelques secondes à chaque pont. Le problème des recadrages avait été réglé
en faisant les gestes dans l'écran et en ne recalculant qu'à l'enregistrement.

**Décision proposée — D164.** L'écran calcule lui-même le tronçon le plus proche (même règle que le
serveur), pose le pont **instantanément**, et le serveur se contente de vérifier cette position à
l'enregistrement. Plus d'attente à l'ajout ; un seul recalcul, quand vous enregistrez.

## P6 — Les ponts linéiques horizontaux ne se voient pas à l'étape des ponts

**C'est normal à ce stade, et c'est prévu.** Les liaisons contre une terrasse (12,89 m au R+1) sont
calculées mais n'apparaissent que dans la fiche de la pièce : les juger dans la passe des ponts est la
**seconde partie de F**, pas encore faite. La liaison des planchers intermédiaires avec la façade (famille IF)
n'est, elle, pas encore représentée du tout.

**Décision proposée — D165.** À l'étape des ponts, chaque liaison linéique se **dessine comme un trait de
couleur le long du côté** concerné, s'attrape au clic et passe dans la passe avec les mêmes gestes
(garder, écarter, réattribuer à un pont type B ou IF), avec sa longueur.

**Q24 — La liaison plancher intermédiaire / façade (IF) doit-elle aussi être créée d'office ?**
- (a) Oui : le long de tout côté de façade, sur chaque niveau qui a un plancher au-dessus ou au-dessous.
- (b) Non : seulement les terrasses et balcons pour l'instant.

---

## Réponses de l'utilisateur (2026-09-28) et décisions

| Question | Réponse |
|---|---|
| Q19 — croquis | **a** : les croquis de la norme, découpés dans le PDF — réservés à son bureau d'études |
| Q20 — vignette du plan | **a** : oui |
| Q21 — passe et local ouvert | **b** : la passe reste sur tout le niveau ; le local ouvert filtre le plan et la liste |
| Q22 — partage à la main | **a** : oui, « partagé avec… » dans la fiche du pont |
| Q23 — ponts par défaut au clic droit | **a** : les 5 plus employés sur ce niveau |
| D163, D164, D165, ordre | validés (« pour le reste ok pour tes recommandations ») |

**Q24 — réponse de l'utilisateur, verbatim :** « Je réalise que c'est un point très stratégique en
réalité. Parce que cela suppose au niveau de la lecture de voir à quel type de liaison nous avons à faire.
Donc pouvoir voir en transparence depuis la vue en plan active si possible le niveau du dessus/dessous. Et
aussi au niveau de plan des élévations et des coupes. Sujet hautement important et maintenant devient
urgent à traiter. »

**D166 — La liaison plancher / façade n'est pas créée d'office tant qu'on ne sait pas la lire.** Elle
dépend de ce qu'il y a au-dessus et au-dessous du plancher (niveau chauffé, terrasse, vide sanitaire, porte
à faux…). Nouveau chantier prioritaire, cadré à part : **superposer en transparence le niveau du dessus ou
du dessous sur le plan actif**, puis exploiter **élévations et coupes**. Fichier de cadrage :
`superposition-niveaux-decisions.md`.

**Q19 a — rappel de licence.** Les croquis découpés restent une reproduction du document CSTB : ils seront
servis depuis les fichiers du projet, à l'usage du bureau d'études titulaire de la licence.

---

## Résultat — P5, ajout instantané (2026-09-28)

- L'écran situe lui-même le pont (`pontsAjoutes.ts`) : passage PDF → feuille **déduit des contours des
  locaux**, qui portent les deux repères (aucune dépendance à la rotation d'affichage), puis la même règle
  de projection que le serveur. Le pont apparaît **aussitôt**, désigné, dans son local ; il s'annule et se
  rétablit sans aucun recalcul. Le serveur ne recalcule qu'à l'enregistrement.
- Le geste porte `troncon` et `abscisse_m` : le serveur les **vérifie** (tronçon existant, abscisse dans le
  tronçon, place libre) et les **reprend tels quels** — l'identité vue par l'écran est donc celle que ses
  gestes suivants visent.
- **Mesuré sur le vrai R+1** : 475 points (milieux de tous les côtés de tous les locaux) situés par l'écran
  et par le serveur — **474 identiques**, le dernier à 1 mm près (arrondi à la limite). D'où le choix de
  faire reprendre la position de l'écran plutôt que de la recalculer.
- Au passage : un pont réattribué garde sa position sur le plan avant recalcul.
- Tests : 2 backend (42 au vert), 4 frontend (**142** au vert), typecheck, build.

## Ce qui était déjà prévu, et ce qui est nouveau

| Remarque | Statut |
|---|---|
| P3 — 50/50 des angles | prévu (sujet 3), pas fait |
| P6 — liaisons horizontales | prévu (F, seconde partie), pas fait |
| P5 — ajout instantané | nouveau, conséquence de mon choix de C |
| P1, P2, P4 | nouveaux |

## Ordre de travail proposé

1. **P5** (ajout instantané) : il gêne dès maintenant.
2. **P2** (ne voir que les ponts d'un local) et **P3** (50/50 des angles) : ils vont ensemble, un pont
   partagé doit apparaître dans les deux locaux.
3. **P6** (liaisons horizontales dans la passe).
4. **P4** (ponts les plus courants au clic droit).
5. **P1** (croquis), selon Q19.
