# Superposition des niveaux, coupes et élévations — cadrage

Date : 2026-09-28. Chantier devenu **prioritaire** à la question Q24 (`retours-ponts-2026-09-28-decisions.md`) :

> « Je réalise que c'est un point très stratégique en réalité. Parce que cela suppose au niveau de la
> lecture de voir à quel type de liaison nous avons à faire. Donc pouvoir voir en transparence depuis la
> vue en plan active si possible le niveau du dessus/dessous. Et aussi au niveau de plan des élévations et
> des coupes. Sujet hautement important et maintenant devient urgent à traiter. »

Répondez sous chaque question par une ligne `REPONSE : …`.

---

## 1. Existant vérifié

**La méthode est déjà écrite, rien n'est construit.** `metre-plans-decisions.md` (2026-09-14) décrit
exactement ce que vous demandez :
- §2.2 point 5 : « **Superposition automatique** du niveau N avec N−1 et N+1 (**calque fantôme** à
  l'écran) et déduction des planchers et des liaisons » ;
- §3.1 : planchers **bas**, **intermédiaires**, **hauts** déduits de la zone chauffée de chaque niveau
  comparée à celle du dessous et du dessus (porche, encorbellement, toiture-terrasse, vide sur…) ;
- §3.2 : la **règle des quatre quarts** — autour de chaque portion de ligne où un mur rencontre un plancher,
  on lit dessus / dessous × intérieur / extérieur, et le type de liaison en sort : intermédiaire, bas,
  haut, **décroché**, **balcon ou loggia** ;
- §3.3 : le catalogue des ponts qui en découlent (plancher/mur, refends, acrotère, balcons…).

**Le calage entre niveaux est déjà décidé** (Q10, 2026-09-11) : un croisement d'axes de trame cliqué sur
chaque plan, plus un second point pour la rotation — « je verrai à l'usage ».

**Ce qui existe dans le code :**
- chaque planche a une **nature** (plan, coupe, façade, plan masse), un **libellé de niveau** (R+1…), une
  **échelle** contrôlée par une cote, un **nord** et une **rotation d'affichage** ;
- le projet a une **planche de référence** (`reference_sheet_id`) ;
- une étude par planche de niveau (locaux, enveloppe, ponts), en **points PDF** de sa propre planche.

**Ce qui n'existe pas :** l'ordre des niveaux et leurs **altitudes / hauteurs**, le **calage** d'une planche
sur une autre, tout **calque fantôme**, toute **déduction** entre niveaux, toute lecture des **coupes** et
**élévations** (elles sont importées et classées, rien de plus).

## 2. Découpage proposé

| Lot | Contenu | Pourquoi dans cet ordre |
|---|---|---|
| **S1 — Niveaux** | Tableau des niveaux du projet : ordre, altitude du plancher fini, hauteur d'étage, épaisseur de plancher | La hauteur donne la longueur des ponts verticaux (angles, refends, D159) et situe les planchers |
| **S2 — Calage** | Outil « Caler sur la référence » : deux points cliqués sur la planche de référence, les mêmes sur la planche active ; l'outil en déduit décalage, rotation et contrôle d'échelle | Sans calage, un niveau ne se pose pas sur l'autre |
| **S3 — Calque fantôme** | Sur le plan actif, le niveau du dessous ou du dessus en transparence | C'est la demande directe : **voir** la liaison avant de la juger |
| **S4 — Quatre quarts** | Déduction automatique des liaisons plancher / mur (intermédiaire, bas, haut, décroché, balcon), créées d'office et jugées dans la passe des ponts avec les liaisons des terrasses (P6, D165) | Transforme ce qu'on voit en ponts chiffrés |
| **S5 — Coupes et élévations** | Voir une coupe ou une façade à côté du plan, y mesurer les hauteurs ; puis lecture assistée | Vérifie et complète S1 |

## 3. Questions

**Q25 — Que montre le calque fantôme ?**
- (a) **L'image** du plan du dessus ou du dessous, en transparence (tout ce qui est dessiné, y compris les
  balcons, auvents, décrochés — même si ce niveau n'a pas encore été étudié).
- (b) **Les contours** du niveau voisin (ses locaux et son enveloppe), en traits de couleur : plus lisible,
  mais seulement si ce niveau a déjà été analysé.
- (c) Les deux, avec un curseur d'opacité ; (b) par défaut quand le niveau voisin est étudié, (a) sinon.
REPONSE : a

**Q26 — Où et comment le choisir ?** Proposition : dans la barre « Ce qui s'affiche sur le plan », un
choix **« Voir en transparence : aucun / niveau du dessous / niveau du dessus »**, disponible à toutes les
étapes, et allumé d'office à l'étape des ponts. (a) d'accord (b) autre.
REPONSE : oui deux cases à cocher, une "Voir niveau inférieur" et une autre "Voir niveau supérieur"

**Q27 — Les hauteurs (S1) : d'où viennent-elles d'abord ?**
- (a) **Saisies** par le thermicien dans le tableau des niveaux (lues sur les coupes), l'outil les
  contrôlant plus tard par S5.
- (b) **Mesurées sur une coupe** dès S5, sans saisie : S1 attend S5.
REPONSE : Alors c'est très intéressant, en vrai j'attend à ce que la vue en coupe puisse me permettre de déterminer la hauteur sous plafond pour chacune des pièces, donc la vue en coupe doit pouvoir identifier des pièces et se les rattacher à celles de la vue en plan (automatiquement si possible), puis faire une lecture automatique de la heuteur pour chacune des pièces.

**Q28 — Coupes et élévations (S5), premier pas ?**
- (a) Une **vue côte à côte** : le plan à gauche, la coupe ou la façade choisie à droite, avec l'outil de
  mesure de hauteur ; le tracé de la coupe repéré sur le plan.
- (b) Directement une **lecture par agent** des hauteurs, allèges et linteaux sur les coupes et façades.
- (c) (a) puis (b).
REPONSE : Je sais pas si j'ai bien compris la question mais idéalement j'aimerais que sur la vue en plan on puisse, grâce à des case à cocher "Voir les coupes/élévations, voir des lignes épaisse alors permettant de cliquer dessus et affcihe directement la vue faisant référence à cette ligne, cela suggère qu'un augent à parfaitement détecté les orientations des élévations et des coupes sur le plan.

**Q29 — Et les remarques en cours (P2 ne voir que les ponts d'un local, P3 50/50 des angles, P4 ponts
courants au clic droit, P1 croquis) ?**
- (a) Elles attendent : S1 à S3 d'abord.
- (b) P2 et P3 d'abord (courts, déjà validés), puis S1 à S3.
REPONSE : a

## 3 bis. Décisions tirées des réponses (2026-09-28)

**D168 — Le calque fantôme est l'image du plan voisin (Q25 a).** Toute la planche du niveau inférieur ou
supérieur, en transparence sur le plan actif, qu'il ait été étudié ou non.

**D169 — Deux cases à cocher (Q26) :** « Voir niveau inférieur » et « Voir niveau supérieur », dans la barre
d'affichage du plan, indépendantes (les deux peuvent être allumées), disponibles à toutes les étapes. Les
voisins se déduisent de l'ordre des niveaux déjà lu sur les planches (`levelRank` : R−1, RDC, R+1…).

**D170 — Les hauteurs viennent des coupes, pièce par pièce (Q27).** Réponse : « la vue en coupe doit pouvoir
identifier des pièces et se les rattacher à celles de la vue en plan (automatiquement si possible), puis
faire une lecture automatique de la hauteur pour chacune des pièces ». S1 se réduit donc à l'ordre des
niveaux (déjà lu) ; **la hauteur sous plafond est une donnée de chaque local**, lue sur la coupe qui le
traverse (S5).

**D171 — Coupes et élévations se repèrent sur le plan (Q28).** Réponse : « sur la vue en plan, grâce à des
cases à cocher "Voir les coupes/élévations", voir des lignes épaisses permettant de cliquer dessus et
afficher directement la vue faisant référence à cette ligne ». Un agent repère sur chaque plan les traits
de coupe et les repères d'élévation (position, sens de vue, nom), et les rattache aux planches de coupe
et de façade. S5 devient : **repérage des coupes sur le plan → ouverture de la coupe au clic → pièces de la
coupe rattachées aux locaux du plan → hauteur sous plafond lue par local.**

**D172 — Ordre (Q29 a) :** S2 calage et S3 calque fantôme d'abord ; P1 à P4 et M4, M5 attendent.

**D173 — Mise en œuvre du calage (Q10 précisé).** Chaque planche porte sa correspondance avec la planche de
référence du projet : une similitude (rotation, échelle, décalage) de ses points PDF vers ceux de la
référence, calculée depuis **deux paires de points communs**. Le geste se fait **sur le plan actif, calque
fantôme allumé** : on clique un point du fantôme (croisement d'axes, angle de cage d'escalier, poteau),
puis le même point du plan actif, deux fois. Tant qu'une planche n'est pas calée, le fantôme est posé
provisoirement (mêmes centres, rapport des échelles déclarées) et un bandeau le dit. L'écart d'échelle
entre la correspondance trouvée et les échelles déclarées est affiché : au-delà de 2 %, un des deux points
est probablement mal placé.

## Résultat — S2 calage et S3 calque fantôme (2026-09-28)

- **Deux cases** dans la barre d'affichage du plan, à toutes les étapes : « Voir niveau inférieur » (calque
  **bleu**) et « Voir niveau supérieur » (calque **orange**). Les voisins sont les plans juste en dessous
  et juste au-dessus dans l'ordre des niveaux ; une case est grisée s'il n'y en a pas.
- Le voisin s'affiche en **image**, ses traits teintés et multipliés avec le plan actif (le blanc
  disparaît), sous tous les autres dessins, jamais attrapable. Seules les tuiles visibles sont chargées,
  au niveau de détail du zoom.
- **Calage** : un panneau en bas du plan dit, pour chaque calque affiché, « calé » ou « posé
  provisoirement, non calé », avec « Caler ce niveau » / « Recaler ». Quatre clics guidés — un point du
  calque, le même sur le plan, deux fois — puis l'enregistrement ; Échap abandonne. On cale la planche
  qui ne l'est pas sur celle qui l'est ; la référence ne se cale pas ; un calage fait sur une ancienne
  référence ne vaut plus. Au-delà de 2 % d'écart entre l'échelle trouvée et les échelles déclarées, le
  panneau prévient qu'un point est sans doute mal placé.
- Serveur : colonne `thermique_sheets.calage_json` (**migration 0087**), route
  `POST /sheets/{id}/calage`, service `thermique_calage.py` (similitude par deux paires, composition vers
  la référence, contrôle d'échelle).
- Tests : 8 backend (`test_thermique_calage.py`, migration comprise), 6 frontend
  (`superposition.test.tsx`, **152** au vert), typecheck, build.
- **Non éprouvé à la souris**, et le R+1 est le seul niveau étudié : pour voir le calque, il faut un
  second plan de niveau importé et classé « plan » avec son libellé de niveau.

## 4. Ce que je vérifierai à chaque lot

- Le métré du R+1 ne bouge pas tant qu'aucune déduction n'est activée (170,12 m déperditifs, 229 côtés).
- Le calage est mesurable : deux niveaux calés se superposent au trait près sur leurs cages d'escalier et
  poteaux ; l'écart résiduel est affiché.
- Rien n'est déduit en silence : chaque liaison créée d'office passe dans la passe des ponts.
