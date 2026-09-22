---
read_policy: lire avant de toucher à l'identification des pièces (passe globale) ou à leur recalage
---

# Tous les locaux, contours recalés — décisions (étape 1 de la passe pièce par pièce)

Date : 2026-09-22. Stratégie : [carences-agents-strategie.md](carences-agents-strategie.md) (S5, § 5 bis).

## 1. Existant vérifié

- Passe globale (`thermique_claude_agent.py`, agent `thermicien-plan`) : catégorie `piece`, polygone « au nu
  intérieur », nom lu dans `subtype`. R+1 : 22 pièces, aucune circulation ; plusieurs contours s'arrêtent avant la
  façade (rattachements par repli jusqu'à 1,8 m, carence C5).
- `mettre_au_propre` (`thermique_vision_geometrie.py`) redresse les formes mais ne les recale pas sur les murs.
- Le schéma de sortie de l'agent accepte des champs en plus si on les déclare ; `save_result` les conserve.

## 2. Décisions

- **D24 — Nature du local.** Chaque pièce porte `local` : `chauffe` (bureau, salle, sanitaire chauffé…),
  `circulation` (couloir, hall, dégagement, palier), `non_chauffe` (local technique, escalier encloisonné non
  chauffé, gaine, local vélo…). Par défaut `chauffe`. Règle D23 : tout local donnant sur l'extérieur ou un local non
  chauffé est déperditif — une circulation en façade l'est donc aussi.
- **D25 — Tous les locaux.** La consigne de la passe globale demande toutes les pièces du niveau, circulations
  comprises : les pièces couvrent tout le volume intérieur, murs exceptés. Les espaces ouverts regroupant plusieurs
  locaux restent d'un seul tenant (D22 : demande de découpage).
- **D26 — Recalage des contours sur les murs (algorithme, pixels seuls).** Sur le plan à ~59 px/m : masque des murs
  (encre sombre, petits éléments isolés retirés : textes, mobilier) ; chaque pièce part de son contour d'agent
  rétréci de 20 cm et s'étend dans l'espace libre, toutes les pièces en même temps, jusqu'à 1,5 m au plus, sans
  franchir un mur ni sortir du bâtiment. Une porte ouverte laisse passer : deux pièces voisines se partagent alors
  l'embrasure. Garde-fou : surface recalée entre 0,6 et 1,8 fois celle de l'agent, sinon le contour d'agent est
  gardé et signalé.
- **D27 — Espaces libres non attribués.** Ce qui reste libre après le recalage et dépasse 2 m² est listé comme
  **local candidat** (circulation ou local oublié), avec sa position et sa surface : il est donné à l'agent pour
  qu'il le nomme.

## 3. Essai sur le R+1 (2026-09-22)

- Recalage : 21 pièces sur 22 recalées (le petit local technique garde le contour de l'agent) ; les bureaux passent de
  10,8 m² (contour d'agent débordant) à 9,9 m² entre murs ; les contours épousent les murs et la ligne intérieure du
  mur-rideau. Mobilier et battants de porte collés aux murs : encoches refermées (jusqu'à 1,4 m).
- 4 espaces libres : la « boîte à vents / boîte à lumière » (22,9 m², puits de lumière, écarté), deux circulations
  oubliées (5,2 et 4,4 m², ajoutées), une bande contre la façade nord du 6.1.3 (épaisseur de mur, écartée).
- Agent (consigne courte, 30 s) : 24 pièces au final — 17 chauffées, 5 circulations, 2 non chauffées (escalier
  encloisonné, locaux techniques). Il signale que le « vide sur accueil » est une trémie incluse à tort dans une
  pièce, et que la petite terrasse forme une encoche du Pôle multimédia.
- Limites : l'escalier atrium et le vide sur accueil restent dans le polygone du Pôle multimédia (chevauchement) :
  à retirer par soustraction des vides et des pièces incluses (prochaine amélioration).
- Le fichier de rôle de `thermicien-plan` n'a pas été modifié (refus de l'utilisateur) : les nouvelles règles
  (tous les locaux, nature, vides exclus) passent par la consigne (`build_prompt`) et le champ facultatif `local`.

### Retour utilisateur du 2026-09-22 (coquilles marquées sur l'image)

- Effet sur le calcul : une erreur de contour entre deux locaux chauffés ne change que les surfaces (volumes,
  renouvellement d'air, apports) ; sur une façade ou un local non chauffé, elle peut ajouter ou retirer une paroi
  déperditive : c'est là qu'il faut être exact.
- **D26 bis — Deuxième passe à travers les traits fins.** Après la première croissance, les traits fins (battants de
  porte, évier, contour de meuble, trait de tableau) ne bloquent plus, jusqu'à 1 m ; seuls les recoins de plus de
  40 cm de large sont gardés (la bande de 25 à 33 cm d'un mur-rideau reste hors de la pièce) ; les espaces libres
  déjà repérés comme locaux candidats ne sont pas absorbés ; une pièce n'empiète jamais sur une autre.
  R+1 : salle de pause corrigée (évier, angle ouest) ; débattements de porte comptés ; il reste des cases de
  meubles DVD non attribuées (frontière intérieure, sans effet sur les déperditions).
- Recoin de la fenêtre de retour à l'ouest du B.dir : exclu parce que le guide de l'enveloppe coupe la dent de scie
  (T62–T68, carence C4) ; sera réglé par S3.
- **D28 — Boucle de retouche pièce par pièce (demande utilisateur).** Dans la validation par pièce, le thermicien
  modifie (contour, adjacences, parois, baies, ponts thermiques), clique **« Remodéliser »** (l'outil recalcule la
  fiche du local : métrés, parois déperditives, ψ), revérifie, retouche si besoin, puis **enregistre** et passe à
  la pièce suivante. « Remodéliser » exécute le moteur Python : cette page doit donc vivre dans l'application
  (frontend + route backend), pas dans une page autonome.

## 4. Questions

- Q1 — Un escalier encloisonné est-il `non_chauffe` par défaut, ou selon le projet ?
- Q2 — Une gaine ou un placard de moins de 2 m² doit-il apparaître comme local ?
