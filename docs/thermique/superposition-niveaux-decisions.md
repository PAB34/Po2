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

**Q26 — Où et comment le choisir ?** Proposition : dans la barre « Ce qui s'affiche sur le plan », un
choix **« Voir en transparence : aucun / niveau du dessous / niveau du dessus »**, disponible à toutes les
étapes, et allumé d'office à l'étape des ponts. (a) d'accord (b) autre.

**Q27 — Les hauteurs (S1) : d'où viennent-elles d'abord ?**
- (a) **Saisies** par le thermicien dans le tableau des niveaux (lues sur les coupes), l'outil les
  contrôlant plus tard par S5.
- (b) **Mesurées sur une coupe** dès S5, sans saisie : S1 attend S5.

**Q28 — Coupes et élévations (S5), premier pas ?**
- (a) Une **vue côte à côte** : le plan à gauche, la coupe ou la façade choisie à droite, avec l'outil de
  mesure de hauteur ; le tracé de la coupe repéré sur le plan.
- (b) Directement une **lecture par agent** des hauteurs, allèges et linteaux sur les coupes et façades.
- (c) (a) puis (b).

**Q29 — Et les remarques en cours (P2 ne voir que les ponts d'un local, P3 50/50 des angles, P4 ponts
courants au clic droit, P1 croquis) ?**
- (a) Elles attendent : S1 à S3 d'abord.
- (b) P2 et P3 d'abord (courts, déjà validés), puis S1 à S3.

## 4. Ce que je vérifierai à chaque lot

- Le métré du R+1 ne bouge pas tant qu'aucune déduction n'est activée (170,12 m déperditifs, 229 côtés).
- Le calage est mesurable : deux niveaux calés se superposent au trait près sur leurs cages d'escalier et
  poteaux ; l'écart résiduel est affiché.
- Rien n'est déduit en silence : chaque liaison créée d'office passe dans la passe des ponts.
