---
read_policy: lire avant toute suppression ou refonte dans l'application thermique
---

# Refondation de l'application thermique — inventaire et proposition

Date : 2026-09-22. Demande de l'utilisateur : « tout effacer ce qui a été développé dans l'application hormis la
création du projet et des fonctionnalités connexes, pour repartir sur de bonnes bases saines ».
Rien n'est supprimé tant que les questions du § 5 ne sont pas tranchées.

## 1. Pourquoi

L'application a empilé des approches successives, abandonnées depuis : détection par les vecteurs du PDF, calques,
superposition, zonage automatique, métré sur contours vectoriels, première version des pièces et de l'enveloppe. La
méthode retenue est désormais : **image seule + agents + algorithmes de mesure, pièce par pièce**
([chaine-analyse-plan-raster.md](chaine-analyse-plan-raster.md)). Garder l'ancien code brouille l'application et
chaque évolution.

## 2. Inventaire (branche `feat/thermique-inventaire-objets-r1`)

### Frontend (`saas/frontend/src/thermique/`)

| Page / module | Rôle | Proposition |
|---|---|---|
| `ThermiqueLoginPage`, `RequireAuth`, `Shell` (dans `ThermiqueApp.tsx`) | connexion, cadre | **garder** |
| `ProjectsPage`, `ProjectPage`, `projectCache.ts`, `api.ts` | liste et fiche projet, dépôt des plans | **garder** (à alléger : liens vers les pages retirées) |
| `LibraryPage`, `ProjectLibraryPage`, `LibraryHomePage`, `library/ComponentLibrary`, `library/WallEditor`, `MaterialsPanel`, `ElementsPanel`, `library.ts`, `components.ts` | bibliothèque du projet et modèles réutilisables (en production), référentiel Th-Bât | **garder** (c'est là que viendra le catalogue appris) |
| `SheetPage`, `components/TileSheetViewer`, `raster.ts`, `scale.ts` | affichage d'une planche, échelle | **garder** (utile à la future page pièce par pièce) |
| `AutoZoningPage` (`/analyse`), `vision.ts` | éditeur des objets de l'analyse IA | à trancher (Q2) : base possible de la page pièce par pièce |
| `MetrePage` (1 289 lignes), `metre.ts`, `snap.ts`, `natures.ts`, `zoning.ts` | métré sur contours (ancienne méthode) | **archiver** |
| `CalquesPage`, `calques.ts` | calques vectoriels | **archiver** |
| `SuperpositionPage`, `superposition.ts` | superposition des niveaux | **archiver** (la superposition reviendra sur les nouvelles fiches) |
| `EnveloppePage`, `PiecesPage`, `pieces.ts` | première version enveloppe et pièces | **archiver** |

### Backend (`saas/backend/`)

| Élément | Rôle | Proposition |
|---|---|---|
| `models/thermique.py` : `ThermiqueProject`, `ThermiqueDocument`, `ThermiqueSheet`, `ThermiqueComponent` | projet, documents, planches, composants | **garder** |
| `models/thermique.py` : `ThermiqueLevel`, `ThermiqueZone`, `ThermiqueRoom` | niveaux, zones du métré, pièces (ancienne méthode) | Q3 : tables gardées en base au début (aucune suppression de données), code retiré ; `ThermiqueLevel` probablement réutilisé |
| `services/thermique.py`, `thermique_raster.py`, `thermique_composants.py` | projets, rendu des planches, bibliothèque | **garder** |
| `thermique_moteur/referentiel` (matériaux, menuiseries, éléments Th-Bât) | référentiel Th-Bât | **garder** |
| `services/thermique_calques.py`, `thermique_detection.py`, `thermique_enveloppe.py`, `thermique_metre.py`, `thermique_pieces.py`, `thermique_superposition.py` | anciennes méthodes | **archiver** |
| `thermique_moteur/` hors référentiel (détection, murs, traits, vecteurs, lignes, calques, signatures, reconnaissance, quadrilatère, redressement, textes, métré, pièces, locaux, parois, bande, coupes, évaluation, superposition) — ~5 000 lignes | moteur vectoriel | **archiver** (à vérifier un par un : `coupes.py`, `parois.py` peuvent contenir du réutilisable) |
| `services/thermique_vision.py`, `thermique_claude_agent.py`, `thermique_vision_geometrie.py` | passe globale par l'agent | **garder** (nouvelle chaîne) |
| `services/thermique_parcours_enveloppe.py`, `thermique_enveloppe_pieces.py`, `thermique_locaux.py`, `thermique_fiches_locaux.py`, `thermique_controle_image.py` + scripts `run_*`, `exporter_validation.py` | nouvelle chaîne (image seule, pièce par pièce) | **garder et intégrer** à l'application |
| `api/routes/thermique.py` (1 134 lignes) | toutes les routes | **garder** projets, documents, planches, bibliothèque, analyse ; **retirer** les routes des modules archivés |

## 3. Méthode proposée (sûre, réversible)

1. **Mettre à l'abri le travail en cours** : commit local du moteur raster (non commité à ce jour), puis étiquette
   git `thermique-avant-refondation` sur l'état complet. Tout ce qui est archivé reste récupérable.
2. **Retirer le code des modules archivés** (pages, routes, services, moteur vectoriel, tests associés) dans une
   branche dédiée, en vérifiant à chaque étape que la connexion, les projets, les planches et la bibliothèque
   marchent toujours (tests ciblés + construction du frontend).
3. **Ne supprimer aucune donnée** au début : les tables des anciennes méthodes restent en base, simplement plus
   utilisées. Leur suppression (migration) viendra plus tard, sur décision explicite.
4. **Reconstruire proprement** sur ce socle : étude par niveau (commande unique), locaux, fiches par local, puis
   la page « Pièce par pièce » avec la boucle modifier → remodéliser → vérifier → enregistrer.
5. **Rien n'est poussé ni déployé** sans votre accord (l'application est en production).

## 4. Effet attendu

- Frontend : ~4 000 lignes retirées sur ~8 700 ; backend : ~7 000 lignes retirées (services + moteur vectoriel).
- Une application qui ne contient que : connexion, projets, plans, bibliothèque, et la nouvelle chaîne.

## 5 bis. Réalisé le 2026-09-22 (branche `feat/thermique-socle-raster`, rien de poussé)

Réponses de l'utilisateur : Q1 liste validée ; Q2 `/analyse` supprimée ; Q3 données des anciennes méthodes
supprimées ; Q4 commit préalable fait.

- Mise à l'abri : commit `63f8c447` (moteur raster pièce par pièce) + étiquette `thermique-avant-refondation`.
  Le test `test_thermique_locaux.py` (moteur vectoriel), écrasé par erreur par les nouveaux tests, a été restauré
  avant ce commit ; les nouveaux tests s'appellent `test_thermique_locaux_raster.py`.
- Frontend : pages Métré, Calques, Superposition, Enveloppe, Pièces et `/analyse` retirées avec leurs modules
  (`metre`, `snap`, `zoning`, `calques`, `superposition`, `pieces`, `vision`) ; onglets du projet réduits à « Plans
  et planches » et « Bibliothèque » ; 205 lignes de CSS mortes retirées. `ElementsPanel` et `natures.ts` gardés
  (bibliothèque, planches). Types et construction OK, tests unitaires OK.
- Backend : routes réduites au socle (509 lignes au lieu de 1 331) ; services `thermique_calques`, `_detection`,
  `_enveloppe`, `_metre`, `_pieces`, `_superposition`, `_vision` supprimés (l'analyse par l'API OpenAI disparaît avec
  ses réglages `THERMIQUE_VISION_*`) ; moteur vectoriel supprimé (19 modules) ; il reste `thermique_moteur` =
  bibliothèque Th-Bât + calcul des parois + composants. Catégories et découpage en tuiles rapatriés dans
  `thermique_claude_agent.py`, verrou pdfium dans `thermique_raster.py`. Schémas réduits au socle.
- **Réparation au passage** : le commit #209 (24893dff) avait écrasé `thermique_moteur/composants.py` et
  `parois.py` (bibliothèque et calcul du U, lots B2a/B2b-1/L1/L2) par des modules vectoriels du même nom, avec leurs
  tests : la bibliothèque des composants était cassée sur cette branche (test en échec signalé depuis le début).
  Versions d'avant #209 restaurées ; tests OK.
- Données : migration `0082` qui supprime `thermique_levels`, `thermique_zones`, `thermique_rooms` et la colonne
  `thermique_projects.signatures_json` (`north_deg` gardée) ; retour arrière qui recrée les tables vides ; testée
  dans les deux sens sur SQLite (la chaîne complète des migrations ne tourne pas sur SQLite depuis 0007 : défaut
  antérieur, la production est sous PostgreSQL).
- Vérifications : application importée ; 114 tests de l'outil thermique OK ; 661 tests collectés sans erreur
  d'import ; scripts de la chaîne OK.
- À faire avant la mise en production : relire le diff, pousser la branche, appliquer la migration 0082 (suppression
  définitive des données des anciennes pages).

## 5. Questions

- **Q1** — « Fonctionnalités connexes » à garder : connexion, projets, dépôt des plans et planches, bibliothèque du
  projet et modèles, référentiel Th-Bât. Est-ce bien la liste ? Autre chose à garder ?
- **Q2** — La page `/analyse` (éditeur des objets de l'analyse IA, retouchée récemment) : la garder comme base de la
  future page pièce par pièce, ou l'effacer aussi et repartir de zéro ?
- **Q3** — Les données déjà saisies en production avec les anciennes pages (niveaux, zones, pièces) : les laisser en
  base (masquées) pour l'instant, ou les supprimer ?
- **Q4** — Faut-il faire d'abord le commit local du travail en cours (moteur raster, fiches, locaux) avant la
  refondation ? (recommandé)
