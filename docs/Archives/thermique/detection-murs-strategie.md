---
type: decisions
status: actif
read_policy: si la tâche concerne la détection des murs sur les plans (priorité absolue de l'utilisateur)
related:
  - metre-plans-decisions.md
  - parois-menuiseries-pt-decisions.md
---

# Détection des murs — stratégie exacte par les vecteurs

> Écrit le 2026-09-14 après le retour de l'utilisateur : « Je suis très déçu du produit fini. Les PDF ont
> des lignes vectorielles qui devraient permettre une parfaite détection des murs. Je veux qu'on
> travaille ici uniquement sur ça. » **Aucune autre fonctionnalité (menuiseries, ponts thermiques)
> n'avance tant que les murs ne sont pas détectés parfaitement, mesure à l'appui.**

## 1. Constat honnête : pourquoi le résultat actuel déçoit

| Erreur de méthode | Conséquence |
|---|---|
| Détection par **pixels** (image rastérisée, dilatations, remplissages) au lieu des vecteurs | Précision limitée au pixel, formes rabotées, réglages fragiles |
| **Contour d'abord**, murs ensuite (rayons partant du contour) | Une erreur de contour se propage à tous les murs (bande plantée, trait fin) |
| Réglages ajustés **niveau par niveau** en regardant des images | Ce qui améliore un niveau en dégrade un autre ; aucune garantie |
| **Aucune vérité terrain** ni mesure chiffrée | Impossible de dire « juste » ou « faux » objectivement, ni d'empêcher les régressions |

## 2. Ce que contiennent réellement les PDF (vérifié le 2026-09-14)

| Fait | Preuve |
|---|---|
| **Aucun calque** : impression PDFCreator / Ghostscript 9.04 (2012) | Pas d'`/OCProperties`, aucune marque de contenu |
| **Faces de murs** = traits épais (1,56 et 0,96 pt), **hachés en petits morceaux** (médiane 0,35 m) | Niveau 0 : 579 morceaux épais ; niveau 2 : 437 |
| Les morceaux **alignés se recollent exactement** en lignes continues | Niveau 2 : 437 morceaux → 423 lignes ; niveau −1 : 255 → 239 (78 de plus de 2 m) |
| **Remplissage des murs** = aplats gris **triangulés** (pas un polygone par mur) | Niveau 0 : 1 178 triangles sur 1 500 aplats gris |
| **Isolant** = motif en nid d'abeille de petits traits gris (0,48 pt, luminance 152) | Relevé sur le mur de 40 cm du niveau 2 |
| **Un mur = deux faces parallèles** : leur écartement donne l'épaisseur **exacte** | Niveau 2 façade droite : faces à x = 1 249,8 et 1 261,2 pt → **0,402 m** ; niveau −1 : paires à **0,300 m et 0,302 m** sur 32 m |
| Le cadre de la feuille n'a **aucune face partenaire** | Lignes de 57 et 59 m sans paire : écartées naturellement |

## 3. Principe

1. **100 % vectoriel, zéro pixel** : coordonnées exactes du PDF, tolérances exprimées en points (0,05 pt ≈ 2 mm réels à 1/100).
2. **Le mur est l'objet de base** : une paire de faces parallèles, avec axe, épaisseur, début, fin.
3. **Tout se déduit du réseau de murs** : enveloppe, contour au nu intérieur, baies, refends, liaisons
   (ponts thermiques) — jamais l'inverse.
4. **Chaque règle est justifiée par une mesure** sur une vérité terrain ; aucune règle n'est gardée si elle
   fait baisser un score.

## 4. Chaîne de détection

| Étape | Traitement exact | Résultat |
|---|---|---|
| **1. Lecture** | Tous les objets : traits (extrémités, largeur, couleur, pointillé), aplats (triangles), textes éventuels ; courbes gardées comme arcs | Inventaire complet de la planche |
| **2. Normalisation** | Fusion des morceaux colinéaires (angle ≤ 0,1°, écart ≤ 0,05 pt, jointure ≤ 0,1 pt) ; accrochage des extrémités ; union des triangles d'aplat en polygones | Lignes continues, masses de remplissage exactes |
| **3. Dictionnaire des plumes** | Rôle de chaque plume établi par statistiques de la planche (faces = traits épais longs appariables ; hachures = motifs courts périodiques ; cotes, axes, mobilier = reste), présenté au thermicien | « 1,56 pt = mur coupé, 0,96 pt = cadre et murs, 0,48 gris = isolant… » |
| **4. Appariement des faces** | Pour chaque ligne de face : lignes parallèles à 5-80 cm qui la recouvrent, **sans autre face entre elles** ; contenu entre les faces vérifié (aplat, motif d'isolant, vide) | Segments de mur : axe, épaisseur au mm, début, fin, composition lue |
| **5. Topologie** | Graphe des murs : jonctions en L, T, X aux intersections d'axes ; **fins de mur** fermées par un petit trait perpendiculaire (jambage) ; **ouverture** = interruption des deux faces entre deux jambages alignés | Réseau de murs continu, baies exactes (largeur au mm) |
| **6. Enveloppe** | Union des murs + fermeture des baies → bord extérieur ; face intérieure des murs d'enveloppe → contour au nu intérieur ; murs intérieurs → refends et cloisons | Contour exact, sans raster |

## 5. Vérité terrain et mesure (condition de réussite)

- **Référence par niveau** (fichier versionné) : chaque mur coupé (axe, épaisseur, extrémités), chaque baie
  (position, largeur), classement enveloppe / refend / cloison.
- **Construction** : proposée par la chaîne, puis **contrôlée tuile par tuile** (zooms de 8 × 8 m) et
  corrigée à la main ; **validée par le thermicien** sur une page de superposition par niveau.
- **Mesures automatiques**, relancées à chaque modification (test de non-régression) :

| Indicateur | Objectif |
|---|---|
| Linéaire de murs de référence retrouvé (axe à ± 2 cm) | **100 %** |
| Linéaire détecté absent de la référence (faux murs ≥ 0,5 m) | **0** |
| Épaisseur | **± 1 cm** sur 100 % des murs |
| Extrémités et jonctions | **± 2 cm** |
| Baies (position, largeur) | **± 2 cm**, 100 % retrouvées |

- **Rapport par niveau** : scores, liste des écarts, image de superposition.

## 6. Généralisation

- Les règles tirent leurs réglages de la planche elle-même (dictionnaire des plumes), pas de constantes
  propres au projet d'essai.
- **Deux ou trois autres projets** (autres architectes, logiciels récents : Revit, ArchiCAD, AutoCAD ;
  PDF avec calques quand ils existent) sont indispensables pour prétendre à une détection fiable ailleurs.
- Si le PDF contient des **calques**, ils sont lus en premier (« MUR », « CLOISON »…) et recoupés avec la
  géométrie.

## 7. Jalons

| Jalon | Contenu | Critère de sortie |
|---|---|---|
| **J1** | Lecture exacte, fusion des morceaux, union des aplats, dictionnaire des plumes | Rapport par planche validé ; 0 morceau de face orphelin inexpliqué |
| **J2** | Vérité terrain des 4 niveaux | Validée par le thermicien |
| **J3** | Appariement des faces → murs | Niveau −1 à **100 %** ; épaisseurs ± 1 cm |
| **J4** | Topologie : jonctions, fins de mur, ouvertures | Baies ± 2 cm ; 4 niveaux à **100 %** |
| **J5** | Enveloppe et contour déduits ; remplacement de la détection actuelle dans l'outil | Contour exact sur les 4 niveaux |
| **J6** | Autres projets | Mêmes scores sans réglage propre au projet |

## 8. Ce qui s'arrête

- La détection par pixels (`thermique_moteur/detection.py`, `enveloppe.py`) n'est plus améliorée : elle
  sera **remplacée** au jalon J5 (elle reste en ligne d'ici là, faute de mieux).
- Menuiseries (M4b), ponts thermiques (M4c, M2) : **suspendus** jusqu'à J5.

## 9. Questions

- **Q54 — Vérité terrain** : je la construis et vous la validez sur une page de superposition par niveau ?
- **Q55 — Autres projets** : pouvez-vous fournir deux ou trois projets d'autres architectes ou logiciels
  (PDF, et DWG si possible) ?
- **Q56 — Périmètre** : tous les murs coupés (façades, refends, cloisons, gaines) ou l'enveloppe seulement ?
- **Q57 — En ligne** : garder la détection actuelle jusqu'à J5, ou la retirer tout de suite ?

## 10. Réponses (2026-09-14)

- **Q54** : je construis la vérité terrain, le thermicien la **valide** sur une page de superposition par
  niveau.
- **Q55** : le thermicien **dépose** deux ou trois autres projets (autres architectes, logiciels) dans
  `Thermique/`.
- **Q56** : **tous les murs coupés** (façades, refends, cloisons, gaines).
- **Q57** : la détection actuelle reste en ligne jusqu'à **J5**, puis est remplacée.
