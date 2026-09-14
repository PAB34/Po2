---
type: decisions
status: actif
read_policy: si la tâche concerne le métré sur les plans (géométrie, niveaux, ponts thermiques)
related:
  - etape2-geometrie-decisions.md
  - bibliotheque-projet-decisions.md
  - metre-thermique-decisions.md
---

# Outil thermique — métré sur les plans : contour de référence, niveaux, détection et composants

> Fichier « fil du dev » écrit **avant** de coder (2026-09-14). Il remplace le découpage des étapes 2
> et 3 de `metre-thermique-decisions.md` par une méthode unique, fondée sur la façon de travailler
> du thermicien décrite par l'utilisateur et sur les règles Th-Bât (fascicules « méthodes »).

## 1. Où en est-on (existant vérifié sur `main`, 2026-09-14)

| Élément | État |
|---|---|
| Import des plans, visionneuse en tuiles, nature de planche, échelle contrôlée par une cote, outil « mesurer » | **En prod** (étape 1, migration 0076) |
| Bibliothèque de projet et modèles (murs, planchers bas / intermédiaires / hauts, menuiseries, ponts thermiques ; catégorie avec « donne sur ») | **En prod** (L1 + L2, migration 0077) |
| Lecture des traits d'un PDF et filtre par épaisseur de trait | **Prototype seulement** (`proto_detection_murs.py`, niveau 0 du projet exemple) |
| Niveaux ordonnés, calage entre plans, nord | **Rien** : la planche n'a qu'un libellé de niveau (`level_label`) |
| Contour, murs, baies, planchers, ponts thermiques sur le plan | **Rien** |
| Projet de test | `Thermique/PLAN EXEMPLE PROJET` : niveaux −1, 0, 1, 2, 3, toiture, coupes AB et CD, façades, plan masse |
| Calcul de polygones | `numpy` présent ; **`shapely` absent** (ni en local ni dans `requirements.txt`) |

**En clair : la modélisation du métré sur les plans n'a pas commencé.** Seuls le socle (plans,
échelle, mesure) et la bibliothèque existent.

## 2. La méthode du thermicien, formalisée

Description de l'utilisateur : on dessine d'abord une **ligne au nu intérieur des murs extérieurs**
qui entourent les locaux chauffés, en général au rez-de-chaussée ; on la **décalque** sur le R−1 et
le R+1 pour en déduire les surfaces chauffées / non chauffées et les ponts thermiques ; on fait de
même à chaque niveau.

### 2.1 Ce que disent les règles Th-Bât (vérifié dans les fascicules)

| Règle | Source |
|---|---|
| **Seules les dimensions intérieures** servent au calcul des déperditions ; décrochements, angles rentrants et baies mesurés côté intérieur | Généralités §3.5, fig. 5 |
| Parois déperditives = celles qui séparent le volume chauffé de l'**extérieur**, du **sol** ou d'un **local non chauffé** | Généralités §3.3 |
| Cloisons légères ignorées ; cas des planchers bas avec refend ou poutre à retombée | Généralités §3.5 fig. 6 et 7 |
| Hauteur intérieure d'une paroi verticale avec faux plafond : incluse si la résistance est conservée, sinon arrêtée au faux plafond | Généralités §3.5 fig. 8 |
| « **Volume intérieur** » (cage, circulation sans paroi extérieure) : chauffé ou non selon ouvertures, sas, et si le linéaire vers l'extérieur ou LNC (c + d) est inférieur au linéaire vers le chauffé (a + b) | Généralités §3.3 fig. 3 |
| Linéaires des ponts thermiques **déterminés à partir des dimensions intérieures** ; ponctuels comptés en nombre | Ponts thermiques §1 |
| Plancher **bas** = chauffé au-dessus seulement ; **intermédiaire** = chauffé des deux côtés ; **haut** = chauffé en dessous seulement | Ponts thermiques §1.3.1 |
| Liaisons **périphériques** (au pourtour du plancher) et **intermédiaires** (à l'intérieur du pourtour) | Ponts thermiques §1.3.1 |
| ψ < 0,03 W/(m.K) négligeable (sauf ponts intégrés) ; liaison dont une paroi donne sur l'extérieur ou le sol = donne sur l'extérieur | Généralités §3.4 |
| Poutrelles : ψ moyen = pondération about / rive par les linéaires, ou **60 % about / 40 % rive** par défaut | Ponts thermiques p. 16 |
| Indicateurs **Ratio ψ** (Σψ·l / surface de référence) et **ψ9** (moyenne des liaisons plancher intermédiaire / mur) | Généralités §4.1 et §4.2 |
| Coefficient **b** d'un local non chauffé : calculé (Aiu, Aue, débits) ou tabulé par type de local | Généralités §5 |

La méthode de l'utilisateur est donc exactement celle des règles : **le contour au nu intérieur est
l'objet de base**, tout le reste s'en déduit.

### 2.2 Méthode proposée, rendue robuste

1. **Niveaux** : ordre, altitude du plancher fini, hauteur d'étage, épaisseur du plancher ; une
   planche « plan » par niveau ; **calage** de chaque plan sur le niveau de référence (deux points
   communs, décision Q10) ; **nord** posé une fois (Q11).
2. **Contour de référence** par niveau : un ou plusieurs polygones fermés au **nu intérieur** des
   parois déperditives (plusieurs volumes, patios en trous). Proposé automatiquement (§4), corrigé à
   la main avec aimantation sur les traits du plan.
3. **Qualification de chaque côté** du contour : donne sur **extérieur**, **local non chauffé**
   (nommé : garage, cave, cage d'escalier, combles perdus, vide sanitaire…), **sol** (mur enterré),
   **bâtiment chauffé mitoyen** (non déperditif) ; plus le **composant** mur rattaché.
4. **Locaux non chauffés** dessinés comme polygones par niveau, avec leur type (pour b).
5. **Superposition automatique** du niveau N avec N−1 et N+1 (calque fantôme à l'écran) et
   **déduction** des planchers et des liaisons (§3).
6. **Baies** posées sur les côtés (largeur lue sur le plan, hauteur saisie ou lue en façade / coupe),
   rattachées à un composant menuiserie ; orientation déduite du nord et de la normale du côté.
7. **Points singuliers** : refends et poteaux qui touchent le contour, angles (déduits des sommets).
8. **Récapitulatif** par composant, niveau et orientation : surfaces nettes, linéaires, nombres ;
   Ubât, Ratio ψ, ψ9 ; export tableur puis Pléiades / Perrenoud (Q18).

Principe : **seuls les objets dessinés sont enregistrés** (contours, côtés qualifiés, LNC, baies,
refends) ; surfaces, linéaires et ponts thermiques sont **recalculés** à chaque modification. Une
valeur peut être forcée à la main, elle est alors marquée « forcée ».

## 3. Superposition des niveaux : la règle de déduction

### 3.1 Surfaces horizontales

Avec C(N) la zone chauffée du niveau N (contour moins LNC) :

| Zone | Déduction | Type |
|---|---|---|
| C(N) ∩ C(N−1) | Chauffé dessus et dessous | Plancher **intermédiaire** (non déperditif) |
| C(N) − C(N−1) | Chauffé dessus, pas dessous | Plancher **bas** de N : sur **extérieur** (porche, encorbellement, pilotis), sur **LNC** si un LNC est dessous, sur **terre-plein / vide sanitaire / sous-sol** au niveau le plus bas |
| C(N) − C(N+1) | Chauffé dessous, pas dessus | Plancher **haut** de N : **toiture-terrasse** / terrasse accessible, sous **combles perdus** (LNC), **rampant** si le niveau est sous toiture (coupe) |
| « Vide sur » (double hauteur, trémie importante) | Zone marquée dans C(N+1) | Pas de plancher ; les murs du niveau inférieur prennent la double hauteur |

### 3.2 Liaisons plancher / mur : la règle des quatre quarts

Chaque portion de ligne où un mur rencontre un plancher est entourée de **quatre quarts** : dessus /
dessous × côté intérieur / côté extérieur du mur. En lisant l'état de chaque quart dans la
superposition (chauffé, LNC, extérieur, sol), le type de liaison sort sans ambiguïté :

| Dessus intérieur | Dessous intérieur | Liaison déduite |
|---|---|---|
| chauffé | chauffé | Plancher **intermédiaire** / mur (entre dans ψ9) |
| chauffé | LNC, vide sanitaire, sol, extérieur | Plancher **bas** / mur |
| extérieur, combles perdus | chauffé | Plancher **haut** / mur (acrotère si toiture-terrasse) |
| chauffé (mur en retrait) | chauffé, décalé | **Décroché** : plancher haut du dessous + mur du dessus posé sur la terrasse |
| chauffé | chauffé, avec dalle extérieure continue | Plancher intermédiaire / mur **avec balcon ou loggia** |

On découpe toutes les arêtes de C(N) et C(N−1) aux points où l'état change : une façade qui se
décale au droit d'un étage est ainsi traitée par morceaux, ce qui est précisément ce que le
thermicien obtient en décalquant. Tolérance d'alignement entre niveaux : épaisseur du mur (un nu
intérieur qui bouge de 2 cm n'est pas un décroché).

### 3.3 Catalogue des ponts thermiques générés

| Pont thermique | Mesure | Référence Th-Bât |
|---|---|---|
| Plancher bas / mur | Linéaire de la liaison | ITI / ITE / ITR / DC.1, fascicule §3.1.1 |
| Plancher bas / refend (intermédiaire) | Linéaire du refend sur le plancher bas | §3.1.3, DC.7 ; déjà dans Ue si terre-plein / vide sanitaire |
| Plancher intermédiaire / mur (ψ9) | Linéaire ; about / rive si poutrelles | ITI.2, ITE.2, ITR.2, p. 16 |
| Plancher haut / mur, acrotère | Linéaire | §3.3.1, additif ITE.3 |
| Plancher haut / refend | Linéaire du refend sous plancher haut | §3.3.2 |
| Mur / refend | Nombre de refends × hauteur intérieure | §3.4.2 (dont mur sur décroché) |
| Angle sortant / rentrant | Nombre de sommets × hauteur intérieure | §3.4.1 |
| Menuiserie / mur : appui, linteau, tableaux | Largeur (appui), largeur (linteau), 2 × hauteur (tableaux) | §3.5, ITI.5, ITE.5 |
| Seuil de porte | Largeur des portes et portes-fenêtres | DC.3, ITI.6, ITE.6 |
| Menuiserie / refend, fenêtre de toit / rampant | Linéaire | DC.5, DC.4 |
| Balcon, loggia | Linéaire de dalle extérieure | Fascicules d'application |
| Poteaux en plancher bas (ponctuel χ) | Nombre | DC.6 |

Tous les ponts sont **mesurés**, même ceux dont ψ < 0,03 (signalés « négligeables » plutôt
qu'omis), pour que le thermicien voie ce qui a été écarté. Le **type d'isolation** (ITI, ITE,
répartie, mixte) est déduit de la composition du mur rattaché (position de la couche isolante), ce
qui oriente vers la bonne ligne des tableaux Th-Bât (lot B3).

## 4. Détection automatique et rattachement aux composants

Souhait de l'utilisateur : que l'outil détecte les catégories et les composants de la bibliothèque et
les modélise sur le plan (couleur, symbole).

### 4.1 Chaîne de détection

```
traits du PDF (ou DXF) ─► zone utile ─► classes d'épaisseur de trait
  ─► MURS    : faces épaisses appariées → axe, épaisseur, longueur (obliques et arcs compris)
  ─► ENVELOPPE : murs dont une face borde l'extérieur de l'emprise
  ─► CONTOUR PROPOSÉ = face intérieure de l'enveloppe, fermée, par niveau
  ─► BAIES   : interruptions des murs d'enveloppe ; porte = arc, fenêtre = traits fins
  ─► REFENDS / POTEAUX : murs et contours fermés qui touchent le contour
  ─► hachures et remplissages conservés comme indice de matériau
```

La détection **propose**, le thermicien **valide** : chaque objet garde sa source
(automatique / corrigé / manuel) et une correction n'est jamais écrasée par une nouvelle détection
(décision D5 de l'étape 2).

### 4.2 Des « types géométriques » aux composants

- Les côtés du contour sont **regroupés** par épaisseur de mur (± 1 cm), motif de hachure et
  « donne sur ». Chaque groupe devient une **proposition** : « mur de 30 cm sur extérieur — 86 m sur
  4 niveaux ».
- Pour chaque proposition : **rattacher** à un composant existant (suggestion par épaisseur totale
  et catégorie) ou **créer** le composant, catégorie et « donne sur » préremplis, code proposé
  (MUR 3). Les baies sont regroupées de même par largeur × hauteur (F1, F2…), les liaisons par type
  de pont thermique (PT 1…).
- Un composant peut être rattaché avant d'être complet : le métré avance en « hypothèse », la
  composition se précise ensuite (statut par composant, Q35).

### 4.3 Représentation sur le plan

- **Une couleur par composant**, choisie automatiquement et modifiable, reprise sur la carte de la
  bibliothèque (pastille) : trait épais le long du côté intérieur pour les murs, étiquette du code.
- Planchers : aplat translucide (bas, haut, intermédiaire), avec motif différent par type.
- Menuiseries : repère rectangulaire au droit de la baie, code (F1) et orientation.
- Ponts thermiques : trait pointillé coloré pour les linéaires, symboles pour les ponctuels et les
  verticaux (▲ refend, ◆ angle, ● poteau).
- **Survol et sélection croisés** : cliquer une carte de la bibliothèque surligne toutes ses
  occurrences sur les plans ; cliquer un élément du plan ouvre sa carte. Légende = bibliothèque.
- Calques activables : niveau inférieur / supérieur en fantôme, LNC, ponts thermiques.

## 5. Pièges à couvrir (robustesse)

| Cas | Traitement |
|---|---|
| Plans d'échelle, d'origine ou de rotation différentes | Calage par deux points communs (Q10), contrôle de l'échelle par une cote |
| Contour non fermé, traits qui se chevauchent | Fermeture assistée, alerte sur les trous et les auto-intersections |
| Plusieurs bâtiments ou volumes, patios | Plusieurs polygones et trous par niveau |
| Garage, cave, local technique **dans** l'emprise | LNC dessiné : ses côtés communs avec C(N) deviennent des murs sur LNC |
| Cage d'escalier, circulation | Aide à la règle « volume intérieur » (linéaires a + b et c + d calculés) |
| Mitoyenneté | Côté « bâtiment chauffé mitoyen » non déperditif ; bâtiment adjacent non résidentiel à part |
| Façade en retrait ou en débord d'un étage à l'autre | Règle des quatre quarts (§3.2) |
| Double hauteur, mezzanine, demi-niveau | Zones « vide sur », niveau partiel, hauteur par zone |
| Combles aménagés, rampants, toitures en pente | Plancher haut de type rampant, hauteur lue sur les coupes |
| Sous-sol semi-enterré, terrain en pente | Côté « sol » avec profondeur (lot B2c) |
| Murs courbes et obliques | Arcs discrétisés, longueurs exactes |
| Balcons, loggias, acrotères | Dalle extérieure détectée hors contour, pont thermique dédié |
| Poutrelles de sens inconnu | 60 / 40 par défaut ; sens tracé par zone de plancher si connu |
| Faux plafonds | Hauteur intérieure selon Généralités fig. 8 |
| Scans | Pas de détection : tracé à la main, même outil et mêmes calculs |
| Surfaces réglementaires (SHAB, SU, Sref) | Hors contour : nécessitent les pièces (plus tard, Q44) |

## 6. Décisions proposées (à valider)

| # | Proposition | Raison |
|---|---|---|
| MP-D1 | **Contour de référence au nu intérieur, par niveau** = objet central du métré | Méthode du thermicien = règles Th-Bât §3.5 |
| MP-D2 | Planchers et ponts thermiques **déduits** de la superposition des niveaux (§3), jamais ressaisis ; forçage manuel possible et signalé | Une seule source de vérité, recalcul instantané |
| MP-D3 | Règle des **quatre quarts** pour typer chaque portion de liaison | Robuste aux décrochés, porches, LNC partiels |
| MP-D4 | Détection = **proposition** ; même outil pour corriger, tracer à la main et traiter les scans | Exigence « irréprochable », scans |
| MP-D5 | Rattachement par **types géométriques** proposés automatiquement → composants de la bibliothèque, **couleur par composant** | Souhait utilisateur ; lien bibliothèque ↔ plan |
| MP-D6 | Calculs géométriques dans le **moteur autonome** `thermique_moteur/` ; ajout de **`shapely`** (opérations sur polygones éprouvées) | Superposition fiable ; voie « logiciel » gardée |
| MP-D7 | Tous les ponts mesurés, les négligeables signalés et non omis | Traçabilité pour le thermicien |

## 7. Découpage proposé

| Lot | Contenu | Livrable visible |
|---|---|---|
| **M1 — Niveaux et contour** | Niveaux (ordre, altitudes, hauteurs), calage, nord ; tracé du contour avec aimantation sur les traits ; qualification des côtés ; LNC ; niveaux voisins en fantôme | Le RDC du projet exemple a son contour, calqué sur le R−1 et le R+1 |
| **M2 — Déductions** | Planchers bas / hauts / intermédiaires, murs (côté × hauteur), liaisons plancher / mur par les quatre quarts, angles ; récapitulatif | Surfaces et linéaires de tout le bâtiment, par niveau |
| **M3 — Détection** | Murs, enveloppe, **contour proposé automatiquement**, contrôle ± 1 cm sur les cotes | Contour du projet exemple proposé sans clic |
| **M4 — Baies et refends** | Baies détectées, menuiseries, orientation, appuis / linteaux / tableaux / seuils, refends | Métré des menuiseries et des ponts verticaux |
| **M5 — Composants sur le plan** | Types géométriques → composants, couleurs, sélection croisée, Ubât, Ratio ψ, ψ9, export tableur | Le plan est « coloré » par la bibliothèque |

## 8. Questions ouvertes

- **Q39 — Ordre.** Outil de contour et déductions d'abord (M1, M2), détection ensuite (M3) ; ou
  détection d'abord ?
- **Q40 — Hauteurs.** Saisies par niveau (altitude, hauteur d'étage, épaisseur de plancher) au
  départ, lecture des coupes plus tard ; ou lecture des coupes tout de suite ?
- **Q41 — Poutrelles.** 60 / 40 par défaut ; tracer le sens des poutrelles par zone doit-il être
  proposé dès le départ ?
- **Q42 — Couleurs.** Une couleur par composant (MUR 1, MUR 2…) ou par catégorie ?
- **Q43 — Liste des ponts thermiques.** Le catalogue du §3.3 est-il complet pour votre pratique ?
  Les angles mur / mur sont-ils comptés ?
- **Q44 — Surfaces réglementaires.** SHAB / SU / Sref calculées par l'outil (pièces à dessiner) ou
  saisies ?
- **Q45 — Tolérance de superposition.** Un nu intérieur décalé de moins d'une épaisseur de mur est-il
  toujours considéré comme aligné ?

## 9. Réponses (2026-09-14)

- **Q39** : contour d'abord (M1 + M2), détection ensuite (M3).
- **Q40** : hauteurs saisies par niveau ; lecture des coupes plus tard.
- **Q41** : 60 / 40 par défaut ; tracé du sens des poutrelles plus tard.
- **Q42** : une couleur par composant.
- Q43, Q44, Q45 : valeurs par défaut du document (catalogue §3.3 avec angles comptés, surfaces
  réglementaires hors périmètre, tolérance = épaisseur du mur), à revoir à l'usage.
- **Prochain : M1** (niveaux, calage, nord, contour tracé avec aimantation, côtés qualifiés, LNC,
  niveaux voisins en fantôme).

## 10. Lot M1 livré (2026-09-14)

| Élément | Réalisation |
|---|---|
| Traits d'aimantation | `thermique_moteur/traits.py` : chemins **tracés** lus par pdfium (formulaires imbriqués compris), classes d'épaisseur, seuil proposé = classes ≥ 1,9 × plume médiane pondérée par la longueur. Projet d'essai : seuil 0,96 pt sur les niveaux −1 à 2, 250 à 630 traits, 0,6 s par plan ; cache par planche et seuil |
| Repère commun | Calage A-B par niveau (points PDF de sa planche) ; origine A, axe x vers B, mètres ; contrôle des distances A-B entre niveaux (alerte au-delà de 5 cm) |
| Nord | Deux clics sur un niveau calé → angle dans le repère commun, stocké sur le projet |
| Tracés | Contour chauffé, local non chauffé (type), patio ; stockés en points PDF ; une qualification par côté (donne sur, composant mur) |
| Synthèse | Surfaces (contour, LNC et patios déduits s'ils sont dedans, par échantillons le long des côtés), linéaires par « donne sur », hauteur intérieure = hauteur d'étage − plancher, surfaces brutes de murs ; alertes : tracé qui se recoupe, local qui déborde, échelle absente |
| Niveaux | Créés depuis les libellés de planches (« Niveau −1 », « RDC », « R+2 »… ; toiture exclue) ou à la main ; ordre modifiable |
| Écran | Onglet « Métré » : outils Déplacer, Contour, Local non chauffé, Patio, Modifier (glisser un sommet, Maj + clic ajoute, Alt + clic retire), Caler, Nord ; aimantation (sommets, extrémités, croisements, traits), Maj = orthogonal, Alt = libre ; calques des niveaux voisins ; côtés colorés par « donne sur » |
| Données | Migration `0078` : `thermique_levels`, `thermique_zones`, `thermique_projects.north_deg` |

Limites connues, traitées plus tard : cadre et cartouche aussi aimantés (zone utile au lot M3) ;
local qui déborde du contour déduit en entier (opérations exactes sur polygones au lot M2).
