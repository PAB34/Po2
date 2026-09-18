# Parois mesurées et objets désignés par l'exemple — décisions

> Fil du dev. Ce fichier est écrit **avant** de coder. Il remplace la stratégie du §18 de
> `refondation-parcours-decisions.md` (« Tout détecter » par heuristiques), qui est abandonnée.
> Sujet ouvert le 2026-09-18.

## 0. L'objectif, redit par le client le 2026-09-18

> « Calcul des déperditions thermiques pièce par pièce ; mon objectif est derrière de proposer des
> prestations plus bas que les autres grâce à un modèle me permettant une réalisation rapide. »

**Le livrable n'est pas un plan redessiné, c'est un tableau de déperditions par local.** Un plan
imparfait peut donner un calcul juste ; un plan magnifique peut donner un calcul faux. Toutes les
mesures de réussite se prennent sur le tableau, jamais sur l'aspect du plan redessiné — c'est l'erreur
de méthode qui a fait juger le travail « de pire en pire » : on corrigeait des détails à 2 % pendant que
65 % de la surface était mal délimitée.

### 0.1 Ce que le calcul demande, par local

Surface et **volume** ; **type** de local (consigne, débits d'air réglementaires, apports internes) ;
parois **déperditives** avec leur U, leur surface, leur orientation **et ce qu'il y a de l'autre côté** ;
menuiseries (surface, U, orientation, facteur solaire) ; ponts thermiques ; renouvellement d'air.

### 0.2 L'exigence n'est pas uniforme — D10

Une paroi entre deux locaux chauffés à la même température **ne déperd rien**.

| Élément | Part typique des déperditions | Exigence |
| --- | --- | --- |
| Menuiseries | 25 à 40 % | exacte |
| Murs extérieurs, toiture, plancher bas | 20 à 35 % | exacte |
| Renouvellement d'air (donc le **type** de local) | 20 à 40 % | exacte |
| Ponts thermiques | 5 à 20 % | bonne |
| Parois vers locaux **non chauffés** | variable | exacte |
| Cloisons entre locaux chauffés | **0 %** | approximatif suffit |

**D10 — L'effort suit la part de déperdition.** S'acharner sur les cloisons intérieures était une
erreur : elles pèsent zéro et ne servent qu'à délimiter les locaux.

### 0.3 Le calcul par types de locaux — D11, D12

Méthode de travail du client : calculer un local type, puis l'appliquer à ses semblables. Les sondes du
§2.2 montrent que **c'est aussi une propriété du fichier** : un local recopié est le même groupe de
traits, recopié. Le même appariement qui trouve les portes trouve les locaux jumeaux.

- **D11 — La maille est le type × la position.** Un même local n'a pas les mêmes déperditions au dernier
  étage (toiture), au rez-de-chaussée (plancher bas) ou en angle (deux façades). C'est l'erreur classique
  du calcul par échantillon.
- **D12 — L'échantillon se choisit par les cas limites** (angle, dernier niveau, local sur passage non
  chauffé), jamais au hasard : un local courant en milieu de façade n'apprend rien.
- **D13 — Les équipements se comptent comme des motifs.** WC, douches, baignoires, éviers sont des
  symboles recopiés : le client en désigne un, l'outil les compte tous et les attribue à leur local. Le
  type de local se déduit de ce qu'il contient, recoupé avec son nom écrit.
- **D14 — Les conventions du dessinateur se capitalisent** (cette plume = un mur, ce symbole = une
  cuvette) : valables pour tout le projet, puis pour toute l'agence. C'est le levier du modèle
  économique — la dixième affaire avec le même architecte doit coûter presque rien.

### 0.4 Comment on juge, sans étalon extérieur

Le client ne fournit pas de bâtiment déjà calculé (choix du 2026-09-18) et la cible est le tertiaire du
projet TEST. Trois juges objectifs remplacent la vérité terrain :

1. **Bouclage des surfaces** : la somme des locaux retombe sur la surface du niveau.
2. **Aucune paroi sans deux côtés identifiés** (extérieur, local non chauffé, local chauffé).
3. **Forme des locaux** : compacité `4πA/P²` ≥ 0,5. En dessous de 0,3, le contour est en étoile : local
   raté.

### 0.5 État mesuré au 2026-09-18 (R+1, tableau des locaux)

24 locaux, 841,2 m² pour un niveau de 898 m² (94 % de bouclage). Mais : **16 contours nets qui ne pèsent
que 132 m²**, et **2 contours ratés qui pèsent 544 m², soit 65 % de la surface** (« salle consultation »
329 m² et 158 sommets ; « catalogage » 214 m² et 136 sommets). Noms lus : 9 sur 24.

Autrement dit : les petits locaux sont bons, les grands plateaux — qui portent la surface — sont ratés.
C'est le premier chantier.

### 0.6 Parcours cible

1. **Locaux justes** — le client clique dans un local, le contour est tracé sur les traits réels.
2. **Types de locaux** — nom lu exactement (alphabet de motifs) + équipements comptés (D13).
3. **L'autre côté de chaque paroi** — le cœur du calcul, et le vrai travail manuel à supprimer.
4. **Menuiseries** — depuis les baies déjà trouvées, croisées avec les élévations.
5. **Calcul et export** Pléiades / Perrenoud.

## 1. Pourquoi on change de stratégie

L'essai de « Tout détecter » sur le R+2 puis sur le R+1 a été refusé : « ça va pas du tout, même le R+2
ça allait pas ». Le reproche est constant depuis M3/M4a : **dès que l'outil devine, le résultat est
inutilisable**, parce qu'il faut le vérifier trait par trait — et vérifier coûte plus cher que désigner.

Cause commune de tous les défauts constatés (contours en patatoïde, 4 portes sur un plateau, 153
menuiseries invérifiables, « ferrasse ») : on reconstruit du **sens** à partir de la **forme** des traits,
par des seuils métier (arc de 0,55 à 1,4 m, traits parallèles à 12 cm, pixels de 5 cm dilatés de 2 m).
Chaque seuil est réglé sur un plan et casse sur le suivant.

Ce qui marche, à l'inverse, ne devine rien : lecture vectorielle, désignation par plume, lasso,
superposition, métré. **L'outil ne doit plus jamais produire un résultat probable.**

## 2. Ce que les plans contiennent — sondes du 2026-09-18 (lecture seule)

### 2.1 Ce qu'ils ne contiennent pas

Sondé sur les 4 plans du projet TEST (R+1, R+2, RDC, R+3), tous identiques sur ce point :

| Cherché | Trouvé |
| --- | --- |
| Calques d'origine (`/OCProperties`) | **absent** |
| Texte extractible | **0 caractère** — le texte est vectorisé (l'OCR était donc obligatoire) |
| Blocs (Form XObject) | **0** |
| Aplats de pièces | **aucun** — le plus grand remplissage fait 0,34 × 1,35 m |

Ce sont des exports **aplatis** : il ne reste que de la géométrie et le style de plume.

### 2.2 Ce qu'ils contiennent : des motifs recopiés

R+1 : 7 738 petits remplissages pour **1 012 formes distinctes**, dont 516 vues au moins 3 fois couvrant
**92 %** des dessins. Les mots ressortent comme motifs (« allège » ×8, « 3-A2 », « 3-13 »).

Les portes sont des copies conformes entre elles : sur les 31 trouvées, **15 partagent la même empreinte**
(46 traits, rayon 0,96 m) ; 11 empreintes couvrent les 31.

**Mais** le découpage automatique du plan en objets échoue : « traits de même style qui se touchent »
trouve les symboles, les cercles techniques et les mots, **pas les portes** — une porte mélange deux
plumes (arc pointillé, vantail plein) et touche son mur. Aucune règle générale ne sait où un objet
commence et finit. **C'est l'utilisateur qui le sait, d'un coup d'œil.**

### 2.3 Les parois se mesurent par leurs faces

Une paroi n'est pas recopiée (chaque mur a sa longueur) mais elle a deux faces parallèles. Appariement
des faces longues (≥ 60 cm, écart 4 à 70 cm, parallèles à 2°, recouvrement ≥ 50 %) :

| Plume | Faces appariées | Épaisseurs (cm) |
| --- | --- | --- |
| 1,56 pt noir (murs) | 86 % (R+1), 84 % (R+2) | 12 ×102, 24 ×36, 18 ×23, 30 ×16, 42 ×15 |
| 0,96 pt noir (cloisons) | 73 % | **10, et rien d'autre** (28 paires sur 28) |
| 0,36 pt noir (trame) | 90 % | 10, 20, 30, 40, 50, 60 — ~500 chacune |

Les deux premières sont de vraies parois : épaisseurs **piquées**. La troisième est un quadrillage apparié
avec lui-même : distribution **plate**. D'où le garde-fou D5 ci-dessous.

## 3. Décisions

- **D1 — L'outil ne propose jamais un résultat probable.** Ce qui n'est pas certain est présenté comme
  « à désigner », jamais comme un calque ou une pièce. Le bouton « Tout détecter » du §18 est retiré.
- **D2 — Deux mécaniques, pas une.** Les **objets** (portes, menuiseries, symboles, textes) sont recopiés :
  ils se désignent **par l'exemple**. Les **parois** (murs, cloisons, isolant) sont uniques : elles se
  **mesurent** par paires de faces. Ne pas essayer de traiter les unes comme les autres.
- **D3 — « Montrez-m'en un, je trouve les autres ».** L'utilisateur entoure un objet au lasso ; l'outil
  retrouve toutes ses copies à translation, rotation, symétrie et échelle près. C'est l'extension du geste
  déjà validé (désignation par plume), appliqué à la forme.
- **D4 — Une paroi est un segment à deux faces**, portant son épaisseur, sa longueur et ses deux côtés.
  C'est cet objet-là qu'on rend au thermicien, pas une liste de traits.
- **D5 — Garde-fou des épaisseurs.** Une famille de parois n'est retenue que si ses épaisseurs sont
  piquées (une part significative sur quelques valeurs). Une distribution plate = appariement d'une trame,
  refusé.
- **D6 — L'isolant est mesuré, pas seulement désigné.** Sa plume est déjà reconnue (hachure vs zigzag :
  0,997 contre 0,125) ; son épaisseur se lit entre les deux faces qui l'encadrent.
- **D7 — Les menuiseries ont deux sources qui doivent tomber d'accord** : le motif dit quel châssis,
  la **baie** (interruption de la paroi) dit quelle largeur. Divergence = signalée, jamais arbitrée seule.
- **D8 — Les pièces se calculent en vectoriel**, par intersections réelles des parois, jamais en pixels.
  Le raster de `thermique_moteur/pieces.py` est abandonné pour cet usage.
- **D9 — Ordre de construction** : parois (socle du métré, de l'enveloppe et des pièces), puis appariement
  par l'exemple, puis pièces vectorielles, puis menuiseries croisées motif × baie.

## 4. Questions ouvertes

- **Q86** — Une paroi dont les deux faces n'ont pas la même plume (par exemple mur coupé d'un côté,
  doublage de l'autre) : une seule paroi de l'épaisseur totale, ou deux parois accolées ?
- **Q87** — Les épaisseurs proposées doivent-elles être **arrondies** aux valeurs franches du bâtiment
  (12, 20, 24, 30 cm) ou rendues telles que mesurées au millimètre ?
- **Q88** — Quand une copie trouvée par le lasso est partielle (l'objet est coupé par un mur, ou dessiné
  à moitié), on la propose quand même en la signalant, ou on l'écarte ?
- **Q89** — Un motif désigné sur un niveau doit-il être cherché **sur tous les niveaux** du projet
  d'emblée, ou seulement sur celui où on l'a montré ?
- **Q90** — Pour les baies : une fenêtre à deux vantaux jumelés compte-t-elle comme une baie ou deux ?
  (Le §14 penchait pour une baie d'ensemble — à confirmer sur ce nouveau socle.)

## 5. Comment on saura que c'est bon

Chaque brique se mesure sur les plans réels du projet TEST, et le score est rendu avant toute suite :

1. **Parois** : part des faces appariées, distribution des épaisseurs, et comptage manuel de contrôle sur
   une façade complète.
2. **Appariement par l'exemple** : un lasso sur une porte du R+1 doit rendre les 15 jumelles — pas 12.
3. **Pièces** : contours sans aucun sommet inventé, chaque côté porté par une face réelle.
