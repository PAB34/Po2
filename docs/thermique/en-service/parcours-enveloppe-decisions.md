---
type: decisions
status: actif
read_policy: si la tache concerne la lecture de l'enveloppe exterieure sur plan raster
related:
  - analyse-ia-visuelle-r1-decisions.md
---

# Parcours de l'enveloppe extérieure — décisions

## 1. Demande (2026-09-21)

La première analyse globale du R+1 identifie mal les parois extérieures (isolants notamment). Proposition de
l'utilisateur : une fois les pièces identifiées, l'agent part d'un point stratégique et **longe l'enveloppe**
dans une bande de travail d'environ 60 cm, jusqu'à revenir à son point de départ. Il doit relever tout ce qui
compte pour la bibliothèque de composants : composition des murs (mur + isolant + doublage, RE2020 ; ici
double mur avec isolant entre les deux), cadres de menuiserie, menuiseries, poteaux, angles.

## 2. Existant vérifié

- `vision-analysis.json` / `claude_agent_R1.json` : 22 pièces (polygones au nu intérieur, nom lu), murs,
  menuiseries et poteaux de la passe globale, en coordonnées de la feuille 0..1000.
- `thermique_vision_geometrie.py` : nettoyage et recalage raster ; `thermique_claude_agent.py` : paquet
  d'images, projection, reprojection vers la feuille.
- Échelle du plan : 1/100 (contrôlée par cote le 2026-09-11).
- Aucun parcours d'enveloppe n'existe ; aucune lecture de composition de paroi n'existe.

## 3. Décisions

- **D1 — Guide = pièces.** Le chemin est le contour extérieur de l'union des pièces (fermeture des cloisons par
  dilatation puis érosion de 25 cm). Il suit le nu intérieur de l'enveloppe, redents compris. Les espaces
  extérieurs (terrasses) restent dehors ; les trous intérieurs (patio, trémie) sont signalés, pas parcourus.
- **D2 — Départ** : l'angle le plus au nord-ouest du contour, parcours dans le sens horaire vu en plan.
- **D3 — Bande de travail** : 30 cm côté intérieur (doublage, nu intérieur) et 90 cm côté extérieur (murs,
  isolant, double mur, saillies). Les 60 cm proposés ne suffisent pas pour un double mur isolé dont le nu
  intérieur estimé peut être décalé de 10 à 20 cm.
- **D4 — Images redressées.** Chaque côté du contour est découpé en tronçons de 5 m au plus (plus 60 cm de
  recouvrement à chaque bout, pour voir les angles), rendus à **300 dpi** (≈ 0,85 cm par pixel, au lieu de
  1,7 cm) et redressés à l'horizontale : extérieur en haut, intérieur en bas. Une règle graduée donne
  l'abscisse le long de l'enveloppe (en m) et la profondeur par rapport à la ligne guide (en cm).
- **D5 — Lecture linéaire.** L'agent ne renvoie pas des points 2D mais des **intervalles d'abscisse**
  (début/fin en m) avec, pour chacun, le type (paroi opaque, menuiserie, poteau, angle…), la composition
  couche par couche de l'extérieur vers l'intérieur avec épaisseurs, et la position des nus. Mesurer le long
  d'une règle est bien plus fiable que placer des coordonnées sur un plan entier.
- **D6 — Retour en géométrie.** Les intervalles sont reprojetés sur la feuille (abscisse + profondeur →
  point) et produisent des objets éditables de l'écran `/analyse` (murs, isolants, menuiseries, poteaux), avec
  la pièce intérieure concernée.
- **D7 — Bibliothèque.** Les compositions identiques sont regroupées en **types de paroi candidats** (ex.
  « voile 20 + isolant 12 + voile 16 + doublage 5 ») avec leur linéaire total ; idem pour les menuiseries
  (type, largeur, position du cadre dans le mur). C'est la liste à valider pour créer les composants.
- **D8 — Raster seul**, comme toute la piste : aucun vecteur PDF n'est lu, le rendu 300 dpi est un rendu de
  pixels.

## 4. Questions ouvertes

- Q1 : les épaisseurs lues doivent-elles être arrondies aux épaisseurs commerciales (isolant 10/12/14/16 cm)
  ou gardées telles que lues ?
- Q2 : l'escalier extérieur est et la « boîte à vents » : extérieur ou local non chauffé ?
- Q3 : faut-il ensuite parcourir aussi les parois sur locaux non chauffés (même mécanisme, autre guide) ?

## 5. Essai sur le R+1 (2026-09-21) et décisions complémentaires

- **D9 — Guide raster (remplace D1 quand l'image est disponible).** Le contour des pièces ne suit pas les
  zigzags. Le guide devient la face extérieure réelle du volume, obtenue sur l'image par remplissage de
  l'extérieur. Deux remplissages : (A) tous les traits font barrière ; (B) les traits simples et fins (rive de
  dalle, axes, arcs) sont ignorés, sans pénétrer à plus de 30 cm dans les pièces. On retire de A les poches
  que B voit extérieures hors des pièces, ce qui correspond aux dents de scie fermées par une rive. Terrasses,
  balcons et espaces extérieurs à déterminer sont exclus. Garde-fou : surface entre 0,85 et 1,6 fois celle des
  pièces, sinon retour au guide « pièces ». Bande : 40 cm côté extérieur et 90 cm côté intérieur.
- **D10 — Planches de relevé annotées** (`releve-XX.png`) : les couches lues par l'agent sont dessinées en
  couleur sur les bandes. Le thermicien voit d'un coup d'œil ce qui a été lu et où l'agent s'est trompé.
- **D11 — Familles de parois** : les compositions sont regroupées par suite de couches (épaisseurs médianes
  pondérées par le linéaire et fourchettes) ; une famille = un composant candidat de la bibliothèque.

Résultat R+1 : 72 tronçons et 171,3 m parcourus en entier. Parois 53 m, menuiseries 70 m, poteaux 4 m,
77 liaisons, 27 m à déterminer (16 %). Familles : « mur 12 + isolant 13 + mur 20 » (double mur, 41,5 m),
« parement 4 + isolant 18 + mur 16 » (9,4 m, façade sud : même mur, voile extérieur lu comme parement ?),
voile béton non isolé de la cage d'escalier (1,7 m).

Limites constatées :

- dents de scie ouest : la paroi isolée est en biais derrière des massifs triangulaires ; l'agent ne peut
  décrire que des couches parallèles au guide. **Prochaine évolution : nus en début ET en fin d'intervalle.**
- claustra sud-ouest (T35-T45) : le guide suit les blocs du claustra au lieu du vitrage en retrait ; pointe
  parasite en T38. À relever à nouveau une fois le guide corrigé.
- regroupement des menuiseries par position du cadre trop fin ; les baies de retour vues de chant ont une
  largeur fausse (10 à 14 cm lus au lieu d'environ 90 cm).

Questions ajoutées : Q4 « parement 4 » au sud = voile mince du double mur ? Q5 poteaux béton non isolés derrière
le mur-rideau est : pont thermique à retenir ?

## 6. Retour utilisateur du 2026-09-21 : apprentissage, ponts thermiques, épaisseurs

- **D12 — Épaisseurs commerciales (fait).** Chaque famille donne une composition « retenue » ramenée à la gamme
  commerciale de la couche (voiles 10/12/15/16/18/20/22/25…, isolants par pas de 2 cm, doublages x+1,3 cm) ;
  l'épaisseur lue reste affichée à côté.
- **Constat — l'agent n'apprend pas.** Chaque lancement repart de zéro et les trois agents parallèles ne se
  parlaient pas : le même double mur a été appelé « mur 12 » au nord et « parement 4 » au sud.
- **D13 (proposé) — Catalogue de composants appris.** Le parcours devient séquentiel, par lots de planches.
  Chaque lot reçoit le catalogue construit par les lots précédents : identifiant (P1, M1, PT1…), vignette de
  l'image où le composant a été vu la première fois, composition, décision *intégré / exclu*, et règle de
  reconnaissance (« trait noir épais + alvéoles entre deux gris = P1 »). L'agent doit réutiliser un
  identifiant existant ou en créer un nouveau en le justifiant. Le thermicien valide ou corrige chaque entrée ;
  le catalogue validé est enregistré pour le projet, puis pour l'agence (mêmes conventions graphiques d'un
  projet à l'autre, D14 de parois-et-motifs-decisions.md). Complément classique : la signature d'image d'un
  composant validé (texture de la hachure) permet de retrouver ses autres occurrences sans l'agent.
- **D14 (proposé) — Typologie des ponts thermiques** : rupture de l'isolant par (a) un angle sortant ou
  rentrant, (b) une jonction avec un autre composant (menuiserie : appui, linteau, tableaux ; poteau ; about de
  mur), (c) une discontinuité (changement de composition ou d'épaisseur, fin d'isolant) ; auxquels s'ajoutent
  (d) les liaisons avec les planchers (intermédiaire, bas, haut ou toiture, terrasse ou balcon en
  porte-à-faux), invisibles en plan mais présentes sur tout le périmètre de chaque niveau ; (e) les refends et
  murs lourds qui traversent ou touchent l'isolant ; (f) les ponts ponctuels (fixations de brise-soleil,
  consoles, attaches de garde-corps).

## 7. Catalogue appris : essai complet sur le R+1 (2026-09-21)

- D13 mis en œuvre : parcours en 4 lots successifs de 3 planches. Chaque lot reçoit le catalogue et une
  planche de vignettes (`catalogue-avant-lot-K.png`) ; un intervalle qui renvoie à un composant connu laisse ses
  couches vides, et c'est la fiche qui fait foi. Commandes : `--lot K` (consigne), `--integrer-lot K fichier`,
  puis `--from-raw lot-1 … lot-4` ; en ligne de commande autonome, les lots s'enchaînent tout seuls.
- D15 — Parois en biais : l'agent donne les nus au début et à la fin de l'intervalle. Paroi d'épaisseur
  constante : couches empilées depuis le nu extérieur. Épaisseur variable (massif triangulaire) : couches calées
  sur le nu intérieur, la première couche absorbe la variation et les couches sont comprimées si la place manque.
- Résultat : 23 composants (lot 1 : 14 ; lot 2 : +3 ; lot 3 : +3 ; lot 4 : +3), chaque création étant justifiée
  (« ce n'est pas PO1 parce que… »). P1 est reconnu 29 fois (41,6 m) sur toutes les façades ; l'incohérence
  « parement » a disparu. Exclus : X1 brise-soleil, X2 escalier extérieur, X3 potelets de terrasse, X4 claustra
  (11 m). À confirmer : P3 voile non isolé, P4 massif triangulaire (14,5 m), M2 porte, L3, L4, L6, L7, L8.
- Limites restantes : là où le guide suit le claustra (T39-T45, T56-T57), le vitrage réel n'est que
  partiellement dans la bande ; boucle parasite T70-T71 ; largeur réelle des baies de retour des dents de scie à
  lire en profondeur, pas en abscisse.

## 8. Contrôle par l'image et couches lisibles (2026-09-22)

- Contrôle indépendant (script de recette, hors moteur) : alvéoles d'isolant et béton gris repérés sur l'image
  tous les 5 cm, comparés au relevé. Isolant : 87 % de l'isolant visible est compté ; les 7 m non comptés sont
  dans les angles et jonctions (L1 5,8 m, L2, L3, L5). Béton : P1 96 %, P2 94 %, P3 98 %, P4 74 % (le guide
  coupe les dents de scie : T34, T67, T68) ; aucune menuiserie posée sur du béton, sauf M5 devant le claustra.
- Convention confirmée par l'utilisateur : **métré français en dimensions intérieures**. L'isolant de l'angle
  n'entre pas dans les surfaces ; il est porté par le pont thermique d'angle (ψ). Les 5,8 m ne manquent donc pas.
- **D16 — Rôle de chaque couche.** Dans le rendu, chaque couche d'une paroi devient un objet distinct : voile
  extérieur, isolant, voile intérieur (double peau), doublage. Un voile placé avant l'isolant est « voile
  extérieur », après l'isolant « voile intérieur », seul « voile ». Nouvelle catégorie d'objet `doublage`.
- **D17 — Doublage présumé.** Le doublage (plaque de plâtre BA13, 1,3 cm) n'est presque jamais dessiné au
  1/100 ; l'utilisateur l'estime présent dans 99 % des cas. Une paroi intégrée dont la dernière couche est un
  voile reçoit un doublage BA13 1,3 cm **présumé**, posé côté pièce contre le nu intérieur dessiné, marqué
  « présumé » (tracé distinct) et à confirmer par composant dans le catalogue. Un doublage lu sur le plan prime.

### Découpage pièce par pièce — décisions (validées par l'utilisateur le 2026-09-22 : « règles de bonne pratique »)

- **D18 (Q6) — Coupe des parois.** Chaque intervalle relevé est coupé là où la pièce située derrière sa face
  intérieure change (sondage tous les 5 cm, 30 cm à l'intérieur du nu intérieur, dans les pièces de la passe
  globale ; plus tard dans le contour des zones du Métré quand il existe). La coupe est recalée sur l'about de
  cloison ou de refend relevé à moins de 30 cm. Longueur retenue : longueur de la face intérieure (dimensions
  intérieures), y compris pour une paroi en biais.
- **D19 (Q7) — Menuiseries.** Une baie est coupée de la même façon au droit de la cloison ; chaque morceau est
  rattaché à la pièce et déduit de sa façade.
- **D20 (Q8) — Ponts thermiques.** Angle : à la pièce qui le contient. About de refend ou de cloison : moitié
  à chacune des deux pièces qu'il sépare. Liaison plancher : linéaire de façade de chaque pièce (parois +
  baies). Les surfaces attendent la hauteur sous plafond et la hauteur des baies (coupe, carnet) : le découpage
  donne d'abord les linéaires.

### Retour utilisateur du 2026-09-22 sur le découpage

- **D22 — Espaces regroupés : ne pas découper, demander.** Un espace qui regroupe plusieurs locaux (« inclut »,
  « et », plus de 30 m de façade) reste d'un seul tenant ; l'outil produit une **demande** « découpage précis des
  zones » à adresser à l'architecte ou au maître d'ouvrage (apport de l'étude). Section « Demandes à formuler »
  de la bibliothèque.
- **À traiter plus tard — circulations vitrées.** Un vitrage qui donne sur une circulation apporte déperditions et
  apports à cette circulation : elle devient un local à part entière (système CVC, règles de renouvellement
  d'air). Aujourd'hui les circulations ne sont pas identifiées comme pièces ; leurs vitrages vont à la pièce la plus
  proche. Pas prioritaire.
- **Prochain chantier — coupes.** Lire les coupes pour fixer le zonage thermique pièce par pièce, les hauteurs
  (sous plafond, baies, allèges) et les éléments (planchers, toitures) ; les surfaces en découlent.
- **D21 — Angles : raccord des faces intérieures.** À chaque angle, les faces intérieures des deux murs sont
  prolongées jusqu'à leur point de rencontre, comme au métré manuel : l'angle rentrant allonge la face intérieure,
  l'angle sortant la raccourcit, quelle que soit la largeur que l'agent a donnée à l'angle. Règles : mur contre mur
  ou angle tout vitré seulement (un mur contre une baie s'arrête au tableau, déjà relevé) ; pas les poteaux ;
  angle entre 15° et 135° ; garde-fou : chaque face ne bouge pas de plus de 1,1 épaisseur de mur rapportée à
  l'angle, sinon le raccord est refusé et listé « relevé à revoir ». R+1 : 21 angles, 12 sortants (−1,28 m),
  4 rentrants (+0,02 m), 5 refusés (T14, T22, T59, T65, T66). Sur ce plan, les angles rentrants des dents de scie
  sont des angles mur contre baie : la longueur intérieure y était déjà juste.

- **D23 — Règle utilisateur (2026-09-22) : tout local qui donne sur l'extérieur ou sur un local non chauffé**, par
  un mur, une menuiserie ou tout autre composant, est **déperditif et source d'apports**. Conséquence : les
  circulations en façade sont des locaux à identifier comme tels dès la passe globale.
- **Angles : pas de seuil réglementaire connu.** Les bornes 15°–135° de D21 sont des tolérances géométriques du
  raccord, pas une règle thermique. Piste proposée : l'excès de longueur extérieure sur la longueur intérieure à un
  changement de direction d'angle θ vaut environ 2·e·tan(θ/2) (e : épaisseur du mur) ; il mesure l'effet
  géométrique de l'angle et tend vers 0 quand le mur est presque droit. Les jonctions hors catalogue (angles aigus
  des dents de scie, voile non isolé contre mur-rideau à l'angle sud-est) relèvent d'un calcul numérique 2D
  (NF EN ISO 10211), que l'utilisateur fait avec ubakus.

### Questions (découpage pièce par pièce, posées le 2026-09-22)

- Q6 — Découpe des parois par pièce : aux abouts de cloisons et de refends sur la face intérieure (L3, L4), ou
  au contour des pièces du Métré (nu intérieur, doublages compris) quand il existe ?
- Q7 — Menuiseries déduites de la paroi de la pièce où elles s'ouvrent ; une baie à cheval sur deux pièces est
  coupée au droit de la cloison ?
- Q8 — Ponts thermiques rattachés à une pièce : angle à la pièce qui le contient, refend partagé à moitié entre
  les deux pièces, liaison plancher sur le linéaire de façade de chaque pièce ?
