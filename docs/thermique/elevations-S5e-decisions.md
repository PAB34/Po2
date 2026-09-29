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

---

## 4. Ce que je vérifierai

- Le métré du R+1 ne bouge pas (170,12 m déperditifs, 229 côtés) : une hauteur de menuiserie ne change pas les
  linéaires ; les surfaces de baies viendront au lot qui branchera les surfaces.
- Les repères du R+1 recomptés (58 menuiseries) contre le relevé.
- La largeur mesurée en élévation comparée à celle du plan, sur quelques menuiseries relevées à l'œil (vérité
  terrain, comme pour les coupes).
