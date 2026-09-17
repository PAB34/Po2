# Refondation du parcours d'analyse thermique — décisions

> Ouvert le 2026-09-16 à la demande de l'utilisateur : « repartir à 0 sur l'expérience utilisateur » pour
> automatiser autant que possible l'analyse thermique d'un bâtiment à partir des plans vectoriels.
> Prolonge `detection-guidee-decisions.md` (lots G1-G4) et `detection-murs-strategie.md` (moteur vectoriel).

## 1. Demande (reformulée)

1. Garder le moteur de détection des parois (vectoriel), qui détecte beaucoup mais pas encore tout.
2. Un bouton pour **effacer tous les documents et données de test**.
3. Première passe du moteur : **identifier les « calques » identiques** créés par l'architecte.
4. Deuxième passe : **identifier les calques isolants** (murs, planchers) ; la projection de l'isolant sur la
   longueur des couches qui lui sont collées construit la bibliothèque des parois.
5. Nouveau parcours :
   - un **point géographique commun** à tous les plans ;
   - sur chaque planche (plans, coupes, élévations), des lignes qui délimitent les zones chauffées, non chauffées
     et extérieures, **deux lignes par zone** (nu intérieur, nu extérieur) ;
   - analyse de tout ce qui se trouve entre les deux lignes ;
   - modèle géométrique construit étape par étape, qui donne les surfaces sur l'extérieur ou sur local non chauffé ;
   - puis détection des parois et menuiseries ;
   - puis détection des pièces et de leurs dénominations.

## 2. Faits vérifiés sur le projet d'essai

| Sujet | Constat |
|---|---|
| Calques (OCG) | **Aucun** dans les PDF : les calques de l'architecte sont aplatis à l'export. |
| Ce qui en reste | Une **signature graphique** par calque : largeur de plume, gris, motif de hachure, teinte de remplissage. Relevé : murs coupés 1,56 pt noir ; vitrages 0,24 pt ; habillage (nez de dalle, mobilier, rayures de terrasse) 0,36 pt ; portes et escaliers 0,48 pt ; doublages 0,96 pt ; remplissage des murs gris 152 ; isolant = petits traits 0,48 pt gris 118 ou 152 ; trame 0,12 pt gris 166. |
| Textes | **Zéro caractère** : lettres dessinées en contours. Essai de regroupement des formes identiques : aucune répétition exacte (N0 : 5 269 petits tracés, 5 032 formes ; coupe AB : 8 013 / 8 013). Lecture des noms = lecture visuelle (Claude Code) ou reconnaissance de caractères. |
| Isolant | Dessiné par endroits seulement (doublages du N-1) : niveau de détail d'un dossier de permis de construire au 1/100. |
| Trame d'axes | Présente sur les plans (1 à 14, A à R) ; repères de coupe A, B, C, D visibles sur les plans. |
| Moteur de murs | N-1 : aucune face inexpliquée ; N0 à N3 : faux murs et vitrages non appariés (voir `detection-guidee-decisions.md` §6). |

## 3. Avis : cohérent, avec six ajustements

1. **« Calques identiques » = catalogue des signatures graphiques**, validé une fois par projet (et réutilisable
   pour le même architecte) : « ce gris = béton », « ce motif = isolant », « cette plume = vitrage », « ce
   symbole = porte ». C'est la bonne première passe : tout le reste s'appuie dessus.
2. **Isolant projeté** : oui. Une paroi = l'empilement de ses couches dans l'épaisseur ; la longueur de
   l'isolant donne son étendue. **Repli** quand l'isolant n'est pas dessiné : type = épaisseur + remplissage,
   composition saisie une fois par type. Les planchers et toitures se lisent sur les coupes.
3. **Repère commun = trame d'axes**, détectée et confirmée par l'utilisateur ; sur les coupes, position le long
   de l'axe + altitude NGF. Point cliqué en secours seulement.
4. **Deux lignes sur les plans et les coupes seulement.** Une élévation n'est pas une coupe : pas de nu
   intérieur. Les élévations servent aux menuiseries (hauteur, allège) et au repérage des façades.
5. **Pièces avant zones.** Détecter les pièces (espaces fermés par murs et menuiseries), l'utilisateur clique
   chaque pièce « chauffée / non chauffée / extérieure » (le nom lu pré-remplit : garage → non chauffé) ; zones
   = unions de pièces ; nu intérieur déduit ; le **« donne sur » se déduit de ce qu'il y a de l'autre côté
   de la bande** : plus de qualification côté par côté.
6. **Ponts thermiques déduits du modèle** : jonctions de bandes (angles, refends), planchers contre façades
   (coupes), contours de baies.

## 4. Parcours proposé

| Étape | Automatique | L'utilisateur |
|---|---|---|
| E0 Import | Classement des planches (plan, coupe, élévation), échelle, niveau. | Vérifie ; peut tout effacer. |
| E1 Catalogue des signatures | Regroupe plumes, gris, motifs, remplissages, symboles répétés. | Nomme chaque signature (béton, isolant, vitrage, porte…) une fois. |
| E2 Repère commun | Trame d'axes et altitudes. | Confirme deux axes (ou clique un point). |
| E3 Pièces | Espaces fermés, noms lus. | Clique chauffé / non chauffé / extérieur. |
| E4 Zones et deux lignes | Unions de pièces, nu intérieur et nu extérieur ; coupes : planchers et hauteurs. | Corrige (glisser, clic droit). |
| E5 Parois | Bande découpée en tronçons, composition par signatures, types, « donne sur ». | Valide les types par groupe, rattache à la bibliothèque. |
| E6 Menuiseries | Baies dans la bande (vitrages, symboles), largeur ; hauteur sur élévations. | Valide les types, saisit la hauteur par type si besoin. |
| E7 Ponts thermiques | Linéaires de jonctions et de contours de baies. | Choisit les valeurs par type. |
| E8 Export | Surfaces et linéaires par composant. | — |

## 5. Existant : gardé ou remplacé

| Élément | Sort |
|---|---|
| Moteur vectoriel des murs (`vecteurs.py`, `murs.py`, `evaluation.py`) | Gardé : base de E1, E3, E5. |
| Deux lignes (`lignes.py`), outil Nu extérieur, clic droit | Gardés : E4 (correction). |
| Niveaux, calage A-B, nord, hauteurs par coupe | Gardés ; le calage A-B devient le secours de E2. |
| Contour raster (`detection.py`) et types de murs le long du contour (`enveloppe.py`, M4a) | À retirer une fois E5 livré. |
| Qualification « donne sur » côté par côté | Remplacée par la déduction de E5. |

## 6. Bouton « Tout effacer »

- Supprime, pour le compte connecté, tous les projets thermiques : documents, planches, images, niveaux,
  tracés, composants des projets, fichiers sur le disque.
- Confirmation forte : taper le mot « EFFACER ».
- Périmètre à trancher : Q62.

## 7. Questions

- **Q62** — Le bouton efface-t-il aussi la bibliothèque de modèles réutilisables, ou seulement les projets ?
- **Q63** — Repère commun : trame d'axes détectée, ou point cliqué sur chaque planche ?
- **Q64** — Ordre : pièces d'abord (zones par clic), ou deux lignes tracées d'abord ?
- **Q65** — Élévations : double ligne aussi, ou réservées aux menuiseries et aux façades ?

## 8. Réponses et décisions (2026-09-16)

| N° | Décision |
|---|---|
| Q62 → D9 | « Tout effacer » supprime **les projets seulement** (documents, planches, images, niveaux, tracés, composants de projet, fichiers). La bibliothèque de modèles réutilisables est gardée. |
| Q63 → D10 | Repère commun = **trame d'axes** détectée et confirmée ; altitude NGF sur les coupes ; point cliqué en secours. |
| Q64 → D11 | **Pièces d'abord** : détection des pièces et de leurs noms, classement par clic, zones et deux lignes déduites, « donne sur » déduit. |
| Q65 → D12 | Élévations réservées aux **menuiseries et aux façades** ; double ligne sur plans et coupes. |
| D13 | Ordre de construction : bouton « Tout effacer », puis E1 (catalogue des signatures), E2 (trame d'axes), E3 (pièces), E4 (zones et lignes), E5 (parois), E6 (menuiseries), E7 (ponts thermiques). |

## 9. E1 — Catalogue des signatures (livré le 2026-09-16)

- **Signature d'un trait** = largeur (pt) + couleur exacte + motif de tirets ; **d'un remplissage** = couleur exacte.
  Lecture : `traits.lire_traits(..., detail=True)` et `traits.lire_aplats(..., detail=True)`.
- **Mesures** par signature (`thermique_moteur/signatures.py`) : nombre, linéaire ou surface, part de traits
  courts (< 40 cm), part en paires de faces (traits foncés d'au moins 0,7 pt seulement), part dans les murs
  détectés, part dans le prolongement d'un mur interrompu (baies).
- **Rôle proposé** avec sa raison ; l'utilisateur valide, change ou annule. Rôles des traits : face de mur,
  cloison ou doublage, vitrage ou menuiserie, isolant, motif (sol, végétation), projection, habillage, annotation,
  trame, à ignorer. Rôles des remplissages : maçonnerie, isolant, terrasse ou sol extérieur, autre, à ignorer.
- **Stockage** : `thermique_projects.signatures_json` (migration 0080), `{clé: rôle}`.
- **Écran** : onglet « Signatures » du projet ; plan à gauche, signature choisie surlignée en magenta ; liste à
  droite avec aperçu du trait, mesures, rôle proposé, bouton « Valider les propositions restantes ».
- **Projet d'essai** (5 plans, 0,8 à 2,9 s par plan) : 1,56 pt et 1,44 pt noir → face de mur ; 0,96 pt noir →
  cloison ; 0,24 pt noir → vitrage ; 0,48 pt gris 40 % → isolant ; 0,12 pt gris clair → trame ; rouge →
  annotation ; verts → végétation ; remplissage gris 40 % → maçonnerie (86 % dans les murs).
- **Limites** : les symboles répétés (portes, sanitaires) ne sont pas encore reconnus comme blocs (E6) ; les
  rôles validés ne pilotent pas encore la détection (E3 à E6 s'appuieront dessus).

## 10. E1 révisée — Désigner les calques par l'exemple (2026-09-17)

Constat de l'utilisateur sur le catalogue §9 : « il mélange plusieurs éléments différents ». Vérifié au niveau 0 :
la plume 0,36 pt noire réunit 2 834 éléments de natures différentes (1 856 traits courts, 400 polylignes,
354 traits droits, 224 contours fermés). Proposition de l'utilisateur : cliquer un élément, donner la nature de
son calque, et reporter sur tous les niveaux de signature identique.

| N° | Décision |
|---|---|
| Q66 → D14 | « Semblable » = **même trait et même forme** (droit, polyligne, court < 40 cm, petit contour fermé < 1,5 m, grand contour fermé, arc) ; élargissement possible à tout le trait. |
| Q67 → D15 | Natures proposées : mur (maçonnerie, béton), isolant, cloison ou doublage, menuiserie extérieure, porte, garde-corps ou limite de terrasse, plancher ou dalle (coupes), toiture (coupes). |
| Q68 → D16 | Ce qui n'est pas désigné est **ignoré**. |
| Q69 → D17 | L'onglet « Signatures » est **remplacé** par l'onglet **« Calques »** (plan + outil de désignation + récapitulatif). |

- **Élément** = tracé continu du PDF (d'un « moveto » au suivant), lu par `thermique_moteur/calques.py`
  (0,7 à 1,3 s par plan ; 8 000 à 84 000 éléments ; cache de 2,5 à 7,8 Mo à côté des tuiles).
- **Règle** = signature + forme (ou « * ») → nature, avec les éléments retirés un à un ; stockée dans
  `thermique_projects.signatures_json` (`{"version": 2, "regles": [...]}`), appliquée à toutes les planches de
  plan à l'échelle définie. Une règle de forme précise l'emporte sur « toutes formes ».
- **Clic** : trait le plus proche (8 px à l'écran) ; traits superposés → le plus épais ; sinon le plus petit
  remplissage qui contient le point.
- **API** : `GET/POST /projects/{id}/calques`, `DELETE /projects/{id}/calques/{règle}`,
  `POST /projects/{id}/calques/{règle}/exclusions`, `POST /sheets/{id}/calques/designer`,
  `GET /sheets/{id}/calques/famille`, `GET /sheets/{id}/calques/designes`.
- Le catalogue §9 (liste à valider, routes `/signatures`) est retiré ; le moteur `signatures.py` reste pour les
  libellés de couleur et d'éventuelles suggestions.

## 11. Retrait par zone et menuiseries (2026-09-17)

| N° | Décision |
|---|---|
| Q70 → D18 | Zone = **Maj + glisser** ; glisser seul déplace le plan. |
| Q71 → D19 | La zone sert à **retirer et remettre** les éléments désignés (pas à désigner). |
| Q72 → D20 | Menuiseries : **baies sur le plan** (ouvertures dans les murs désignés), types par l'exemple, hauteur par type, **contrôle sur l'élévation** après la trame d'axes. Lot E6, après E2 à E4. |
| Q73 → D21 | Deux fenêtres séparées par un montant = **une baie d'ensemble**. |

Lot livré maintenant : E1b, retrait par zone (§11.1).

Retours de l'utilisateur sur l'onglet « Calques » :
1. Le retrait élément par élément est apprécié, mais un objet peut compter des centaines de traits (un escalier
   désigné à tort comme isolant) → il faut **sélectionner une zone à la souris**.
2. Les menuiseries ne se détectent pas : le clic ne trouve que le cadre ou le profilé, jamais la fenêtre entière,
   et ce « cadre » est souvent le **montant commun à deux fenêtres**. Faut-il passer par les élévations ?

### 11.0 bis — E1 validée par l'utilisateur (2026-09-17)

« J'ai pu appliquer toutes les modifications que j'ai voulu et les éléments contenus dans les calques sont les
bons pour moi. » Lasso et correctif d'affichage : PR #197. Suite : E2 (§12).

### 11.0 Retours du 2026-09-17 sur E1b (PR #196)

- Le rectangle droit ne sait pas isoler des éléments **en biais** (couvertures, murs inclinés) : pour contenir un
  trait diagonal, il avale aussi les voisins. → **D22** : Maj + glisser trace un **lasso à main levée** (contour
  libre) ; un élément est pris si tous ses points sont dans le lasso. Le rectangle disparaît (un lasso peut le
  remplacer).
- Bug : « Voir » un calque montrait encore les éléments retirés. Causes : la famille surlignée ignorait les
  retraits, et l'écran gardait l'ancienne famille en cache. → **D23** : la famille affichée (et les nombres
  proposés au clic) déduisent les retraits du calque existant ; toute modification rafraîchit l'affichage.

### 11.1 Proposition : sélection par rectangle

- Maintenir **Maj** et glisser (ou activer le mode « Zone ») trace un rectangle ; le glisser simple déplace
  toujours le plan.
- Les éléments désignés **entièrement dans le rectangle** sont listés par calque (« Isolant : 312 éléments »),
  puis retirés en un clic, et remis de la même façon (« Remettre la zone »).
- Stockage : les exclusions existantes (planche + élément), sans changement de format.

### 11.2 Analyse des menuiseries

- Sur un plan, une fenêtre n'est pas **un** élément : c'est un **assemblage** (tableaux du mur, dormant,
  vitrage à 0,24 pt, appui, parfois l'arc d'ouverture). Désigner un trait ne peut donc pas la saisir entière.
- Ce qui est sûr sur un plan, c'est **l'ouverture dans le mur** : une interruption du mur désigné sur la bande
  entre les deux lignes (nu intérieur et nu extérieur). Sa largeur est celle de la baie, son emplacement donne la
  façade et la pièce desservie, et un montant commun à deux fenêtres ne la coupe pas.
- L'élévation donne ce que le plan ne donne pas (hauteur, allège, découpage en vantaux), mais seule elle ne suffit
  pas : façades non dessinées (cours, retraits), niveau d'appartenance incertain sans trame d'axes, textures très
  lourdes (442 000 éléments sur la toiture du projet d'essai).

Recommandation : **baies trouvées sur le plan** (ouvertures dans les murs désignés), **types désignés par
l'exemple** (un rectangle autour d'une fenêtre = modèle ; les assemblages de même composition sont retrouvés sur
tous les plans), **hauteur saisie par type** (réponse Q60), puis **contrôle sur l'élévation** une fois la trame d'axes
(E2) posée.

### 11.3 Questions

- **Q70** — Sélection de zone : Maj + glisser, ou bouton « Zone » ?
- **Q71** — La zone sert-elle seulement à retirer / remettre, ou aussi à désigner ?
- **Q72** — Menuiseries : baies sur le plan + contrôle sur l'élévation (recommandé), élévation seule, ou dessin
  manuel des baies ?
- **Q73** — Deux fenêtres séparées par un montant : une seule baie (dimensions d'ensemble), ou deux ?

## 12. E2 — Repère commun et superposition des niveaux (2026-09-17)

| N° | Décision |
|---|---|
| Q77 → D24 | **Superposition automatique** (décalage calculé sur les murs désignés, contrôle visuel, validation d'un clic) ; la recherche de trame d'axes est abandonnée (révision de Q63/D10). |
| Q74 → D25 | Niveau de référence **choisi**, RDC par défaut. |
| Q75 → D26 | Correction d'un niveau décalé : **glisser le plan** en transparence. |
| Q76 → D27 | **Tous les plans** sont superposés, TOITURE et R+3 compris. |

### 12.1 Existant vérifié

- `ThermiqueLevel` : niveau → planche de plan, hauteurs, **calage A-B** (`calage_json`, deux points cliqués
  communs à tous les niveaux) ; écran « Métré » (M1). Rien n'est encore calé sur le projet de production.
- Aucune détection de trame d'axes dans le code.

### 12.2 Constats sur le projet de production (« TEST », 6 plans au 1/50, lecture seule)

| Sujet | Constat |
|---|---|
| Trame d'axes | **Absente** : aucun trait en tirets, aucune longue ligne d'axe (seuls 4 à 8 traits de plus de 15 m, tous des plumes d'habillage). |
| Format | Six planches de même format (2 384 × 3 997 pt), même échelle, un PDF par planche. |
| Orientation | Bâtiment dessiné **en biais** (murs à environ 80° et 170°). Le calque « mur » désigné est la hachure 0,48 pt à 135° des murs coupés. |
| Superposition | Comparaison des murs désignés (corrélation 2D, tolérance 1 pt) : **R+1, R+2 et R-1 tombent déjà sur le RDC** (décalage 0 à 2 pt, soit 0 à 3,5 cm). R+3 (attique ?) et TOITURE (textures) : pas de correspondance nette. |

Conclusion : sur ce projet, le « point géographique commun » existe déjà, c'est **le cadre du PDF**, parce que
l'architecte a exporté tous les niveaux depuis la même maquette. Chercher une trame d'axes ne servirait à rien ici.

### 12.3 Proposition

1. **Niveau de référence** choisi par l'utilisateur (RDC par défaut).
2. **Contrôle automatique** : pour chaque autre plan, le décalage qui superpose le mieux ses murs sur ceux de la
   référence, avec un indice de confiance ; « déjà superposé » si le décalage est nul.
3. **Vérification visuelle** : le niveau choisi en transparence par-dessus la référence, avec ses murs
   désignés en couleur. L'utilisateur valide d'un clic.
4. **Correction** si besoin : glisser le niveau jusqu'à la superposition (ou deux points A-B, déjà codés).
5. **Trame d'axes** : abandonnée comme méthode principale (Q63 révisée) ; le décalage calculé la remplace.

### 12.4 Questions

- **Q74** — Niveau de référence : RDC imposé, ou choisi par l'utilisateur ?
- **Q75** — Correction d'un niveau décalé : glisser le plan, ou deux points A-B ?
- **Q76** — TOITURE et R+3 : les superposer comme les autres, ou TOITURE hors superposition (sert aux
  toitures, E5) ?
- **Q77** — Trame d'axes abandonnée au profit du cadre du PDF et du décalage calculé (révision de Q63) ?

### 12.5 Livraison (2026-09-17)

- Moteur `thermique_moteur/superposition.py` : image des traits au point près, corrélation (FFT) → 20 candidats
  + translation nulle, note = part des traits du niveau retombant sur la référence (1 pt), affinage ±3 pt
  (départage par le recouvrement exact). États : `superpose` (≤ 1 pt), `decale` (gain ≥ 5 points),
  `incertain` (note < 20 %).
- Sonde de production : tout le dessin > murs désignés (hachures) pour la toiture. Résultats : R+1, R+2,
  TOITURE (0 ; 0), R-1 (0 ; −1), **R+3 (74 ; −39) pt**, confirmé à l'œil (patios, escalier, façades) ;
  1 à 4 s par plan.
- Service `app/services/thermique_superposition.py` ; validation = calage du niveau (A (−dx, −dy),
  B (100 − dx, −dy), `source: superposition`) ; niveau créé pour un plan qui n'en a pas (TOITURE au-dessus) ;
  changement de référence = superpositions validées recalculées.
- API : `GET /projects/{id}/superposition`, `GET …/superposition/proposition?planche_id=&reference_id=`,
  `POST /projects/{id}/superposition`, `DELETE /projects/{id}/superposition/{planche}`.
- Écran : onglet **Superposition** (référence en gris, plan choisi en couleurs de calques, Maj + glisser,
  flèches au point, validation, annulation).

## 13. E3 — Pièces et noms (2026-09-17)

| N° | Décision |
|---|---|
| Q78 → D28 | Pièces **proposées automatiquement** (espaces fermés par les calques), corrections : ajout par clic, fusion, découpe. |
| Q79 → D29 | Noms lus par **reconnaissance de caractères sur le serveur** ; nom toujours modifiable. |
| Q80 → D30 | **Pré-classement** chauffé / non chauffé / extérieur d'après le nom, corrigé d'un clic. |

Lots : E3a pièces (moteur + onglet « Pièces »), E3b lecture des noms, E3c classement.

### 13.1 Existant et constats (projet de production, RDC, lecture seule)

| Sujet | Constat |
|---|---|
| Superpositions (E2) | Aucune validée pour l'instant. Utile avant E4 (zones sur plusieurs niveaux), pas bloquant pour E3. |
| Calques désignés | 2 : « mur » (hachure 0,48 pt gris 152, toutes formes, 1 731 retirés) et « isolant » (0,24 pt gris 128, traits courts, 1 834 retirés). |
| Pièces avec ces seuls calques | Image des éléments désignés, baies refermées jusqu'à 1 m : **1 à 2 espaces clos** (6 et 3 m²). Les cloisons, portes et menuiseries ne sont pas désignées : les pièces communiquent. |
| Noms de pièces | Dessinés : **7 294 petits remplissages noirs** au RDC (lettres en contours), aucun caractère dans le PDF. |
| Code existant | Tracés de zones (`ThermiqueZone`, contour nu intérieur, locaux non chauffés M1) ; aucune détection de pièce ni lecture de texte. |

### 13.2 Proposition

1. **Compléter les calques** (onglet Calques) : cloison ou doublage, menuiserie extérieure, porte. Ce sont les
   limites des pièces.
2. **Pièces proposées automatiquement** : espaces fermés par les calques désignés, portes et baies refermées
   (jusqu'à environ 1 m), entre 1 et 400 m². **Clic dans un espace** pour en ajouter un oublié ; fusion et
   découpe à la main.
3. **Noms lus** dans chaque pièce : les petites formes noires de la pièce sont rendues en image puis lues par
   une **reconnaissance de caractères installée sur le serveur** ; le nom lu reste modifiable.
4. **Classement** chauffé, non chauffé ou extérieur par clic, pré-rempli d'après le nom (garage, parking, local
   vélos : non chauffé ; terrasse, balcon : extérieur) (D11).

### 13.3 Questions

- **Q78** — Pièces : proposées automatiquement avec corrections (recommandé), ou créées une à une par clic ?
- **Q79** — Lecture des noms : reconnaissance de caractères sur le serveur (gratuite, à éprouver), IA de vision
  (plus fiable, coût par plan), ou saisie à la main ?
- **Q80** — Pré-classement chauffé / non chauffé / extérieur d'après le nom lu : oui ou non ?

### 13.4 Livraison E3 (2026-09-17)

- Moteur `thermique_moteur/pieces.py` : image des calques-limites à 5 cm ; **épaississement** de la moitié de la
  fermeture (une fermeture morphologique laisse ouvert l'espace entre deux bouts de cloison alignés) ; espaces
  libres hors bord ; pixels rendus au plus proche jusqu'à la diagonale (angles droits) ; contour par les bords
  des pixels puis Douglas-Peucker ; surface corrigée d'un demi-pixel le long du contour ; ajout par clic,
  fusion (fermeture de la paroi entre deux pièces), découpe par un trait.
- Moteur `thermique_moteur/textes.py` : page rendue à 250 dpi, Tesseract (fra, psm 11), mots replacés en points
  PDF par pdfium ; nom = mots de la pièce (≥ 3 lettres, une voyelle) dans l'ordre de lecture de l'image ;
  repère « 6-B14 » ; pré-classement par mots-clés.
- Essai sur le RDC de production (calques simulés en mémoire : arcs et vantaux de portes, contour 1,56 pt) :
  10 pièces à 1 m de fermeture (bureau, sanitaires, local, poussettes, escalier…), 0,6 s ; lecture des noms
  38 s. Les plateaux ouverts le restent tant que les vitrages ne sont pas désignés.
- Table `thermique_rooms` (migration 0081), service `thermique_pieces.py`, lecture des noms en tâche de fond
  (cache `mots_v1.json` à côté des tuiles).
- API : `GET /sheets/{id}/pieces`, `POST /sheets/{id}/pieces/detecter`, `POST /sheets/{id}/pieces`,
  `POST /sheets/{id}/pieces/fusion`, `PATCH /pieces/{id}`, `DELETE /pieces/{id}`, `POST /pieces/{id}/decoupe`.
- Écran : onglet **Pièces** (clic : choisir ; Maj + clic : plusieurs, fusion ; Alt + glisser : couper ; clic
  hors pièce : ajouter ; nom, classe, surface, totaux par classe).

## 14. Calques : élément seul, lasso « Désigner », vitrages intérieurs (2026-09-17)

Retours de l'utilisateur après E3 :
1. des menuiseries (vitrages) **intérieures** ont la même signature que les extérieures ;
2. pouvoir donner une nature à **un seul élément** ;
3. une menuiserie cliquée ne donne que son cadre : les traits du vitrage entre les cadres (autres signatures,
   souvent plusieurs gris) n'y sont pas.

| N° | Décision |
|---|---|
| Q81 → D31 | Intérieur / extérieur **déduit des pièces** de part et d'autre (extérieure si elle sépare une pièce chauffée de l'extérieur ou d'un local non chauffé) ; nature « menuiserie intérieure » ajoutée pour forcer un cas. Les deux ferment les pièces. |
| Q82 → D32 | Lasso **« Désigner »** : les familles présentes dans la zone sont listées et cochées ; la nature s'applique à ces familles **sur tous les plans** (par défaut) ou **aux seuls éléments de la zone**. Révise D19 (zone = retirer / remettre seulement). |
| D33 | Portée **« Seulement cet élément »** au clic. Désignations ponctuelles stockées dans `signatures_json.elements` (`planche`, `element`, `nature`) ; elles priment sur les règles. |

## 15. Enveloppe thermique avant les pièces : désigner « seulement dans l'enveloppe » (2026-09-17)

| N° | Décision |
|---|---|
| Q83 → D34 | Deux lignes **proposées depuis les calques** puis corrigées (déplacer, ajouter, supprimer un sommet). |
| Q84 → D35 | Nouvel onglet **« Enveloppe »** entre Superposition et Pièces ; lignes enregistrées comme zones du niveau (reprises par le Métré). |
| Q85 → D36 | Portée d'un calque : **partout / dans l'enveloppe / à l'intérieur** ; une même famille peut avoir une nature par portée. |

Demande de l'utilisateur : « c'est pour ça que je t'avais parlé de pouvoir dessiner les zones de surface
thermique au nu intérieur et au nu extérieur : cela permettrait de dire je ne veux sélectionner cet élément que
dans la zone thermique (option) ».

### 15.1 Existant vérifié (production, projet « TEST »)

- Les six niveaux sont **superposés et calés** (E2 validée par l'utilisateur).
- Calques : mur (hachure), isolant, cloison (0,96 pt, droit et polyligne), porte (0,48 pt, petit contour fermé).
- **Aucune** zone tracée (`ThermiqueZone`) : ni nu intérieur (`contour`), ni nu extérieur (`nu_exterieur`).
- Outils existants dans l'onglet Métré : tracé à la main des zones, clic droit pour ajouter un sommet, détection
  « deux lignes » (G1) fondée sur l'ancien moteur de murs, **pas sur les calques** (juste au N-1 du premier
  projet, trop grande ailleurs).

### 15.2 Proposition

1. Nouvel onglet **« Enveloppe »**, entre Superposition et Pièces : par niveau, les deux lignes.
2. **Proposition automatique à partir des calques** : les limites désignées (murs, menuiseries, portes) sont
   épaissies comme pour les pièces ; tout ce qui communique avec le bord du plan est l'extérieur ; son bord est le
   **nu extérieur**. Le **nu intérieur** est le bord de l'espace libre situé juste derrière le mur de façade.
   Patios et cours intérieures : lignes propres.
3. **Corrections** : déplacer un sommet, clic droit pour en ajouter un, supprimer ; le niveau de dessous
   s'affiche en repère (les niveaux sont superposés).
4. Enregistrement dans les zones existantes (`contour` et `nu_exterieur` du niveau) : le Métré les reprend.
5. **Calques, option « Où ? »** pour une famille : partout / **dans l'enveloppe** (entre les deux lignes) /
   **à l'intérieur** (en deçà du nu intérieur). Un élément est « dans l'enveloppe » si tous ses points sont dans le
   nu extérieur (à 10 cm près) et aucun à plus de 10 cm à l'intérieur du nu intérieur.
6. Pièces (E3) : inchangées ; les menuiseries de l'enveloppe sont alors extérieures sans attendre E4.

### 15.3 Questions

- **Q83** — Lignes : proposées depuis les calques puis corrigées (recommandé), tracées à la main, ou détection G1 ?
- **Q84** — Où : nouvel onglet « Enveloppe » (recommandé) ou dans l'onglet Métré ?
- **Q85** — Options de portée d'un calque : partout / dans l'enveloppe / à l'intérieur (recommandé), ou seulement
  partout / dans l'enveloppe ?

### 15.4 Livraison (2026-09-17)

- Moteur `thermique_moteur/bande.py` : proposition des deux lignes (`proposer`), décalage d'un demi-pixel vers
  l'axe des traits-limites, filtre `Bande` (tolérance 10 cm) ; `calques.membres` / `attribuer` appliquent la
  portée ; une règle restreinte ne s'applique pas sur un plan sans lignes.
- Moteur des pièces : pixels rendus par **croissance pas à pas sans franchir de limite** (avant : au plus
  proche, à travers les traits ; une pièce ou l'extérieur gagnait l'intérieur des murs creux).
- Service `thermique_enveloppe.py` ; route `POST /niveaux/{id}/proposer-enveloppe` ; règles avec `perimetre` ;
  route famille `?perimetre=` ; onglet **Enveloppe** (proposer, glisser un sommet, clic droit : ajouter,
  Alt + clic : retirer) ; option **« Où ? »** dans Calques (clic et lasso).
- Essai en production (calques réels, rien enregistré) : RDC à 3 m de fermeture → un bâtiment de 1 060 m² au nu
  extérieur, 676 m² au nu intérieur, contours qui suivent les façades mais festonnés là où les vitrages ne sont
  pas désignés ; R+3 inexploitable tant que la texture de terrasse reste dans le calque « mur » (même signature
  que la hachure des murs, à retirer au lasso).
