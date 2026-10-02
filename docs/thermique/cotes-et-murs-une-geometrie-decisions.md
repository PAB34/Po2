# Les métrés des locaux et les lignes des murs : une seule géométrie ? (D255 à D258, proposées)

Date : 2026-10-02. Question du thermicien : « on a des métrés et aussi des lignes représentant les parois ; l'un ne
peut-il pas servir l'autre, ou le remplacer ? » Objectifs 1 (R+1 parfait) et 5 (livrable) de la boussole.

## Existant vérifié

Aujourd'hui, **deux tracés indépendants décrivent la même face intérieure** :

| | Côtés des locaux (« métrés », les cotes du plan) | Lignes de métré des murs |
|---|---|---|
| D'où ils viennent | Contour de chaque local (agent, recalé sur l'image, retouché par le thermicien) ; chaque côté est sondé tous les 10 cm pour savoir ce qu'il y a derrière (`thermique_fiches_locaux.py`) | Relevé de la façade par l'agent : un tronçon guide + abscisses + nus (`reprojeter`, D242) |
| Ce qu'ils portent | longueur, **adjacence** (extérieur, local non chauffé, autre local, vide), voisin, orientation, épaisseur du mur sondée, déperditif | **composition** (couches), épaisseur, composant |
| Ce qu'ils couvrent | **tous** les côtés de tous les locaux (façade, cloisons, locaux non chauffés, circulations) | l'enveloppe seulement (façade et complément D46) |
| Comment on les relie | un élément du relevé est rattaché au côté déperditif **le plus proche à moins de 90 cm** | — |

Conséquence : quand les deux tracés ne tombent pas au même endroit, l'outil le signale après coup (« côté
extérieur sans élément d'enveloppe », « élément(s) sans côté correspondant », écart entre le tour des locaux et la
façade relevée). Une partie des anomalies du R+1 vient de là. Et chaque retouche doit être faite deux fois : le
contour du local d'un côté, le mur de l'autre.

## Trois options

- **A — Garder les deux, mieux reliés.** Alerte dès qu'un côté et sa ligne s'écartent de plus de 2 cm ; geste
  « caler le local sur ce mur ». Peu de travail, mais le doublon et la double retouche restent.
- **B — Le mur commande le local.** Les lignes de métré sont la géométrie de l'enveloppe ; le contour d'un local
  s'y accroche automatiquement. Une retouche au lieu de deux sur la façade, mais les cloisons et les locaux non
  chauffés gardent l'ancien système, et le mur reste attaché au guide de façade de l'IA.
- **C — Le côté du local devient la ligne de métré (recommandé).** Une seule géométrie : les contours des locaux.
  Un mur n'est plus un tracé à part mais **la composition affectée à un côté** (ou à une partie de côté) ; une
  menuiserie est posée **sur un côté** ; les ponts sont aux **sommets** (angles) et aux jonctions. C'est la façon de
  travailler des logiciels de calcul thermique.

## Pourquoi C

1. **Dimensions intérieures par construction** : le contour du local *est* la face intérieure (convention
   française, D21). Plus de raccord d'angles à calculer.
2. **Le livrable devient direct** : surface d'une paroi = longueur du côté × hauteur du local ; déperditions par
   local = somme sur ses côtés. C'est le chemin le plus court vers l'objectif 5.
3. **Tout est couvert** : cloisons sur local non chauffé, circulations, refends : ce sont des côtés comme les
   autres. Le problème du « côté extérieur » des murs intérieurs (D251) disparaît : l'adjacence dit de quel côté
   est l'extérieur.
4. **Plus de dépendance au guide de façade de l'IA**, et une identité stable : un côté se désigne par son local et
   ses deux sommets, pas par une abscisse le long d'un tronçon.
5. **Une seule retouche** : glisser un sommet du contour déplace le côté, donc le mur, donc la surface.
6. **Le relevé de l'IA ne disparaît pas** : il devient une **proposition** de composition par côté (le rattachement
   à 90 cm existe déjà), que le thermicien accepte d'un clic.

## Ce que coûte C (honnêtement)

- Un gros lot, à découper. Le contour des locaux doit être précis : aimant sur les sommets des locaux voisins,
  côté partagé entre deux locaux (la cloison) modifié en une fois.
- Les gestes faits aujourd'hui sur les murs (poignées, créer, ajouter un point) **changent de cible** : ils
  s'appliqueront aux sommets et côtés des contours (« Reprendre le contour » sait déjà glisser un sommet). Leur
  logique (aimant, longueur en direct, enregistrement immédiat) se réutilise ; le geste sur le relevé devient
  inutile à terme.
- Un mur partagé par deux locaux (cloison) doit garder **une** composition pour ses deux faces.
- L'épaisseur du mur reste utile (dimensions extérieures, ponts) : elle vient de la composition.

## Impact sur l'analyse des plans par l'IA et les algorithmes (question du 2026-10-02)

| Étape de la chaîne actuelle | Avec l'option C |
|---|---|
| Inventaire des composants et des pièces (`thermicien-plan`) | **Inchangé, et plus central** : les contours des locaux deviennent la base de tout |
| Recalage des pièces sur les murs (D26, algorithme) | **Inchangé**, et c'est lui qui donne la précision des côtés |
| Nature des locaux (consigne courte) | Inchangé |
| Parcours de la façade (`thermicien-enveloppe`) | **Gardé, mais il ne fournit plus la géométrie** : ses lectures (composition, menuiseries) deviennent des propositions rattachées aux côtés (rattachement à 90 cm déjà en place). Ses mesures fausses (10 % des nus à plus de 11 à 21 cm) ne déforment plus le métré : l'IA n'a plus qu'à reconnaître, ce qu'elle fait bien |
| Découpage pièce par pièce, réunion des morceaux à 6 cm, lignes de métré, raccord des angles | **Deviennent inutiles** : un côté appartient déjà à son local, et le contour est déjà la face intérieure. Des étapes et leurs erreurs en moins |
| Guide de façade (claustra suivi, dents de scie coupées) | Ses erreurs ne touchent plus que des propositions, plus le métré |
| Contrôle par l'image | Inchangé |
| Études existantes (R+1) | **Rien n'est perdu** : les côtés se calculent déjà depuis les contours, et les compositions corrigées passent aux côtés par le rattachement existant |
| Essai cloud du R+2 | Son résultat reste lisible (même format) |
| Report entre niveaux (D233–D237) | Plus simple : on reporte des contours et leurs compositions |

À terme, l'agent de façade pourrait même faire **le tour de chaque local** au lieu de longer un guide calculé.
C'était l'essai « local par local » du 2026-09-22, écarté alors parce que la géométrie venait de la façade. Avec la
détection par l'exemple pour les menuiseries et une composition par type de mur (5 à 10 types par projet), une
grande partie du parcours de façade par l'IA pourrait être remplacée par vos clics, à mesurer avant de décider.

**Point de vigilance** : la qualité des contours devient critique. Un mauvais inventaire des pièces (R+2 en Opus 4.7 :
8 pièces) dégrade tout, mais c'est déjà le cas aujourd'hui.

## Décisions proposées

- **D255** — Option C : la géométrie de référence est le contour des locaux ; un mur = une composition affectée à
  un côté (ou à une portion entre deux points du côté).
- **D256** — Le relevé de l'IA devient une proposition de composition et de menuiseries par côté, acceptée d'un clic
  ou d'un geste « accepter tout ce qui est sûr ».
- **D257** — Une menuiserie se pose sur un côté (position le long du côté, largeur, modèle) ; sa surface est retirée
  de celle de la paroi.
- **D258** — Ordre : (1) côtés éditables et partagés entre locaux voisins (aimant, cloison commune) ; (2) composition
  par côté avec reprise du relevé ; (3) menuiseries par côté ; (4) surfaces et premier livrable ; (5) retrait des
  lignes de métré et du découpage par tronçon.

## Questions

1. **Option** : C vous convient-elle, ou préférez-vous A ou B ?
2. **Côté partagé** : quand deux locaux chauffés se touchent, le côté commun porte-t-il une composition (cloison) à
   saisir, ou seulement les côtés déperditifs (extérieur, local non chauffé, vide) ?
3. **Portion de côté** : un côté qui change de composition en cours de route (mur puis vitrage puis mur) : on le
   coupe par des points (comme « Ajouter un point »), d'accord ?
4. **Ce qui vient d'être fait sur les murs** : on le garde tel quel jusqu'à la fin du lot (2) de D258, puis on le
   retire. D'accord ?
