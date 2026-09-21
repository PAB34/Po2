---
type: decisions
status: actif
read_policy: si la tâche concerne le nouveau MVP de zonage automatique
related:
  - contours-pieces-decisions.md
  - refondation-parcours-decisions.md
---

# Nouveau MVP - zonage automatique puis correction

> Audit ciblé du **2026-09-21**, avant écriture du nouveau frontend.

## Existant vérifié

### Backend conservé comme boîte à outils

- Le raster tuilé affiche déjà les planches PDF sans recharger le document à chaque zoom.
- `thermique_detection` sait enchaîner automatiquement reconnaissance des murs, portes et
  menuiseries, détection de toutes les pièces, lecture des noms et synthèse.
- Les pièces sont persistées sous forme de polygones et leur surface est recalculée à l'échelle.
- Les sommets peuvent être corrigés par l'API ; fusion, découpe, ajout et suppression existent aussi.
- Les moteurs vectoriels, OCR, reconnaissance, enveloppe et composants restent disponibles mais ne
  doivent plus dicter l'organisation du nouvel écran.

### Frontend écarté du nouveau parcours

- Les fonctions sont dispersées entre Calques, Pièces, Enveloppe et Métré.
- Le bouton de détection globale est caché dans Calques alors que le résultat attendu est un zonage.
- L'utilisateur doit comprendre l'ordre interne des moteurs et peut rencontrer des exigences de
  classification qui ne correspondent pas à son objectif.
- `TileSheetViewer` et les primitives géométriques sont réutilisables ; les pages métier existantes ne
  sont pas reprises dans le MVP neuf.

## Contrat visuel et fonctionnel

La référence est `projection_zonage_thermique_R1_mediatheque.pdf` : le plan et toutes les zones proposées
sont visibles en même temps, avec aplats colorés, identifiants, noms, surfaces, catégories et légende.

## Décisions

1. Une route isolée `/projets/:projectId/analyse` porte le nouveau MVP. L'ancien parcours reste accessible
   tant que le nouveau n'est pas validé.
2. L'action principale unique est **Analyser le plan**. Elle appelle l'enchaînement automatique existant ;
   aucune désignation préalable de calque, porte ou menuiserie n'est demandée à l'écran.
3. Le résultat est la totalité des pièces proposées sur la planche, jamais une détection pièce par pièce.
4. Le zonage proposé est affiché sur le plan avec une légende synthétique inspirée du PDF de référence.
5. Une pièce sélectionnée peut immédiatement passer en correction : déplacement, ajout et retrait de
   sommets, puis enregistrement. La donnée corrigée devient manuelle et survit aux relances.
6. Les détails techniques (calques, composants, enveloppe, calculs) sont absents de cette première
   livraison. Ils seront ajoutés seulement après validation métier de ce socle.
7. Le frontend ne duplique aucun moteur : il orchestre les API existantes derrière un contrat simple.

## Critères de validation de l'étape 1

- une planche de plan prête peut être sélectionnée ;
- un clic lance l'analyse globale et montre son avancement ;
- toutes les pièces retournées apparaissent ensemble, colorées et légendées ;
- un clic sélectionne une pièce ;
- ses sommets sont visibles, saisissables à tous les zooms et enregistrables ;
- aucun passage par Calques n'est présenté ou requis dans ce parcours.
