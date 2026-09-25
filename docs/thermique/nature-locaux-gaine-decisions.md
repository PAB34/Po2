# Nature des locaux et gaines techniques — décisions avant développement

> Cadrage du sujet 8 demandé le 2026-09-25. Ce document est écrit avant toute modification du code.
> Périmètre : rendre la nature d'un local directement modifiable, puis ajouter la nature
> `gaine_technique`. Le Ctrl+Z fera l'objet d'un fichier de décisions distinct après ce lot.

## 1. Existant vérifié le 2026-09-25

### Changer la nature d'un local

- Le serveur accepte déjà une opération `modifier` limitée au champ `nature` :
  `thermique_etude_edition.py:110-126`. La nature est contrôlée par `LOCAL_NATURES`.
- Les routes existantes savent prévisualiser puis enregistrer cette opération :
  `POST .../etude/remodeliser` et `POST .../etude/enregistrer` dans
  `api/routes/thermique.py:616-670`. Un enregistrement crée déjà une version.
- Le front sait déjà envoyer `nature` dans une opération `modifier` :
  `useStudyEdition.ts:63-74`, mais le choix est enfoui dans le brouillon de reprise du contour
  (`StudyPanel.tsx:185-221`).
- La fiche n'affiche aujourd'hui la nature qu'en texte sous le nom du local
  (`StudyPanel.tsx:290-303`).
- Le clic droit hors édition ne propose que l'ouverture de la fiche, la reprise du contour et la coupe
  (`WorkspacePage.tsx:509-537`).
- Une modification de nature recalcule les fiches du local et de ses voisins. Elle ne doit pas valider
  implicitement le contour : le serveur sait conserver l'état avec `valider: false`.
- Les corrections d'éléments ont leur propre pile locale dans `useStudyElements.ts`. Enregistrer une
  nature pendant que cette pile est en attente ferait afficher une base ancienne. Le geste doit donc
  être indisponible tant que ces corrections ne sont pas enregistrées ou abandonnées.

### Ajouter `gaine_technique`

- D115 est déjà tranchée par l'utilisateur : la quatrième nature est `gaine_technique`, avec le libellé
  « Gaine technique ».
- Les trois natures actuelles sont déclarées côté serveur dans `thermique_etudes.py:52`, dans le schéma
  d'opération, dans deux consignes d'agents raster et dans le validateur de benchmark.
- Côté front, `StudyLocalNature`, l'ordre, les libellés et les couleurs ne connaissent que trois valeurs.
- La fiche considère aujourd'hui une adjacence `non_chauffe` comme déperditive, mais empêche un local de
  nature `non_chauffe` de compter ses propres déperditions (`thermique_fiches_locaux.py:26,166,180,295`).
- Le contrôle ciblé de tous les `non_chauffe` du code applicatif a trouvé deux chemins actifs absents de
  la liste de passation :
  - `thermique_locaux.py:25,211-216,230,236` porte le vocabulaire du classement raster des locaux ;
  - `thermique_lecture_locaux.py:24-25,150-160` décide quels côtés d'un local chauffé sont lus comme
    donnant sur un local non chauffé. Sans `gaine_technique` dans ces adjacences, une paroi voisine
    pourrait sortir du relevé en silence.
- `thermique_lecture_locaux.LOCAUX_LUS` doit rester limité à `chauffe` et `circulation` : une gaine ne
  produit pas ses propres déperditions. En revanche, `ADJACENCES_LUES` et `ADJACENCES_COMPLEMENT` doivent
  accepter une gaine derrière le mur d'un local chauffé.
- Les vocabulaires « nature du local » et « adjacence d'un côté » restent distincts. La sonde reprend
  toutefois la nature du voisin comme valeur d'adjacence ; c'est pourquoi `gaine_technique` doit être
  admise dans les ensembles d'adjacences déperditives.

## 2. Décisions datées

**D115 — 2026-09-25 — Nature dédiée.** Les quatre natures de local sont `chauffe`, `circulation`,
`non_chauffe` et `gaine_technique`.

**D116 — 2026-09-25 — Nature directement sur la fiche.** Sous le nom du local, le texte statique devient
une liste de choix. Changer sa valeur enregistre immédiatement la nouvelle nature avec l'opération
existante `modifier`, sans ouvrir ni fabriquer un brouillon de contour.

**D117 — 2026-09-25 — Recalcul et traçabilité sans validation implicite.** Le changement direct appelle
la route d'enregistrement existante, crée une version au motif `nature_local`, recalcule les métrés et
utilise `valider: false`. Un local validé reste validé ; un local à vérifier ne devient pas validé par le
seul fait d'avoir été reclassé. Les voisins déjà validés repassent à revoir si leur fiche change, selon la
règle serveur existante D63.

**D118 — 2026-09-25 — Choix depuis le clic droit.** Hors édition de contour, le menu du plan propose une
action « Classer : … » pour chacune des autres natures. La nature actuelle n'est pas répétée. Le geste
utilise exactement la même fonction d'enregistrement que la fiche.

**D119 — 2026-09-25 — Pas de mélange de brouillons.** Le choix de nature est désactivé pendant un tracé
de contour, un calcul en cours ou tant que des corrections d'éléments attendent d'être enregistrées ou
abandonnées. L'écran explique la raison ; aucune correction locale n'est écrasée en silence.

**D120 — 2026-09-25 — Comportement thermique d'une gaine.** Une gaine se calcule comme un local non
chauffé : aucune déperdition propre ; toute limite d'un local chauffé avec elle est une paroi déperditive
sur local non chauffé. Les filtres de fiches, de lecture des côtés et de planche d'adjacences doivent tous
appliquer cette règle. Ajouter la valeur sans reclasser de local ne doit modifier aucun chiffre du R+1.

**D121 — 2026-09-25 — Restitution distincte.** Le libellé est « Gaine technique » et la couleur dédiée est
violette (`#7c3aed`), distincte du gris du non chauffé. La même couleur est utilisée dans la restitution
front et la planche d'adjacences produite par le serveur.

**D122 — 2026-09-25 — Les agents raster apprennent la nouvelle valeur.** Les deux consignes serveur qui
classent des locaux doivent distinguer une gaine (`gaine_technique`) d'un autre local technique non
chauffé (`non_chauffe`). Le fichier `.claude/agents/thermicien-plan.md` reste strictement inchangé.

## 3. Question tranchée avant le code

**Q1 — Validation du geste direct.** Valides-tu le comportement recommandé D116 à D119 : choix enregistré
immédiatement depuis la fiche ou le clic droit, sans bouton supplémentaire, sans valider implicitement le
local, et temporairement bloqué si une autre correction locale est encore en attente ?

**Réponse utilisateur du 2026-09-25 : « ok recommandation ».** D116 à D119 sont validées.

## 4. Vérifications prévues

- Tests front ciblés du workspace : quatrième nature, ordre/libellé/couleur et déclenchement du geste
  direct depuis la fiche et le menu du plan.
- Tests backend ciblés : validation/enregistrement de la nature, fiches et adjacences, lecture des côtés,
  classement raster et validation des sorties d'agent.
- Typecheck front, puis uniquement les tests thermiques concernés.
- Garde-fou sur le R+1 réel, sans reclassification : **227 éléments, 222 côtés cotés, 170,12 m
  déperditifs, 289 formes, 77 liaisons**, strictement inchangés.
- Cas synthétique reclassé en gaine : zéro déperdition propre pour la gaine ; la pièce chauffée voisine
  conserve une paroi déperditive, comptée dans `sur_non_chauffe_m` et non dans `facade_m`.

## 5. Résultats du développement (2026-09-25)

- La nature est maintenant choisie directement dans la fiche et depuis les actions « Classer : … » du
  clic droit. Le brouillon de contour ne porte plus ce choix.
- Le geste crée une version `nature_local`, recalcule le niveau avec `valider: false` et se bloque quand
  un contour ou des corrections d'éléments sont en attente.
- `gaine_technique` est reconnue par l'import, les deux chaînes raster, le benchmark, les fiches, la
  planche d'adjacences et le front. Une gaine a sa couleur violette et son libellé propre.
- Tests backend ciblés : **43 réussis** au total (42 sur édition/fiches/lecture/classement/benchmark,
  plus le contrôle d'import dédié).
- Tests frontend thermiques ciblés : **11 fichiers, 86 tests réussis** ; typecheck et build Vite réussis.
  Le build ne signale que l'avertissement préexistant sur la taille du bundle principal.
- Recalcul du vrai `etude-R1.v3.json` : **227 éléments, 222 côtés, 170,12 m déperditifs, 289 formes,
  77 liaisons**, strictement identiques avant et après.
- Simulation en mémoire de `piece-015` reclassé de `non_chauffe` en `gaine_technique` : 0 m de
  déperdition propre ; les côtés des locaux chauffés voisins restent déperditifs ; totaux inchangés
  (`sur_non_chauffe_m` 36,33 m, `facade_m` 138,63 m).
- Aucune recette authentifiée à la souris n'a été faite : conformément à la règle permanente, aucun mot
  de passe n'a été demandé, affiché ou saisi.

## 6. Hors périmètre de ce lot

- Dessiner une gaine absente : dépend du futur geste d'ajout d'un local.
- La nature extérieure des terrasses : comportement thermique différent, décision séparée.
- Ctrl+Z / Rétablir : fichier de décisions et question dédiée après livraison de D115.
