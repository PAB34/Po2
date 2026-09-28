# S5 — Coupes et élévations : repères sur le plan, hauteur par local — décisions et questions

Date : 2026-09-28. Suite de `superposition-niveaux-decisions.md` (D170, D171, D177). Choisi par l'utilisateur
en reprise de session (« S5 coupes/élévations »). Répondez sous chaque question par une ligne `REPONSE : …`.

Rappel de ce que vous avez demandé :
- **D171 (Q28)** : sur la vue en plan, une case « Voir les coupes/élévations » montre des **lignes épaisses
  cliquables** ; un clic **affiche la vue** qui correspond à la ligne ; un agent repère ces lignes et leur sens ;
- **D170 (Q27)** : la coupe **identifie ses pièces**, les **rattache aux locaux du plan** (automatiquement si
  possible) et **lit la hauteur de chaque pièce** ;
- **D177 (Q33)** : la hauteur des menuiseries se lit **sur les élévations**.

---

## 1. Existant vérifié (code et planches réelles)

**Dans le code :**
- une planche = **une page** d'un PDF importé, avec une nature (`plan`, `coupe`, `facade`, `plan_masse`,
  `autre`) devinée depuis le nom du fichier (« COUPE », « ELEV », « FACADE »), un libellé de niveau, une
  échelle, une rotation d'affichage, un nord et, depuis S2, un calage (`calage_json`) ;
- **rien ne lit une coupe ni une façade** : elles sont importées et classées, c'est tout. La fiche d'un local
  affiche « hauteur sous plafond (coupes) » dans `a_completer` ; les ponts verticaux attendent une hauteur
  d'étage (D159) ;
- les agents tournent **sur votre poste** par le relais (`scripts/relais_thermique.py`) : le site tient une
  file de travaux (`thermique_travaux`), le relais la vide en lançant `run_etude_niveau.py`. Cette file ne
  connaît qu'**un seul type de travail : l'étude d'un niveau**. Deux agents existent (`thermicien-plan`,
  `thermicien-enveloppe`) ; `thermicien-plan` ne doit pas être modifié → un **agent nouveau** sera créé.

**Sur les planches des deux projets d'exemple (lues à l'œil, 2026-09-28) :**

| | Projet 1 — Frontignan (**le R+1 étudié**, 1/100) | Projet 2 — Balaruc (1/50) |
|---|---|---|
| Repère de coupe sur le plan | **deux drapeaux gris** en bord de plan (A, B, C, D), **sans trait** entre eux | **trait rouge continu**, flèches aux deux bouts, **avec décrochés** (C et D) |
| Planches de coupe | PC10 = coupes A et B, PC11 = C et D : **2 coupes par page**, **tournées d'un quart de tour** | C01 = CC, DD, AA ; C02 = BB, EE, FF : **3 coupes par page** |
| Repère de niveau sur la coupe | cotes relatives ±0,00 / +4,16 / +8,00 / +11,84 / +12,96 / +14,72 | cotes NGF (+2,01 / +6,38 / +10,80 NGF) |
| Hauteurs écrites | presque aucune : à **mesurer** entre dalles | beaucoup de cotes verticales (3,55 ; 4,01 ; 2,70…) et « faux plafond » |
| Nom des pièces dans la coupe | **numéros du programme** (6.1.2 Bureau assist, 6.1.6 Salle de réunion…), **les mêmes que sur le plan** | noms en clair (Salle de pause, Couloir, Espace BD…), **les mêmes que sur le plan** |
| Axes de trame dans la coupe | **oui** (1 à 16, A à R, en bord de coupe) | oui (bulles JD, axes) |
| Repère d'élévation sur le plan | **aucun** | **aucun** (et pas de planche d'élévation) |
| Planches d'élévation | PC08 Est-Nord, PC09 Sud-Ouest (2 façades par page) | — |

Ce qu'on en tire :
1. **Une planche contient plusieurs vues.** Il faut une notion de **vue** (une coupe ou une façade, son nom,
   son cadre dans la page), distincte de la planche. Elle n'existe pas.
2. **Le trait de coupe n'est pas toujours dessiné** : au projet 1, il se reconstitue entre les deux drapeaux
   de même lettre. Au projet 2, il a des décrochés : c'est une ligne brisée, pas un segment.
3. **Trois moyens indépendants** de rattacher une pièce de la coupe à un local du plan : sa **position le long
   du trait** (le trait traverse les locaux dans un ordre et sur des longueurs connues à l'échelle), son
   **nom ou numéro** (identique sur les deux planches), et les **axes de trame** communs. Leur accord confirme
   le rattachement ; leur désaccord désigne une erreur (la leçon du projet : deux lectures indépendantes).
4. **Les élévations ne sont pas repérées sur les plans.** Elles se rattachent par leur **orientation** (le nom
   « Élévation Est », le nord du projet) et leur **silhouette**. La « ligne épaisse cliquable » d'une élévation
   serait donc **la façade elle-même**, repérée par l'agent, pas un trait dessiné par l'architecte.
5. Une coupe traverse **tous les niveaux** : une même lecture donne les hauteurs du RDC, du R+1, du R+2…

## 2. Découpage proposé

| Lot | Contenu | Vérifié par |
|---|---|---|
| **S5a — Vues et repères** | Nouvel agent `thermicien-coupe`, lancé par le relais. Sur chaque planche de coupe/façade : les **vues** (nom, cadre, sens). Sur chaque plan : les **traits de coupe** (lettre, ligne brisée, sens de vue). Rattachement trait ↔ vue **par le nom** (A ↔ « COUPE A », C ↔ « COUPE CC »). | Vérité terrain que je relève moi-même sur les deux projets : 4 + 6 traits, 4 + 6 vues |
| **S5b — Au clic** | Case « Voir les coupes/élévations » ; traits épais cliquables ; le clic ouvre la vue, cadrée sur elle, **à côté du plan** (Q39) | Tests écran ; pas de recette à la souris |
| **S5c — Pièces de la coupe ↔ locaux** | L'agent lit, dans la coupe, chaque pièce traversée : nom/numéro, bornes le long de la coupe, niveau. Le serveur rattache par la position le long du trait **et** par le nom ; il signale les désaccords | R+1 du projet 1 : taux de rattachement et désaccords mesurés |
| **S5d — Hauteur par local** | Cotes de niveau lues (±0,00, +4,16… ou NGF), **hauteur mesurée** entre le sol fini et la sous-face (dalle ou faux plafond), à l'échelle de la vue. Hauteur **proposée** dans la fiche du local, validée par le thermicien. Alimente les ponts verticaux (D159) | Hauteurs du R+1 comparées à celles que je lis à l'œil |
| **S5e — Élévations** | Façades repérées sur le plan (Q38) ; menuiseries de l'élévation rattachées à celles du plan ; **hauteur des menuiseries** (D177) et repère complet M5 | Projet 1, PC08 et PC09 |

## 3. Questions

**Q34 — Quelle hauteur retenir pour un local ?** La coupe en donne plusieurs.
- (a) **Sous plafond fini** (sous le faux plafond s'il y en a un) : c'est le volume chauffé et ventilé.
- (b) **Sous dalle** (du sol fini à la sous-face de la dalle haute) : c'est la hauteur des parois qui
  déperdent, cohérente avec les dimensions intérieures (ψi).
- (c) **Les deux**, chacune pour son usage : sous dalle pour les surfaces de parois et les ponts verticaux,
  sous plafond fini pour le volume. *Recommandé.*
REPONSE :

**Q35 — Un local qu'aucune coupe ne traverse** (au R+1 du projet 1, quatre coupes pour une vingtaine de
locaux : beaucoup ne seront pas traversés) :
- (a) il prend la hauteur **du niveau** (la hauteur la plus fréquente des locaux traversés du même niveau),
  affichée « déduite, pas lue », modifiable ;
- (b) il reste sans hauteur tant que le thermicien ne l'a pas saisie ;
- (c) il prend celle du **local voisin traversé** le plus proche.
REPONSE :

**Q36 — Deux lectures différentes pour un même local** (deux coupes qui le traversent, faux plafond partiel,
rampant) :
- (a) la plus petite, signalée ;
- (b) la moyenne pondérée par la longueur traversée, signalée ;
- (c) aucune retenue d'office : le thermicien choisit dans la fiche.
REPONSE :

**Q37 — Quand l'agent des coupes travaille-t-il ?**
- (a) **d'office** : dès qu'une planche est classée « coupe » ou « façade », elle entre dans la file du relais,
  après les niveaux ;
- (b) **sur demande** : un bouton « Lire les coupes et façades » pour le projet ;
- (c) d'office, mais les **traits de coupe d'un plan** sont relevés en même temps que l'étude de son niveau.
REPONSE :

**Q38 — Les élévations n'ont pas de repère sur les plans.** Proposition : l'agent repère la **façade
concernée** (orientation écrite + nord du projet + silhouette), et la « ligne épaisse » d'une élévation est
**la façade du plan elle-même**, portant son nom (« Élévation Est ») ; un clic ouvre l'élévation. (a) d'accord
(b) autre.
REPONSE :

**Q39 — Où s'ouvre la vue au clic ?**
- (a) **À côté du plan**, dans un panneau qui remplace la fiche de droite, cadré sur la vue ; survoler une
  pièce de la coupe allume le local sur le plan, et inversement. *Recommandé.*
- (b) À la place du plan (on revient au plan par un bouton ou Échap).
- (c) Dans une fenêtre flottante déplaçable au-dessus du plan.
REPONSE :

**Q40 — Ordre des lots.** Proposition : **S5a + S5b** d'abord (les traits cliquables et l'ouverture de la
vue : ce que vous avez demandé en premier), puis **S5c + S5d** (hauteurs), puis **S5e** (élévations).
(a) d'accord (b) hauteurs d'abord, les traits ensuite.
REPONSE :

**Q41 — Vérité terrain.** Avant d'écrire l'agent, je relève moi-même, à l'œil, sur les deux projets : les
traits de coupe (position, sens), les vues de chaque planche, et pour le R+1 du projet 1 la hauteur de
chaque local traversé. L'agent devra retrouver ce relevé ; son écart sera chiffré à chaque lot. (a) d'accord
(b) seulement le projet 1.
REPONSE :

---

## 4. Ce que je vérifierai à chaque lot

- Le métré du R+1 ne bouge pas tant qu'aucune hauteur n'est validée (170,12 m déperditifs, 229 côtés).
- Chaque trait de coupe et chaque vue relevés par l'agent sont comparés à la vérité terrain (Q41).
- Rien n'est pris en silence : une hauteur lue est **proposée**, le thermicien la valide dans la fiche.
