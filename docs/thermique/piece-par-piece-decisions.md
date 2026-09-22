---
read_policy: lire avant de coder la page « Pièce par pièce » de l'application thermique
---

# Page « Pièce par pièce » — décisions

Date : 2026-09-22. Demande de l'utilisateur (D28, [locaux-decisions.md](locaux-decisions.md)) : dans l'application,
le thermicien modifie un local, clique **« Remodéliser »**, revérifie, **enregistre** et passe au local suivant.
Rien n'est codé tant que les questions du § 4 ne sont pas tranchées.

## 1. Existant vérifié (après la refondation, `main` = `119df335`)

| Élément | État |
|---|---|
| `SheetPage` + `components/TileSheetViewer` (298 l.) | affichage d'une planche en tuiles, rotation, échelle : **base de la vue plan** |
| `ProjectPage` | liste des planches ; onglets « Plans et planches » et « Bibliothèque » |
| Bibliothèque du projet (`ThermiqueComponent`, `ComponentLibrary`, `WallEditor`) | parois et menuiseries avec U calculé : **cible des composants de l'étude** |
| Modèles en base | projet, document, planche, composant. **Aucune table pour une étude de niveau** |
| Routes | socle seulement (projets, documents, planches, tuiles, bibliothèque) |
| Chaîne d'étude (`run_etude_niveau.py`) | tourne **sur le poste, dans Claude Code** (mode session, pas d'API) ; produit `passe-globale.json` (locaux, objets), `enveloppe.json`, `enveloppe.raw.json` (éléments d'enveloppe rattachés aux locaux), `enveloppe/enveloppe-manifeste.json` (tronçons, échelle), `catalogue.json`, `controle.json` |
| Calcul des fiches (`thermique_fiches_locaux.fiches`) | à partir de l'analyse, du manifeste et des éléments : côtés (adjacence, épaisseur, orientation, déperditif), enveloppe rattachée. **N'a pas besoin de l'image** : rapide, exécutable sur le serveur |
| Rattachement des éléments aux locaux (`thermique_enveloppe_pieces.decouper_par_piece`) | pas d'image non plus : rejouable après une modification de contour |
| Recalage des contours (`thermique_locaux.recaler_pieces`) | a besoin de l'image de la page (rendu 300 dpi) : plus lourd |
| Dépendances serveur | `scipy`, `numpy`, `Pillow` présents ; **`shapely` absent de `requirements.txt`** : le moteur ne tournerait pas en production, et les tests qui l'importent échouent en intégration continue |

Constat : la page n'a pas besoin de l'agent. Tout ce que « Remodéliser » recalcule (rattachement des éléments,
côtés, adjacences, parois déperditives, métrés) est du calcul classique, déjà écrit et testé.

## 2. Principe

1. **Sur le poste (Claude Code)** : `run_etude_niveau.py` fait l'étude d'un niveau (agents + algorithmes) et écrit
   un **fichier d'étude unique** `etude-<niveau>.json`.
2. **Dans l'application** : le thermicien importe ce fichier sur la planche du niveau, puis valide local par local.
3. Ce que le thermicien signale comme hors de portée du calcul (zonage d'un grand local, doute de lecture) part dans
   une **liste de demandes** reprise à la session Claude Code suivante.

## 3. Décisions proposées

- **D34 — Stockage.** Nouvelle table `thermique_etudes` (une étude par planche) : analyse (locaux, objets),
  manifeste, éléments d'enveloppe, catalogue, fiches calculées, état de chaque local (`a_verifier` / `valide`),
  demandes, dates. Colonnes JSON, comme `calibration_json` et `composition_json` aujourd'hui.
- **D35 — Import.** Bouton « Importer une étude » sur la planche : dépôt du fichier `etude-<niveau>.json` produit par
  la commande. Pas d'envoi automatique depuis le poste (il faudrait des identifiants dans la commande).
- **D36 — Écran.** À gauche, le plan (visionneuse en tuiles existante) avec les locaux en surimpression ; le local
  courant est mis en avant, ses côtés sont colorés par adjacence (extérieur, local non chauffé, local chauffé, vide)
  et ses éléments d'enveloppe sont affichés. À droite, la fiche du local : nom, nature, surface, côtés (adjacence,
  épaisseur, orientation, déperditif), éléments d'enveloppe (paroi, menuiserie, poteau : composant, longueur,
  inclus ou exclu), liaisons (angles, refends). En bas : liste des locaux avec leur état.
- **D37 — Modifications possibles (première version).** Contour (déplacer, ajouter ou supprimer un sommet), nom,
  nature, adjacence forcée d'un côté, rattachement d'un élément à un autre local, exclusion d'un élément,
  changement de composant (lien vers la bibliothèque du projet).
- **D38 — « Remodéliser ».** Le serveur rejoue le rattachement des éléments et le calcul des fiches **pour tout le
  niveau** (quelques secondes au plus), puis l'écran montre ce qui a changé : dans le local courant, et chez les
  **voisins touchés**. Votre remarque : modifier un contour peut ajouter ou retirer des éléments déperditifs chez un
  voisin. Rien n'est enregistré à ce stade.
- **D39 — « Enregistrer et suivant ».** Enregistre l'état remodélisé, passe le local en `valide`, garde une trace
  (qui, quand, quoi) et ouvre le local suivant non validé. Un local validé dont un voisin change repasse en
  `a_verifier`, avec le motif.
- **D40 — Hors de portée de la première version.** Le recalage automatique des contours sur l'image, le découpage
  d'un grand local en zones (le Pôle multimédia : on émet une demande), les valeurs de ψ et les hauteurs (après les
  coupes).
- **D41 — Préalable.** Ajouter `shapely` aux dépendances du serveur (voir § 1), avant tout le reste.

## 5. Réponses du 2026-09-22 et recadrage

**Recadrage de l'interface (demande utilisateur).** Ce n'est plus une « page pièce par pièce » ajoutée aux autres,
c'est **un espace de travail unique du thermicien** :

- un écran d'accueil pour **choisir le projet** ;
- puis un seul écran, sans jamais en sortir : le **plan de référence** s'ouvre (RDC par défaut), on **passe de plan
  en plan** (niveaux, coupes) dans la même vue, et on ouvre sur place la **bibliothèque**, les **informations du
  projet**, les **étapes de l'étude** et la **fiche du local** (panneaux latéraux, tout dynamique, sans rechargement).
- Les pages actuelles (liste des planches, planche, bibliothèque séparée) deviennent des panneaux de cet espace.

| Q | Réponse | Conséquence |
|---|---|---|
| Q1 | Import par fichier : oui | D35 retenue |
| Q2 | Tout pouvoir dessiner, **dans le processus étape par étape des agents** | chaque étape de la chaîne a un point d'arrêt où le thermicien corrige ou dessine avant l'étape suivante (voir § 6) |
| Q3 | Pouvoir revenir à l'état antérieur | historique versionné (chaque enregistrement = une version, retour possible) |
| Q4 | Au passage local par local, **associer les ponts thermiques** et ajouter/modifier les éléments de bibliothèque selon le référentiel des ponts thermiques | la fiche du local propose les liaisons détectées ; le thermicien leur associe un type de pont de la bibliothèque (catégorie déjà prévue) ou en crée un |
| Q5 | **Aucune hauteur par défaut** : chantier à part entière | les hauteurs viendront des coupes (étape dédiée) ; en attendant, longueurs seulement, surfaces « en attente de hauteur » |
| Q6 | Locaux chauffés d'abord | ordre du « suivant » : chauffés, puis circulations, puis non chauffés |

## 6. Synthèse : des plans fournis à la bibliothèque

| # | Étape | Qui | Produit | Point d'arrêt du thermicien (Q2) |
|---|---|---|---|---|
| 0 | Dépôt des PDF, découpage en planches, échelle, rotation, niveau | application | planches | vérifier niveau et échelle |
| 1 | Lecture globale du plan (image seule) : murs, baies, locaux, objets | agent `thermicien-plan` | objets du plan | — |
| 2 | Locaux : recalage des contours sur les murs, nom, nature (chauffé, circulation, non chauffé, vide) | algorithme + agent | locaux | **dessiner, fusionner, couper, renommer, changer la nature** |
| 3 | Guide de l'enveloppe : contour extérieur découpé en tronçons de 5 m au plus, bandes redressées | algorithme | tronçons | — |
| 4 | Relevé de l'enveloppe par lots : composition des parois (couches), menuiseries, poteaux, liaisons | agent `thermicien-enveloppe` | **catalogue des types** (P1, M2…) avec les tronçons où chaque type apparaît | **valider ou corriger chaque type** |
| 5 | Restitution : couches positionnées, doublage présumé, rattachement au local, faces intérieures, liaisons (angles, refends) | algorithme | éléments d'enveloppe par local | — |
| 6 | Contrôle indépendant par l'image (isolant alvéolé, béton) | algorithme | alertes | — |
| 7 | Fiches par local : côtés, adjacences, déperditif, éléments, liaisons, alertes | algorithme | fiches | **local par local : modifier, remodéliser, associer les ponts, enregistrer** |
| 8 | Hauteurs et planchers depuis les coupes | à construire | hauteurs, surfaces | à définir |
| 9 | Bibliothèque du projet alimentée | application | composants du projet | valider |

Aujourd'hui les étapes 1 à 7 tournent sur le poste (Claude Code) ; le catalogue sort en fichier
(`enveloppe.bibliotheque.md`, `catalogue.json`) mais **n'entre pas encore dans la bibliothèque de l'application**.
C'est le maillon manquant.

## 7. Alimentation de la bibliothèque : générale ou pièce par pièce ?

Recommandation : **les deux, à deux moments différents.**

1. **Générale d'abord (étape 4).** Une paroi se répète : le relevé de l'enveloppe identifie des **types** (P1, M2…)
   sur tout le niveau, avec la liste des tronçons où chacun apparaît. Ces types entrent dans la bibliothèque du
   projet au statut **« hypothèse »** (le statut existe déjà). Le thermicien les valide une fois pour tous les
   locaux, au lieu de les ressaisir pièce par pièce.
2. **Pièce par pièce ensuite (étape 7).** Dans chaque local, le thermicien **affecte** les types aux éléments,
   **associe** les ponts thermiques, corrige. S'il découvre un élément nouveau (une paroi différente, un pont
   particulier), il le **crée dans la bibliothèque** depuis la fiche.
3. **Propagation proposée, jamais imposée.** Quand un type est créé ou modifié dans un local, l'outil cherche les
   éléments semblables **dans les autres locaux et les autres niveaux** (même composition, même épaisseur, même
   aspect sur l'image) et **les propose** : « 6 autres éléments ressemblent à celui-ci, les rattacher ? ». Les
   locaux déjà validés concernés repassent « à vérifier ».
4. **Entre projets** : un type validé peut devenir un **modèle réutilisable** du compte (fonction déjà en
   production).

## 8. Essai « lecture par local » (accord utilisateur du 2026-09-22)

Question de l'utilisateur : les tronçons sont-ils une bonne idée, ne peut-on pas tout faire au pièce par pièce ?
Essai sur le R+1, sans toucher à la méthode actuelle (option `--par-local` de `run_enveloppe_claude.py`, dossier
séparé), puis comparaison chiffrée avant toute décision.

- **D42** — Un tronçon devient un **côté d'un local** chauffé ou de circulation qui donne sur l'extérieur, un local
  non chauffé, un vide ou « rien trouvé » (sondage de la fiche du local, D30). Coupé à 5 m au plus.
- **D43** — La ligne 0 de la bande est la **face intérieure du local** ; la paroi est au-dessus (vers l'extérieur).
  Bande : 90 cm côté extérieur, 40 cm côté pièce. Les longueurs intérieures sont lues directement.
- **D44** — Le reste de la chaîne est inchangé : mêmes lots, même catalogue appris, même restitution, mêmes fiches ;
  le bâtiment (pour dire « extérieur ») reste la face extérieure trouvée par remplissage.
- **D45** — Comparaison : isolant compté sur une référence d'alvéoles commune aux deux méthodes, façade par local,
  bureau de direction (14,05 m lus contre 18,00 m attendus), alertes des fiches, nombre de planches.

### Résultats de l'essai (R+1, 2026-09-22)

Lots lus en parallèle avec le catalogue déjà appris sur le R+1 (P1, M1…), ce qui avantage plutôt la lecture par local.

| Critère | Tronçons (actuel) | Par local (essai) |
|---|---|---|
| Isolant compté (624 alvéoles vues par l'une ou l'autre méthode) | **89 %** | 74 % |
| Bandes à lire par l'agent | **72 (12 planches)** | 148 (25 planches) |
| Bureau de direction : façade relevée / côtés du local | 18,00 / 14,05 m | 14,15 / 14,05 m |
| Bureaux assistants : écart façade / côtés | ±0,10 m | ±0,05 m |
| Parois sur locaux non chauffés, gaines, vides relevées | non | **oui (≈ 60 m)** |

Constats :
- La lecture par local ne vaut que ce que vaut le contour du local. Dans les dents de scie, le contour est une corde
  droite : les massifs sont lus en biais, une partie de l'isolant sort de la bande (Pôle multimédia : 90 alvéoles
  manquées), et la longueur développée du bureau de direction (18,00 m) n'est plus mesurée.
- Là où le contour colle au mur (bureaux, catalogage, lecture confort), les deux méthodes s'accordent au centimètre.
- La moitié des bandes supplémentaires ne sert à rien : meubles pris pour des côtés (DVD), cabine d'ascenseur,
  sanitaires dont le contour est faux.
- Apport réel : les parois vers les locaux non chauffés et les vides sont relevées (voile de gaine, cloisons de la
  boîte à vents), ce que le parcours de la façade ne fait pas.

Conclusion proposée : **garder le parcours de la façade (tronçons) pour lire l'enveloppe**, invisible pour le
thermicien, et **ajouter une lecture par local limitée aux côtés sur local non chauffé ou vide**. Le thermicien ne
voit et ne valide que le pièce par pièce (§ 7).

- **D46 (retenue par l'utilisateur le 2026-09-22)** — La préparation standard ajoute aux tronçons de façade (T) des
  tronçons « U » : côtés des locaux chauffés dont au moins 30 % des sondages trouvent un local non chauffé ou un
  vide, 0,5 m au moins, lus depuis la face intérieure, sur des planches et dans des lots à part. Leurs parois sont
  comptées « sur local non chauffé », hors façade, et rattachées au côté correspondant de la fiche du local. Sur le
  R+1 : 17 côtés, 39,5 m, un lot de plus (boîte à vents, cage d'escalier, gaines, vestiaire, sanitaires).
  Validation de bout en bout (5 lots, catalogue repris) : isolant compté 91 % comme la référence, façade par local
  cohérente, 28 alertes au lieu de 30 ; 44 m de parois et baies « sur local non chauffé ou vide » rattachés aux bons
  côtés (voile de cage 22 cm non isolé, cloison vitrée pare-flamme de la boîte à vents, porte palière).
  Nouveau composant récurrent à valider : voile de cage ou de gaine non isolé (22 cm).

## 4. Questions (tranchées au § 5)

- **Q1** — Import par dépôt d'un fichier d'étude (D35) : cela vous convient ?
- **Q2** — Modifications de la première version (D37) : suffisantes, ou faut-il aussi pouvoir **dessiner** un local
  manquant, en **fusionner** deux ou en **couper** un ?
- **Q3** — Historique : suffit-il de garder le dernier état et la trace « qui, quand, quoi » ? Ou faut-il pouvoir
  revenir à une version antérieure d'un local ?
- **Q4** — Ponts thermiques : en première version, afficher leur type et leur longueur seulement (les ψ viendront
  avec la bibliothèque) ?
- **Q5** — Hauteurs : sans les coupes, mettre une hauteur sous plafond par défaut (par exemple 2,50 m), modifiable
  par local, pour avoir des surfaces de parois ? Ou n'afficher que les longueurs ?
- **Q6** — Ordre du « suivant » : ordre de lecture du plan, locaux chauffés d'abord, ou locaux en alerte d'abord ?
