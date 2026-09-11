# Bibliothèque de projet — cadrage (2026-09-11)

Outil de métré thermique (`thermique.patrimoineaucarre.com`). Fait suite à
`bibliotheque-composants-decisions.md` (lots B1, B2a, B2b-1 en production).

## 1. Constat de l'utilisateur (2026-09-11)

- Dans un logiciel thermique, on **constitue sa bibliothèque pour chaque projet** ou on **réutilise
  une bibliothèque par défaut / enregistrée** ; elle regroupe tous les composants du bâtiment par
  catégorie : murs, planchers (bas, intermédiaires, hauts…), menuiseries, ponts thermiques…
- Une fois une paroi ou une menuiserie composée, on doit pouvoir **en créer une autre** et
  **déplier / replier** chaque composition pour en voir le contenu.
- La bibliothèque est **l'élément central de l'expérience** : elle doit être intuitive et pratique.
- Le travail fait jusqu'ici est jugé bon, mais **ne correspond pas à l'usage réel** : on consulte
  des données et on calcule une paroi, sans rien enregistrer ni réutiliser.
- Deux questions ouvertes : détecter d'abord puis proposer une bibliothèque, ou l'inverse ? Lire
  d'abord les CCTP (gros œuvre, menuiseries, cloisons-doublages) ? Sachant qu'une **étude
  préliminaire** (voire pièce par pièce, pour dimensionner les CVC et préconiser les épaisseurs
  d'isolant) précède la rédaction des CCTP, et que **l'étude RE2020** vient ensuite (phase PRO / PC).

## 2. Existant vérifié (sur `main`, 2026-09-11)

- **Projet** (`app/models/thermique.py`) : `ThermiqueProject` → documents (PDF) → planches (nature,
  niveau, échelle, calage). **Aucune table de composants** : rien n'est enregistré par projet.
- **Page `/bibliotheque`** (front `src/thermique/pages/LibraryHomePage.tsx`) : globale, en lecture —
  référentiel Th-Bât (menuiseries B1, matériaux B2a, éléments tabulés B2b-1) + « Composer une
  paroi » qui calcule sans enregistrer.
- **Moteur autonome** `saas/backend/thermique_moteur/` : `calculer_paroi` (couches, Rsi/Rse, lames
  d'air, ΔU1, ΔU2, couche « élément ») et `epaisseur_isolant` (U cible) ; menuiseries (Uw, Sw, TLw,
  Ujour-nuit). **Tout cela est réutilisable tel quel** : ce sont les ingrédients des composants.

## 3. Modèle proposé : trois niveaux

| Niveau | Contenu | Qui le modifie |
|---|---|---|
| **Référentiel réglementaire** | Données Th-Bât versionnées : matériaux, éléments tabulés, menuiseries par défaut, ponts thermiques (B3) | Personne (reconstruit depuis les documents officiels) |
| **Ma bibliothèque** (modèles) | Compositions enregistrées pour être réutilisées d'un projet à l'autre, + une bibliothèque par défaut fournie (Q34) | L'utilisateur (ou son bureau d'études, Q33) |
| **Bibliothèque du projet** | Les composants du bâtiment étudié, par catégorie | L'utilisateur, dans le projet |

- Importer un modèle dans un projet en fait une **copie** : modifier le composant du projet ne
  change ni le modèle ni les autres projets. Action inverse : « Enregistrer comme modèle ».
- Le référentiel Th-Bât reste consultable (onglets actuels) et devient surtout la **source de
  recherche** de l'éditeur de composition.

## 4. Catégories (valeur par défaut, Q36)

| Catégorie | Sous-catégories | Résultat |
|---|---|---|
| Murs | extérieurs, sur local non chauffé, enterrés ; refends et cloisons (entre locaux, utiles au calcul pièce par pièce) | Up |
| Planchers bas | sur terre-plein, sur vide sanitaire, sur local non chauffé, sur extérieur | Up (Ue en B2c) |
| Planchers intermédiaires | entre niveaux chauffés, sur local d'une autre zone | Up |
| Planchers hauts et toitures | toiture terrasse, combles perdus, rampants, sous local non chauffé | Up |
| Menuiseries | fenêtres, portes-fenêtres, portes, lanterneaux ; avec ou sans fermeture | Uw, Sw, TLw, Ujn |
| Ponts thermiques | liaisons plancher bas, intermédiaire, haut, refend, menuiserie… | ψ |

Un composant porte : un **code** (proposé automatiquement, modifiable : `MUR 1`, `PB 1`, `PH 1`,
`F 1`, `PT 1` — Q38), un nom, sa catégorie, sa composition, son résultat, son épaisseur totale,
ses sources (tableau et page Th-Bât, valeur fabricant), un statut (hypothèse / conforme CCTP) et
des notes.

## 5. Expérience proposée

- **Onglet « Bibliothèque » dans chaque projet** : à gauche, l'arborescence des catégories avec
  leur nombre de composants ; au centre, les composants sous forme de **cartes repliées** sur une
  ligne (`MUR 1 · Parpaing 20 + PSE 12 cm · Up 0,24 · 34 cm`).
- **Déplier une carte** = voir ses couches (de l'intérieur vers l'extérieur) et le détail du calcul ;
  actions : modifier, dupliquer, enregistrer comme modèle, supprimer. Plusieurs cartes peuvent être
  dépliées à la fois pour comparer.
- **« + Nouveau »** dans chaque catégorie : partir de zéro, d'un modèle de « Ma bibliothèque » ou
  d'un composant existant (dupliquer puis ajuster, le geste le plus fréquent).
- **Éditeur** = l'actuel « Composer une paroi », intégré à la carte, avec une **recherche unique**
  pour ajouter une couche (« parpaing 20 », « laine de verre 32 », « ba13 ») qui cherche à la fois
  dans les matériaux, les éléments tabulés et « Ma bibliothèque » ; épaisseur d'isolant pour un U
  cible dans la carte (préconisation).
- **Page « Ma bibliothèque »** (hors projet) : même présentation, pour gérer les modèles.

## 6. Détecter d'abord, ou bibliothèque d'abord ?

**Position : la bibliothèque d'abord, indépendante des plans ; la détection vient ensuite et
rattache la géométrie aux composants.**

1. Un plan ne dit pas la composition : au mieux une épaisseur, une hachure, une légende. La
   détection ne peut produire que des **types géométriques** (« mur extérieur 30 cm, 124 m »,
   « baie 120 × 215, 14 unités »), jamais un U.
2. Un bâtiment compte **peu de types** (3 à 6 murs, 2 à 4 planchers, 3 à 8 menuiseries) mais des
   centaines de segments : on définit les types une fois, on les affecte ensuite.
3. L'étude préliminaire se fait parfois sur des plans provisoires : la bibliothèque doit vivre sans
   détection.
4. **La boucle** : la détection liste les types trouvés (épaisseur × position × quantité) ; pour
   chacun, l'utilisateur choisit un composant existant ou en crée un à la volée ; les métrés
   portent la référence du composant → quantités par composant (m² de `MUR 1`, ml de `PT 3`).

Conséquence sur les données : le composant est **indépendant** de la géométrie ; un élément
géométrique pointe vers un composant (ou reste « non affecté »). Les deux chantiers avancent sans
se bloquer.

## 7. Et les CCTP ?

- **Phase préliminaire** (APS / APD, dimensionnement CVC, pièce par pièce) : le CCTP n'est pas
  encore écrit ; c'est l'étude qui produit les **préconisations** (R minimale et épaisseur
  d'isolant, Uw, Sw) reprises ensuite dans le CCTP. L'outil doit donc surtout **exporter** ces
  préconisations, composant par composant, plutôt que lire un CCTP.
- **Phase PRO / PC** (étude RE2020) : le CCTP existe ; le lire aiderait à **mettre à jour** les
  compositions et à repérer les écarts avec les hypothèses. Utile, mais plus tard : la lecture de
  documents rédigés librement donne des résultats à valider un par un.
- Donc : pas de lecture de CCTP en première étape ; un statut par composant (hypothèse / conforme
  CCTP) et une notion de phase dans le projet (Q35).

## 8. Découpage proposé

| Lot | Contenu |
|---|---|
| **L1** | Données : composants du projet et modèles de l'utilisateur (composition en JSON au format du moteur, résultat recalculé côté serveur à chaque enregistrement avec la version du référentiel utilisée) ; API (créer, modifier, dupliquer, supprimer, importer un modèle, enregistrer comme modèle) |
| **L2** | Onglet « Bibliothèque » du projet : arborescence, cartes repliables, éditeur de paroi opaque intégré avec recherche unique ; page « Ma bibliothèque » |
| L3 | Composants menuiseries (fenêtre + fermeture → Uw, Sw, TLw, Ujn) et ponts thermiques (ψ saisi, puis tabulé avec B3) |
| L4 | Bibliothèque par défaut fournie (Q34) ; export des préconisations |
| ensuite | Référentiel : B2b-2 (U tabulés), B2b-3 (ψ, χ intégrés), B2c (sol, ΔU3), B3 ; étape 2 géométrie → affectation aux composants |

## 9. Décisions proposées

| # | Décision |
|---|---|
| BP-D1 | Trois niveaux : référentiel Th-Bât (lecture seule), modèles réutilisables, bibliothèque du projet |
| BP-D2 | Importer un modèle dans un projet = copie ; « Enregistrer comme modèle » pour l'inverse |
| BP-D3 | La composition est stockée au format d'entrée du moteur ; le résultat est recalculé côté serveur, avec la version du référentiel, pour la traçabilité |
| BP-D4 | Composant indépendant de la géométrie ; la détection rattache ensuite des types géométriques aux composants |
| BP-D5 | Pas de lecture de CCTP en première étape ; export des préconisations en L4 |
| BP-D6 | Codes proposés automatiquement par catégorie et modifiables (Q38) |

## 10. Questions

- **Q33** — Partage : « Ma bibliothèque » personnelle seulement, ou aussi une bibliothèque de
  bureau d'études partagée entre plusieurs comptes (lié à Q16 et Q17) ?
- **Q34** — Fournir une bibliothèque par défaut (compositions types courantes), ou partir vide ?
- **Q35** — Phases : un projet porte les deux phases (préliminaire puis RE2020) avec la même
  bibliothèque qui évolue, ou on duplique le projet à chaque phase ?
- **Q36** — Les catégories du §4 sont-elles complètes (murs-rideaux, vérandas, parois
  enterrées…) ?
- **Q37** — Priorité : la bibliothèque de projet (L1, L2) avant de continuer le référentiel
  (B2b-2…) ?
- **Q38** — Codes des composants : proposés automatiquement (`MUR 1`, `PB 1`…) et modifiables, ou
  une autre convention propre à votre pratique ?

## 11. Réponses (2026-09-11)

| Question | Réponse | Conséquence |
|---|---|---|
| Q37 priorité | **Bibliothèque de projet d'abord** | L1 puis L2 ; B2b-2 et suivants après |
| Q33 partage | **Modèles personnels d'abord** | Modèles rattachés au compte ; partage de bureau d'études avec Q16 / Q17 |
| Q34 par défaut | **Oui, quelques compositions types** | En L4, sourcées Th-Bât |
| Q35 phases | **Un projet, statut par composant** | Statut « hypothèse » / « conforme CCTP » sur chaque composant, pas de phases |
| Q36 catégories | Sans réponse : **liste du §4 retenue** | Ajustable sans migration (catégories dans le moteur, pas en base) |
| Q38 codes | Sans réponse : **codes proposés et modifiables** | `MUR 1`, `PB 1`, `PI 1`, `PH 1`, `F 1`, `PT 1` |

## 12. Résultat L1 + L2 (2026-09-11)

- **Données** : table `thermique_components` (migration 0077) — un composant appartient à un
  projet ou aux modèles du compte (`project_id` vide) ; composition au format du moteur, résultat
  et éditions du référentiel stockés à chaque enregistrement ; `source_component_id` garde l'origine
  d'une copie sans lien actif.
- **Moteur** `thermique_moteur/composants.py` : catégories, codes proposés, calcul (parois en
  couches ; menuiseries et ψ saisis en attendant L3), épaisseur totale et résumé des couches ; une
  composition incomplète s'enregistre comme brouillon (« à compléter »).
- **API** : `GET /composants/categories`, `POST /composants/evaluer`, composants d'un projet
  (lister, créer, importer un modèle), `GET/POST /modeles`, `PATCH/DELETE /composants/{id}`,
  `POST /composants/{id}/dupliquer`, `POST /composants/{id}/modele`.
- **Écran** : onglets « Plans et planches » / « Bibliothèque » dans chaque projet ; « Mes modèles »
  en premier onglet de la page Bibliothèque (le référentiel Th-Bât reste consultable à côté) ;
  navigation par catégorie avec compteurs, cartes repliables (code, nom, résumé des couches,
  épaisseur, Up, statut), tout déplier / replier, recherche ; « + Nouveau », « Depuis mes
  modèles », Modifier, Dupliquer, Enregistrer comme modèle, Supprimer ; éditeur de paroi intégré
  avec **recherche unique** des couches (matériaux et éléments tabulés, synonymes du métier :
  parpaing, BA13, PSE, XPS…) et épaisseur d'isolant pour un U cible appliquée en un clic.
- L'ancien onglet « Composer une paroi » (calcul sans enregistrement) est retiré : l'éditeur des
  cartes le remplace.
