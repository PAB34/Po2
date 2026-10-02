---
type: decisions
status: actif
read_policy: si la tâche concerne la détection automatique ou la vérification par IA du métré thermique
related:
  - metre-plans-decisions.md
  - bibliotheque-projet-decisions.md
---

# Outil thermique — détection automatique et vérification par IA, planche par planche

> Fichier « fil du dev » écrit **avant** de coder l'étage IA (2026-09-14). Il fait suite au retour
> de l'utilisateur après le lot M1 : « il faut forcément une couche de type agent IA pour valider
> automatiquement la détection des parois, menuiseries, ponts thermiques » et « une méthodologie de
> détection et de vérification étape par étape, planche par planche ».

## 1. Retour de l'utilisateur (2026-09-14)

1. Les **coupes** doivent donner la hauteur sous plafond des niveaux ; saisie manuelle possible.
2. Le métré doit être **détecté automatiquement** (composants de l'enveloppe), puis ajusté à la main
   facilement.
3. Les **locaux non chauffés** restent déterminés par le thermicien.
4. Une **couche IA** valide automatiquement la détection (parois, menuiseries, ponts thermiques),
   avec une méthode **étape par étape, planche par planche**.

Réponse à « comment avancer sur la détection » : **intégrer maintenant**, améliorer ensuite.

## 2. Existant vérifié

| Élément | État |
|---|---|
| Onglet Métré (niveaux, calage, contours tracés à la main, synthèse) | En prod (M1, migration 0078) |
| Traits vectoriels du PDF (épaisseur) | En prod (`thermique_moteur/traits.py`) |
| Prototype **contour automatique** | Scratchpad : −1 et 2 justes, 0 presque, 1 à reprendre (façades vitrées, coursives, bandes plantées) |
| Prototype **planchers sur coupes** | Scratchpad : paires de traits épais parallèles ; écarts 4,16 / 3,84 / 3,84 m = cotes imprimées |
| Intégration IA (Anthropic ou autre) dans le dépôt | **Aucune** (ni SDK, ni clé, ni configuration) |
| `scipy` (morphologie d'image pour la détection) | Présent en local, **absent de l'image serveur** → à ajouter aux dépendances |

## 3. Pourquoi une couche IA, et pour quoi faire exactement

La géométrie vectorielle est **précise** (au millimètre) mais **aveugle** : elle ne sait pas lire
« terrasse », « coursive », « vide sur », une cote, une altitude NGF, un repère de menuiserie ou une
légende — ces textes sont vectorisés dans les PDF d'architecte. Un modèle de vision (Claude) **lit**
tout cela sur une image, mais ne donne pas de coordonnées fiables au centimètre.

**Principe retenu (proposé) : la géométrie mesure, l'IA vérifie et explique, le thermicien valide.**

- L'IA ne dessine jamais une coordonnée : elle **juge** des éléments proposés par le moteur
  (« ce côté est-il le nu intérieur d'une paroi sur l'extérieur ? »), **lit** des valeurs imprimées
  (cotes, altitudes, repères) et **signale** les incohérences.
- Chaque verdict porte une **justification courte** et une **image** du passage concerné : le
  thermicien voit pourquoi un élément est validé ou contesté.
- Une correction proposée par l'IA reste **« à valider »** tant que le thermicien ne l'a pas acceptée
  (acceptation groupée possible).

## 4. Méthode : étapes par planche

Chaque planche avance par étapes ; chaque étape a un statut **à faire → proposé (moteur) →
vérifié (IA) → validé (thermicien)**. On ne passe à l'étape suivante d'un niveau qu'après validation
de la précédente, mais les planches avancent en parallèle.

| # | Étape | Moteur géométrique | Vérification IA | Validation thermicien |
|---|---|---|---|---|
| 0 | **Tri des planches** | Nature et niveau d'après le nom du fichier (en prod) | Lit le cartouche : titre, niveau, échelle, indice | Confirme en un clic |
| 1 | **Échelle** | Échelle déclarée, contrôle par une cote (en prod) | Lit 2 ou 3 cotes imprimées et les compare aux longueurs mesurées → échelle confirmée sans clic | Accepte ou corrige |
| 2 | **Calage des niveaux** | Repère les files d'axes (cercles + traits d'axe) | Lit les repères d'axes (A…R, 1…18) et apparie les mêmes croisements d'un plan à l'autre | Contrôle la superposition |
| 3 | **Hauteurs** (coupes) | Planchers = paires de traits épais ; écarts et épaisseurs | Lit altitudes NGF et cotes de hauteur, rattache chaque plancher à un niveau, signale les écarts | Accepte, ou saisit la hauteur sous plafond |
| 4 | **Contour chauffé** | Contour au nu intérieur proposé (lot M3) | Vérifie tronçon par tronçon : terrasse, coursive, bande plantée, vide, patio ; propose de retirer ou d'ajouter une zone | Accepte les corrections, retouche |
| 5 | **Locaux non chauffés** | — | — (décision utilisateur) | **Trace lui-même** |
| 6 | **Parois : types** | Épaisseur de chaque côté (faces appariées), hachure | Lit la légende et les indications de matériau ; regroupe en types et suggère le composant de la bibliothèque | Rattache les composants |
| 7 | **Menuiseries** | Baies = interruptions des murs d'enveloppe, largeurs | Lit les repères et dimensions (plans, façades, tableau des menuiseries) ; hauteurs sur façades | Rattache aux composants menuiserie |
| 8 | **Ponts thermiques** | Déduits par superposition des niveaux (règle des quatre quarts, lot M2) | Vérifie les cas singuliers sur coupes : balcons, acrotères, décrochés, poutres | Rattache les composants ψ |
| 9 | **Rapport de vérification** | Récapitulatif chiffré | Liste ce qui a été vérifié, contesté, non vérifiable | Clôture le projet |

## 5. Architecture proposée

- **Moteur géométrique** (`thermique_moteur/`) : reste autonome et **sans IA** ; il produit des
  éléments identifiés (côtés, planchers, baies) avec leur emprise sur la planche.
- **Couche de vérification** (`thermique_agent/`, nouveau paquet autonome) : pour chaque étape,
  prépare les **images recadrées** (rendu pdfium de la zone, élément surligné), appelle **l'API
  Claude** avec une sortie **structurée** (verdict, valeur lue, confiance, justification), et renvoie
  les verdicts. Pas d'agent « libre » au départ : un **enchaînement piloté par le code**, étape par
  étape, plus simple à contrôler et à chiffrer ; un agent à outils pourra venir ensuite pour les cas
  ambigus.
- **Serveur** : exécution en **tâche de fond** par planche, progression visible ; les vérifications
  non urgentes d'un projet entier passent par l'API **Batches** (moitié prix).
- **Modèle** : `claude-opus-5` (vision, raisonnement adaptatif), avec repli automatique côté serveur
  en cas de refus.
- **Traçabilité** : chaque verdict est stocké (étape, élément, modèle, date, justification, image) ;
  une nouvelle détection ne remplace jamais une validation du thermicien.

## 6. Décisions proposées

| # | Proposition |
|---|---|
| AG-D1 | La géométrie mesure, l'IA vérifie et lit, le thermicien valide ; l'IA ne produit jamais de coordonnées |
| AG-D2 | Méthode en étapes 0 à 9 par planche, statut par étape (à faire, proposé, vérifié, validé) |
| AG-D3 | Couche IA dans un paquet autonome `thermique_agent/`, appelée par le serveur en tâche de fond |
| AG-D4 | Enchaînement piloté par le code avec sorties structurées ; pas d'agent libre au départ |
| AG-D5 | Toute correction de l'IA reste « à valider » ; acceptation groupée possible |
| AG-D6 | Détection géométrique livrée d'abord (contour M3 + hauteurs sur coupes), étage IA ensuite |

## 7. Questions ouvertes

- **Q46 — Confidentialité.** Les plans (images recadrées) sont envoyés à l'API d'Anthropic. Par
  défaut, les données de l'API ne servent pas à entraîner les modèles et sont conservées 30 jours.
  Est-ce acceptable pour les plans de vos clients (ou faut-il le mentionner dans vos conditions) ?
- **Q47 — Clé et facturation.** Un compte API Anthropic est nécessaire ; la clé sera placée par vous
  dans la configuration du serveur (je ne la manipule pas). Avez-vous déjà un compte, ou faut-il le
  créer ?
- **Q48 — Coût.** Estimation à confirmer par une mesure réelle : quelques dizaines de centimes à
  1 € par planche vérifiée (images recadrées, sorties courtes). Plafond par projet à prévoir ?
- **Q49 — Autonomie.** L'IA applique-t-elle directement ses corrections évidentes (marquées
  « corrigé par l'IA »), ou tout reste-t-il en proposition ?
- **Q50 — Ordre des étapes IA.** Proposition : commencer par **3 Hauteurs** et **4 Contour** (là où la
  géométrie seule bute), puis **1 Échelle** et **2 Calage** (gain de clics), puis 6, 7, 8.

## 8. Réponses

- **2026-09-14** — Détection : « Intégrer maintenant » (proposition corrigée à la main, améliorée
  ensuite). Sur les autres plans à tester, l'utilisateur répond par la demande de couche IA : « il faut
  forcément une couche de type agent IA pour valider automatiquement la détection des parois,
  menuiseries, ponts thermiques […] avoir une méthodologie de détection et de vérification étape par
  étape, planche par planche » → objet de ce document.
- **2026-09-14** — **Q46** : « l'agent IA doit être inclus dans Claude Code dans ce compte-ci, pas
  d'API » → pas d'appel à l'API Anthropic depuis le serveur (architecture §5 remplacée par §10).
  **Q47/Q48** : sans objet (pas de clé API). **Q49** : l'IA **propose**, le thermicien valide.
  **Q50** : commencer par **contour + hauteurs**.

## 10. Vérification par Claude Code (remplace l'architecture API du §5)

La vérification est faite par **Claude Code**, sur le compte de l'utilisateur, à sa demande :

1. Dans Claude Code, l'utilisateur lance la vérification d'un niveau ou d'une coupe
   (commande de projet, par exemple `/verifier-metre`).
2. Un script **prépare** sur le serveur (accès SSH existant) les pièces à examiner : image recadrée de
   chaque tronçon du contour et de chaque zone laissée dehors, élément surligné ; pour une coupe, image
   de chaque plancher repéré avec les cotes et altitudes autour ; plus un fichier des éléments détectés.
3. Claude Code **examine** chaque image selon une grille écrite (terrasse ? coursive ? bande plantée ?
   vide ? nu intérieur ? altitude lue ? cote lue ?) et rédige ses **verdicts** (conforme, à corriger avec
   la correction proposée, non vérifiable) avec une justification courte.
4. Un script **enregistre** les verdicts comme **propositions** dans la base ; l'onglet Métré les affiche
   sur le plan (image, justification) avec « Accepter » / « Refuser », un par un ou groupés.

Conséquences :

- **Aucune clé API** ni coût à l'appel : la vérification consomme l'abonnement Claude du compte.
- La vérification n'est **pas automatique dans le site** : elle a lieu quand l'utilisateur la lance
  dans Claude Code. Le moteur géométrique, lui, reste disponible dans le site pour tous.
- **À vérifier avant d'ouvrir l'outil à d'autres bureaux d'études** : un abonnement Claude est
  personnel ; un service offert à des tiers devra sans doute passer par l'API (conditions d'Anthropic
  à relire le moment venu). Pour l'étude de l'utilisateur, la voie Claude Code convient.

Décisions : AG-D3 et AG-D4 sont remplacées par **AG-D7** (vérification par Claude Code, scripts de
préparation et d'enregistrement, propositions stockées) ; AG-D5 confirmé (Q49).

## 9. Lot M3 — détection géométrique livrée (2026-09-14)

| Élément | Réalisation |
|---|---|
| Contour automatique | `thermique_moteur/detection.py` ; bouton « Détecter le contour de ce niveau » ; tracé marqué *automatique* → *corrigé* dès qu'on le retouche ; une nouvelle détection ne remplace un tracé corrigé ou manuel que sur confirmation. Projet d'essai : −1 902 m², 0 930 m², 1 854 m², 2 725 m² (0 et 1 à retoucher) ; 10 à 15 s par plan, résultat mis en cache |
| Hauteurs sur coupes | `thermique_moteur/coupes.py` : planchers = paires de traits épais (≥ 3 m cumulés, portée ≥ 2,5 m), orientation choisie par la portée totale, dessins séparés par les grands écarts ; panneau « Hauteurs depuis une coupe » (dessin, sens de lecture, intervalle du niveau le plus bas, aperçu, application). Coupe AB : 2,88 / 4,16 / 3,84 / 3,84 / 2,72 m |
| Hauteur sous plafond | Champ par niveau (migration `0079`), prime sur hauteur d'étage − plancher ; origine « coupe » ou « manuel » |
| Couleur des traits | `traits.lire_traits(..., avec_couleur=True)` : luminance du trait (foncé / hachure grise / trame claire) |
| Dépendance | `scipy` ajouté aux dépendances du serveur |
