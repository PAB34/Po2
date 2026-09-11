---
type: decisions
status: actif
read_policy: si la tâche concerne la bibliothèque de composants de l'outil thermique
related:
  - metre-thermique-decisions.md
  - etape2-geometrie-decisions.md
---

# Outil thermique — bibliothèque de composants (cadrage, décisions, questions)

> Fichier « fil du dev » écrit **avant** de coder (2026-09-11). Demande de l'utilisateur : l'étude
> thermique doit permettre de préciser l'**épaisseur d'isolant** des murs et des planchers et la
> **performance des menuiseries** ; un calcul plus fin des **déperditions** sert ensuite à
> dimensionner les équipements CVC. L'outil doit assister les deux, avec **la même bibliothèque de
> composants et les mêmes performances**, constituée maintenant sur la base de
> `Thermique/REGLES TH BAT`.

## 1. Existant vérifié

- **Po2 : aucune bibliothèque thermique** (recherche de conductivité, U, ψ, 12831, Th-U dans
  `saas/` : rien). Tout est à créer.
- **Sources fournies : 47 PDF « Th-Bât applications », 558 pages** (mesuré le 2026-09-11) :

| Famille | Documents | Pages | Ce qu'ils donnent | Lisibilité |
|---|---|---|---|---|
| Parois opaques | Murs · planchers bas (sur sol ; sur extérieur ou local non chauffé) · toitures, rampants, plafonds · cloisons · isolation inversée · facteur solaire lame d'air | 133 | Résistances R des éléments (maçonneries, blocs…), U de planchers et toitures | Texte, mais une partie des tableaux est en image (murs : 36 pages sur 48 avec image) : à vérifier tableau par tableau |
| Parois vitrées | Fenêtres et portes-fenêtres (Uw, Sw, TLw) · portes (Ud) · Ujour/nuit · protections mobiles · vitrines · lanterneaux · vérandas · briques de verre · façades double peau | 35 | Valeurs tabulées par type de fenêtre, nombre de vantaux, part vitrée σ, vitrage, en conditions de consommation (C) et d'été (E) | **Texte propre**, tableaux lisibles directement |
| Ponts thermiques | ITI · ITE · ITR · isolation mixte · ossatures bois · ossatures métalliques · sandwichs lourds · dispositions constructives (DC) | 390 | ψ en W/(m·K) par liaison, fonction de paramètres (résistance de l'isolant, épaisseur du plancher, du mur…), avec répartition et majorations | Texte + schémas en image ; **ossatures bois (82 pages) entièrement scanné → reconnaissance de caractères** |

- **Version** : les en-têtes portent « Réglementation thermique 2012 » (22 mentions) ; un seul
  document mentionne la RE2020 → Q26.
- **Manquant pour calculer un U à partir des couches** (donc pour déterminer une épaisseur
  d'isolant) : les conductivités λ des matériaux et les méthodes de calcul (fascicules
  « matériaux » et « méthodes », absents du dossier) → Q27.

## 2. Deux usages, mêmes composants

| | Étude thermique | Calcul des déperditions (dimensionnement CVC) |
|---|---|---|
| Parois opaques | U (W/(m²·K)) | U, même valeur |
| Menuiseries | Uw, Sw, TLw, Ujour/nuit | Uw (et Ujour/nuit) |
| Ponts thermiques | ψ, χ | ψ, χ |
| Géométrie | Surfaces et linéaires par paroi, niveau et orientation | Idem **+ pièces et zones** (logements, commerces) |
| Référence de calcul | Règles Th-Bât, moteur réglementaire | NF EN 12831-1 (à confirmer, Q28) |

## 3. Décisions proposées (à valider)

| # | Proposition | Raison |
|---|---|---|
| B-D1 | **Une seule bibliothèque**, lue par les deux calculs | Demande de l'utilisateur : mêmes composants, mêmes performances |
| B-D2 | **Chaque valeur est sourcée** (document, page, tableau, ligne) et porte un statut : *extraite* ou *vérifiée*. Seules les valeurs vérifiées servent aux calculs | Exigence « irréprochable » ; une valeur réglementaire fausse fausse toute l'étude |
| B-D3 | Les **calculs** (U d'une paroi en couches, recherche d'un ψ dans un tableau avec interpolation et majorations) vivent dans le **moteur autonome** (sans base ni serveur) | Même règle que l'étape 2 ; voie « logiciel installé » ouverte |
| B-D4 | Bibliothèque **versionnée par édition des règles** (2012, 2020…) ; un projet reste attaché à l'édition choisie | Les règles évoluent ; une étude doit rester reproductible |
| B-D5 | Paroi opaque = **couches ordonnées** (matériau + épaisseur, ou élément à R tabulé comme un bloc) ; **l'épaisseur d'isolant est un paramètre**, d'où la question « quelle épaisseur pour atteindre tel U » | C'est l'objet même de l'étude (réponse Q1) |
| B-D6 | Valeurs **par défaut** (tableaux Th-Bât) et, plus tard, valeurs **fabricant** (certificats ACERMI, fiches de menuiseries) côte à côte | Les tableaux Th-Bât sont des valeurs par défaut, souvent pénalisantes |

## 4. Modèle proposé

- **Matériau** : nom, λ (W/(m·K)), masse volumique, capacité thermique, source.
- **Paroi opaque** (mur, plancher bas/intermédiaire/haut, toiture, cloison) : couches ordonnées,
  sens du flux (horizontal, montant, descendant) pour les résistances superficielles → U calculé,
  ou U tabulé quand le fascicule le donne directement.
- **Menuiserie** : type (fenêtre, porte-fenêtre, porte, vitrine, lanterneau…), vantaux, part
  vitrée σ, vitrage, fermeture → Uw, Sw (C et E), TLw, Ujour/nuit.
- **Liaison (pont thermique)** : système d'isolation (ITI, ITE, ITR, mixte, ossature), type de
  liaison (plancher bas, intermédiaire, haut, refend, menuiserie, seuil, angle…), paramètres
  d'entrée du tableau → ψ, répartition entre les parois, majorations.

## 5. Chaîne de constitution

```
PDF Th-Bât ─► extraction automatique des tableaux (texte ; reconnaissance de caractères si image)
          ─► fichier structuré par tableau, chaque valeur liée à sa page
          ─► écran de vérification côte à côte : valeur extraite | page d'origine (visionneuse en tuiles déjà en place)
          ─► validation humaine ─► publication dans l'édition de la bibliothèque
```

## 6. Découpage proposé

| Lot | Contenu | Pourquoi dans cet ordre |
|---|---|---|
| **B1** | **Menuiseries** (35 pages, texte propre) : extraction, vérification, consultation | Chaîne complète sur la famille la plus simple ; répond à « performance des menuiseries » |
| **B2** | **Parois opaques** : tableaux + calcul d'U en couches + « épaisseur d'isolant pour un U cible » | Cœur de la demande ; dépend des λ (Q27) |
| **B3** | **Ponts thermiques** ITI, ITE, ITR, mixte, DC : tableaux paramétrés, interpolation | Plus volumineux (≈ 300 pages de texte) |
| **B4** | Ossatures bois et métal, sandwichs lourds (reconnaissance de caractères) | Documents scannés, plus longs à fiabiliser |
| Puis | Rattachement aux éléments géométriques (étape 2), calculs U × surface et ψ × longueur, déperditions par pièce et par zone | Une fois la bibliothèque validée |

## 7. Questions ouvertes

- **Q26 — Édition des règles.** Les fascicules portent « Réglementation thermique 2012 ». Sont-ils
  l'édition en vigueur pour vos études (neuf RE2020, existant) ? S'il existe une édition plus
  récente des règles Th-Bât, pouvez-vous l'ajouter au dossier ?
- **Q27 — Conductivités des matériaux.** Pour calculer un U à partir des couches, il faut les λ.
  Avez-vous le fascicule « matériaux » des règles Th-Bât (et les fascicules « méthodes ») ? Sinon,
  on partira des valeurs des fabricants (certificats ACERMI).
- **Q28 — Calcul des déperditions.** Norme visée : NF EN 12831-1 et son complément national ? Il
  faudra aussi les températures extérieures de base (par zone climatique et altitude).
- **Q29 — Droits de réutilisation.** Pour un outil vendu à des bureaux d'études, la reprise des
  valeurs Th-Bât dans une base est à vérifier auprès de l'éditeur des règles. Sans objet pour un
  usage interne.
- **Q30 — Validation.** Qui vérifie les valeurs extraites : vous, tableau par tableau, ou par
  échantillon ?
- **Q31 — Ordre des lots.** B1 menuiseries puis B2 parois opaques vous convient-il, ou préférez-vous
  commencer par les parois opaques (épaisseurs d'isolant) ?
