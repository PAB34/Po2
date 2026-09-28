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
REPONSE :a

**Q35 — Un local qu'aucune coupe ne traverse** (au R+1 du projet 1, quatre coupes pour une vingtaine de
locaux : beaucoup ne seront pas traversés) :
- (a) il prend la hauteur **du niveau** (la hauteur la plus fréquente des locaux traversés du même niveau),
  affichée « déduite, pas lue », modifiable ;
- (b) il reste sans hauteur tant que le thermicien ne l'a pas saisie ;
- (c) il prend celle du **local voisin traversé** le plus proche.
REPONSE : (a) mais thermicien peut bien évidemment modifier

**Q36 — Deux lectures différentes pour un même local** (deux coupes qui le traversent, faux plafond partiel,
rampant) :
- (a) la plus petite, signalée ;
- (b) la moyenne pondérée par la longueur traversée, signalée ;
- (c) aucune retenue d'office : le thermicien choisit dans la fiche.
REPONSE : b

**Q37 — Quand l'agent des coupes travaille-t-il ?**
- (a) **d'office** : dès qu'une planche est classée « coupe » ou « façade », elle entre dans la file du relais,
  après les niveaux ;
- (b) **sur demande** : un bouton « Lire les coupes et façades » pour le projet ;
- (c) d'office, mais les **traits de coupe d'un plan** sont relevés en même temps que l'étude de son niveau.
REPONSE : a

**Q38 — Les élévations n'ont pas de repère sur les plans.** Proposition : l'agent repère la **façade
concernée** (orientation écrite + nord du projet + silhouette), et la « ligne épaisse » d'une élévation est
**la façade du plan elle-même**, portant son nom (« Élévation Est ») ; un clic ouvre l'élévation. (a) d'accord
(b) autre.
REPONSE : a

**Q39 — Où s'ouvre la vue au clic ?**
- (a) **À côté du plan**, dans un panneau qui remplace la fiche de droite, cadré sur la vue ; survoler une
  pièce de la coupe allume le local sur le plan, et inversement. *Recommandé.*
- (b) À la place du plan (on revient au plan par un bouton ou Échap).
- (c) Dans une fenêtre flottante déplaçable au-dessus du plan.
REPONSE : c

**Q40 — Ordre des lots.** Proposition : **S5a + S5b** d'abord (les traits cliquables et l'ouverture de la
vue : ce que vous avez demandé en premier), puis **S5c + S5d** (hauteurs), puis **S5e** (élévations).
(a) d'accord (b) hauteurs d'abord, les traits ensuite.
REPONSE : b

**Q41 — Vérité terrain.** Avant d'écrire l'agent, je relève moi-même, à l'œil, sur les deux projets : les
traits de coupe (position, sens), les vues de chaque planche, et pour le R+1 du projet 1 la hauteur de
chaque local traversé. L'agent devra retrouver ce relevé ; son écart sera chiffré à chaque lot. (a) d'accord
(b) seulement le projet 1.
REPONSE : a

---

## 3 bis. Décisions tirées des réponses (2026-09-28)

**D178 — Une seule hauteur : sous plafond fini (Q34 a).** Du sol fini au plafond fini (sous le faux plafond
s'il y en a un). Elle sert au volume, aux surfaces de parois et à la longueur des ponts verticaux (D159).
Conséquence assumée : sous un faux plafond, la bande de mur entre faux plafond et dalle n'est pas comptée.

**D179 — Local non traversé (Q35 a).** Il prend la hauteur **du niveau** — la plus fréquente parmi les locaux
traversés du même niveau —, affichée « déduite, pas lue », et le thermicien la modifie librement.

**D180 — Deux lectures pour un local (Q36 b).** Moyenne pondérée par la longueur traversée par chaque coupe,
signalée dans la fiche avec les lectures qui la composent.

**D181 — Agent d'office (Q37 a).** Une planche classée « coupe » ou « façade » entre dans la file du relais,
après les niveaux, comme un travail d'un nouveau type.

**D182 — Élévation repérée par sa façade (Q38 a).** L'agent désigne la façade du plan (orientation écrite,
nord, silhouette) ; la ligne épaisse de l'élévation est cette façade.

**D183 — Fenêtre flottante (Q39 c).** Un clic sur un trait ouvre la vue dans une fenêtre déplaçable au-dessus
du plan, cadrée sur la vue.

**D184 — Hauteurs d'abord (Q40 b).** Ordre : **S5c + S5d** (pièces de la coupe ↔ locaux, hauteur par local),
puis **S5a + S5b** côté écran (traits cliquables, fenêtre), puis **S5e** (élévations). Le rattachement par la
position le long du trait a quand même besoin des traits et des vues : ils sont **relevés dès le premier
lot**, mais **montrés** seulement au second.

**D185 — Vérité terrain sur les deux projets (Q41 a).** Traits de coupe et vues des deux projets, et
hauteur de chaque local traversé du R+1 du projet 1, relevés à l'œil avant l'agent, dans
`docs/thermique/verite-terrain-coupes.md`.

## 3 ter. Règles de rattachement, tirées de la vérité terrain (2026-09-28)

**D186 — Une coupe se lit par projection.** L'abscisse d'une pièce de la coupe correspond à la projection
du plan sur la **droite du regard** (regarder dans le sens d = (dx, dy), c'est avoir la droite en (dy, −dx)).
Les décrochés du trait, parallèles au regard, n'ont pas de largeur dans la coupe. Entre la coupe et le plan il
ne manque qu'un **décalage**.

**D187 — Deux calages indépendants.** Le décalage vient d'abord des **numéros de programme** communs
(6.1.2, 4.3.4 : les textes sont abrégés, pas les numéros), sinon du **meilleur recouvrement**. Quand les deux
existent et diffèrent de plus de 30 cm, la fiche le dit.

**D188 — Trait dans l'épaisseur d'un mur.** Un local à moins de **15 cm** du trait est candidat. Chaque
pièce de la coupe va au local qui porte **son numéro** ; à défaut, au local qu'elle **épouse** (recouvrement
rapporté à la plus grande des deux étendues), pas à celui qu'elle recouvre le plus : une circulation qui
longe tout le trait ne prend pas la place des bureaux.

**D189 — L'étage se reconnaît.** Une coupe traverse tous les niveaux : on retient l'étage dont les pièces
ressemblent le plus aux locaux du plan (numéros communs, puis recouvrement). Un volume posé plus bas qui
monte à travers l'étage est une **double hauteur** : signalée, sans hauteur inventée.

**Sol et plafond** se donnent par le **nom d'une ligne de niveau** de la coupe (H10, H11 : la cote écrite
fait foi) ou par une position mesurée, calée sur les lignes de niveau connues. Une hauteur **écrite** sur la
coupe l'emporte sur la mesure.

**Résultat sur les données réelles (projet 1, R+1)** — `thermique_coupes.py`, 9 tests :
- coupe A : **8 locaux sur 8**, par les noms comme sans eux ; le croisement géométrique seul en trouvait 2 ;
  bon étage parmi trois ; 2,88 m partout ; les deux calages concordent à 11 cm ;
- coupe C : formation et lecture confort à 2,88 m, atrium signalé en double hauteur ;
- coupe D : aucune pièce rattachée, dit comme tel.

## 4. Ce que je vérifierai à chaque lot

- Le métré du R+1 ne bouge pas tant qu'aucune hauteur n'est validée (170,12 m déperditifs, 229 côtés).
- Chaque trait de coupe et chaque vue relevés par l'agent sont comparés à la vérité terrain (Q41).
- Rien n'est pris en silence : une hauteur lue est **proposée**, le thermicien la valide dans la fiche.
