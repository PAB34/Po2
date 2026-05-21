# État actuel du développement

> **Mise à jour** : 2026-05-21 (Refonte UI BPU · revue factures titulaire/problemes · CVC import fix · PO2-PAT-002 En cours)
> **Mainteneur principal** : PAB34 + assistance IA (Claude Sonnet 4.6)
> **Dernière commit en prod** : `00af844` (fix(cvc-import): dropdown mapping complet avec tous les bâtiments)

## 🟢 Ce qui tourne en prod (https://patrimoineaucarre.com)

| Module | Route | État |
|---|---|---|
| Auth | `/login`, `/register`, `/account` | Stable |
| Patrimoine — liste | `/buildings`, `/buildings/list` | Stable |
| Patrimoine — détail | `/buildings/:id` | Stable |
| Patrimoine — création / import | `/buildings/create-edit` | Stable |
| Patrimoine — import hiérarchique | `/buildings/create-edit` | `SITE` -> `Site`, `BATIMENT` -> `Building.site_id`, `LOCAL` -> `Local.building_id` |
| Gestion technique SYPEMI | `/buildings/technique` | Stable (310 équip. importés) |
| **Inventaire terrain CVC** | `/buildings/technique` (onglet Terrain) + `/buildings/cvc-import` | **Nouveau (2026-05-20)** — wizard import Excel 3 étapes, fuzzy match sites↔bâtiments, rattachement SYPEMI, badges vétusté |
| Énergie — vue d'ensemble | `/energie` | Stable |
| Énergie — détail PRM | `/energie/:prmId` | Stable |
| Préconisations puissance | `/energie/preconisations` | Stable |
| Factures | `/energie/factures`, `/energie/factures/:id` | Stable en prod pour parser ENGIE, contrôle/décision et import lot ; extension filtre titulaire Ville/Agglo + filtres catégorie/type de problème poussée sur `main` (`fe84fca`), à vérifier après déploiement |
| Facturation TURPE | `/energie/facturation` | Stable |
| **BPU — Timeline** | `/energie/bpu` (onglet Timeline) | Stable — graphe dual-axe Y (fourniture vs accessoires), légende composantes avec exemples chiffrés |
| **BPU — TURPE** | `/energie/bpu` (onglet TURPE) | Refonte 2026-05-21 — 4 blocs : définition · barre empilée facture · courbe évolution · tableau CRE |
| **BPU — Documents & Import** | `/energie/bpu` (onglet Documents) | Nouveau 2026-05-21 — stats + table BPU filtrée + import admin (séparé de Timeline) |
| **BPU — Édition tableau** | `/energie/bpu` (onglet Édition) | Stable (2026-05-20) — tableau Excel cliquable, batch save, 14 endpoints CRUD |
| **CVC import — mapping** | `/buildings/cvc-import` (étape 2) | Fix 2026-05-21 — dropdown complet (suggestions fuzzy + tous les bâtiments du patrimoine) |

## 📦 Migrations alembic appliquées en prod
```
0001_create_users
0002_create_cities_buildings_locals
0003_extend_buildings_for_naming_workflow
0004_add_external_source_fields_for_imports
0005_add_code_postal_to_buildings
0006_add_billing_config
0007_add_lot_to_billing_config
0008_make_tariff_code_nullable
0009_add_billing_bpu_lines
0010_add_energy_invoice_imports
0011_add_energy_invoice_analysis
0012_add_invoice_decision_fields
0013_add_enedis_async_jobs
0014_add_equipment_tables
0015_add_bpu_tables
0016_add_cvc_inventory
0017_add_sites_hierarchy          ← HEAD
```

## 🔧 PRs récentes
| # | Titre | Branche | Statut |
|---|---|---|---|
| 12 | `feat(bpu): pipeline complet historique des prix (Phases 2 + 3 + 4)` | `claude/bpu-phase2` | ✅ Mergée 2026-05-19 |
| 11 | `feat(bpu): add SQL models + alembic migration` | `claude/bpu-feature` | ✅ Mergée |
| 10 | `fix(buildings): adapt BuildingTechniquePage colors for dark mode` | | ✅ Mergée |
| 9 | `feat(energie): UI panneau async ENEDIS (Phase C)` | | ✅ Mergée |

## 🪵 Derniers commits sur `main`
```
fe84fca  feat(billing): add invoice holder and issue filters
00af844  fix(cvc-import): dropdown mapping complet avec tous les bâtiments du patrimoine
9674d50  feat(bpu): ajout exemples chiffrés sur chaque composante Timeline
f29db99  refactor(bpu): Timeline définitions lisibles + TURPE 3 blocs restructurés
cc34a8f  refactor(bpu): refonte UI page /energie/bpu — 4 onglets, Timeline épurée
2f3229f  feat(pat): import patrimoine hiérarchique site/bâtiment/local (PO2-PAT-002)
324d053  feat(bpu): double axe Y dans Timeline (fourniture vs accessoires)
ea53a9f  docs(vault): session PO2-CVC-001 + MAJ module Gestion-technique
fff24e1  fix(cvc): corriger TS7053 referenceCounts manque clé terrain
fd192fe  feat(cvc): import inventaire CVC terrain + rattachement SYPEMI
```

## 📚 Specs historiques

L'inventaire complet des specs `saas/specs/` est dans [[Specs]]. Résumé :

- **4 specs canoniques** à consulter avant tout dev sur le sujet :
  - `04_mapping_facture_engie.md` — mapping PDF facture
  - `05_matrice_controles_factures_energie.md` — codes erreur + tolérances
  - `06_preconisation_abonnement_v1.md` — marges 20/12/5 %
  - `07_referentiel_turpe_7.md` — référentiel CRE
  - `08_enedis_async_kit_analysis.json` — gaps kit ENEDIS async
- **1 spec archivée** : `_archives/02_architecture_technique_v01_obsolete.md` (état v0.1 obsolète)
- **3 specs partielles** dont les pépites ont été synthétisées dans les modules

## 🔥 Chantiers ouverts (en cours / à reprendre)

### 1. ✅ ~~Parser BPU → remplacé par import xlsx canonique~~ (PO2-BPU-002 + PO2-BPU-003 — Livrés 2026-05-20)
- **Stratégie finale** : source de vérité = `extraction_tarifs_electricite_BPU.xlsx` (saisie manuelle validée par l'utilisateur), `extraction_status=manual`, `confidence=1.0`
- **BDD prod** : 17 docs / 49 segments / 138 périodes / **523 composantes** / 36 charges
- **UI** : tableau éditable dans `/energie/bpu` (onglet "Édition tableau"), édition cellule par cellule, batch save
- **Script** : `app.scripts.import_bpu_xlsx` — relancer avec `--force` si re-import xlsx nécessaire
- **Parser PDF** : en pause (PO2-BPU-001) — `raw_text` stocké sur chaque doc pour re-parsing futur éventuel
- **Voir** : [[Sessions/2026-05-20 — Import xlsx BPU + tableau editable]] et [[Modules/Energie-BPU]]

### 2. Module Baux locataires (1.2 de la roadmap)
- Aucun code n'existe encore — c'est le prochain gros chantier "rapidement faisable"
- Pattern à réutiliser : upload PDF côté Frontend + `services/invoice_parsers/` côté Backend
- Modèle à créer : étendre `Local` avec champs bail, OU créer une nouvelle table `Lease`
- À discuter avec l'utilisateur sur le schéma (1-N entre Building et Lease ?)

### 2b. Import patrimoine hiérarchique Site -> Bâtiment -> Local
- **Livre et documente** : migration `0017_add_sites_hierarchy`, modele `Site`, `buildings.site_id`, endpoints `/api/buildings/sites`
- Objectif : importer les fichiers patrimoine avec colonne `Typologie` sans aplatir sites / batiments / locaux
- Flux vise : lignes `SITE` -> table `sites`, lignes `BATIMENT` -> `buildings.site_id`, lignes `LOCAL` -> table `locals` rattachee au batiment parent
- Voir [[Sessions/2026-05-20 — Import patrimoine hierarchique]]

### 2c. Historique factures ENGIE dans `/energie/factures`
- **En cours** : intégrer le lot réel de 83 PDF ENGIE depuis `saas/energie/ENGIE/FACTURES`
- Point atteint : l'UI facture couvre l'import multi-fichiers, les lots persistants, le résumé simple, PRM/FIC, lignes extraites, contrôles BPU/TURPE/ENEDIS et décision utilisateur
- Revue améliorée : le titulaire du contrat est exposé dans la liste et filtrable ; les catégories/types de problèmes remontent du détail facture vers la page principale
- Flux visé ensuite : qualifier le lot complet, corriger les anomalies réelles, puis alimenter le même pipeline par la future API ENGIE
- Voir [[Sessions/2026-05-21 — Historique factures ENGIE]]

### 3. Backfill prod ENEDIS async
- **Pending côté utilisateur** : mettre à jour le canal SETE_ENERGIE (506350699) côté portail ENEDIS pour utiliser le nouveau user FTP `enedis_ftp` + nouveau password (récupérable via `ssh ... "sudo cat /root/.ftp_password_enedis"`)
- Tant que ce n'est pas fait, le scheduler async tourne à vide
- Une fois le canal validé : lancer backfill complet (CDC 2 ans + Conso 3 ans) via `POST /api/energie/sync/async/backfill-full`

### 4. Dette technique ENEDIS async
Cf. spec `saas/specs/08_enedis_async_kit_analysis.json` (synthèse dans [[Modules/Energie-Consommation]]) :
- `UNFILTERED_PRM_BATCH` (medium) — filtrer les PRM non-communicants avant publication
- `ALL_OR_NOTHING_PUBLICATION` (medium) — découper en sous-batchs pour qu'un PRM invalide ne tue pas tout
- `CDC_WINDOW_TOO_LARGE` — probablement traité par les fixes `d784882` + `38ab484`, à confirmer

### 5. Refresh TURPE annuel
- Prochain refresh CRE : **2026-08-01**
- À ce moment, mettre à jour `saas/specs/07_referentiel_turpe_7.md` avec la nouvelle version + adapter les prix dans `services/turpe.py`
- La page `/energie/bpu` expose aussi l'historique moyen TURPE HTA-BT via `list_turpe_evolution_events()` : ajouter le point 2026 dans cette serie si la CRE publie l'indexation attendue.
- Voir [[Modules/Energie-TURPE]]

### 4. Codespaces — devcontainer "à vide"
- Le `.devcontainer/devcontainer.json` minimal a été créé uniquement pour faire passer le prebuild GitHub
- Si l'utilisateur veut vraiment utiliser Codespaces un jour, il faudra enrichir `postCreateCommand` pour installer backend + frontend (pip + npm)

## 📊 Données en prod

| Table | Lignes |
|---|---|
| `users` | (inconnu, mais l'utilisateur principal est créé) |
| `cities` | 1 (Sète) |
| `buildings` | ~530 (audit PRM mentionne 529 PRM) |
| `enedis_async_jobs` | 0 (scheduler en attente du canal validé) |
| `equipment_references` | 310 |
| `building_equipments` | (variable, dépend des saisies utilisateur) |
| `bpu_documents` | **17** (importés 2026-05-20, xlsx canonique) |
| `bpu_segments` | **49** |
| `bpu_time_periods` | **138** |
| `bpu_price_components` | **523** (extraction_status=manual) |
| `bpu_fixed_charges` | **36** |

## 🔐 Secrets et accès

- **GitHub PAT** : récupérable via `git credential fill` depuis la machine de l'utilisateur (gho_*)
- **SSH VPS** : `~/.ssh/po2_vps2` → `ubuntu@135.125.152.112`
- **Password FTP ENEDIS** : `/root/.ftp_password_enedis` sur le VPS (chmod 600, root only)
- **Clé AES déchiffrement ENEDIS** : dans `.env` prod variable `ENEDIS_DECRYPTION_KEY`
- **Canal contact ENEDIS** : `506350699` (SETE_ENERGIE)
- ⚠️ **Ne JAMAIS afficher de password ou de clé en clair dans une conversation, un commit, ou ce vault** — l'utilisateur a déjà rotaté un mot de passe à cause de ça
