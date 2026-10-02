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

Puis le **R+2 en automatique** (méthodes 3 et 4 sans session ouverte, 10-01) : **23, 25 puis 36 objets** contre
130 au R+1, et 21 incohérences. L'essai A/B a écarté la piste « consignes mal transmises » ; **la cause exacte
de l'écart avec le R+1 n'est pas identifiée**. Étude R+2 à ne pas prendre pour base.

## 2. Ce qui a marché

1. **Reconnaître et nommer** : l'IA distingue un mur isolé d'un claustra, regroupe les murs identiques sous un
   même composant, lit un nom de pièce. Le catalogue appris se stabilise (14 → 23 composants).
2. **Le contrôle croisé** : quand deux lectures indépendantes divergent, c'est là qu'est l'erreur (82 à 88 % des
   divergences étaient déjà marquées « à revoir »). La carte des divergences est la bonne liste à faire trancher.
3. **Ce qui ne devine rien** : calage des niveaux, mesure par deux clics dans une coupe, modèle de menuiserie
   mesuré puis posé au clic, désignation par l'exemple (les 31 portes du R+1 ne sont que 11 dessins recopiés).
4. **L'algorithme qui mesure ce que l'IA a désigné** : redressement des tracés, recalage sur le trait réel,
   déduction du trait de coupe.

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
7. **Sans session ouverte, le résultat s'effondre** (R+2) et le coût est élevé.

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

Le départ à zéro du R+1 (demande du 2026-10-02, `murs-traces-decisions.md`) est l'occasion de **mesurer** cette
méthode : temps passé pour un niveau complet tracé à la main, à comparer aux heures de correction du relevé
automatique.
