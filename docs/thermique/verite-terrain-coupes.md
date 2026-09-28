# Vérité terrain des coupes (S5, D185)

Date : 2026-09-28. Relevé à l'œil par Claude sur des rendus quadrillés en points PDF, avant tout agent. Les
données exploitables sont dans `verite-terrain-coupes.json` (même dossier). L'agent des coupes devra les
retrouver ; son écart sera chiffré à chaque lot.

## Projet 1 — Frontignan (le R+1 étudié, 1/100)

**Traits sur le plan R+1 (PC04).** Quatre coupes, marquées seulement par **deux drapeaux gris** en bord de
plan, sans trait entre eux ; le drapeau est du côté où l'on regarde.

| Coupe | Trait | Regard |
|---|---|---|
| A | vertical, x = 1144,5 pt, 40,3 m | vers l'ouest de la page (−x) |
| B | horizontal, y = 1251,25 pt, 41,4 m | vers le bas (−y) |
| C | vertical, x = 824 pt | vers +x |
| D | horizontal, y = 905,75 pt | vers le haut (+y) |

**Vues.** PC10 = coupes A et B, PC11 = C et D : deux coupes par page, **tournées d'un quart de tour** (le haut
de la coupe est vers la droite de la page). Les coupes portent les **axes de trame** (A à R ou 1 à 16) et des
**lignes de niveau nommées** : H10 = sol fini R+1 (+4,16), H11 = plafond fini R+1, H20 = sol fini R+2
(+8,00)… avec la chaîne de cotes écrite **H10 → H11 = 2,88 m**.

**Hauteurs du R+1.** Tous les locaux coupés ont leur plafond fini sur H11 : **2,88 m**. Deux exceptions :
l'escalier de l'atrium (double hauteur, pas de plafond au R+1 : hauteur à signaler, pas à inventer) et la
boîte à vents (hors étude).

| Coupe | Locaux chauffés ou circulations traversés (étude `banc.db`) |
|---|---|
| A | 6.1.1 B.dir, **6.1.2 B.asst 1 à 6**, 6.1.3 équipement |
| B | 6.1.2 B.asst (5), 6.1 circulation, 6.1.6 salle de réunion, escalier atrium (double hauteur), 4.2 Pôle multimédia |
| C | 4.2.4 espace formation, escalier atrium (double hauteur), 4.3.4 lecture confort |
| D | aucun : la coupe longe la coursive sud, extérieure |

**Ce que le relevé apprend déjà :**
1. **Croiser le trait avec les contours ne suffit pas.** Sur la coupe A, le croisement géométrique ne trouve
   que **2 locaux sur 8** : le trait passe **dans l'épaisseur du mur** entre la circulation et les six bureaux,
   à 5 cm de chacun. La coupe, elle, dessine les bureaux coupés et les nomme « 6.1.2 Bur.1 … Bur.6 ». Il faut
   une **tolérance** (quelques centimètres) et l'**arbitrage par le nom**.
2. **Les noms sont abrégés** dans la coupe (« 4.3.4 Jeux vidéo » pour « 4.3.4 et 4.5.2 lecture confort ») : le
   **numéro du programme** (4.3.4, 6.1.2) est la clé fiable ; le texte ne l'est pas.
3. Une coupe qui ne traverse **aucun local chauffé** (D) est un cas normal, pas une erreur.

## Projet 2 — Balaruc (1/50)

**Traits sur le plan R+1 (P03).** Six coupes en **trait rouge**, mesurées sur les pixels rouges :

| Coupe | Forme | Regard |
|---|---|---|
| A | un décroché (x = 1980 puis 1844 pt) | −x |
| B | droite, x = 1505,5 pt | −x |
| C | **quatre décrochés** | +y |
| D, E, F | droites, repères aux deux bouts seulement ; les deux bouts diffèrent de 16 pt (≈ 28 cm) | +y |

**Vues.** C01 = CC, DD, AA ; C02 = FF, EE, BB, **plus un détail** « Zoom sur menuiserie coupe BB » qui n'est
pas une coupe : l'agent doit le reconnaître et ne pas le rattacher. Coupes non tournées (haut = haut de la
page), cotes **NGF**, hauteurs souvent **écrites** par local et **faux plafonds** dessinés.

Les hauteurs du projet 2 ne sont pas relevées (Q41 : seulement le R+1 du projet 1, seul niveau étudié).
