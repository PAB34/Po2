# Détection guidée des murs et des menuiseries — décisions

> Sujet ouvert le 2026-09-14 à la demande de l'utilisateur : « appliquer une autre méthode pour la détection des
> murs et des menuiseries, qui allie pré-détection, puis utilisateur, puis détection automatique complète après
> validation, permettant d'identifier les types de murs et les types de menuiseries ».
> Prolonge `detection-murs-strategie.md` (moteur vectoriel) ; ne le remplace pas.

## 1. Existant vérifié

| Élément | État |
|---|---|
| Moteur vectoriel `thermique_moteur/vecteurs.py`, `murs.py` | En production (PR #190). Mur = paire de faces parallèles ; épaisseur exacte ; parois composées ; murs courbes. |
| Affichage « Murs du plan » (Métré) | En production : polygones colorés par épaisseur, types par épaisseur, création du composant. Pas de validation mur par mur. |
| Résultats | N-1 : 78 murs, aucune face inexpliquée. N0 à N3 : faux murs (8, 47, 49, 69 cm…) venant d'escaliers, de symboles, d'équipements. |
| Arcs sans partenaire | 24 à 42 par niveau (N0-N3) : pour la plupart des **débattements de portes**, donc des candidats menuiseries. |
| Textes du PDF | **Aucun caractère** : étiquettes (« CF1/2H+FP », « 75x1.6 », noms de locaux) dessinées en contours. Lecture impossible sans lecture visuelle (Claude Code, §10 d'`agent-verification-decisions.md`). |
| Calques du PDF | Aucun calque (OCG) sur le projet d'essai. À relire sur chaque nouveau projet : s'il y en a, ils deviennent un indice fort. |
| Façades PC08-PC09 | Chemins vectoriels + 29 images : hauteurs de baies lisibles en vectoriel, à confirmer. |
| Bibliothèque | Catégories `murs` (préfixe MUR) et `menuiseries` (préfixe F) existantes. |

## 2. Méthode proposée : pré-détection → validation par l'exemple → détection complète

### Étape 1 — Pré-détection (automatique, large)
- **Murs candidats** : toutes les paires de faces, comme aujourd'hui, avec leur **signature graphique** :
  plume des faces (largeur, gris), épaisseur, remplissage (teinte de l'aplat ou vide), motif d'isolant
  (hachures, pas, angle), couches de la paroi composée.
- **Menuiseries candidates** : trous dans un mur entre deux jambages (fins de mur face à face, même
  épaisseur, même axe), avec leur signature : largeur de baie, traits fins parallèles dans l'épaisseur
  (dormant, vitrage), arc de débattement (porte battante, sens, nombre de vantaux), allège ou non.
- Chaque candidat reçoit un **groupe** : candidats de signature identique (ex. « 20 cm, aplat gris 152,
  sans isolant »).

### Étape 2 — Validation par l'utilisateur (quelques clics, par groupe)
- L'utilisateur voit les groupes, pas 150 murs un par un. Pour chaque groupe : **valider** (et nommer le
  type ou le rattacher à un composant), **rejeter** (« pas un mur : escalier »), ou **séparer** (deux
  types différents qui se dessinent pareil).
- Il peut aussi corriger à la main : ajouter un mur oublié en cliquant ses deux faces, supprimer un faux mur,
  désigner une baie.
- Chaque décision enregistre une **règle apprise** liée au projet : signature → type validé, ou signature →
  rejet. Rien n'est appris « en boîte noire » : chaque règle reste lisible et annulable.

### Étape 3 — Détection automatique complète
- Les règles apprises s'appliquent à **tous les niveaux et toutes les planches** du projet.
- Sortie : chaque mur et chaque baie reçoit un **type** (composant de la bibliothèque) ; ce qui ne correspond
  à aucune règle part dans une liste **« à revoir »** (jamais classé en silence).
- Métrés par type : linéaire et surface de murs par composant, nombre et dimensions des menuiseries par type.
- Les règles sont réutilisables sur un autre projet du même cabinet d'architecte (même charte graphique).

### Mesure
- Score contre la vérité terrain (`evaluation.py`) avant et après validation : part classée, part à revoir,
  faux murs, erreurs de type. Objectif : 100 % classé ou « à revoir », 0 erreur de type silencieuse.

## 3. Décisions

| N° | Date | Décision |
|---|---|---|
| D1 | 2026-09-14 | Méthode en 3 étapes ci-dessus, adoptée à la demande de l'utilisateur, sur le moteur vectoriel existant. |
| D2 | 2026-09-14 | Validation par **groupes de signature**, pas mur par mur ; corrections unitaires possibles. |
| D3 | 2026-09-14 | Règles apprises lisibles et annulables, stockées par projet ; aucun classement silencieux. |

## 4. Questions

- **Q58** — Où valider : directement sur le plan (clic sur un mur ou un groupe) ou dans une liste de cartes par groupe ?
- **Q59** — Échantillon : valider un niveau puis propager à tous, ou valider chaque niveau ?
- **Q60** — Hauteurs des menuiseries : saisie par type, lecture sur les façades, ou lecture des étiquettes par Claude Code ?
- **Q61** — Ordre : murs d'abord puis menuiseries, ou les deux dans la même passe ?

## 5. Réponses (2026-09-14)

- **Q58** — Sur le plan (option 1). **Et changement de méthode** : « conserver la détection au nu intérieur en
  étape une et ajouter le nu extérieur, avec la possibilité d'ajouter des points sur les lignes par un clic
  droit. Une fois ces deux lignes réalisées, on a théoriquement tout à intégrer comme composant de l'enveloppe,
  plus la détection des éléments de structure intérieurs. »
- **Q59** — Un niveau représentatif validé, puis propagation à tous les niveaux ; les cas nouveaux vont dans « à revoir ».
- **Q60** — Hauteur saisie une fois par type de menuiserie.
- **Q61** — Murs d'abord, menuiseries ensuite.

## 6. Méthode révisée : deux lignes, puis tout le reste

| N° | Date | Décision |
|---|---|---|
| D4 | 2026-09-14 | Étape 1 par niveau = **deux lignes fermées** : nu intérieur et nu extérieur. Pré-détectées, puis corrigées par l'utilisateur (glisser un sommet, **clic droit sur une ligne = ajouter un sommet**). |
| D5 | 2026-09-14 | Les deux lignes sont pré-détectées **sur le réseau de murs vectoriels** (faces extérieure et intérieure des murs périphériques), et non plus sur l'image : c'est la cause des erreurs dans les angles. |
| D6 | 2026-09-14 | **Bande entre les deux lignes = enveloppe** : chaque tronçon donne épaisseur, signature (remplissage, isolant) et type de mur, à valider sur le plan ; les interruptions de la bande sont les baies (lot menuiseries). |
| D7 | 2026-09-14 | **Murs vectoriels à l'intérieur du nu intérieur = structure intérieure** (refends, cloisons, gaines), classés à part, validés par groupe sur le plan. |
| D8 | 2026-09-14 | Validation sur un niveau, propagation des règles aux autres ; hauteur des menuiseries par type ; murs avant menuiseries. |

### Constats G1 sur le projet d'essai (2026-09-14)

| Niveau | Nu extérieur / nu intérieur proposés | Écart constaté |
|---|---|---|
| −1 | 942,5 / 905,7 m², 4 sommets chacun | Juste : faces des murs de 30 cm, façade oblique comprise. |
| 0 | ≈ 955 / 910 m² | Trop grand : pointes des brise-soleil et abri vélo inclus. |
| 1 | ≈ 962 / 914 m² | Trop grand : coursive et terrasse basse incluses ; bosse sur la façade droite. |
| 2 | ≈ 955 / 914 m² | Trop grand : terrasse de lecture incluse. |
| 3 (toiture) | ≈ 800 / 750 m² | Plausible, à vérifier. |

- Façades vitrées : les vitrages sont des traits fins (0,24 pt), pas des paires de faces. Sans eux, l'emprise
  fuit (lignes aberrantes). Avec toutes les plumes fines, l'emprise tient mais inclut terrasses et débords.
- Écarter la plume d'habillage (0,36 pt) a été essayé : l'emprise fuit de nouveau (niveau 2 : 31 m²). Abandonné.
- Suite prévue en G2 : terrasses reconnues par leurs rayures (zone dense de traits parallèles hors murs) et
  brise-soleil (murs saillants hors de la ligne de vitrage) écartés du nu extérieur.

### Lots

| Lot | Contenu | Livrable visible |
|---|---|---|
| **G1** | Nu extérieur (nouveau type de tracé), clic droit pour ajouter un sommet, pré-détection des deux lignes depuis les murs vectoriels. | Bouton « Détecter les deux lignes » : nu intérieur et nu extérieur tracés, corrigeables. |
| **G2** | Bande d'enveloppe découpée en tronçons typés (épaisseur, remplissage, isolant) ; structure intérieure à part ; validation par groupe sur le plan (valider, rejeter, séparer, rattacher à un composant). | Enveloppe colorée par type validé, structure intérieure en gris, liste « à revoir ». |
| **G3** | Règles apprises par projet, propagées à tous les niveaux. | Un seul niveau validé, les autres classés automatiquement. |
| **G4** | Baies : interruptions de la bande, jambages, arcs de portes, traits de vitrage ; types de menuiseries ; hauteur par type. | Menuiseries par type avec largeur, hauteur, nombre. |
