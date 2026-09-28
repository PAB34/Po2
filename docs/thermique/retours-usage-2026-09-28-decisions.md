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

**Q9 — Quels types proposer à la création ?** Aujourd'hui trois : angle sortant, angle rentrant, about de
refend. À ajouter selon vous : liaison plancher intermédiaire, plancher bas, toiture, balcon ou terrasse,
appui, linteau ou tableau de baie, autre (à modéliser) ?

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
- (b) Le **catalogue réglementaire Th-Bât** (fascicule ponts thermiques) intégré à l'outil, puis la
  bibliothèque du projet pour le reste.
- (c) Seulement l'état « à modéliser » pour l'instant, sans aucune valeur ψ dans l'outil.

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

**Q12 — Et un angle plus fermé que 90° (changement de direction > 90°) ?** Majoré, plafonné à ψ₉₀,
ou signalé à vérifier ?

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
**Q14 — Le pont linéique le long du côté commun est-il créé automatiquement** dès qu'un local est classé
terrasse (à juger ensuite dans la passe des ponts), ou ajouté à la main ?
**Q15 — L'agent doit-il apprendre à reconnaître les terrasses** dès l'analyse (consigne ajoutée à
l'agent de lecture des locaux, dans le code — pas `.claude/agents/thermicien-plan.md`) ?

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
- **G2 — Dessiner l'emprise des angles et abouts** : les « vides » visuels aux coins disparaissent.
  Affichage seul (D99), le calcul ne change pas.
- **G3 — Déplacer les bornes d'un élément sur le plan** (reporté par D104) : poignées aux deux extrémités
  de l'élément désigné, glissées le long de son tronçon ; le voisin suit, pour qu'aucun vide ne se crée.
- **G4 — Un agent de liaison** : après le recadrage d'un local, un agent Claude Code (sur le poste, sans
  clé d'API, comme les deux autres) relit le contour recadré et le relevé, et **propose** les rattachements
  paroi ↔ côté, les bornes à déplacer et les vides à combler, **comme des gestes à valider**, jamais
  appliqués en silence.

**Q16 — Dans quel ordre ?** Proposition : G1, puis G2, puis G3, puis G4 (G4 s'appuie sur G1 pour dire ce
qui cloche, et sur G3 pour exprimer ses propositions).
**Q17 — Déplacer une borne d'élément : le voisin suit-il ?**
- (a) Oui, la borne est partagée : allonger un mur raccourcit son voisin (aucun vide possible).
- (b) Non, chaque élément bouge seul : un vide ou un recouvrement peut apparaître, signalé en alerte.
**Q18 — L'agent de liaison se déclenche quand ?**
- (a) À la validation de chaque local (il relit ce local seul).
- (b) Sur demande, pour le niveau entier, une fois les recadrages faits.
- (c) Les deux.

---

## Ordre de travail proposé

1. Pousser le lot en attente (422, sujet 2, validation, A et B) quand vous le décidez.
2. **G1** (le contrôle par côté) : il rend visible le risque sur le calcul dès maintenant.
3. **D** (réattribuer un pont, état « à modéliser ») : le serveur sait déjà faire, seul l'écran manque.
4. **C** (créer un pont au clic droit), selon Q8 et Q9.
5. **E** (angle porté par chaque pont, minoration) puis **Q10** (valeurs ψ).
6. **F** (nature terrasse), **G2**, **G3**, **G4**.

## Résultat de ce lot (A et B)

- `parcours.ts` : `vueDeLEtape` ; `StudyMetrics.tsx` : familles bornées par l'étape ; `StudyPanel.tsx` :
  zonage discret, bouton « Vérifier ses parois → » ; `ElementPanel.tsx` : parois seules et nom du local ;
  `WorkspacePage.tsx` : aiguillage du clic par étape, prise des ponts à 18 px ; `thermique.css`.
- 6 tests nouveaux (`etapes.test.tsx`) : **121 tests frontend thermiques** au vert, typecheck réussi.
- Aucun calcul touché. Aucune recette à la souris.
