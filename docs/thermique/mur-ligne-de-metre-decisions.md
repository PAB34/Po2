# Un mur = une ligne de métré qui porte une composition (D242 à D247)

Date : 2026-10-02. Remplace, à l'écran, le pinceau et le retracé de `parois-comme-menuiseries-decisions.md`
(D239–D241, retirés de l'écran à la demande du thermicien ; le serveur garde `paroi_retracer`).

## Ce que veut le thermicien (2026-10-01/02)

« Le mur est un élément comportant une composition de plusieurs éléments ; c'est la **ligne de métré** qui compte :
elle représente la composition du mur. » Mur normal : une composition ; mur atypique : presque un **modèle
unique**. Des murs détectés à tort doivent se **supprimer facilement**. Chaque mur défini voit sa composition
(matériaux, épaisseurs) **validée dans le bandeau de droite**. Réponses : la ligne de métré est la **face
intérieure** ; redessiner la ligne de métré d'un mur l'intéresse ; il veut aussi composer un mur **non linéaire**
dont les couches **ne sont pas forcément parallèles**.

## Existant vérifié

- Relevé : un élément = un morceau de tronçon, nus extérieur/intérieur **au début et à la fin**
  (`nu_*_fin_cm`) : l'épaisseur peut déjà varier le long du mur ; `couches_positionnees` cale les couches
  d'un massif d'épaisseur variable sur le nu intérieur.
- Le plan dessinait chaque couche (voile, isolant, doublage) en polygone : d'où les rectangles superposés.

## Lot A — fait le 2026-10-02 (en prod)

- **D242 — La ligne de métré.** `reprojeter` produit `lignes_metre` (face intérieure de chaque paroi, longueur,
  épaisseur début/fin), converties en points PDF. À l'étape Parois, le plan dessine **une ligne par mur** avec son
  étiquette (« P1 · 44 cm »), et c'est elle qu'on clique ; les couches une à une n'y sont plus dessinées.
- **D243 — La composition se valide mur par mur.** Fiche d'un mur : couches (nature, épaisseur) éditables, ajout
  et retrait, épaisseur totale, « Valider la composition » ; par défaut **ce mur seul** (modèle unique), case
  « Appliquer aussi aux N autres murs Px ». Le nu intérieur (ligne de métré) ne bouge pas ; le nu extérieur suit
  l'épaisseur. Compteur de l'étape : « N murs à valider sur M ». Le reste (lecture de l'IA, type, écarter avec
  motif) est replié dans « Corriger le relevé ».
- **D244 — Supprimer un mur en un geste** : bouton « Supprimer ce mur », ou touche **Suppr** quand il est désigné.
  Écarté avec le motif « mur supprimé par le thermicien », réactivable.
- Étude d'avant D242 : recalculée une fois à l'ouverture (sans version) pour gagner ses lignes de métré.

## Lot B — remplacé le 2026-10-02 par `murs-traces-decisions.md` (D248–D253 : murs tracés librement)

- **D245 (proposé) — Redessiner la ligne de métré** : mur désigné, « Redessiner la ligne », deux clics sur la
  face intérieure (début, fin). Le serveur en tire les bornes sur le tronçon **et** le nu intérieur au début et à
  la fin : une face intérieure en biais par rapport à la façade devient possible.
- **D246 (proposé) — Couches non parallèles** : chaque couche reçoit une épaisseur **au début** et **à la fin**
  du mur (variation linéaire) ; cas du massif en coin de la capture du 2026-10-01.
- **D247 (proposé) — Mur non linéaire** : un mur peut s'étendre sur plusieurs pans consécutifs de la façade
  (angles compris) ; il garde **une** composition, ses angles restent des ponts thermiques.

### Questions

1. **Couches non parallèles** : une épaisseur au début et une à la fin pour chaque couche (variation régulière)
   suffit-elle, ou faut-il pouvoir dessiner librement la forme d'une couche ?
2. **Mur non linéaire** : s'agit-il d'un mur qui suit plusieurs pans de la façade (avec des angles) et que vous
   voulez traiter comme **un seul mur** à une seule composition ? Ou d'un mur courbe ?
3. **Redessiner** : deux clics sur la face intérieure (début, fin) vous conviennent-ils ?
