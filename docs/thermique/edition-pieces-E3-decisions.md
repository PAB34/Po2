---
read_policy: lire avant de coder le lot E3 (édition pièce par pièce de l'espace de travail thermique)
status: questions_ouvertes
---

# Édition pièce par pièce — décisions du lot E3

Date : 2026-09-23. Périmètre annoncé en E3 : modifier un local (contour, nature, adjacence, rattachement),
**Remodéliser**, **Enregistrer et suivant**, et les versions. S'y ajoute l'intégration de la décision **A6**
(séparer couverture physique et découpage fonctionnel), issue du comparatif d'agents du 2026-09-23.

**Rien n'est codé tant que les questions du § 6 ne sont pas tranchées.**

## 1. Objectif repris et niveau de confiance

- Objectif compris : donner au thermicien la main sur l'étude importée en E2, local par local, avec recalcul
  immédiat, enregistrement versionné et passage au local suivant ; et rendre enfin possible le tracé des limites
  que la machine ne peut pas deviner.
- Niveau de confiance : **élevé** sur le périmètre, **moyen** sur deux points qui appellent votre arbitrage :
  le moment où l'on passe le contrat en version 2, et le coût de stockage des versions.
- Hors lot : alimentation de la bibliothèque et association des ponts thermiques (E4), hauteurs et planchers (E5).

## 2. Existant vérifié le 2026-09-23

### Ce que E2 a livré (commit `7815c026`)

- `app/services/thermique_etudes.py` : `assembler_etude_niveau` (fonction pure, aucun agent), `valider_et_convertir`
  (contrôle strict + conversion des contours en points PDF), `importer_etude`, `serialize_etude`.
- Modèles `ThermiqueEtude` (une par planche, `content_json` + `local_states_json`) et `ThermiqueEtudeVersion`
  (photographie complète : `content_json`, `local_states_json`, `reason`, auteur, date), migration 0083.
- Routes `GET /thermique/sheets/{id}/etude` et `POST /thermique/sheets/{id}/etude/importer`.
- Interface : `workspace/StudyPanel.tsx` (`StudyOverlay`, `StudyRoomList`, `StudyRoomPanel`), `workspace/study.ts`
  (tri chauffés d'abord, couleurs par nature, comptage des validés), état `local=<piece-id>` dans l'adresse.
- Chaque local porte déjà `contour` (repère feuille 0..1000) **et** `contour_pdf` (points PDF durables).

### Ce qui est déjà disponible et qu'il ne faut pas reconstruire

- **L'emprise du bâtiment est déjà dans le fichier d'étude** : `enveloppe.manifeste.batiment_px`, polygone issu
  du raster. C'est la « couverture physique complète de l'intérieur » réclamée par A6 : elle existe, elle n'est
  simplement pas encore confrontée aux contours des locaux.
- Le recalcul sans image est possible côté serveur : `thermique_enveloppe_pieces` (rattachement aux pièces,
  `raccorder_faces`, `synthese_pieces`) et `thermique_fiches_locaux` (fiches) ne lisent aucun pixel.
- La visionneuse sait déjà poser un point et saisir un objet (`renderOverlay`, `onGrab`) : la base de l'édition
  de contour est là.

### Ce que le comparatif d'agents impose

- 15 % de la surface des pièces change d'une lecture à l'autre, **même entre deux lectures du même agent**. Les
  contours importés sont donc une proposition, jamais un relevé.
- Les divergences portent exactement sur les objets ambigus (plateaux ouverts, alcôves, trémies, patios) et sont
  marquées `review_required` dans 82 à 88 % des cas. Ce drapeau doit remonter dans l'interface.
- **Arbitrage du 2026-09-23** : la bande d'escalier le long de la façade est est **extérieure**. Elle ne doit
  jamais être comptée comme local ni comme circulation intérieure, et `batiment_px` doit l'exclure — à vérifier
  sur le R+1 avant de s'appuyer sur cette emprise.

## 3. Décisions proposées

### D59 — Contrat v2 : chaque côté d'un local dit s'il suit une paroi

Un local gagne, en regard de son contour, une liste `limites` de même longueur que ses côtés, chacune valant :

- `paroi` — le côté suit une paroi lue sur le plan (mur, refend, cloison) ;
- `convention` — le côté ne correspond à aucune paroi : c'est une limite d'usage, posée par convention ;
- `exterieur` — le côté est sur l'enveloppe extérieure.

À l'assemblage, la qualification est automatique : un côté est `paroi` (ou `exterieur`) s'il longe un élément
d'enveloppe à moins d'un seuil, `convention` sinon. L'interface distingue les trois au trait, et **seule une
limite `convention` se déplace librement** ; déplacer une limite `paroi` avertit qu'on s'écarte du plan lu.

Le format passe à `format_version: 2`. Aucune étude n'est en production ; le fichier du R+1 se réassemble sans
agent en quelques secondes.

### D60 — Contrôle de couverture à chaque calcul, à partir de l'emprise déjà connue

À l'import et à chaque « Remodéliser », le serveur compare l'union des contours des locaux à `batiment_px` :

- `surface_non_affectee_m2` : l'intérieur qui n'appartient à aucun local ; affiché comme un manque à combler,
  avec les zones en surimpression sur le plan ;
- `chevauchement_m2` : les recouvrements entre locaux ;
- `surface_hors_emprise_m2` : un local qui déborde de l'emprise.

C'est la garantie qu'A6 demandait : la machine garantit qu'aucune surface n'est oubliée, le thermicien place les
limites. Le calcul se fait en points PDF avec `shapely`, déjà installé sur le serveur.

### D61 — Édition du contour, et surtout couper et fusionner

- Déplacer, ajouter et supprimer un sommet, avec aimantation sur les parois d'enveloppe proches.
- **Couper un local en deux** en traçant un segment d'un bord à l'autre : les deux moitiés héritent du nom à
  suffixer et la limite créée naît `convention`.
- **Fusionner deux locaux adjacents** : la limite commune disparaît.

Sans ces deux dernières actions, A6 resterait lettre morte : c'est exactement le cas du plateau 4.2 / 4.3 / 4.4,
que trois lectures sur quatre découpent différemment et qu'aucun agent ne peut trancher.

### D62 — Remodéliser : calculer sans enregistrer

Route `POST /thermique/sheets/{id}/etude/remodeliser` : reçoit les locaux modifiés, relance le rattachement des
éléments, les raccords, la synthèse et les fiches, et renvoie les fiches recalculées, le contrôle de couverture
(D60) et **la liste des voisins dont la fiche a changé**. Rien n'est écrit en base.

### D63 — Enregistrer et suivant

Crée une version (motif `validation_local`), passe le local à `valide`, bascule à `a_revoir` les voisins dont la
fiche a changé, puis sélectionne le premier local encore à vérifier, chauffés d'abord.

### D64 — Versions : ne jamais perdre, sans faire enfler la base

Lister les versions, en consulter une, y revenir (le retour crée une nouvelle version, il n'efface rien).
Le fichier du R+1 pèse 640 Ko ; à raison d'une version par local validé, un bâtiment de cinq niveaux dépasserait
75 Mo de copies quasi identiques. Voir Q3.

### D65 — Hauteurs

Inchangé : aucune hauteur par défaut, surfaces « en attente de hauteur », étape dédiée en E5.

## 4. Fichiers probablement concernés

- Serveur : `app/services/thermique_etudes.py` (contrat v2, qualification des limites), un module de contrôle de
  couverture, `app/services/thermique_enveloppe_pieces.py` (recalcul), `app/api/routes/thermique.py`,
  `app/schemas/thermique.py`, migration si le stockage des versions change (Q3).
- Interface : `workspace/StudyPanel.tsx`, `workspace/study.ts`, `workspace/WorkspacePage.tsx`,
  `components/TileSheetViewer.tsx` (saisie de sommet), `api.ts`, `thermique.css`.
- Tests : qualification des limites, couverture/chevauchement, coupe et fusion, remodélisation, versions ;
  côté interface, tri, sélection, édition et rendu des trois types de limite.

## 5. Vérification prévue

1. Réassembler `etude-R1.json` en version 2 et vérifier la qualification des limites sur le plateau ouvert.
2. Vérifier que `batiment_px` du R+1 **exclut** la bande d'escalier est (arbitrage du 2026-09-23).
3. Couper le plateau 4.2 / 4.3 / 4.4 à la main et contrôler que la couverture revient à 100 % sans chevauchement.
4. Remodéliser un local mitoyen et vérifier que le voisin annoncé change bien.
5. Enregistrer, revenir à la version précédente, réenregistrer.
6. Tests ciblés : `python -m pytest tests -k thermique` et `npx tsc -b && npx vitest run src/thermique && npm run build`.

## 6. Questions à valider avant le code

**Q1 — Passage en version 2.** Je propose de passer le contrat en `format_version: 2` **sans compatibilité avec la
version 1**, et de réassembler le fichier du R+1. Aucune étude n'est en production et le réassemblage ne demande
aucun agent. **Recommandation : oui** ; l'alternative (accepter les deux versions) ajoute du code de conversion
pour un seul fichier qui se régénère en quelques secondes.

**Q2 — Que fait le contrôle de couverture quand il trouve un trou ?** Je propose : **surface non affectée = simple
avertissement** affiché sur le plan (il est normal d'avoir des trous tant que le niveau n'est pas terminé), mais
**chevauchement entre locaux au-delà de 2 % = blocage de l'enregistrement**. **Recommandation : oui** ; un
chevauchement fausse directement les surfaces, un trou se voit et se comble.

**Q3 — Stockage des versions.** Trois options :
1. garder la copie complète à chaque enregistrement (simple, mais ~75 Mo par bâtiment) ;
2. **copie complète à l'import, puis seulement les différences** à chaque enregistrement (quelques kilo-octets),
   reconstruction à la demande ;
3. copie complète mais ne garder que les N dernières versions par local.
**Recommandation : l'option 2.** Elle ne perd rien et reste lisible. Elle demande une petite migration.

**Q4 — Voisins touchés.** Quand vous validez un local, je propose de faire repasser automatiquement ses voisins
concernés à l'état « à revoir », avec la mention de ce qui a changé. **Recommandation : oui** ; sinon une paroi
mitoyenne modifiée passe inaperçue.

**Q5 — Couper et fusionner des locaux.** Je propose de les inclure dans E3 plutôt que de les repousser, parce que
c'est précisément le geste qu'A6 rend nécessaire sur les plateaux ouverts. Cela alourdit le lot d'environ un
tiers. **Recommandation : oui, dans E3.** Si vous préférez un lot plus court, on livre d'abord le déplacement de
sommets et on garde couper/fusionner pour un E3 bis.

**Q6 — Qui code E3 ?** Codex vient de livrer E2 et connaît le code de l'étude ; je viens de mesurer la stabilité
des agents. Le dépôt est partagé, donc **un seul de nous deux doit travailler sur ces fichiers à la fois**.
Dites-moi lequel.
