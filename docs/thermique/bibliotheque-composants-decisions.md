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

## 8. Réponses et décisions (2026-09-11)

- **Q26 → vérifié en ligne** : les trois archives de l'utilisateur sont celles de la page
  officielle RE2020 « Documents d'application » (mêmes noms, tailles 9,9 / 4,4 / 17,9 Mo). Ce sont
  donc les applications **en vigueur** ; l'en-tête « RT 2012 » vient de fiches reprises telles
  quelles. Le tableau officiel de suivi date la mise en ligne au **16/12/2021** (parois vitrées :
  aucune mise à jour depuis). Les méthodes (généralités, matériaux, parois opaques, parois vitrées,
  ponts thermiques) sont publiées le 20/12/2017.
- **Q27** : les λ sont dans le fascicule **« matériaux »** (partie méthodes), absent du dossier mais
  gratuit. Téléchargé avec l'accord de l'utilisateur, avec les autres fascicules « méthodes » et le
  tableau de suivi, dans `Thermique/REGLES TH BAT/methodes_th-bat/` (non versionné).
- **Q28** : chauffage NF EN 12831-1 + complément national NF P 52-612 ; froid NF EN 16798-13 et
  NF EN ISO 52016-1. Normes payantes : exemplaires de l'utilisateur. Les facteurs solaires en
  conditions d'été (colonnes E) sont déjà portés par la bibliothèque.
- **Q30 → validation automatique seulement** (décision utilisateur). Réserve notée : un contrôle
  automatique ne détecte pas une valeur mal lue mais plausible ; compensé par l'affichage de la
  **source de chaque valeur** (document, page, paragraphe).
- **Q31** : B1 menuiseries, puis B2 parois opaques.

### Lot B1 — menuiseries (décisions)

| # | Décision |
|---|---|
| B1-D1 | Périmètre : fenêtres et portes-fenêtres (7 cas de protection × 8 menuiseries × 3 vitrages = 168 lignes) et leurs 4 tableaux de correctifs d'intégration ; portes (Ud) ; résistances des fermetures ; Ujour-nuit ; Uws. Vitrines, lanterneaux, vérandas, briques de verre et façades double peau : lot **B1-bis** |
| B1-D2 | Une édition = un fichier JSON versionné dans le moteur autonome (`thermique_moteur/donnees/menuiseries_<édition>.json`), reconstruit par `python -m thermique_moteur.bibliotheque.build "<REGLES TH BAT>"` ; l'édition est datée par le tableau officiel de suivi |
| B1-D3 | Contrôles automatiques : structure (3 vitrages par tableau, mêmes menuiseries dans chaque cas de protection, intitulés concordants), plages (U de 0,5 à 6,5 ; facteurs de 0 à 1), cohérence physique (triple ≤ double ; protection qui n'augmente ni U ni S ; Ujour-nuit et Uws inférieurs au Uw nu et décroissants avec R ; correctif à 50 cm ≤ correctif à 20 cm). Une **erreur** exclut la valeur des calculs ; une **alerte** la signale |
| B1-D4 | Règles d'usage du document appliquées : fenêtres **ni interpolées ni extrapolées** ; Ujour-nuit et Uws **interpolés** (bilinéaire, sans extrapolation) |
| B1-D5 | Consultation dans l'outil : page « Bibliothèque » (fenêtres par cas de protection, correctifs, portes, fermetures avec calcul Ujour-nuit / Uws) |
| B1-D6 | **Coquille du document officiel** : au §2.5.3 (p. 11), le Uws du triple vitrage est imprimé « 18 » (lu à l'identique par deux extracteurs, pypdf et pdfplumber). Règle : un U imprimé en entier à deux chiffres alors que les 8 autres valeurs ont une virgule est divisé par 10, **toujours signalé en alerte** avec le texte du document, puis soumis aux contrôles de cohérence (1,8 ≤ double 2,0 et ≤ Uw sans protection 2,1) |

**Résultat mesuré (2026-09-11)** : 168 lignes de fenêtres, 16 lignes de correctifs, 11 portes, 6
fermetures, Ujour-nuit (35 lignes) et Uws (18 lignes) ; **0 erreur, 1 alerte** (la coquille B1-D6).

## 9. Lot B2 — parois opaques (cadrage du 2026-09-11)

### Existant vérifié

- **Fascicule matériaux** (méthodes, 33 pages de texte, publié le 20/12/2017) : **88 tableaux** de
  λ utiles par défaut, avec masse volumique, capacité thermique et facteurs de diffusion de vapeur,
  pour les pierres, bétons, plâtres, terre cuite, bois et panneaux, isolants manufacturés (laines,
  PSE, XPS, polyuréthane…), matières synthétiques, métaux, sols, mortiers… Aucun tableau ne se
  poursuit sans en-tête sur la page suivante. Mise en page variable (une ligne par matériau, ou
  colonne par colonne ; cellules sur plusieurs lignes pour les essences de bois) : une lecture du
  texte ligne à ligne risquerait d'associer une λ à la mauvaise masse volumique.
- **Fascicule parois opaques** (méthodes, 39 pages) : Up = Uc + ΔU1 + ΔU2 + ΔU3 ; R = e / λ ;
  résistances superficielles (tableau X) ; lames d'air non ventilées (tableau V, interpolation
  autorisée) ; lames ventilées ; combles (tableau VI) ; ΔU'' sur trois niveaux ; ΔU3 pour les
  toitures inversées (précipitations par département, tableau XI) ; méthodes des planchers sur sol
  et sur vide sanitaire ; arrondis (R à 3 décimales, U à 2 chiffres significatifs).

### Découpage

| Sous-lot | Contenu |
|---|---|
| **B2a** | **Matériaux** (λ, ρ, Cp, μ) extraits des 88 tableaux + **calcul d'une paroi en couches** + **épaisseur d'isolant pour un U cible** + écran « Composer une paroi » |
| B2b | Tableaux d'applications : murs maçonnés (R des blocs et briques, en partie en image), toitures, planchers sur extérieur ou local non chauffé |
| B2c | Planchers sur sol et sur vide sanitaire (Ue), toitures inversées (ΔU3), combles |

### Décisions B2a

| # | Décision |
|---|---|
| B2-D1 | Tableaux matériaux lus **d'après la géométrie de la page** (position des mots, bordures des tableaux), pas ligne à ligne : l'alignement des colonnes est garanti par la page elle-même |
| B2-D2 | Calcul d'une paroi dans le moteur autonome (`thermique_moteur/parois.py`) : couches de l'intérieur vers l'extérieur ; couche = matériau de la bibliothèque, λ saisie (valeur fabricant), résistance connue, lame d'air non ventilée ou fortement ventilée ; ΔU1 saisi ; ΔU2 par niveau |
| B2-D3 | Les constantes du fascicule méthodes reprises dans le moteur (résistances superficielles, lames d'air, ΔU'') sont **recoupées automatiquement avec le texte du document** à chaque construction de la bibliothèque |
| B2-D4 | Épaisseur d'isolant : la plus petite épaisseur telle que Up ≤ U cible (dichotomie, Up décroissant avec l'épaisseur), puis arrondie au centimètre supérieur avec le Up obtenu |
| B2-D5 | Valeurs par défaut du fascicule : quand la masse volumique d'un matériau est inconnue, le document impose la λ la plus élevée de la famille ; l'écran le rappelle |
| B2-D6 | Règles d'extraction apprises sur le document : un appel de note (« 0,25* », « 1,3 (*) ») est gardé et **signalé en alerte** avec renvoi à la page ; une cellule fusionnée ne peut couvrir plusieurs lignes que pour Cp et μ, jamais pour λ ni ρ ; plancher de λ à 0,001 (gaz de vitrage : krypton 0,009, xénon 0,0054) |

**Résultat mesuré (2026-09-11)** : **294 matériaux** dans 96 sections, 14 renvois sans valeur
(« voir l'Avis technique »…), **0 erreur, 3 alertes** (notes du document : ardoises, plaques de
plâtre, mortiers). **Les 14 constantes** du calcul de paroi sont retrouvées à l'identique dans le
fascicule méthodes. Calcul de paroi vérifié sur des cas faits à la main (mur béton + 12 cm
d'isolant λ 0,032 : U = 0,25 ; 15 cm pour U ≤ 0,20).
