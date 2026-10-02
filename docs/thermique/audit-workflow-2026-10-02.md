---
read_policy: lire avant de proposer un lot qui touche au parcours complet ; complète bilan-et-plan-2026-10-02.md
---

# Audit du processus complet de l'outil thermique (2026-10-02)

Demande du thermicien : un point sur tout le workflow, avec ses failles, faiblesses, forces et améliorations.
Base : le code en production (`624ff0a3`), les fichiers de décisions et les mesures faites. Repères : 27 services
serveur, 50 fichiers de décisions, environ 290 tests serveur et 226 tests écran, `WorkspacePage.tsx` de 1 786 lignes.

Légende : **faille** = produit un résultat faux ou un risque sans prévenir ; **faiblesse** = coûte du temps ou de
la fiabilité ; **force** = ce qu'il faut préserver.

## 0. Le workflow en une page

| # | Étape | Qui | Résultat |
|---|---|---|---|
| 1 | Dépôt des PDF, tri en planches (plan, coupe, façade), niveau, échelle, rotation | thermicien + serveur | planches |
| 2 | Nord, calage des niveaux entre eux | thermicien | repère commun |
| 3 | « Analyser » : file d'attente → relais sur le poste → chaîne d'agents IA | serveur + relais + IA | étude du niveau importée |
| 4 | Recalcul : réunion des morceaux, exposition, découpage pièce par pièce, dessin, fiches, couverture, cohérence | serveur (algorithmes) | étude affichée, versionnée |
| 5 | Parcours de 6 étapes : Planche, Analyse, Locaux et hauteur, Parois, Menuiseries, Ponts | thermicien | relevé validé |
| 6 | Coupes et élévations : vues créées à la main, hauteurs, modèles de menuiseries | thermicien | hauteurs, modèles |
| 7 | Livrable : déperditions par local, export | — | **n'existe pas** |

## 1. Dépôt, planches, échelle

- **Forces** : tri automatique par nom de fichier ; rendu raster en tuiles ; échelle contrôlée par une cote.
- **Faiblesse** : l'échelle est arrondie à l'échelle usuelle si l'écart est inférieur à 1 % (`standard_scale_near`).
  Le calage révèle l'écart, mais les métrés héritent de l'arrondi (question ouverte depuis le 2026-09-30).
- **Amélioration** : afficher l'écart mesuré et laisser le thermicien choisir « échelle mesurée » ou « échelle
  usuelle ».

## 2. Nord et calage des niveaux

- **Forces** : calage « comme Aligner d'AutoCAD », validé par le thermicien ; calque fantôme du voisin ; le nord
  recalcule l'exposition de toutes les études.
- **Faiblesse** : le calage n'est encore exploité par rien (report entre niveaux D233–D237 en attente).
- **Amélioration** : c'est la base du report du R+1 vers les autres niveaux. C'est le levier le moins coûteux
  pour les niveaux suivants.

## 3. Analyse par l'IA

- **Forces** : chaîne complète et reproductible (inventaire, puis pièces recalées, locaux, façade, complément, découpage) ;
  reprise après coupure ; journal ; catalogue appris réutilisable.
- **FAILLE n° 1 — mauvais modèle en production.** « Analyser » sur le site passe par le relais du poste, qui lance
  `run_etude_niveau.py --mode cli --model opus`. La commande `claude` du poste traduit cet alias par
  **claude-opus-4-7** et non par Opus 5 (traces du R+2, du RDC et du SS1). Le R+1, fait en session, tournait sur
  Opus 5. Remplacement silencieux, contraire à la règle. **À corriger avant toute nouvelle analyse** : nom de modèle
  exact, et arrêt si la trace montre un autre modèle.
- **Faille n° 2 — l'IA donne des coordonnées.** 10 % des nus faux de plus de 11 à 21 cm, cadres des baies d'un même
  modèle de −14 à +90 cm, coupes 0/13. Tout ce qui en sort doit être revérifié.
- **Faiblesse — coût sans compteur.** 20 000 à 48 000 jetons de sortie par lecture, une dizaine de lectures par
  niveau ; aucun budget ni compteur visible ; un essai qui tourne en boucle n'est arrêté par rien.
- **Faiblesse — pas de référence notée.** Aucun banc d'essai validé ne permet de dire si un changement améliore ou
  dégrade (carence C1 du 2026-09-22, toujours ouverte).
- **Améliorations** : (a) correctif du modèle ; (b) compteur de jetons et plafond par analyse, affichés dans
  l'écran « Analyse » ; (c) « détection par l'exemple » sans IA (regrouper les dessins répétés → le thermicien
  classe un exemplaire → l'algorithme retrouve les copies), à essayer d'abord sur les menuiseries du R+1 ; (d) IA
  seulement à la demande, sur une petite vignette, avec le modèle annoncé.

## 4. Recalcul de l'étude (serveur)

- **Forces** : le relevé brut est la seule source de vérité, tout le reste est recalculé ; versions à chaque
  enregistrement, retour possible ; découpage pièce par pièce juste quand l'amont est juste ; cohérence contrôlée.
- **Faiblesse — tout est recalculé à chaque geste enregistré.** Plusieurs secondes sur le R+1 pour un seul mur.
  Depuis D252, l'écran montre le geste tout de suite et enregistre en arrière-plan, mais une rafale de gestes
  enchaîne autant de recalculs complets.
- **Faiblesse — l'identité d'un élément est sa position** (tronçon, début, fin). Elle change quand on déplace une
  extrémité, et quand le serveur réunit deux morceaux : l'élément désigné peut alors « disparaître » de la fiche.
- **Faiblesse — deux copies de la même règle.** L'écran rejoue certains calculs du serveur pour aller vite
  (`elementsLocal.ts`, `murs.ts`, `pontsAjoutes.ts`). Les tests utilisent les mêmes chiffres des deux côtés, mais
  toute évolution doit être faite deux fois.
- **Améliorations** : un identifiant stable par élément (indépendant de sa position) ; regrouper les gestes
  rapprochés en un seul enregistrement (attente de 1 à 2 s) ; à terme, recalculer seulement le local touché.

## 5. Parcours en 6 étapes

- **Forces** : une étape = une famille d'objets ; compteur « N à valider » par étape ; bandeau de droite
  contextuel ; suppression, création et retouche des murs directes depuis aujourd'hui.
- **Faiblesse — la page de travail fait tout.** 1 786 lignes, sept modes de geste concurrents (contour, calage,
  cadre de vue, hauteur à poser, modèle à poser, tracé de mur, poignées). Chaque nouveau geste risque d'en casser
  un autre.
- **Faiblesse — interface encore chargée** (objectif 2 de la boussole) : cases d'affichage, alertes et panneaux
  d'anciennes étapes.
- **Faiblesse — enregistrement mixte.** Les murs s'enregistrent seuls ; les autres corrections attendent encore
  « Enregistrer ». Deux logiques coexistent dans le même écran.
- **Améliorations** : sortir chaque mode de geste dans son propre module (comme `murs.ts`) ; enregistrement
  automatique pour tous les gestes, avec un seul indicateur « enregistré / en cours » ; l'inventaire « garder /
  replier / supprimer » par étape.

## 6. Murs

- **Forces (depuis aujourd'hui)** : ligne de métré = face intérieure ; composition validée mur par mur ;
  suppression instantanée ; poignées libres avec aimant ; créer un mur ; ajouter un point (mur à plusieurs pans).
- **Faiblesse** : un mur reste attaché à un tronçon de façade calculé par l'IA. Un refend ou un mur loin de la
  façade est représenté, mais ses couches se posent toujours vers l'extérieur de la façade (D251 à faire).
- **Faiblesse** : un déplacement enregistré ne s'annule plus par Ctrl+Z.
- **Amélioration** : « Inverser le côté » ; Ctrl+Z qui renvoie le geste inverse au serveur.

## 7. Menuiseries

- **Forces** : modèle mesuré en élévation avec capture, posé au clic ou « même largeur ± 2 cm » ; morceaux
  réunis ; exposition calculée depuis le nord.
- **Faiblesses** : couper une baie réunie à tort n'existe pas ; les valeurs Uw ne sont pas portées par les
  modèles ; les menuiseries restent des intervalles de façade (pas de surface déduite du mur).
- **Améliorations** : « Séparer cette baie » ; Uw et source sur le modèle (bibliothèque, objectif 3).

## 8. Ponts thermiques

- **Forces** : référentiel NF EN ISO 14683 intégré ; angle mesuré ; chaque pont passe devant le thermicien ; ajout
  au clic droit.
- **Faiblesses** : liaisons plancher et règle des quatre quarts (S4) non faites ; ψ des cas particuliers à la main
  (ubakus) ; minoration des angles proportionnelle, sans règle normative.
- **Amélioration** : S4 dès que deux niveaux sont calés et relevés.

## 9. Coupes, élévations, hauteurs

- **Forces** : vues créées à la main, mesure en deux clics, hauteur posée sur un, plusieurs ou tous les locaux.
- **Faiblesses** : aucune vérification croisée entre la hauteur d'étage du plan et celle des coupes ; code mort
  de l'ancienne lecture IA des coupes.
- **Amélioration** : alerte quand deux mesures d'une même hauteur divergent de plus de 5 cm.

## 10. Livrable

- **FAILLE n° 3 — il n'existe pas.** Pas de surfaces × U, pas de déperditions par local (NF EN 12831-1), pas
  d'export. Tout le travail reste aujourd'hui sans sortie exploitable par une entreprise CVC.
- **Amélioration** : un premier livrable minimal dès que le R+1 est validé (tableau par local : parois,
  menuiseries, ponts, surfaces, U, ψ, déperditions), puis l'export.

## 11. Transversal

| Sujet | Constat | Amélioration |
|---|---|---|
| **Sécurité** | Le dépôt GitHub est **public**. Le plan client du R+2 y est publié (branche `essai/r2-cloud`, avec l'accord du thermicien), et tout le code et les décisions sont visibles | décider : dépôt privé, ou branche supprimée et purgée après l'essai |
| **Tests** | Bons tests de logique, y compris par la porte d'entrée de l'API ; **aucun test du parcours à la souris** ; je ne peux pas me connecter au site | tests d'interaction simulés sur les composants clés (glisser une poignée, tracer un mur) ; recette souris du thermicien après chaque lot |
| **Méthode** | Fichier de décisions avant de coder, mise en ligne à chaque lot testé, mémoire tenue à jour | garder ; mais les décisions sont dispersées dans 50 fichiers : un index à jour par sujet |
| **Dette** | Fonctions retirées de l'écran mais encore dans le serveur : traits de coupe, lecture IA des coupes, pinceau, retracé, « Affecter aussi à », passe globale automatique | lot de nettoyage (objectif 2b) |
| **Données** | `banc.db` local périmé, études d'essai éparpillées dans `Codex/…/outputs` et `Etudes-thermique/` | un seul dossier d'essais, daté, avec les chiffres de référence du R+1 figés |
| **Coût IA** | Aucune mesure suivie ; la session de développement elle-même consomme beaucoup | journal du coût par analyse ; IA seulement là où un essai a prouvé son utilité |

## 12. Priorités proposées

1. **Corriger le modèle du mode automatique et du relais** : petit lot, aucun coût, faille active.
2. **Recette souris des murs** (supprimer, indéterminés, poignées, créer, ajouter un point), puis D251.
3. **Finir le R+1** à 100 % : locaux et hauteurs, murs, menuiseries, ponts. C'est la condition de tout le reste.
4. **Livrable minimal du R+1** : tableau des déperditions par local.
5. **Interface allégée et enregistrement automatique partout**, avec la page de travail découpée en modules.
6. **Identifiant stable des éléments** : supprime une famille de défauts (sélection perdue, gestes qui visent le
   mauvais élément).
7. **Détection par l'exemple**, mesurée sur le R+1, avant toute nouvelle dépense d'IA ; décision sur le résultat
   de l'essai cloud du R+2.
8. **Report du R+1 vers les autres niveaux** par le calage (D233–D237).
9. **Bibliothèque projet unique** avec U, Uw et ψ sourcés.
10. **Nettoyage** du code retiré et du dossier des essais ; décision sur la visibilité du dépôt.
