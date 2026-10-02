---
read_policy: lire avant toute mission ou tout lot ; base du fichier de conventions de chaque projet
statut: synthèse au 2026-10-02, à relire et corriger par le thermicien
---

# Règles métier validées par le thermicien (synthèse)

Les règles thermiques et de métré déjà tranchées, rassemblées en une page. Elles viennent d'une trentaine de fichiers
de décisions (le numéro D renvoie à la décision d'origine, aujourd'hui en `en-service/` ou dans
`docs/Archives/thermique/`). Elles servent de base au **fichier de conventions** de chaque projet (guide, règle 5).
Ce qui est encore ouvert est listé à la fin.

## Lecture des plans

- **Le plan est lu comme une image** (pixels seuls), jamais par les vecteurs du PDF (décision du 2026-09-21).
- **L'IA reconnaît et tranche, le code mesure** ; une valeur incertaine est marquée « à vérifier » ou « supposée »,
  jamais présentée comme sûre (D1 du 2026-09-18, leçon du 2026-10-02).
- **Échelle** : contrôlée sur une cote ; l'arrondi à l'échelle usuelle sous 1 % d'écart est une **question ouverte**.
- **Calage des niveaux** « comme Aligner d'AutoCAD » : point de base, rotation, longueur (D201, D202).
- **Nord** posé par le thermicien sur la planche ; sans nord, les orientations restent « à caler » (D32, D84).

## Métré

- **Dimensions intérieures** (convention française) : on mesure au **nu intérieur** ; l'isolant d'un angle n'entre
  pas dans les surfaces, il est porté par le pont thermique d'angle.
- **Un mur = la composition affectée à une paroi d'un local** ; la paroi est une portion droite du contour du local,
  sa face intérieure (option C, D255 à D262).
- **Couches d'une paroi** de l'extérieur vers l'intérieur : voile extérieur, isolant, voile intérieur, doublage
  (D16). **Doublage BA13 de 1,3 cm présumé** quand il n'est pas dessiné, marqué « présumé » (D17).
- **Épaisseurs** ramenées aux épaisseurs commerciales, l'épaisseur lue restant affichée.
- **Hauteur d'un local** : une seule, **sous plafond fini** (sous le faux plafond s'il y en a un) ; la bande entre
  faux plafond et dalle n'est pas comptée (D178). Un local que ne traverse aucune coupe prend la hauteur la plus
  fréquente de son niveau, affichée « déduite » (D179). Deux coupes : moyenne pondérée par la longueur traversée
  (D180). La hauteur se confirme d'un clic dans la coupe (D191).
- **Surfaces d'une paroi** : brute = longueur × hauteur du local ; baies = Σ largeur × hauteur du modèle ;
  opaque = brute − baies ; ce qui manque est dit, jamais deviné (D269).
- **Paroi vitrée** : devant une menuiserie et sans mur, ou couverte à 90 % par ses baies ; elle se traite avec les
  menuiseries (D263, D268).

## Locaux

- **Natures** : chauffé (par défaut), circulation (chauffée par défaut), non chauffé, **gaine technique** (D24,
  D115). Une gaine se calcule comme un local non chauffé (D120).
- **Tous les locaux** sont relevés, circulations comprises ; un espace qui regroupe plusieurs locaux reste d'un seul
  tenant, et une **demande** de découpage est adressée à l'architecte (D22, D25).
- **Déperditif** : tout local qui donne sur l'extérieur, un local non chauffé ou un vide, par un mur, une menuiserie
  ou tout autre composant, est déperditif et source d'apports ; un local non chauffé ne porte pas de déperditions
  propres, ses côtés vers les locaux chauffés sont les parois déperditives de ceux-ci (D23, D30).
- **Ce qu'il y a derrière un côté** se lit en sondant perpendiculairement tous les 10 cm jusqu'à 1,2 m : autre local,
  extérieur, vide, inconnu ; la distance donne l'épaisseur du mur (D29).
- **Extérieurs** : terrasses, balcons, coursives, loggias sont extérieurs ; un local chauffé contre un espace
  extérieur à plancher porte une liaison linéique le long de ce côté (D161). La bande le long de la façade est du
  projet 1 est extérieure (arbitrage du 2026-09-23).

## Menuiseries

- **Morceaux réunis** : sur un même tronçon, même composant et même modèle, à 6 cm au plus (D223, D238).
- **Identiques** : même composant et même largeur à ± 1 cm (D176) ; « même largeur ± 2 cm » pour poser un modèle.
- **Hauteur** lue sur les élévations ; le **modèle mesuré** (largeur, hauteur, capture) fait foi (D177, D218 à D222).
- **Exposition** : 8 secteurs et azimut, depuis le nord posé (D225).
- **Posée sur la paroi** qu'elle longe ; une baie à cheval sur deux parois se partage (D267).

## Ponts thermiques

- **Référentiel** : normes du dossier NORMES — **NF EN ISO 14683** (valeurs par défaut), **NF EN ISO 10211** (calcul,
  avec ubakus pour les cas particuliers), NF EN 12831-1, 52016… **Pas de Th-Bât.**
- **ψ en dimensions intérieures** (ψi) ; part géométrique d'un angle d'écart θ : environ U·2·e·tan(θ/2).
- **Minoration des angles proportionnelle** (θ/90), faute de règle dans les normes.
- **Chaque pont passe devant le thermicien** ; un pont absent du catalogue est « à modéliser » ; un pont manquant
  s'ajoute au clic droit (D157, D158, D164).
- **Pont vertical** : sa longueur est la hauteur du local (D159). Angle saisi s'il diffère de la mesure (D160).
- **Angle à la jonction de deux pièces** : partagé à moitié (D163) ; refend partagé moitié-moitié (D20).
- **Liaison plancher / façade** : pas créée d'office tant qu'on ne sait pas la lire (D166) ; à terme, règle des
  **quatre quarts** par superposition des niveaux (dessus / dessous × intérieur / extérieur).
- **Jonctions proches** : deux ponts à moins de dmin = max(1 m ; 3 × épaisseur) se calculent dans un même modèle
  (ISO 10211).

## Ce qui reste ouvert (à trancher)

- Arrondi de l'échelle à l'échelle usuelle (< 1 % d'écart).
- Nu intérieur d'un **mur-rideau** : ligne du vitrage, ou face intérieure des poteaux ?
- Cloisons entre locaux chauffés : composition à saisir ou non.
- Classement des liaisons des missions (A à G) dans les familles de la NF EN ISO 14683.
- Convention de nommage des niveaux (`N0`/`N1`/`S1`, ou `RDC`/`R1`/`SS1`).
