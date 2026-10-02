---
read_policy: lire avant toute décision sur la détection automatique des composants (murs, menuiseries, locaux)
---

# Détection des composants par niveau — ce qui a marché, ce qui a échoué (2026-10-02)

Recherche demandée par le thermicien le 2026-10-02. Sources : `detection-murs-strategie.md`,
`detection-guidee-decisions.md`, `agent-verification-decisions.md`, `analyse-ia-visuelle-r1-decisions.md`,
`chaine-analyse-plan-raster.md`, `carences-agents-strategie.md`, `comparatif-agents-claude-openai.md`,
`coupes-elevations-S5-decisions.md`, `vues-sans-ia-decisions.md`, `04-Etat-actuel-du-dev.md`. Projet d'essai :
médiathèque (projet 1), plans PDF aplatis au 1/100.

## 1. Les cinq méthodes essayées, dans l'ordre

| # | Période | Méthode | Résultat mesuré | Verdict |
|---|---|---|---|---|
| 1 | 09-14 | **Pixels** : contour du niveau par traitement d'image (dilatations, remplissages) | −1 et R+2 justes, RDC presque, R+1 à reprendre (façades vitrées, coursives, bandes plantées) | Abandonné : réglages fragiles, formes rabotées, un niveau amélioré en dégrade un autre |
| 2 | 09-14 → 09-18 | **Vecteurs du PDF** : un mur = deux faces parallèles | Sous-sol : **78 murs, épaisseur au mm, aucune face inexpliquée**. RDC à R+3 : faux murs (escaliers, symboles, équipements) ; les deux lignes du nu sont trop grandes (terrasses, brise-soleil) ; les vitrages (traits fins) font fuir l'emprise | Abandonné le 09-21 sur décision du thermicien (règle : ne pas y revenir) |
| 3 | 09-21 → | **IA qui regarde l'image**, passe globale (`thermicien-plan`) | R+1 : 130 objets, 22 pièces, en ≈ 4 min ; 61 à confirmer. Deux lectures de Claude se recouvrent à **85 %** pour les pièces, mais seuls **51 à 63 %** des objets se retrouvent d'une lecture à l'autre | Utile pour **nommer et zoner**, pas pour mesurer |
| 4 | 09-22 → | **IA qui longe la façade** (`thermicien-enveloppe`) sur des bandes redressées, avec catalogue appris | R+1 : 72 tronçons, 171 m, 208 intervalles, **23 composants** ; P1 reconnu 29 fois sous le même nom ; contrôle par l'image : P1 96 %, baies M1/M4 100 % | **Le meilleur résultat obtenu**, mais mesures approximatives (voir § 3) |
| 5 | 09-29 | **IA qui lit les coupes** (`thermicien-coupe`) | **0 sur 13** hauteurs justes (vues et numéros de pièces bien lus) ; l'algorithme qui déduit le trait de coupe fait 8/8 et 3/3 | Retirée le 10-01 (D230) : vues créées et mesurées à la main |

**Ces méthodes 3 et 4 forment une seule chaîne**, encore en service : c'est elle qui a produit l'étude
actuelle du R+1 (`chaine-analyse-plan-raster.md`).

1. L'IA inventorie **tous les composants** du plan : pièces, murs, refends, cloisons, isolants, menuiseries,
   poteaux, terrasses.
2. L'algorithme **recale les pièces** sur les murs (D26, D26 bis) : 21 pièces sur 22 recalées, 2 circulations
   oubliées retrouvées, puis l'IA donne leur nature ; 24 locaux au final.
3. L'IA longe la façade : relevé par tronçon.
4. L'algorithme fait le **découpage pièce par pièce** (D18 à D20, `thermique_enveloppe_pieces.py`) : chaque paroi et
   chaque baie est coupée là où la pièce derrière change, avec recalage sur l'about de cloison à moins de 30 cm.
   Chaque angle va à la pièce qui le contient ; un refend est partagé moitié-moitié. Résultat au R+1 :
   **230 éléments rattachés**, puis les fiches par local.

Le découpage lui-même **fonctionne** : il est exact chaque fois que les pièces et le relevé sont justes. Ses
erreurs viennent de l'amont : guide qui coupe une dent de scie, pièce qui n'atteint pas la façade, espace ouvert
d'un seul tenant (D22).

Puis le **R+2 en automatique** (méthodes 3 et 4 sans session ouverte, 10-01) : **23, 25 puis 36 objets** contre
130 au R+1, et 21 incohérences. L'essai A/B a écarté la piste « consignes mal transmises ». Étude R+2 à ne pas prendre pour base.

**Cause trouvée le 2026-10-02 : ce n'était pas le même modèle.** Le R+2 a bien suivi **toute** la chaîne (journal :
passe globale, recalage, locaux, catalogue du R+1, guide, 6 lots, restitution). Mais tout s'est joué dès la
première étape : **25 objets, dont 8 pièces** (contre 130 et 22 au R+1), et le reste en a hérité (5 pièces
recalées sur 8, aucune circulation).

| | R+1 (09-21 → 09-23, dans la session) | R+2, RDC, SS1 (10-01, mode automatique) |
|---|---|---|
| Modèle réellement utilisé (relevé dans les traces) | **claude-opus-5** | **claude-opus-4-7** |
| Texte produit par lecture | 20 000 à 48 000 jetons | 14 500 à 35 000 jetons |

Le mode automatique demande le modèle par son alias `opus`. La commande `claude` installée sur le poste le
traduit en **Opus 4.7**, un modèle plus ancien. C'est un **remplacement silencieux de modèle**, contraire à la règle
du thermicien. Les agents du R+1, lancés depuis la session, tournaient sur Opus 5.

Correctif à faire avant toute nouvelle passe : nommer le modèle exact, sans alias, et **arrêter** l'étude si la trace
d'un appel montre un autre modèle.

## 2. Ce qui a marché

1. **Reconnaître et nommer** : l'IA distingue un mur isolé d'un claustra, regroupe les murs identiques sous un
   même composant, lit un nom de pièce. Le catalogue appris se stabilise (14 → 23 composants).
2. **Le contrôle croisé** : quand deux lectures indépendantes divergent, c'est là qu'est l'erreur (82 à 88 % des
   divergences étaient déjà marquées « à revoir »). La carte des divergences est la bonne liste à faire trancher.
3. **Ce qui ne devine rien** : calage des niveaux, mesure par deux clics dans une coupe, modèle de menuiserie
   mesuré puis posé au clic, désignation par l'exemple (les 31 portes du R+1 ne sont que 11 dessins recopiés).
4. **L'algorithme qui mesure ce que l'IA a désigné** : redressement des tracés, recalage sur le trait réel,
   déduction du trait de coupe, recalage des pièces sur les murs, **découpage pièce par pièce**.

## 3. Ce qui a échoué

1. **L'IA donne de mauvaises coordonnées** : 10 % des nus faux de plus de 11 cm (extérieur) et 21 cm
   (intérieur) ; cadre des baies d'un même modèle placé de −14 à +90 cm ; hauteurs de coupe 0/13.
2. **La confiance qu'elle annonce ne vaut rien** : 0,66 en moyenne quel que soit le cas ; une lecture
   débordant sur la légende se disait la plus sûre.
3. **Elle ne rend pas deux fois la même chose** : 15 % de la surface des pièces change d'une lecture à l'autre ;
   115 à 130 objets selon le tirage ; un tiers du relevé reste « à vérifier ».
4. **Le guide automatique de la façade se trompe** : il suit le claustra, coupe les dents de scie, fait des
   boucles ; le mur réel sort alors de la bande lue.
5. **Les règles de forme ne se transposent pas** : chaque seuil réglé sur un plan casse sur le suivant.
6. **Le découpage du relevé est celui de la façade, pas celui du mur** : morceaux de menuiseries et de murs, d'où
   la fusion à 6 cm, et des murs impossibles à reprendre proprement (votre demande de ce jour).
7. **Le mode automatique a tourné sur un modèle plus ancien** (Opus 4.7 au lieu d'Opus 5), sans que personne ne
   le voie : c'est l'explication probable de l'effondrement du R+2.

## 4. La leçon

**L'IA reconnaît, elle ne mesure pas ; un geste du thermicien mesure juste et ne coûte rien.** Toute
détection qui produit une géométrie « probable » doit être revérifiée trait par trait ; elle fait alors perdre
plus de temps qu'elle n'en fait gagner. Ce qui a marché a toujours la même forme : le thermicien montre ou mesure
**une fois**, l'outil reproduit.

## 5. Proposition pour les composants, par niveau

| Composant | Qui fait quoi |
|---|---|
| **Murs** | Le thermicien **trace** la ligne de métré (clic droit « Créer un mur », extrémités étirables, aimant sur les autres murs) et choisit une composition dans la bibliothèque. L'ancien relevé de l'IA sert, au mieux, de **calque de suggestions** à accepter ou effacer. |
| **Locaux** | Contours tracés ou repris, nom et nature validés ; l'IA peut proposer les noms lus. |
| **Menuiseries** | Modèle mesuré en élévation, posé au clic ; ensuite **« par l'exemple »** : on montre une fenêtre, l'outil retrouve ses copies sur l'image (D233–D237, objectif 4b). |
| **Autres niveaux** | Report du R+1 par le calage (murs superposés repris d'office, à confirmer), puis tracé de ce qui diffère. |
| **IA** | Seulement en lecture ciblée et à la demande : nommer un composant, lire une composition sur un zoom, vérifier une divergence. Jamais de coordonnées, jamais de passe globale. |

## 6. Projets existants du même genre (recherche du 2026-10-02, à évaluer, rien d'installé)

| Projet | Ce qu'il fait | Réserve |
|---|---|---|
| [CubiCasa5k](https://github.com/CubiCasa/CubiCasa5k) | jeu de 5 000 plans annotés (80 catégories) et modèle qui segmente murs, pièces, portes, fenêtres | plans de logements finlandais ; usage commercial soumis à licence CubiCasa |
| [CubiCasa5k-Next](https://github.com/Lqm1/CubiCasa5k-Next) | réécriture du même modèle, licence Apache-2.0 | même domaine d'apprentissage |
| [FloorPlanNet](https://github.com/thatguywhodoestecheverysatnight/FloorPlanNet) | segmente murs, pièces, portes, fenêtres puis **vectorise** en polygones et axes de murs, avec calage d'échelle et export SVG/DXF | à mesurer sur nos plans |
| [floor-plan-object-detection](https://github.com/sanatladkat/floor-plan-object-detection) | détection YOLOv8 : poteaux, murs, portes, fenêtres | jeu d'apprentissage réduit |
| [FloorPlanAnalyzer](https://github.com/mageaustralia/FloorPlanAnalyzer) | combine segmentation classique, YOLOv8 et CubiCasa5k | expérimental |
| [FloorPlanCAD](https://floorplancad.github.io/) | 15 663 plans CAO annotés, 30 classes (portes, fenêtres, escaliers…) | données vectorielles ; projet arrêté en 2022 |
| Recherche « symbol spotting » ([Rezvanifar 2020](https://openaccess.thecvf.com/content_CVPRW_2020/papers/w34/Rezvanifar_Symbol_Spotting_on_Digital_Architectural_Floor_Plans_Using_a_Deep_CVPRW_2020_paper.pdf)) | **on recadre un symbole, l'outil retrouve ses semblables** : c'est la détection par l'exemple | travaux de recherche, pas d'outil clé en main repéré |

Constat : ces modèles reconnaissent murs, portes, fenêtres et pièces, mais **pas la composition thermique** (isolant,
doublage) ; ils ont appris sur d'autres graphismes, surtout du logement. Un « modèle perso » serait un **petit
modèle de vision** (et non un LLM) réentraîné sur nos plans corrigés : le R+1 validé en serait la première vérité
terrain. Coût en jetons nul à l'usage. À tester d'abord tel quel sur l'image du R+1, sur le serveur ou en session
cloud (rien sur le poste), avec l'accord du thermicien.

Le départ à zéro du R+1 (demande du 2026-10-02, `murs-traces-decisions.md`) est l'occasion de **mesurer** cette
méthode : temps passé pour un niveau complet tracé à la main, à comparer aux heures de correction du relevé
automatique.
