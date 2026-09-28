# Retours d'usage du 2026-09-28 — décisions et questions

Date : 2026-09-28. Retours de l'utilisateur après manipulation de l'outil sur le R+1, regroupés en sept
remarques (A à G). Mesures faites sur le vrai R+1 (`banc.db`), scripts dans le bloc-notes de session.

## Défaut corrigé d'abord — l'erreur 422 à l'enregistrement des ponts

**Constat.** Le serveur refusait tout enregistrement de plus de **50 gestes** (`EtudeRemodelage`,
`max_length=50`). Juger 61 ponts d'un coup (77 − 16) dépassait le plafond : tout le lot était refusé,
rien n'était enregistré, et l'écran n'affichait que « Erreur 422 ».
**Corrigé** (commit `1755b92e`, non poussé) : plafond à 2 000, message explicite si un 422 revient
(« vos modifications sont toujours dans cet onglet »). Les gestes non enregistrés vivent dans l'onglet :
tant qu'il n'est pas rechargé, un nouvel « Enregistrer » après déploiement les sauve.

---

## A — « Dans une étape, je ne dois voir que les objets de cette catégorie et ses actions » — FAIT

> « quand je suis dans l'une des sections […] je ne dois voir que les objets/composants concernés par la
> catégorie dans laquelle je suis et les actions prévues à cet effet »

**Existant.** Les étapes réglaient les calques du *reste du niveau*, mais le local ouvert montrait
toujours tout (D83) : cotes, murs et ponts à toutes les étapes, et la fiche du local avec la liste de tous
ses éléments, ponts compris.

**D155 — Chaque étape borne ce qui existe à l'écran, local ouvert compris** (`vueDeLEtape`, `parcours.ts`) :

| Étape | Plan | Clic sur le plan | Panneau |
|---|---|---|---|
| Locaux | contours, cotes, surfaces | locaux et côtés | fiche du local : nature, côtés, validation, édition |
| Parois et menuiseries | murs, menuiseries, cotes | murs et menuiseries | le nom du local et **ses parois seules** (ponts exclus) |
| Ponts thermiques | **les ponts seuls** | **les ponts seuls** | la passe sur les ponts |
| Planche, analyse, hauteurs | inchangé | inchangé | inchangé |

À l'étape des locaux, « Valider ce local » bloqué par des parois douteuses propose **« Vérifier ses
parois → »**, qui ouvre l'étape des parois sur le même local.

## B — « J'ai du mal à sélectionner les ponts, ils se confondent avec la limite de la pièce » — FAIT

**Existant.** Le local ouvert était tracé d'un trait de 5 px coloré, plus ses limites colorées côté par
côté ; les pastilles de ponts (5 px de rayon) posées sur cette limite s'y noyaient. Et au clic, le côté,
le mur ou le local pouvaient l'emporter sur le pont.

**D156 — À l'étape des ponts, le pont est seul.** Le zonage s'estompe (trait fin pointillé, remplissage
presque nul, plus de limites colorées) aux étapes des parois et des ponts ; le local ouvert garde un trait
fin plein pour rester repérable. À l'étape des ponts, le clic ne vise **que** les ponts, dans un rayon
porté de 8 à **18 px**, et un clic dans le vide ne fait plus perdre le pont en cours.

---

## C — Créer un pont manquant par clic droit

> « pouvoir créer des ponts thermiques manquants, déjà existants sur le plan ou nouveaux, par un clic
> droit, attention des fois il est derrière le calque de la pièce »

**Existant.** Le geste « ajouter un élément ou un pont absent » a été reporté en F4 (**D104**). Un pont
est un élément du relevé, repéré par son tronçon et son abscisse ; le serveur n'a pas d'opération
« ajouter ». Le « derrière le calque de la pièce » est en partie réglé par D156 (zonage estompé).

**Piste.** Clic droit sur le plan à l'étape des ponts → « Ajouter un pont ici » (proposé même si un local
est sous le curseur) → choix du type → le serveur projette le point sur le tronçon le plus proche et
insère l'élément dans le relevé, avec la mention « ajouté par le thermicien ».

**Q8 — Un pont peut-il être ailleurs que sur l'enveloppe relevée ?** Exemple : la liaison d'une terrasse
ou d'un plancher, à l'intérieur du bâtiment.
- (a) Non, pour commencer : un pont ajouté se pose toujours sur l'enveloppe, au tronçon le plus proche.
- (b) Oui : un pont peut être posé n'importe où, rattaché au local sous le curseur, sans tronçon.
REPONSE : Délicat, normalement c'est toujours à l'intersection de deux tronçons mais faut il que les tronçons soient biens existants. Donc c'est le mélange de a et de b mais pllutot b puisque ce sera l'utilisateur qui le définiera.

**Q9 — Quels types proposer à la création ?** Aujourd'hui trois : angle sortant, angle rentrant, about de
refend. À ajouter selon vous : liaison plancher intermédiaire, plancher bas, toiture, balcon ou terrasse,
appui, linteau ou tableau de baie, autre (à modéliser) ?
REPONSE : Il faut travailler à l'extraction de tous les ponts thermiques et autres éléments qui pourraient nous servir des normes faisant références aux éléments qui constituent une bibliothèque en vu de la réalisation des déperditions et apports thermiques "C:\Users\pa.borja\Documents\Po2\Thermique\NORMES", ceci nous permettra d'obtenir une bibliothèque Dans laquelle puiser ces ponts thermique en vue de réaliser la bibliothèque projet.

## D — Réattribuer un pont mal reconnu, et le « à modéliser »

> « des fois le pont thermique n'existera pas en bibliothèque […], il faut une option à modéliser. De plus
> des fois le pont découvert par l'outil n'est pas le bon, il faut pouvoir le réattribuer »

**Existant.** Le serveur sait déjà corriger le **type** et le **composant** d'un élément
(`element_corriger`), ponts compris ; seul l'écran des ponts ne le propose pas (Garder / Écarter). **Aucune
valeur ψ n'existe encore dans l'outil** : un pont est aujourd'hui compté, pas valorisé. La bibliothèque du
projet (L1, L2) porte des parois et menuiseries, pas de ponts.

**Piste.** Troisième geste dans la passe des ponts : « Réattribuer » → type, puis référence de pont.
Un pont sans référence dans le catalogue réglementaire reçoit l'état **« à modéliser »** : il est compté,
signalé dans la fiche et l'export, et attend une valeur ψ calculée à part.

**Q10 — D'où viennent les références de ponts ?**
- (a) Un catalogue de ponts **dans la bibliothèque du projet**, comme les parois (L1, L2) : le thermicien
  crée ses ponts types (nom, ψ, source), réutilisables.
Il faut travailler à l'extraction de tous les ponts thermiques et autres éléments qui pourraient nous servir des normes faisant références aux éléments qui constituent une bibliothèque en vu de la réalisation des déperditions et apports thermiques "C:\Users\pa.borja\Documents\Po2\Thermique\NORMES"
- (b) Le **catalogue réglementaire Th-Bât** (fascicule ponts thermiques) intégré à l'outil, puis la
  bibliothèque du projet pour le reste.
C'est pas la bonne réglementation nous devons précisemment travailler sur les normes liées aux déperditions et apports thermiques en vue de fournir aux entreprises de travaux CVC une étude parfaite pour leur travail de dimensionnement provenant de "C:\Users\pa.borja\Documents\Po2\Thermique\NORMES" et si besoin d enouvelles normes tu me dis je te les fournirai
- (c) Seulement l'état « à modéliser » pour l'instant, sans aucune valeur ψ dans l'outil.
Il faut que les valeurs puisses s'affiher donc il faut ces valeurs

## E — Minorer les angles de moins de 90°

> « tout semble avoir été calculé sur des angles à 90°, mais lorsque l'angle est inférieur il faut minorer
> sa valeur déperditive »

**Mesuré sur le R+1** (changement de direction entre les deux tronçons qui se rencontrent ; 90° = angle
droit, mesure indicative) : sur les **64 angles**, environ **25 sont proches de l'angle droit** (75 à 95°),
**27 sont très ouverts** (24 à 55° de changement de direction, soit des angles intérieurs de 125 à 155°),
**9 dépassent 100°**, et **5 sont à 0° environ** — des angles du tracé qui n'en sont pas. Le relevé ne
garde aujourd'hui aucun angle sur les ponts : seuls 16 raccords de faces en portent un.

**Piste.** Porter l'angle mesuré sur chaque pont d'angle, l'afficher dans la passe, et appliquer un
coefficient de minoration au moment de la valorisation ψ (voir Q10). Les angles à 0° deviennent des
candidats « à écarter » signalés d'office.

**Q11 — Quelle règle de minoration ?**
- (a) Proportionnelle au changement de direction : ψ(θ) = ψ₉₀ × θ / 90.
- (b) Les valeurs du catalogue réglementaire à 90° et à 135°, interpolées entre les deux.
- (c) Une autre règle que vous me donnez (référence normative à citer dans le fichier).
REPONSE : Il faut ce fier aux normes provenant de "C:\Users\pa.borja\Documents\Po2\Thermique\NORMES", si aucune précision dan sla norme alors utiliser la proportionnalité (peut être le plus simple et cohérent)

**Q12 — Et un angle plus fermé que 90° (changement de direction > 90°) ?** Majoré, plafonné à ψ₉₀,
ou signalé à vérifier ?
Tout dépend du type de pont thermique mais normalement cela entre dans la même problématique que la question précédente non ?

## F — Les terrasses sont des locaux extérieurs

> « les terrasses extérieures ne sont pas détectées comme un local extérieur. Car une terrasse a un
> plancher qui crée une liaison thermique avec ses locaux adjacents. »

**Existant.** Sujet 5 de `reprise-sujets-ouverts.md`. Quatre natures aujourd'hui (chauffé, circulation,
non chauffé, gaine technique), aucune pour l'extérieur. On peut déjà dessiner un local sur une terrasse
(clic droit « Créer un local ici »), mais pas lui donner une nature qui le sorte de la surface chauffée.

**Piste.** Une cinquième nature **`terrasse`** (ou `exterieur`) : hors surface chauffée, et ses côtés
communs avec un local chauffé deviennent **déperditifs** et portent une **liaison terrasse** (pont linéique
le long du côté commun).

**Q13 — Terrasse seulement, ou toute pièce extérieure ?** (balcon, loggia, coursive, patio…) : une nature
« terrasse » ou une nature « extérieur » plus large ?
REPONSE : toute pièce extérieures comme tu les as cités entre autres
**Q14 — Le pont linéique le long du côté commun est-il créé automatiquement** dès qu'un local est classé
terrasse (à juger ensuite dans la passe des ponts), ou ajouté à la main ?
REPONSE : créer automatiquement
**Q15 — L'agent doit-il apprendre à reconnaître les terrasses** dès l'analyse (consigne ajoutée à
l'agent de lecture des locaux, dans le code — pas `.claude/agents/thermicien-plan.md`) ?
REPONSE : Oui dès l'analyse

## G — Coller au plan réel : vides, longueurs, points des éléments, agent de liaison

> « il peut y avoir des vides entre certains tronçons. Ou encore la longueur de la reconstruction
> géométrique n'est pas exactement celle du plan. J'ai peur que cela fausse les calculs thermiques. »

**Mesuré sur le R+1 — ce qui fausse et ce qui ne fausse pas :**
1. **Le relevé est continu** : aucun vide ni recouvrement le long des 89 tronçons (211,7 m).
2. **Les vides que l'on voit sont dans le dessin** : les angles et abouts sont relevés avec une emprise
   (**14,13 m** au total) mais **jamais dessinés**. Une fois cette emprise ajoutée, 62 tronçons sur 89
   tombent à moins de 2 cm du relevé, 74 à moins de 10 cm. Aux jonctions, 45 sur 82 montrent un écart,
   dont 6 de plus de 30 cm (jusqu'à 2,6 m, contour intérieur U, locaux 6.1, sanitaires, palier ascenseur).
3. **Les longueurs déperditives ne viennent pas du dessin** mais des **contours des locaux** (nu
   intérieur) : c'est pourquoi le recadrage compte tant.
4. **Le vrai risque est l'affectation des parois aux côtés.** Globalement les longueurs se tiennent
   (163,63 m de côtés déperditifs, 164,19 m de parois rattachées, 0,3 %), mais **8 côtés déperditifs
   s'écartent de 50 cm ou plus** (jusqu'à 2 m) de leurs parois et **10 côtés déperditifs n'ont aucune
   paroi rattachée** : leur composition — donc leur U — est inconnue du calcul.

**Pistes, par ordre de gain :**
- **G1 — Un contrôle visible par côté** : dans la fiche, chaque côté déperditif affiche l'écart entre sa
  longueur et celle de ses parois, et une alerte « aucune paroi rattachée ». Peu coûteux, rend le risque
  visible avant tout calcul.
REPONSE : OK
- **G2 — Dessiner l'emprise des angles et abouts** : les « vides » visuels aux coins disparaissent.
  Affichage seul (D99), le calcul ne change pas.
REPONSE : OK
- **G3 — Déplacer les bornes d'un élément sur le plan** (reporté par D104) : poignées aux deux extrémités
  de l'élément désigné, glissées le long de son tronçon ; le voisin suit, pour qu'aucun vide ne se crée.
REPONSE : OK
- **G4 — Un agent de liaison** : après le recadrage d'un local, un agent Claude Code (sur le poste, sans
  clé d'API, comme les deux autres) relit le contour recadré et le relevé, et **propose** les rattachements
  paroi ↔ côté, les bornes à déplacer et les vides à combler, **comme des gestes à valider**, jamais
  appliqués en silence.
REPONSE : OK

**Q16 — Dans quel ordre ?** Proposition : G1, puis G2, puis G3, puis G4 (G4 s'appuie sur G1 pour dire ce
qui cloche, et sur G3 pour exprimer ses propositions). 
REPONSE : Ok de G1 à G4
**Q17 — Déplacer une borne d'élément : le voisin suit-il ?**
- (a) Oui, la borne est partagée : allonger un mur raccourcit son voisin (aucun vide possible).
- (b) Non, chaque élément bouge seul : un vide ou un recouvrement peut apparaître, signalé en alerte.
REPONSE : Ok (a)
**Q18 — L'agent de liaison se déclenche quand ?**
- (a) À la validation de chaque local (il relit ce local seul).
- (b) Sur demande, pour le niveau entier, une fois les recadrages faits.
- (c) Les deux.
REPONSE : OK (b)
---

## Décisions tirées des réponses (2026-09-28)

**D157 — Un pont ajouté est posé par le thermicien, là où il le dit (Q8 : « plutôt b »).** Il est
d'ordinaire à l'intersection de deux tronçons, mais ceux-ci peuvent manquer ou être faux : le point posé
fait foi, rattaché au local sous le curseur ; le tronçon le plus proche n'est qu'une proposition.

**D158 — La référence des ponts, ce sont les normes du dossier `Thermique/NORMES`, pas Th-Bât (Q9, Q10).**
Objectif : une étude de déperditions et d'apports utilisable par une entreprise CVC pour dimensionner.
Premier fruit : le **tableau C.2 de la NF EN ISO 14683** transcrit dans
`saas/backend/app/data/thermique_ponts_iso14683.json` — **76 ponts types** (toitures R1–R12, balcons
B1–B4, angles C1–C8, planchers intermédiaires IF1–IF8, murs intérieurs IW1–IW6, planchers bas GF1–GF16,
poteaux P1–P4, baies W1–W18), chacun avec ψe, ψoi et ψi et la page de son croquis. Ces valeurs
**s'affichent** (Q10 c : « il faut ces valeurs »). La bibliothèque du projet y puisera ; ce qui n'y est
pas devient « à modéliser » (calcul selon la NF EN ISO 10211).

**D159 — ψi, dimensions intérieures.** Les longueurs de l'outil sont prises au nu intérieur ; la NF EN
12831-1 (annexe C) impose alors ψ rapporté aux dimensions intérieures. **Un angle ou un about de refend
est vertical : sa longueur est la hauteur d'étage**, d'où la dépendance à l'étape « Hauteurs ».

**D160 — Angles hors 90° : la norme d'abord, sinon la proportionnalité (Q11, Q12).** Aucune des normes du
dossier ne traite de minoration d'angle (recherche texte sur 14683, 12831-1, 12831-2, 10211 ; le tableau
C.2 ne dessine que des angles droits). Règle retenue : ψ(θ) = ψ₉₀ × θ / 90, θ étant le changement de
direction ; la même règle vaut au-delà de 90° (Q12 : « même problématique »), avec un signalement au-delà
de 135° où le tracé est suspect.

**D161 — Une nature « extérieur » pour toute pièce extérieure** — terrasse, balcon, loggia, coursive,
patio (Q13). Le pont linéique le long d'un côté commun avec un local chauffé est **créé automatiquement**
(Q14), puis jugé dans la passe des ponts. L'agent de lecture apprend à les reconnaître **dès l'analyse**
(Q15).

**D162 — Coller au plan : G1, G2, G3, G4 dans cet ordre (Q16).** Déplacer une borne **entraîne le voisin**
(Q17 a). L'agent de liaison se lance **sur demande, pour le niveau entier**, une fois les recadrages faits
(Q18 b).

**Point d'attention — licence.** Le PDF de la 14683 porte la mention « CSTB Editions pour DEXO — licence
nominative ». Reprendre ses valeurs dans un outil utilisé par d'autres bureaux d'études relève des
conditions de licence AFNOR/CSTB : à vérifier avant d'ouvrir la bibliothèque à des tiers.

**Normes à demander à l'utilisateur.** L'annexe nationale française de la NF EN 12831-1 (températures
extérieures de base par département, températures intérieures, valeurs nationales par défaut), si elle
existe sous forme de document séparé : la norme elle-même renvoie ces valeurs au niveau national.

---

## Ordre de travail proposé

1. Pousser le lot en attente (422, sujet 2, validation, A et B) quand vous le décidez.
2. **G1** (le contrôle par côté) : il rend visible le risque sur le calcul dès maintenant.
3. **D** (réattribuer un pont, état « à modéliser ») : le serveur sait déjà faire, seul l'écran manque.
4. **C** (créer un pont au clic droit), selon Q8 et Q9.
5. **E** (angle porté par chaque pont, minoration) puis **Q10** (valeurs ψ).
6. **F** (nature terrasse), **G2**, **G3**, **G4**.

## Résultat — E, l'angle réel et la minoration de ψ (2026-09-28)

- **Mesure** (`thermique_angles.py`) : l'angle d'un angle sortant ou rentrant est le changement de
  direction entre son tronçon et celui qui le prolonge, à l'extrémité la plus proche (moins d'un mètre).
  La façade se referme en boucle ; un tronçon lu depuis la face intérieure ne se prolonge que là où il
  touche le suivant. Un pont posé à la main ne se mesure pas : son angle se saisit.
- **Règle D160** : ψ retenu = ψi × θ / 90. Sans angle connu, 90° (le catalogue). Alertes sous 15° (« ce
  n'est sans doute pas un angle ») et au-delà de 135° (« tracé suspect »).
- **Écran** : la fiche du pont affiche « Angle : 45° (mesuré sur le tracé) → ψ × 0,50 » et, s'il a un pont
  type, « ψ retenu : 0,15 × 0,50 = 0,08 W/(m·K) ». « Réattribuer… » propose l'angle, modifiable : le
  changer le **saisit** (`angle_deg`, corrigeable sur un angle seulement, entre 0 et 180), et il l'emporte
  sur la mesure.
- Chaque liaison porte `angle_mesure_deg`, `angle_deg`, `angle_saisi`, `coefficient_angle`,
  `reference_pont` (affichage ; aucun métré ne lit `liaisons`).
- **Mesuré sur le vrai R+1** : métré inchangé (227, 222, 170,12 m, 289, 77). Sur les 64 angles : 23 droits
  (75–105°), 26 ouverts (15–75°), 3 entre 105 et 135°, **5 au-delà de 135° signalés**, 7 non mesurables
  (90° retenu). Somme des coefficients : **54,4** au lieu de 64 — les angles du niveau pèsent environ
  15 % de moins qu'à angle droit partout.
- Tests : 8 backend (`test_thermique_angles.py`, **130** tests thermiques ciblés au vert), 5 frontend
  (**136** au vert), typecheck, build.

## Résultat — C, créer un pont au clic droit (2026-09-28)

- À l'étape des ponts, le clic droit propose **« Ajouter un pont ici : angle sortant / angle rentrant /
  about de refend (mur intérieur) »**, y compris sur un local (le zonage est estompé, D156). Rien d'autre
  n'est proposé à cette étape (D155).
- **Le point posé fait foi (D157)** : il est gardé dans le relevé (`point_feuille`), le pont se dessine
  exactement là, et son local est **celui qui contient le point**, recalculé à chaque reconstruction
  (sinon le plus proche à moins d'un mètre). Le tronçon le plus proche ne donne que l'identité du pont
  dans le relevé — deux ponts posés au même endroit restent deux éléments.
- Le pont posé est **jugé d'emblée** et **désigné** : la passe des ponts s'ouvre dessus, avec
  « Réattribuer… » pour lui donner son pont type. Il s'écarte et se réattribue comme les autres. Sa fiche
  dit « Pont posé par vous sur le plan ».
- Seul le serveur sait sur quel tronçon tombe un pont : l'ajout déclenche donc un **recalcul d'aperçu**
  (quelques secondes), rien n'est enregistré avant « Enregistrer ». Annuler / rétablir un geste relance
  cet aperçu dès qu'un ajout est dans la liste.
- **Mesuré sur le vrai R+1** : sans ajout, 227 éléments, 222 côtés, 170,12 m, 289 formes, 77 liaisons —
  inchangés. Un angle posé au milieu de « 6.1.6 salle de réunion » : 228 éléments, 78 liaisons, il est
  rattaché à ce local et y compte 1 angle sortant ; le reste du métré est identique.
- Tests : 5 backend (**122** tests thermiques ciblés au vert), 2 frontend (**131** au vert), typecheck,
  build. Aucune recette à la souris.

## Résultat — D, réattribuer un pont (2026-09-28)

- Troisième geste dans la passe des ponts : **« Réattribuer… »** → type de liaison (angle sortant,
  rentrant, about de refend), puis **pont type** NF EN ISO 14683 — ceux de la famille d'abord (C1–C4,
  C5–C8 ou IW1–IW6), toutes les autres familles ensuite —, ou **« À modéliser — absent du catalogue »**.
  Le croquis de référence (page du PDF) et les trois ψ s'affichent au choix. Le geste vaut jugement.
- La fiche du pont affiche le pont type retenu et son **ψi**, ou « À modéliser : ψ à calculer
  (NF EN ISO 10211) ».
- Serveur : champ corrigeable `reference_pont` (code du catalogue ou `a_modeliser`), refusé sur un mur
  et pour un code inconnu ; route `GET /thermique/ponts/catalogue` ; service
  `thermique_ponts_catalogue.py`. La référence survit au recalcul (le relevé fait foi, D99).
- Pas encore : le **total ψ × longueur** par local — il attend la minoration des angles (E) et les
  hauteurs d'étage (D159).
- Tests : 3 backend (45 ciblés au vert), 3 frontend (**129** au vert), typecheck et build.

## Résultat — G1 et catalogue ISO 14683 (2026-09-28)

- **G1 fait** : chaque côté déperditif de la fiche dit « Aucune paroi rattachée : la composition de ce
  côté est inconnue du calcul », ou « Parois : x m pour un côté de y m (± z m) » dès 20 cm d'écart
  (`controleCote`, `cotes.ts`) ; un bandeau en tête de liste les compte. Sur le R+1 : **10 côtés sans
  paroi** et **15 écarts de 20 cm ou plus** seront signalés.
- **Catalogue** : `app/data/thermique_ponts_iso14683.json` (76 ponts types) et
  `tests/test_thermique_ponts_catalogue.py` (complétude par famille, grille de 0,05, angles).
- 5 tests front nouveaux : **126 tests frontend thermiques**, typecheck ; 3 tests backend.

## Résultat de ce lot (A et B)

- `parcours.ts` : `vueDeLEtape` ; `StudyMetrics.tsx` : familles bornées par l'étape ; `StudyPanel.tsx` :
  zonage discret, bouton « Vérifier ses parois → » ; `ElementPanel.tsx` : parois seules et nom du local ;
  `WorkspacePage.tsx` : aiguillage du clic par étape, prise des ponts à 18 px ; `thermique.css`.
- 6 tests nouveaux (`etapes.test.tsx`) : **121 tests frontend thermiques** au vert, typecheck réussi.
- Aucun calcul touché. Aucune recette à la souris.
