# Retour d'usage sur l'étape « Parois et menuiseries » — décisions et questions

Date : 2026-09-28. Cinq remarques de l'utilisateur (M1 à M5), deux captures à l'appui : une seule fenêtre
en haut d'un local, désignée en deux morceaux (le premier sur les trois quarts de gauche, le second sur le
quart de droite). Répondez sous chaque question par une ligne `REPONSE : …`.

---

## M1 — Menuiseries trop fines pour être vues et attrapées — FAIT

À l'étape « Parois et menuiseries », les menuiseries sont dessinées **en trait épais** (5 px, 7 px quand
elles sont désignées, halo élargi) et le clic les attrape dans un rayon porté de 6 à **10 px**. Hors de
cette étape, rien ne change. (`StudyMetrics.tsx` : `accentMenuiseries` ; `thermique.css`.)

## M2 — Une menuiserie vue comme deux

> « aucune séparation entre les traits physique, j'aimerais que ce cas de figure ne puisse pas se produire
> et dire simplement il s'agit d'une menuiserie »

**Cause trouvée dans le code.** Un élément du relevé qui longe **deux locaux** est **découpé au dessin** là
où le local derrière lui change (`decouper_par_piece`) : c'est ce qui répartit un mur entre deux pièces.
Mais l'écran comparait des identités exactes, si bien qu'un clic désignait **le morceau** et non l'élément.
Sur le R+1, **24 formes de murs** sont déjà des morceaux. Pour une fenêtre, un recadrage qui laisse une
partie de la fenêtre hors du contour de son local, ou face à un autre local, produit exactement votre
capture. Le relevé, lui, n'a qu'une fenêtre.

**Corrigé (D167).** Un morceau renvoie à l'élément entier : un clic sur n'importe quel morceau désigne la
fenêtre entière, **tous ses morceaux s'allument ensemble**, elle apparaît une seule fois dans la fiche, et
dans la liste de chacun des locaux qu'elle longe. La même règle vaut au serveur pour « Valider ce local » :
un mur douteux qui longe deux locaux bloque les deux (R+1 : 65 éléments à trancher au lieu de 63, toujours
11 locaux validables sur 24).

**Reste un cas possible** : l'agent a réellement lu **deux** fenêtres côte à côte là où il n'y en a qu'une.
Sur le R+1, 4 paires de menuiseries se touchent dans le relevé ; toutes ont des composants différents et des
indices qui les distinguent (porte + vitrage fixe), donc légitimes.

**Q30 — Deux menuiseries qui se touchent, de même composant, sans rien entre elles :**
- (a) **fusionnées d'office** au recalcul — elles ne peuvent plus exister séparément ;
- (b) **signalées**, avec un bouton « Fusionner avec la voisine » ;
- (c) les deux : fusion d'office si le composant est le même, bouton sinon.

## M3 — « Nu extérieur / Nu intérieur » : de quoi s'agit-il ? — FAIT

Ce sont les **deux faces du mur**, repérées depuis le **trait de façade** qui guide le relevé, en
centimètres, négatives vers l'intérieur. Exemple : face extérieure −3, face intérieure −45 → la face
extérieure est 3 cm en retrait du trait, le mur fait **42 cm**. Pour une menuiserie, ce sont les faces du
mur dans lequel elle est posée.

**Corrigé** : les champs s'appellent désormais « Face extérieure du mur (cm) » et « Face intérieure du mur
(cm) », avec la phrase d'explication et **l'épaisseur calculée** en dessous.

## M4 — Supprimer une menuiserie, ou en dessiner une, au clic droit

**Existant.** « Écarter » existe déjà : l'élément sort du dessin et du calcul, reste dans l'étude, et se
remet d'un clic. Dessiner un élément absent est le geste reporté par **D104**.

**Piste.** Clic droit sur une menuiserie → « Supprimer cette menuiserie » (= l'écarter avec le motif
« supprimée », récupérable). Clic droit sur un mur → « Dessiner une menuiserie ici » : deux clics le long du
mur pour ses deux extrémités, projetés sur le tronçon ; le mur est coupé de part et d'autre, la menuiserie
prend le composant choisi.

**Q31 — Le composant d'une menuiserie dessinée :** (a) le plus employé du niveau, modifiable ensuite
(b) choisi dans la liste avant de dessiner.

## M5 — Des menuiseries identiques rangées pareil, pour la bibliothèque du projet

**Existant.** Les menuiseries sont regroupées par **composant** (le type lu par l'agent : M1 = 29 menuiseries
au R+1, M3 = 8, M4 = 7…). Les **largeurs** sont connues par le plan et gardées ; les **hauteurs** ne le sont
pas encore — elles viendront des façades et des coupes (chantier S5). Aucun regroupement par dimensions
n'existe. Or le Uw d'une menuiserie dépend de ses dimensions.

**Piste.** Un **repère de menuiserie**, comme la nomenclature d'un architecte : composant + largeur +
hauteur (« M1 · 120 × 135 »), attribué d'office aux menuiseries identiques, compté par repère dans la fiche et
dans la bibliothèque du projet.

**Q32 — Deux menuiseries sont « identiques » quand :** (a) même composant et même largeur au cm près
(b) même composant et largeur à ± 2 cm (c) autre.
**Q33 — Tant que la hauteur n'est pas connue :** (a) repère sur la largeur seule, complété plus tard
(b) hauteur saisie à la main dans la fiche de la menuiserie en attendant S5.

---

## Résultat de ce lot (M1, M2 corrigé à l'écran et au serveur, M3)

- `elements.ts` : `faitPartieDe`, `parentDeForme` ; `viserSurLePlan` et `elementsDuLocal` passent par
  l'élément entier. `StudyMetrics.tsx` : morceaux allumés ensemble, `accentMenuiseries`.
  `ElementPanel.tsx` : libellés des faces et épaisseur. `WorkspacePage.tsx` : prise à 10 px à l'étape des
  parois. Serveur : `parois_a_trancher` par morceaux.
- Tests : 4 frontend (`morceaux.test.tsx`, **146** au vert), 1 backend (43 au vert), typecheck, build.
- Aucun calcul du métré touché. Pas de recette à la souris.
