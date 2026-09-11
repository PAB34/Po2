---
type: decisions
status: actif
read_policy: si la tâche concerne l'étape 2 de l'outil thermique
related:
  - metre-thermique-decisions.md
  - 00-audit-existant-faisabilite.md
---

# Outil thermique — étape 2 : géométrie des plans (décisions et questions)

> Fichier « fil du dev » de l'étape 2, écrit **avant** de coder (2026-09-11). Cadrage général :
> `metre-thermique-decisions.md`. Objectif fixé par l'utilisateur : « un outil qui analyse de
> manière **irréprochable** la géométrie du bâtiment et ses composants : murs, cloisons,
> menuiseries, planchers ». Les entités thermiques (Th-Bât) viennent après.

## 1. Existant vérifié

| Élément | État | Où |
|---|---|---|
| Lecture du flux PDF avec transformations, filtre par épaisseur de trait | Prototype, prouvé sur le niveau 0 : 550 traits retenus sur 225 018, emprise = cotes 31,82 × 33,13 m | `proto_detection_murs.py`, `preuve_detection_murs_niveau0.png` |
| Épaisseurs de trait du niveau 0 | 0,12 · 0,16 · 0,24 · 0,36 · 0,48 · **0,96 · 1,56** pt ; murs coupés ≥ 0,96 pt | audit §4 |
| Pièges connus | Segments à 45° = lettres vectorisées ; vitrages en trait fin ; poteaux = petits rectangles ; cadre et cartouche en trait épais | audit §4 |
| Échelle par planche | En prod ; l'utilisateur a contrôlé 10 planches par une cote : **1/100 confirmé à 0,1 % près** | base prod, 2026-09-11 |
| Coordonnées | Points PDF ; transformation PDF → pixels de la visionneuse déjà fournie (calque possible) | `thermique_raster.py`, `raster.ts` |
| Calque de dessin sur la visionneuse | Déjà en place pour les mesures (SVG au-dessus des tuiles) | `TileSheetViewer.tsx` |

## 2. Décisions proposées (à valider)

| # | Proposition | Raison |
|---|---|---|
| D1 | **Moteur autonome** `saas/backend/thermique_moteur/` : aucune dépendance à `app.` (base, serveur web, Po2), testé seul ; le backend ne fait que l'appeler. Un test vérifie l'absence d'import de `app.` | Garder ouverte la voie « logiciel installé » (Q13, Q20) |
| D2 | **Modèle commun de traits** (segment, épaisseur, couleur, calque éventuel), alimenté par le PDF puis par le DXF | Une seule détection pour tous les formats |
| D3 | Détection en **tâche de fond**, résultat mis en cache par planche | 20 à 40 s de lecture brute par plan |
| D4 | **Seuil d'épaisseur par planche**, proposé automatiquement (histogramme) et modifiable | La convention de plume dépend du dessinateur |
| D5 | Chaque élément garde sa **source** (automatique / corrigé / ajouté à la main) ; une correction n'est jamais écrasée par une nouvelle détection | Exigence « irréprochable » : l'humain a le dernier mot |
| D6 | Géométrie stockée en **points PDF** et restituée en **mètres** via l'échelle de la planche | Cohérent avec l'étape 1 |

## 3. Chaîne de détection

```
traits (PDF / DXF) ─► zone utile (sans cadre ni cartouche)
                  ─► classes de traits par épaisseur (histogramme, seuil par planche)
                  ─► MURS     : faces épaisses parallèles appariées → axe, épaisseur, longueur (obliques compris)
                  ─► POTEAUX  : petits contours fermés isolés
                  ─► CLOISONS : faces de trait moyen appariées, épaisseur faible
                  ─► BAIES    : interruptions alignées d'un mur → largeur, position
                  ─► MENUISERIES : porte = arc d'ouverture dans la baie ; fenêtre = traits fins parallèles dans la baie
PLANCHERS : sur les coupes (épaisseurs, niveaux) → étape 3, avec le calage des niveaux
```

## 4. Découpage de l'étape 2

| Sous-étape | Contenu | Livrable visible |
|---|---|---|
| **2a** | Moteur PDF : zone utile, histogramme, **murs + poteaux** ; calque en lecture seule sur la visionneuse ; longueurs et épaisseurs en mètres | Le niveau 0 affiche ses murs, avec épaisseur et longueur |
| **2b** | **Baies, menuiseries, cloisons** | Portes et fenêtres repérées, cloisons distinguées des murs |
| **2c** | **Correction à la main** (supprimer, ajouter, reclasser, ajuster) + enregistrement | Géométrie validée par le thermicien |
| **2d** | **Import DXF** (calques d'origine) ; DWG selon Q15 | Même résultat depuis un DXF |

## 5. Questions ouvertes

- **Q21 — Précision attendue.** Quelle tolérance jugez-vous « irréprochable » sur une longueur de
  mur et sur une épaisseur (proposition : ± 1 cm) ?
- **Q22 — Menuiseries.** Que faut-il en sortir : position, largeur, sens (porte/fenêtre) ? Les
  hauteurs et allèges viendront des façades et des coupes (étape 3).
- **Q23 — Référence de contrôle.** Pour juger la détection, pouvez-vous me donner, sur le niveau 0,
  quelques épaisseurs de murs et longueurs de façade que vous connaissez (ou un métré existant
  du projet) ?
- **Q24 — Pièces.** Faut-il aussi détecter les **pièces** (contours, surfaces), utiles pour les
  surfaces chauffées ?
- **Q25 — DXF de la médiathèque.** Avez-vous le DWG/DXF du même projet ? Il permettrait de
  comparer la détection PDF à la géométrie d'origine.
