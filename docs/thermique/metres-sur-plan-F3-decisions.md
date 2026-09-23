---
read_policy: lire avant de coder les métrés et ponts thermiques dessinés sur le plan (lot F3)
status: livre
---

# Métrés et ponts thermiques sur le plan — décisions du lot F3

Date : 2026-09-23. Demande de l'utilisateur, formulée après son premier usage réel : « j'aimerais que
lorsque je clique sur une pièce tous les métrés apparaissent sur la pièce ainsi que les ponts thermiques ».

Cadre déjà validé : **D73** (ce qu'on dessine), **D74** (ponts localisés), **D75** (tracé des éléments).
Ce document ne les rediscute pas ; il vérifie ce qui existe et pose les questions restées ouvertes.

Questions tranchées par l'utilisateur le 2026-09-23 (§ 6). **Lot livré**, vérifié au § 7.

## 1. Pourquoi ce lot maintenant

Deux défauts ont traversé la chaîne aujourd'hui sans que rien ne les voie, et c'est l'utilisateur qui les a
repérés en regardant le plan. Le contrôle de cohérence (D77) en attrape désormais une partie, mais il ne
remplace pas l'œil : **tant que les métrés ne se lisent pas sur le plan, le thermicien ne peut pas arbitrer.**
C'est la raison de passer F3 devant F0 et F2.

## 2. Existant vérifié le 2026-09-23 (fichier `etude-R1.v3.json`, 24 locaux)

### Ce qui est déjà là et dessinable

| Donnée | Où | Contenu |
|---|---|---|
| Contour du local | `locaux[].contour_pdf` | déjà dessiné par `StudyOverlay` |
| Nature des côtés | `locaux[].limites[]` | `exterieur` / `paroi` / `convention`, déjà dessinée en couleur |
| Tracé des éléments | `enveloppe.objets[]` | **289 objets**, `points_pdf`, `category`, `subtype`, `confidence`, `review_required`, et `source_parcours.piece` pour filtrer par local |
| Ponts thermiques | `enveloppe.liaisons[]` | **77 liaisons**, `type`, `point_pdf`, `piece`, `composant`, `longueur_m` |
| Surface du local | `locaux[].surface_m2` | déjà affichée dans la fiche |

Les catégories d'éléments présentes sur le R+1 : `mur_exterieur`, `isolation`, `doublage`,
`menuiserie_exterieure`, `poteau`, `garde_corps`, `indetermine`. Les trois types de liaisons :
`angle_sortant`, `angle_rentrant`, `about_refend`.

### Ce qui manque, et c'est le seul vrai trou

**Les côtés de la fiche n'ont aucune position.** Un côté porte aujourd'hui :

```json
{"adjacence": "exterieur", "voisin": "extérieur", "longueur_m": 14.05, "epaisseur_cm": 47,
 "orientation": "nord à caler", "deperditif": true, "enveloppe": [{"composant": "P1", "lineaire_m": 8.06}, …]}
```

… mais pas un seul point. Et l'interface ne peut pas les recalculer : un côté n'est pas une arête du contour,
c'est un **regroupement de sondages contigus de même adjacence** (`thermique_fiches_locaux._regrouper`). Ses
limites tombent au milieu des arêtes, là où le voisin change. Sans géométrie exportée, il est impossible de
poser « 14,05 m » au bon endroit. C'est l'objet de la question Q1.

### Observation annexe

`orientation` vaut `"nord à caler"` sur tout le niveau : le nord du plan n'est jamais renseigné
(`nord_deg = None`). L'orientation des parois est une donnée de calcul thermique, pas un ornement. Hors lot,
mais à traiter (Q8).

## 3. Décisions proposées

### D80 — Chaque côté de fiche porte sa polyligne

`thermique_fiches_locaux.fiches` connaît déjà la ligne de chaque côté (`lignes_cotes`, construite depuis les
sondages). Elle est jetée à la fin. On la conserve, simplifiée au centimètre, dans `cotes[].trace` (repère
feuille 0..1000), convertie en `trace_pdf` à l'import comme les contours.

Ajout purement additif : une étude v3 déjà importée récupère ses tracés au premier **Recalculer**, sans rien
réimporter et sans qu'un contour bouge.

### D81 — Le plan montre, la fiche détaille

Sur le plan : la **mesure** (longueurs, surface, position des ponts). Dans la fiche latérale : le **détail**
(composants rattachés, épaisseurs, orientation, alertes). On ne duplique pas le tableau sur le dessin ; le
plan répond à « où » et « combien », la fiche à « quoi ».

### D82 — Les étiquettes s'effacent plutôt que de se chevaucher

Une cote ne s'affiche que si son côté mesure assez de pixels à l'écran pour être lue ; la surface ne
s'affiche que si le local est assez grand. En dessous, le trait reste, l'étiquette disparaît. Aucun
empilement d'étiquettes illisibles, jamais.

## 4. Questions à valider avant le code

**Q1 — Exporter la géométrie des côtés (D80).** Sans elle, aucune cote ne peut être posée sur le plan. Le
fichier grossit d'environ 30 à 40 Ko sur un niveau comme le R+1, et votre étude déjà importée doit passer une
fois par « Recalculer » (10-15 s, aucun contour modifié).
**Recommandation : oui.** C'est le seul moyen, et le moins intrusif.

**Q2 — Ce qui s'affiche par défaut quand vous cliquez un local.** D73 dit : cotes des côtés **déperditifs**
seulement, surface au centre, ponts en pastilles.
**Recommandation : conforme à D73**, avec un réglage « tout montrer » pour les côtés intérieurs.

**Q3 — Contenu d'une étiquette de cote.** Trois possibilités : (a) la longueur seule, `14,05 m` ; (b) longueur
+ épaisseur, `14,05 m · 47 cm` ; (c) longueur + épaisseur + orientation.
**Recommandation : (b)**, la longueur en gras et l'épaisseur en petit dessous. L'orientation reste dans la
fiche tant que le nord n'est pas défini (Q8), sinon elle afficherait « à caler » partout sur le dessin.

**Q4 — Les ponts thermiques.** Une pastille par liaison relevée, couleur par type (angle sortant, angle
rentrant, about de refend), infobulle donnant le composant et le linéaire. Sur le R+1 cela fait 3 à 5
pastilles par local.
**Recommandation : oui**, une pastille par liaison. Les regrouper masquerait justement ce qu'on veut vérifier.

**Q5 — Dessine-t-on aussi les éléments d'enveloppe dès F3 ?** Murs, isolants, doublages, menuiseries, poteaux
sont disponibles (289 tracés). Les dessiner en trait fin sous les cotes, c'est ce qui permet de juger la
détection à l'œil ; les **isoler d'un clic** reste le lot F4.
**Recommandation : oui, les dessiner dès F3**, en retrait visuel (trait fin, couleur par catégorie), avec un
réglage pour les masquer. C'est peu de travail de plus et cela rend F3 réellement utile.

**Q6 — Où se règlent ces affichages ?** Un petit menu dans la barre d'outils de la visionneuse : « Cotes
déperditives / toutes / aucune », « Ponts », « Éléments ». Le choix est mémorisé par planche.
**Recommandation : oui**, et réglages mémorisés pour ne pas les reposer à chaque local.

**Q7 — Faut-il un affichage « niveau entier » ?** Aujourd'hui tout est lié au local sélectionné. On pourrait
permettre d'afficher les ponts de **tout le niveau** d'un coup, pour repérer les oublis.
**Recommandation : oui pour les ponts seulement** (77 pastilles restent lisibles), non pour les cotes (elles
se chevaucheraient).

**Q8 — Le nord du plan.** Il n'est jamais renseigné, donc aucune orientation n'est calculée, alors que c'est
une donnée de calcul. Le poser demanderait un geste simple à l'étape 1 (comme l'échelle : cliquer la flèche
nord du plan, ou saisir un angle).
**Recommandation : hors F3**, mais à inscrire au parcours de l'étape 1 dans le lot F2. Dites-moi si vous
préférez le traiter tout de suite.

## 5. Vérification prévue

1. Sur le banc local avec le vrai R+1 : cliquer `6.1.1 B.dir + EAPMR` et retrouver ses deux côtés déperditifs
   cotés (14,05 m et le second), sa surface au centre, et ses pastilles de ponts.
2. Recouper les cotes dessinées avec la fiche latérale : mêmes longueurs, au centimètre.
3. Recouper le nombre de pastilles d'un local avec `synthese.ponts` du même local.
4. Vérifier qu'au zoom arrière les étiquettes disparaissent sans jamais se chevaucher.
5. Vérifier que le geste de déplacement du plan reste intact au-dessus des étiquettes et des pastilles (D79).
6. Tests ciblés serveur et interface, typage et construction.

## 6. Réponses de l'utilisateur du 2026-09-23

| Question | Réponse |
|---|---|
| Q1 géométrie des côtés | **oui** |
| Q2 affichage par défaut | **conforme à D73** |
| Q3 contenu de l'étiquette | **(c)** longueur + épaisseur + orientation |
| Q4 ponts | **une pastille par liaison** |
| Q5 éléments dessinés dès F3 | **oui** |
| Q6 réglages mémorisés | **oui** |
| Q7 portée de l'affichage | **libre par famille sur tout le plan ; tout s'affiche dans le local sélectionné** |
| Q8 nord du plan | **plus tard, mais important** |

### D83 — Le local sélectionné montre tout ; le reste du plan, ce qu'on coche

Réponse Q7, qui remplace ma proposition plus étroite : « une case pour choisir ponts thermiques, métrés… sur
tout le plan, mais tout doit s'afficher dans le local ».

- **Local sélectionné** : cotes, surface, ponts et éléments, toujours, sans réglage.
- **Reste du niveau** : trois cases indépendantes — *Métrés*, *Ponts*, *Éléments* — qui étendent chaque
  famille à tout le plan. Décochées par défaut, mémorisées par planche (Q6).

Les cotes sur tout le niveau se chevaucheraient si on les dessinait toutes : c'est **D82** qui règle le
problème, en effaçant l'étiquette dont le côté est trop court à l'écran. Le trait de cote, lui, reste.

### D84 — L'orientation ne s'affiche que si le nord est connu

Conséquence directe de Q3 **(c)** combinée à Q8 **plus tard** : tant que le nord du plan n'est pas renseigné,
`orientation` vaut `"nord à caler"` sur **tous** les côtés du niveau. L'afficher écrirait « à caler » sur
chaque étiquette du plan — du bruit, et une fausse précision.

L'étiquette porte donc la longueur, l'épaisseur, et l'orientation **seulement quand elle est réellement
calculée**. Dès que le nord sera posé (Q8, lot F2), les orientations apparaîtront d'elles-mêmes, sans
retoucher F3. La fiche latérale, elle, continue d'afficher « nord à caler » : c'est là que l'information
manquante doit se voir, pas sur le dessin.

## 7. Vérification faite le 2026-09-23, sur le R+1 réel

Banc local, vrai PDF, étude v3 réassemblée. Local témoin : `6.1.1 B.dir + EAPMR`.

| Contrôle | Attendu (fichier) | Dessiné | Verdict |
|---|---|---|---|
| Cotes déperditives | 14,05 m / 47 cm et 0,31 m / 86 cm | idem | ✅ |
| Surface au centre | 17,79 m² | 17,79 m² | ✅ |
| Pastilles de ponts | 8 liaisons rattachées | 8 | ✅ |
| Éléments d'enveloppe | 36 rattachés | 36 | ✅ |
| Niveau entier, tout coché | 222 côtés, 289 éléments, 77 liaisons | idem | ✅ |
| Effacement des étiquettes | invisible à 5 % de zoom, lisible à 575 % | conforme | ✅ D82 |
| Déplacement du plan au-dessus des métrés | intact | intact | ✅ D79 |

### Ce que le dessin a révélé (et qui n'était pas prévu)

**Les ponts thermiques étaient affichés en mètres dans la fiche, alors que ce sont des comptes.**
`synthese_pieces` incrémente `ponts[genre] += part`, où `part` vaut `1.0`, ou `0.5` quand un refend est
partagé entre deux locaux (`thermique_enveloppe_pieces._couper` et le partage des abouts). Le panneau
affichait `meters(6.0)` → « 6 m » pour **six angles sortants**. Corrigé : la fiche affiche le nombre, avec
une infobulle expliquant la demie. `liaison_plancher_m`, lui, est bien un linéaire et reste en mètres.

Ce défaut était invisible tant que la donnée ne vivait que dans un tableau. Il est apparu au premier
recoupement avec le plan. C'est exactement la raison d'être de ce lot.

**Trois liaisons ne sont rattachées à aucun local** (77 relevées, 74 rattachées). Elles sont désormais
dessinées en gris avec les ponts du niveau, plutôt que passées sous silence : ce qu'on ne voit pas ne se
corrige pas. Leur rattachement relève de F4.

### Reste ouvert

- L'étiquette de cote n'affiche pas l'orientation tant que le nord n'est pas posé (**D84**) ; elle
  apparaîtra d'elle-même dès que Q8 sera traitée, sans retoucher F3.
- Les cotes des côtés intérieurs sont derrière la case « Côtés intérieurs », décochée par défaut.
