# État actuel du développement

> **Mise à jour** : 2026-05-19 (fin de session BPU + Codespaces)
> **Mainteneur principal** : PAB34 + assistance IA (Claude Sonnet 4.5)
> **Dernière commit en prod** : `88bdd4b` (chore codespaces fix)

## 🟢 Ce qui tourne en prod (https://patrimoineaucarre.com)

| Module | Route | État |
|---|---|---|
| Auth | `/login`, `/register`, `/account` | Stable |
| Patrimoine — liste | `/buildings`, `/buildings/list` | Stable |
| Patrimoine — détail | `/buildings/:id` | Stable |
| Patrimoine — création / import | `/buildings/create-edit` | Stable |
| Gestion technique | `/buildings/technique` | Stable (310 équip. importés) |
| Énergie — vue d'ensemble | `/energie` | Stable |
| Énergie — détail PRM | `/energie/:prmId` | Stable |
| Préconisations puissance | `/energie/preconisations` | Stable |
| Factures | `/energie/factures`, `/energie/factures/:id` | Stable (parser ENGIE) |
| Facturation TURPE | `/energie/facturation` | Stable |
| **BPU historique** | `/energie/bpu` | **Nouveau (2026-05-19)** — 15 BPU stockés, parser à améliorer |

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
0015_add_bpu_tables               ← HEAD
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
88bdd4b  fix(codespaces): remove docker-in-docker feature
d9b1895  chore(codespaces): minimal .devcontainer
1fbd58c  feat(bpu): pipeline complet historique (#12)
f2b7e4c  feat(bpu): add SQL models + alembic migration (#11)
ffdcd3e  fix(buildings): dark mode BuildingTechniquePage (#10)
d784882  fix(enedis): ne recaler que la première fenêtre CDC
38ab484  fix(enedis): respecter la limite historique CDC
5e6b40f  fix(enedis): reprendre le backfill sans doublonner
e1d6d26  feat(energie): UI panneau async ENEDIS (Phase C) (#9)
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

### 1. Parser BPU — taux d'extraction faible
- **Symptôme** : 16/17 PDFs en `extraction_status='ocr_review'`, seuls 4 prix unitaires extraits (au lieu de ~300 attendus)
- **Cause** : parser regex actuel (`_extract_segments`, `_extract_components_from_line` dans `services/bpu.py`) trop conservateur sur les tableaux multi-colonnes
- **Mitigation déjà en place** : `raw_text` stocké sur chaque `BpuDocument` → re-parsing sans re-OCR possible
- **Solution proposée** : passer à `pdfplumber` qui détecte les colonnes des tableaux (à ajouter à `requirements.txt`)
- **Localisation** : `saas/backend/app/services/bpu.py` lignes ≈ 350-500
- **Voir** : [[Modules/Energie-BPU]]

### 2. Module Baux locataires (1.2 de la roadmap)
- Aucun code n'existe encore — c'est le prochain gros chantier "rapidement faisable"
- Pattern à réutiliser : upload PDF côté Frontend + `services/invoice_parsers/` côté Backend
- Modèle à créer : étendre `Local` avec champs bail, OU créer une nouvelle table `Lease`
- À discuter avec l'utilisateur sur le schéma (1-N entre Building et Lease ?)

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
| `bpu_documents` | **15** (importés 2026-05-19) |
| `bpu_segments` | 18 |
| `bpu_time_periods` | 3 |
| `bpu_price_components` | 4 |
| `bpu_fixed_charges` | 0 |

## 🔐 Secrets et accès

- **GitHub PAT** : récupérable via `git credential fill` depuis la machine de l'utilisateur (gho_*)
- **SSH VPS** : `~/.ssh/po2_vps2` → `ubuntu@135.125.152.112`
- **Password FTP ENEDIS** : `/root/.ftp_password_enedis` sur le VPS (chmod 600, root only)
- **Clé AES déchiffrement ENEDIS** : dans `.env` prod variable `ENEDIS_DECRYPTION_KEY`
- **Canal contact ENEDIS** : `506350699` (SETE_ENERGIE)
- ⚠️ **Ne JAMAIS afficher de password ou de clé en clair dans une conversation, un commit, ou ce vault** — l'utilisateur a déjà rotaté un mot de passe à cause de ça
