---
type: decisions
status: actif
read_policy: si la tache concerne l'analyse IA visuelle des plans
related:
  - refondation-parcours-decisions.md
---

# Analyse IA visuelle du R+1 - decisions

## 1. Objectif

Analyser le plan R+1 comme le ferait un thermicien : a partir de l'image uniquement, extraire murs
exterieurs, refends, cloisons, isolation, menuiseries interieures et exterieures, terrasses et balcons.
Les objets sont proposes en une passe puis corriges manuellement uniquement en dernier recours.

## 2. Decision utilisateur du 2026-09-21

Le moteur de cette nouvelle piste **ne prend pas en compte les vecteurs PDF**, les plumes, les calques ou les
signatures graphiques. Le PDF est rasterise ; l'analyse repose sur la vision IA et le contexte du dessin.

Les moteurs vectoriels existants restent dans le backend pour conservation, mais ne participent ni a la
detection ni au score de cette piste.

## 3. Chaine retenue pour le test

1. Rendu du plan complet en haute definition.
2. Redressement de l'orientation et separation du cartouche.
3. Decoupage en tuiles recouvrantes ; une vue globale est conservee pour le contexte.
4. Analyse visuelle de chaque tuile avec une taxonomie imposee.
5. Pour chaque objet : masque ou ligne, nature, sous-type, confiance et justification visuelle.
6. Fusion des doublons dans les recouvrements et controle de coherence sur la vue globale.
7. Projection coloree complete sur le plan, avec file `a confirmer` limitee aux cas ambigus.

## 4. Taxonomie du MVP

- mur_exterieur ;
- refend ;
- cloison ;
- isolation ;
- menuiserie_exterieure ;
- menuiserie_interieure ;
- terrasse ;
- balcon ;
- poteau ;
- garde_corps ;
- indetermine.

Une porte est un sous-type de menuiserie. Une baie ou un mur-rideau reste une menuiserie exterieure ou
interieure selon le contexte visuel.

## 5. Sortie attendue

- inventaire JSON des objets avec coordonnees normalisees dans l'image source ;
- projection PNG/PDF avec une couleur par nature et un identifiant par objet ;
- bilan par famille et par niveau de confiance ;
- aucune classification silencieuse sous le seuil de confiance : l'objet reste `indetermine` ou
  `a confirmer`.

## 6. Verite terrain du R+1

La premiere projection IA n'est pas consideree comme vraie par principe. Elle devient la base de validation :
le thermicien corrige les objets faux ou manquants, et cette version validee sert ensuite de jeu d'evaluation
pour les prochains plans.

## 7. Audit de l'existant (2026-09-21)

- Le bouton `Analyser le plan` appelait `thermique_detection.py`, qui lisait les elements vectoriels,
  designait leurs signatures puis imposait l'ordre objets -> pieces -> enveloppe -> menuiseries.
- `AutoZoningPage.tsx` ne savait afficher et corriger que des polygones de pieces.
- Le rendu raster haute definition existe deja (`thermique_raster.py`) et fournit la transformation exacte
  pixels <-> points PDF : il est reutilise sans rouvrir les vecteurs.
- Aucun client IA multimodal n'existait dans le depot.

## 8. Premier socle livre sur la branche

- Nouveau service `thermique_vision.py`, completement separe de `thermique_moteur/reconnaissance.py`.
- Entree : pyramide raster existante recomposee, une vue globale et six tuiles recouvrantes.
- Sortie structuree : categorie, sous-type, geometrie, points, confiance, indice visuel et besoin de revue.
- Conversion des coordonnees normalisees IA vers les points PDF de la visionneuse.
- Persistance par planche dans le stockage thermique (`vision-analysis.json`), sans migration de base pour ce
  premier test.
- Ecran transforme en inventaire colore des composants : selection sur le plan ou dans la liste, changement
  de nature, validation et edition de chaque point ; ajout et suppression manuels restent disponibles en
  dernier recours.
- Les anciennes routes et technologies sont conservees, mais la route `/analyse` ne les appelle plus.

## 9. Changement de mode d'execution : agent Claude Code personnel

Decision utilisateur du 2026-09-21 : le premier essai ne doit pas etre facture ou authentifie par une cle
multimodale du SaaS. L'analyse doit etre realisee par un agent specialise lance depuis le compte Claude Code
du thermicien.

Le socle est donc complete par :

- un agent de projet `.claude/agents/thermicien-plan.md`, limite a la lecture des images ;
- un lanceur generique `scripts/run_thermicien_claude.py` qui rasterise un PDF, prepare une vue globale et six
  tuiles, impose le schema JSON et interroge Claude Code en mode non interactif ;
- un manifeste qui conserve dimensions, rotation et bornes normalisees de chaque tuile ;
- un recadrage automatique par densite d'encre qui separe le dessin principal du cartouche et des marges,
  avec reprojection des points vers le repere de la feuille complete ;
- une consigne explicite de simplification des lignes droites afin d'eviter les traces en zigzag.
- une projection PNG generee apres chaque analyse, avec couleurs, identifiants, bilan par categorie et nombre
  d'objets a confirmer.

Ce pont utilise l'authentification deja geree localement par Claude Code. Il ne lit, ne copie et ne stocke
aucun secret Claude. L'adaptateur API existant reste conserve comme solution de repli technique, mais ce n'est
plus la voie recommandee pour le test R+1.

Limite assumee de cette etape : l'agent local doit etre connecte et lance sur le poste du thermicien. Une
execution autonome pour plusieurs utilisateurs devra passer par une authentification serveur officiellement
supportee (API Anthropic, identite de charge, ou routine Claude Code lorsque ce mode experimental repondra au
besoin de fichiers et de retour de resultat).
