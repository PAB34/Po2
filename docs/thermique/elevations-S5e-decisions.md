# S5e — Élévations : hauteur des menuiseries — décisions et questions

Date : 2026-09-29. Suite de `coupes-elevations-S5-decisions.md` (D177, D182, D183, D190, D191) et de
`retours-menuiseries-2026-09-28-decisions.md` (M5, D176). Lancé par l'utilisateur (« Go S5e »). Répondez sous
chaque question par une ligne `REPONSE : …`.

Rappel :
- **D177** : la hauteur des menuiseries se lit **sur les élévations** ;
- **D176** : deux menuiseries sont « identiques » quand elles ont **même composant et même largeur à ± 1 cm** —
  c'est le **repère** de menuiserie (M5), comme la nomenclature d'un architecte ;
- **D182** : l'élévation se repère par **sa façade sur le plan** (orientation écrite, nord, silhouette).

---

## 1. Existant vérifié

**Dans l'étude du R+1 (projet 1)** : 58 menuiseries dans le relevé, chacune avec son **composant** (M1 mur-rideau
× 29, M3 × 8, M4 × 7, M-L5-1 × 7, M2, M5…), sa **largeur** (bornes le long du tronçon), son tronçon, et la normale
extérieure de ce tronçon sur la page. Pas de hauteur. Le **nord n'est pas posé** sur la planche de l'étude
(« nord à caler ») : l'orientation d'une façade n'est donc pas encore connue.

**Sur les planches** (PC08 = façades Est et Nord, PC09 = Sud et Ouest) : deux élévations par page, **tournées
d'un quart de tour** comme les coupes ; mêmes repères de niveau (H10, H11…) et axes de trame (A à R) ; menuiseries
dessinées en rectangles, souvent répétées (mur-rideau de la façade Est) ; **presque aucune cote de hauteur de
menuiserie écrite** : il faut mesurer.

**Dans le code** : la lecture des vues par l'agent (`run_lecture_coupes.py`) sait déjà trouver et nommer les
façades d'une planche (nature `facade`), mais ne les lit pas plus avant ; la fenêtre flottante (D183) et la
confirmation en deux clics (D191) existent pour les coupes.

**Leçon de l'essai des coupes** (0/13) : l'agent nomme bien, mesure mal. On ne lui confie donc pas la hauteur.

## 2. Proposition

1. **Repères de menuiserie (M5)** calculés d'office sur chaque niveau étudié : composant + largeur regroupée à
   ± 1 cm (« M3 · 120 »), avec le nombre de menuiseries et les niveaux où ils se trouvent. Hauteur : « à lire en
   élévation ».
2. **Élévation ouverte dans la fenêtre flottante**, depuis la fiche d'une menuiserie ou d'un repère (« Voir la
   façade Est »), et par un trait épais le long de la façade concernée sur le plan (D182), avec la case « Voir
   les coupes » devenue « Voir les coupes et façades ».
3. **Deux clics sur une menuiserie de l'élévation**, deux coins opposés : l'outil en tire **sa largeur et sa
   hauteur**, **propose le repère** de même composant et de largeur voisine, vous validez ; la hauteur vaut pour
   **toutes les menuiseries du repère** (Q45).
4. L'agent ne fait que **repérer et nommer** les façades (déjà en place).

## 3. Questions

**Q43 — Le geste sur l'élévation :**
- (a) **deux coins opposés** de la menuiserie : largeur et hauteur mesurées, l'outil propose le repère dont la
  largeur colle, vous validez (le contrôle de la largeur attrape une erreur de menuiserie) ; *recommandé* ;
- (b) deux clics **bas et haut** seulement, puis vous choisissez le repère dans une liste.
REPONSE :

**Q44 — Tolérance sur la largeur mesurée en élévation** pour proposer un repère. D176 fixe ± 1 cm entre deux
menuiseries **du plan** ; une largeur **cliquée** sur une élévation au 1/100 est à ± 3 à 5 cm. (a) proposer les
repères à ± 5 cm, le plus proche d'abord (b) autre.
REPONSE :

**Q45 — Portée d'une hauteur confirmée :**
- (a) **toutes les menuiseries du repère, sur tous les niveaux** du projet (même composant, même largeur) ;
  *recommandé* : c'est le sens du repère ;
- (b) seulement celles de la façade cliquée ;
- (c) seulement celles du niveau.
REPONSE :

**Q46 — Et un mur-rideau** (M1 : 29 morceaux de largeurs variées, du sol au plafond) ? (a) sa hauteur = la
**hauteur sous plafond du local** qu'il borde (déjà connue par les coupes, D178), sans clic ; (b) il se confirme
comme les autres, repère par repère.
REPONSE :

**Q47 — L'allège** (hauteur du bas de la menuiserie au-dessus du sol fini), utile pour les apports solaires et
les masques : (a) pas maintenant ; (b) oui, lue au même geste (un troisième clic sur le sol fini).
REPONSE :

**Q48 — Le nord n'est pas posé** sur le R+1 : sans lui, « Façade Nord » ne se relie pas à un côté du plan. (a)
le trait de façade sur le plan attend que le nord soit posé (l'outil le dit) ; l'ouverture depuis la fiche d'un
repère marche sans ; (b) autre.
REPONSE :

## 3 bis. Décisions (2026-09-29 : « Ok pour tes recommandations, go »)

**D193 (Q43 a)** — Deux coins opposés d'une menuiserie sur l'élévation : largeur et hauteur mesurées le long de la
droite et du haut de la vue ; l'outil propose le repère dont la largeur colle ; le thermicien valide.
**D194 (Q44 a)** — Repères proposés à ± 5 cm de la largeur mesurée, le plus proche d'abord.
**D195 (Q45 a)** — Une hauteur confirmée vaut pour toutes les menuiseries du repère (même composant, largeur à
± 1 cm), sur tous les niveaux du projet. La confirmation est gardée avec la vue de façade ; la plus récente
l'emporte.
**D196 (Q46 a)** — Un mur-rideau prend la hauteur sous plafond du local qu'il borde (D178), sans clic.
**D197 (Q47 a)** — L'allège attend.
**D198 (Q48 a)** — Le trait de façade sur le plan attend que le nord soit posé ; l'élévation s'ouvre depuis la
fiche de la menuiserie sans lui.

## 3 ter. Mesure sur le vrai R+1 et décisions révisées (2026-09-29)

Les 58 menuiseries du R+1 donnaient **52 repères** (composant + largeur à ± 1 cm) : largeurs vraiment différentes
d'une baie à l'autre (M4 de 2,02 à 4,15 m) et morceaux de 8 à 30 cm. Trois causes : une menuiserie coupée à la
jonction de deux tronçons (T04/T05 à 17,26 m…), des modules de mur-rideau entre poteaux (légitimes), des tranches
de M3 en bout des tronçons de la façade en dents de scie.

Choix de l'utilisateur : « Nettoyer d'abord », puis « Nettoyer + par composant ».

**D199 — Baie.** Des menuiseries contiguës (± 2 cm) de même composant, sans rien entre elles, **même de part et
d'autre d'une jonction de tronçons**, forment une **baie** (D174 appliquée). Le relevé garde ses morceaux (leur
identité porte les corrections du thermicien) ; la baie est l'unité qui se compte, se mesure et reçoit une
hauteur. R+1 : 58 menuiseries → **49 baies** (9 fusions). Une baie de moins de 40 cm restée seule est signalée
« morceau à vérifier » : 8 sur le R+1 (5 tranches de M3 de 8 à 30 cm, deux de mur-rideau de 7 et 10 cm, une M-L5-1
de 31 cm).

**D200 — Hauteur par composant (remplace D195).** Une hauteur confirmée vaut pour **toutes les baies du
composant**, sur tous les niveaux, quelle que soit leur largeur ; une baie particulière peut recevoir sa propre
hauteur, qui l'emporte. D193 reste : les deux coins donnent largeur et hauteur ; la largeur mesurée doit être à
± 5 cm d'une baie du composant choisi (D194), sinon l'outil refuse (mauvaise menuiserie cliquée).

## Résultat (2026-09-29, commits locaux, non poussé, jamais éprouvé à la souris)

- Serveur : `thermique_menuiseries.py` (baies D199, hauteur par composant ou par baie D200, mur-rideau D196,
  mesure de deux coins D193, proposition à ± 5 cm D194), routes `GET /projects/{id}/menuiseries`,
  `POST /vues/{id}/menuiseries`, `DELETE /vues/{id}/menuiseries/{composant}`. Pas de migration : les hauteurs
  sont gardées avec la vue de façade.
- Écran : dans la fiche d'une menuiserie, sa baie (largeur réunie, morceaux, hauteur et provenance, alerte
  « morceau à vérifier ») et « Voir la façade … » ; dans la fenêtre d'une façade, « Mesurer une menuiserie » →
  deux coins → largeur et hauteur → « Pour toutes les M4 » / « Pour cette baie seule ».
- R+1 réel : 58 menuiseries → 49 baies, 8 morceaux à vérifier.
- Tests : 5 backend (`test_thermique_menuiseries.py`), 6 frontend (`baies.test.tsx`, 172 au vert), typecheck,
  build.
- Pas fait : le trait de façade sur le plan (D198, attend le nord) ; l'usage des hauteurs dans le calcul des
  surfaces (lot des surfaces).

---

## 4. Ce que je vérifierai

- Le métré du R+1 ne bouge pas (170,12 m déperditifs, 229 côtés) : une hauteur de menuiserie ne change pas les
  linéaires ; les surfaces de baies viendront au lot qui branchera les surfaces.
- Les repères du R+1 recomptés (58 menuiseries) contre le relevé.
- La largeur mesurée en élévation comparée à celle du plan, sur quelques menuiseries relevées à l'œil (vérité
  terrain, comme pour les coupes).
