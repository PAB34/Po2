---
read_policy: lire avant de toucher aux fiches par local (étape 2 de la passe pièce par pièce)
---

# Fiche par local — décisions (étape 2)

Date : 2026-09-22. Suite de [locaux-decisions.md](locaux-decisions.md) ; stratégie :
[carences-agents-strategie.md](carences-agents-strategie.md) § 5 bis.

## 1. Existant vérifié

- Locaux : `locaux.json` (contours recalés sur les murs, nature `local` : chauffe, circulation, non_chauffe).
- Enveloppe : relevé découpé par pièce (`thermique_enveloppe_pieces.py`) : parois et baies de façade par pièce, faces
  intérieures raccordées aux angles, ponts thermiques (angles, abouts de refend), liaison plancher.
- Guide de l'enveloppe (`enveloppe-manifeste.json`) : face extérieure du bâtiment.
- Métré (`thermique_metre.py`) : zones par niveau avec côtés et composants (base de l'application) ; le nord y est
  calé par niveau (`set_north`).

## 2. Décisions

- **D29 — Tour de chaque local.** Chaque côté du contour recalé est sondé tous les 10 cm : on avance
  perpendiculairement vers l'extérieur de la pièce, de 5 cm en 3 cm jusqu'à 1,2 m, et le premier élément rencontré
  donne l'**adjacence** : autre local (avec sa nature), extérieur (hors du bâtiment ou sur une terrasse, un balcon),
  vide (puits de lumière, trémie : à confirmer), inconnu (rien avant 1,2 m). La distance parcourue donne
  l'**épaisseur du mur**. Les sondages contigus de même adjacence forment un **côté** ; un côté de moins de 15 cm
  rejoint son voisin.
- **D30 — Déperditif** (règle D23) : un côté sur l'extérieur, sur un local non chauffé ou sur un vide est
  déperditif ; sur un local chauffé ou une circulation (chauffée par défaut), non. Un local non chauffé ne porte pas
  de déperditions : ses côtés vers les locaux chauffés sont les parois déperditives de ces locaux.
- **D31 — Rattachement de l'enveloppe.** Sur un côté extérieur, les éléments de l'enveloppe de ce local dont la face
  intérieure passe à moins de 90 cm du côté y sont rattachés, chacun au seul côté le plus proche (parois par composant, baies). Écart signalé si un côté
  extérieur n'a aucun élément relevé, ou si un élément relevé ne trouve aucun côté.
- **D32 — Orientation.** Donnée par la normale sortante du côté par rapport au haut de la feuille, puis au nord
  quand il est calé (paramètre) ; sinon « nord à caler ».
- **D33 — Ce que la fiche ne sait pas encore** : planchers bas et hauts, hauteurs (coupes, étape suivante) ;
  compositions des parois intérieures (refend, cloison) : épaisseur mesurée seulement.

## 3. Essai sur le R+1 (2026-09-22)

- 24 fiches en 30 s (`enveloppe_R1.locaux.md`, plan `enveloppe_R1.adjacences.png`, `fiches_locaux` dans le JSON).
- Bureaux B.asst : façade 2,95 m (mur-rideau de 29 cm, baies M1 rattachées), cloisons de 17 cm entre bureaux,
  14 cm sur la circulation ; côtés extérieurs = façade relevée sur l'enveloppe au centimètre près. Idem 6.1.4, 6.1.5.
- Escalier encloisonné et locaux techniques : leurs murs vers les locaux chauffés sont déperditifs pour ces locaux.
- Salle de réunion : 6,45 m déperditifs sur le puits de lumière (Q2 à trancher).
- Écarts signalés : B.dir 14,05 m de côtés extérieurs contre 18,00 m relevés (guide coupant les dents de scie, C4) ;
  espace formation 6,42 contre 7,76 m ; palier d'ascenseur 8,4 m sans rien derrière (gaine d'ascenseur, pas un
  local) ; sanitaires et Pôle : côtés sur gaines ou vides.

## 4. Réponses de l'utilisateur (2026-09-22)

- Q1 : **les circulations sont chauffées par défaut** (pas de déperdition vers les locaux voisins) — c'est le
  comportement actuel.
- Q2 : la « boîte à vents / boîte à lumière » est **un vide donnant sur l'extérieur**, qui sert aussi de colonne de
  désenfumage : ses parois sont des parois sur l'extérieur (déperditives). Règle générale retenue : un puits de
  lumière ou un patio ouvert est un vide sur l'extérieur ; une trémie intérieure (vide sur accueil) ne l'est pas.

## 5. Questions (historique)

- Q1 — Une circulation est-elle chauffée par défaut (non déperditive vers les locaux voisins) ?
- Q2 — La « boîte à vents / boîte à lumière » est-elle un patio extérieur ou un volume non chauffé fermé ?
