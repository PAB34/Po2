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
