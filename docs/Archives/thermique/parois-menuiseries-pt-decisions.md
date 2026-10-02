---
type: decisions
status: actif
read_policy: si la tâche concerne la détection des types de murs, des menuiseries ou des ponts thermiques
related:
  - metre-plans-decisions.md
  - agent-verification-decisions.md
---

# Outil thermique — détection des types de murs, menuiseries et ponts thermiques (lot M4)

> Fichier « fil du dev » écrit avant de coder (2026-09-14), à la demande de l'utilisateur : « il faut
> avancer sur la détection de tous les types de murs, menuiseries, ponts thermiques ».

## 1. Existant vérifié

| Élément | État |
|---|---|
| Contour au nu intérieur détecté (M3) | En prod ; justes sur −1 et 2, retouches sur 0 et 1 (bande plantée, coursive) |
| Hauteurs par niveau lues sur coupe (M3) | En prod |
| Côtés qualifiés « donne sur » + composant mur (M1) | En prod, saisis à la main |
| Catalogue des ponts thermiques et règle des quatre quarts | Cadrés (`metre-plans-decisions.md` §3), non codés |
| Vérification par Claude Code | Cadrée (`agent-verification-decisions.md` §10), non codée |

## 2. Ce que les prototypes ont appris (projet d'essai, 2026-09-14)

1. **Épaisseur par rayons depuis le contour** : juste au niveau −1 (murs 30 cm sur 109 m), mais sur les
   niveaux 0 et 2 une erreur de contour se propage (côté droit, le contour suit la bande plantée : les
   rayons partent de l'extérieur du mur et ne trouvent rien).
2. **Dessin des murs** : chaque mur est un **empilement de couches** — aplat gris (béton), bande à motif
   en nid d'abeille (isolant), bordures en trait épais. Un aplat seul donne l'épaisseur d'**une couche**
   (10 à 15 cm au niveau −1 pour un mur de 30 cm), pas du mur.
3. **Fenêtres** : paires de traits fins foncés parallèles entre deux morceaux de mur. Au niveau 0,
   21 fenêtres repérées (0,6 à 1,2 m pour la plupart) : façades à redents et entrée bien lues, façade
   vitrée droite (montants en petits rectangles gris) **non lue**, quelques faux positifs (mobilier
   collé à la façade).
4. **Refends et angles** : bien lus au niveau −1 (6 refends entre places de parking, 9 angles
   sortants, 2 rentrants).

## 3. Méthode proposée

| Étape | Méthode | Résultat |
|---|---|---|
| **A. Corps de mur** | Regrouper les couches accolées (aplats, motifs d'isolant, bordures) en un corps ; épaisseur totale mesurée perpendiculairement ; reconnaître les couches (plein gris = maçonnerie/béton, nid d'abeille = isolant) et leur ordre (isolant côté intérieur ou extérieur) | Pour chaque tronçon du contour : épaisseur, isolant intérieur / extérieur / réparti |
| **B. Types de murs** | Regrouper les tronçons de même épaisseur (± 2 cm) et même composition | « Mur 30 cm isolé par l'intérieur — 109 m » → proposé comme composant de la bibliothèque |
| **C. Menuiseries** | Fenêtre = traits fins parallèles entre deux corps de mur ; porte = arc d'ouverture ; mur-rideau = succession de montants ; filtrage du mobilier (hors de l'épaisseur du mur) | Baies positionnées sur le contour, largeur, type ; regroupées par largeur (F1, F2…) |
| **D. Ponts thermiques verticaux et menuiseries** | Refends touchant le contour × hauteur sous plafond ; angles × hauteur ; appuis et linteaux = largeur des baies ; tableaux = 2 × hauteur ; seuils = largeur des portes | Linéaires par niveau, type d'isolation déduit de l'étape A |
| **E. Ponts thermiques horizontaux** | Superposition des niveaux calés (lot M2, règle des quatre quarts) | Plancher bas / intermédiaire / haut par portion de façade |
| **F. Vérification Claude Code** | Images recadrées par tronçon, baie et liaison ; verdicts proposés au thermicien | Corrections proposées, jamais appliquées d'office |

## 4. Découpage proposé

| Lot | Contenu |
|---|---|
| **M4a** | Corps de mur, épaisseur et composition par tronçon, types de murs proposés comme composants |
| **M4b** | Menuiseries (fenêtres, portes, murs-rideaux) sur le contour, regroupées par type |
| **M4c** | Ponts thermiques verticaux et des menuiseries, par niveau |
| **M2** | Planchers et ponts thermiques horizontaux par superposition (calage de tous les niveaux requis) |

## 5. Questions ouvertes

- **Q51 — Hauteur des menuiseries.** Les plans ne donnent que la largeur. Hauteurs par défaut par type
  (fenêtre 1,35 m, porte-fenêtre et porte 2,15 m, mur-rideau = hauteur sous plafond), modifiables, en
  attendant leur lecture sur les façades ?
- **Q52 — Types de murs.** Les types détectés créent-ils directement des composants « à compléter »
  dans la bibliothèque du projet, ou restent-ils des propositions à accepter ?
- **Q53 — Ordre.** M4a (murs) → M4b (menuiseries) → M4c (ponts thermiques) → M2, ou une autre
  priorité ?

## 6. Réponses (2026-09-14)

- **Q51** : **lecture des hauteurs sur les façades d'abord** (pas de hauteur par défaut) → intégrée au
  lot M4b menuiseries.
- **Q52** : les types de murs détectés sont des **propositions à accepter** (un clic crée ou rattache le
  composant et colore les tronçons).
- **Q53** : ordre **M4a murs → M4b menuiseries (avec façades) → M4c ponts thermiques → M2**.

## 7. Lot M4a livré (2026-09-14)

| Élément | Réalisation |
|---|---|
| Aplats | `traits.lire_aplats` : contours des chemins remplis avec leur luminance (sous le verrou pdfium) |
| Corps de mur | `thermique_moteur/enveloppe.py` : aplats gris 96-176 + traits épais + zones denses de petits traits (isolant), refermés de 2 cm, vides étroits entre faces comblés |
| Mesure | Rayon perpendiculaire tous les 5 cm, corps le plus proche du contour (± 50 cm), coupures ≤ 8 cm ignorées ; épaisseur − largeur du trait de bordure ; au-delà de 60 cm : non lu ; position de l'isolant (intérieur, extérieur, réparti) |
| Lissage et types | Tronçons homogènes (± 4 cm, < 50 cm absorbés) ; épaisseur dominante par côté ; côtés regroupés par épaisseur (± 3 cm) |
| Écran | « Détecter les types de murs » sur un contour : liste des types (épaisseur, isolant, linéaire, côtés) avec « Rattacher à… » ou « Créer le composant » (composant *murs* créé dans la bibliothèque du projet, composition à compléter) ; mur lu affiché pour chaque côté |
| Contour (M3) amélioré | Recalage sur la **face intérieure** d'un mur (ligne épaisse ayant sa face extérieure parallèle à 8-80 cm), la plus proche jusqu'à 1,5 m dans les deux sens, morceaux alignés additionnés, direction de la face reprise, petits pans d'angle supprimés. Niveau 2 : 725 → 742 m² (contour arrêté 60 cm avant le mur) |

Résultats sur le projet d'essai : −1 **32 cm sur 119 m** (121 m lus sur 121) ; 0 : 42 cm sur 19 m
(44 m lus sur 157) ; 1 : 22 cm et 41 cm sur 13 m chacun (34 m lus sur 167) ; 2 : **42 cm isolant
réparti sur 31 m** (47 m lus sur 116). Parties non lues : vitrages (normal), contour encore faux côté
bande plantée au niveau 0, murs de même famille répartis en plusieurs types proches (le thermicien les
rattache au même composant).
