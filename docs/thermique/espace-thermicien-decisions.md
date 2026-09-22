---
read_policy: lire avant de coder l'espace de travail du thermicien (interface de l'application thermique)
---

# Espace de travail du thermicien — décisions

Date : 2026-09-22. Demande de l'utilisateur : « une page pour sélectionner le projet, puis la page s'ouvre avec le
plan de référence (par défaut RDC), dans cette même page naviguer de plan en plan, accéder à la bibliothèque et aux
informations du projet sans sortir de la page, tout dynamique, tout centralisé dans l'environnement de travail pur
thermicien ». Décisions métier déjà prises : [piece-par-piece-decisions.md](piece-par-piece-decisions.md) (§ 5 à 8).
Rien n'est codé tant que les questions du § 5 ne sont pas tranchées.

## 1. Existant vérifié (branche `feat/thermique-socle-raster`)

| Élément | Où | Réutilisation |
|---|---|---|
| Liste des projets | `pages/ProjectsPage.tsx` (150 l.) | reste l'écran d'accueil |
| Fiche projet : dépôt des PDF, planches (nature, niveau, échelle) | `pages/ProjectPage.tsx` (353 l.) | devient le panneau « Documents et planches » |
| Planche : visionneuse, échelle, rotation | `pages/SheetPage.tsx` (365 l.), `components/TileSheetViewer.tsx` (298 l.) | la visionneuse devient le centre de l'espace ; elle sait déjà afficher un calque (`renderOverlay`), poser un point, saisir et déplacer un objet (`onGrab`) : base de l'édition des contours |
| Bibliothèque du projet, modèles du compte, référentiel Th-Bât | `pages/ProjectLibraryPage.tsx`, `LibraryHomePage.tsx`, `library/ComponentLibrary.tsx`, `library/WallEditor.tsx` | deviennent le panneau « Bibliothèque » (catégories : murs, planchers, menuiseries, ponts thermiques ; statut « hypothèse ») |
| Routes serveur | projets, documents, planches, tuiles, bibliothèque | inchangées ; routes de l'étude à ajouter (§ 3) |
| Chaîne d'étude (poste, Claude Code) | `run_etude_niveau.py` | produit l'étude d'un niveau ; façade par tronçons + côtés sur local non chauffé (D46) |
| Calcul des fiches, rattachement des éléments | `thermique_fiches_locaux`, `thermique_enveloppe_pieces` | sans image : exécutable sur le serveur pour « Remodéliser » |

Aujourd'hui : quatre pages séparées (projets, projet, planche, bibliothèque) ; on sort de l'une pour aller à l'autre.

## 2. L'écran

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ Médiathèque Frontignan ▾ │ R+1 · RDC · R+2 · Toiture │ Coupes ▾ Façades ▾ │ Infos  Biblio │
├───────────┬──────────────────────────────────────────────────────────┬───────────────┤
│ ÉTUDE     │                                                          │ FICHE DU LOCAL│
│ ✓ Planches│                                                          │ 6.1.1 B.dir   │
│ ✓ Locaux  │                 PLAN (visionneuse en tuiles)             │ chauffé 21 m² │
│ ✓ Enveloppe│         locaux colorés par état, local courant          │ côtés, parois,│
│ ◐ Pièce   │         mis en avant, côtés colorés par adjacence       │ baies, ponts  │
│   par pièce│                                                         │ [Remodéliser] │
│ ○ Hauteurs│                                                          │ [Enregistrer  │
│           │                                                          │  et suivant]  │
│ LOCAUX    │                                                          │               │
│ ● 6.1.1 … │                                                          │ Bibliothèque ⇄│
│ ○ 6.1.2 … │                                                          │ Infos projet ⇄│
└───────────┴──────────────────────────────────────────────────────────┴───────────────┘
```

- **Barre du haut** : le projet (changer de projet sans revenir à l'accueil), les niveaux dans l'ordre du bâtiment,
  les coupes et façades dans des menus ; « Infos » et « Biblio » ouvrent leur panneau.
- **Colonne de gauche** : les étapes de l'étude du niveau et leur état, puis la liste des locaux (chauffés d'abord,
  Q6 de la page pièce par pièce), avec une pastille d'état : à vérifier, validé, à revoir (un voisin a changé).
- **Centre** : le plan, toujours visible. Changer de niveau ne recharge pas la page ; le zoom est gardé par niveau.
- **Panneau de droite** : un seul panneau à onglets (fiche du local, bibliothèque, infos du projet, documents et
  planches). Rien ne recouvre le plan.
- **Adresse** : l'état de l'écran est dans l'adresse (`/projets/12?niveau=R1&local=6.1.1&panneau=fiche`) : le
  bouton « Précédent » du navigateur et un lien partagé rouvrent exactement la même vue.

## 3. Décisions proposées

- **D47 — Deux écrans seulement** : l'accueil (liste des projets) et l'espace de travail du projet. Les pages
  planche, projet et bibliothèque du projet deviennent des panneaux ; la bibliothèque du compte (modèles
  réutilisables) reste accessible depuis le panneau « Bibliothèque ».
- **D48 — Plan de référence** : à l'ouverture, le plan du RDC (niveau marqué « RDC » ou « niveau 0 ») ; le
  thermicien peut en désigner un autre dans les infos du projet (Q1).
- **D49 — Étude du niveau** (reprend D34 à D41) : table `thermique_etudes` (une par planche de niveau) et table
  `thermique_etude_versions` (chaque enregistrement crée une version : qui, quand, motif ; retour à une version
  antérieure, Q3 de la page pièce par pièce). Import d'un fichier d'étude unique produit par la commande.
- **D50 — Routes** : importer une étude, la lire, **remodéliser** (calcul sans enregistrer, renvoie les fiches et ce
  qui a changé chez les voisins), **enregistrer** un local (nouvelle version), lister et restaurer les versions.
- **D51 — Bibliothèque alimentée** (§ 7 de la page pièce par pièce) : à l'import, les types du catalogue (P1, M1…)
  entrent dans la bibliothèque du projet au statut « hypothèse » ; les liaisons deviennent des ponts thermiques à
  associer local par local ; la propagation aux éléments semblables est proposée, jamais imposée.
- **D52 — Hauteurs** : aucune hauteur par défaut ; surfaces affichées « en attente de hauteur » ; étape dédiée,
  construite plus tard à partir des coupes.

## 4. Découpage en livraisons

| Lot | Contenu | Serveur |
|---|---|---|
| **E1** | Espace de travail avec l'existant : choix du projet, plan de référence, navigation de plan en plan, panneaux Documents et planches, Bibliothèque, Infos projet | aucun changement |
| **E2** | Import de l'étude d'un niveau ; locaux sur le plan ; fiche du local en lecture | tables D49, import, lecture |
| **E3** | Modifier (contour, nature, adjacence, rattachement), Remodéliser, Enregistrer et suivant, versions | remodéliser, enregistrer, versions |
| **E4** | Bibliothèque alimentée par l'étude, ponts thermiques associés par local, propositions pour les éléments semblables | import du catalogue |
| **E5** | Hauteurs et planchers depuis les coupes | à cadrer |

Chaque lot est livrable seul et mis en production après votre accord.

## 5. Questions

- **Q1** — Plan de référence : RDC par défaut, modifiable dans les infos du projet. D'accord ?
- **Q2** — Ordre de la navigation : niveaux du plus bas au plus haut (sous-sol → toiture), puis coupes et façades
  dans des menus à part. D'accord ?
- **Q3** — Panneau de droite : un seul à la fois (onglets), ou pouvoir afficher la fiche du local **et** la
  bibliothèque côte à côte (le plan rétrécit) ?
- **Q4** — Écran visé : poste de bureau (grand écran) seulement, ou aussi tablette ?
- **Q5** — On commence par **E1** (sans toucher au serveur) pour que vous validiez l'ergonomie sur vos vrais plans
  avant la suite ?
