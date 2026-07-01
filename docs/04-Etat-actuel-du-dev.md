---
type: state
status: actif
read_policy: toujours
source_of_truth: true
related:
  - 00-Index.md
  - 49-Spec-execution-refonte-Factures-Decisions-V1.md
  - Backlog.md
do_not_auto_read:
  - Archives/Journal-etat-dev-2026.md
---

# État actuel du développement

> Snapshot du **présent** : ce qui tourne en prod, les chantiers ouverts, et où reprendre.
> Détail chronologique des mises à jour passées → `Archives/Journal-etat-dev-2026.md` (ne pas lire par défaut).
> Détail par session → `Sessions/` (ne pas lire par défaut).

## 🔜 Reprise prochaine session

> Mis à jour : 2026-07-01 (soir) — **PR #32, #33, #34, #35 toutes mergées sur `main` et déployées en PROD** (3 deploys OK, migration 0066 appliquée en prod). Détail → journal `Archives/Journal-etat-dev-2026.md`.

- **État global** : tout le travail de la session est **en production** (`patrimoineaucarre.com`, santé 200) :
  - **Budget par marché v1** (PR #33) : `accounting_budget_lines` (migration 0066), API `/api/accounting-budget/*`, module front « Marchés » (`/refonte-v1/marches`). Décisions : pilote DALKIA, annuel, atterrissage pro-rata.
  - **Import codification DALKIA** (PR #34) : lit le « Code contrat » de la feuille « Poste facturé vers Nature ctpab » + colonnes de validation compta. Classeur canonique = `MATRICE_DALKIA-COMPATBILITE.xlsx`. Règle process « fil du dev » actée (05-Conventions §2 + AGENTS/CLAUDE).
  - **Matrice versionnée éditable** (PR #35) : `/refonte-v1/matrices` = fenêtre pleine page éditable (axes comptables, tri, colonnes redimensionnables, import/export). Édition directe version active (archivée figée). Colonne « Désignation site » (facture). Antenne DALKIA = code court. Enrichissement suggested_antenna via **référentiel CIRIL** (`saas/backend/app/data/index_compta.json`). `prefill_energy_matrices()` pré-remplit ENGIE/EDF (antenne 100%, service/fonction best-effort, opération vide car élec=fonctionnement).
- **⚠️ Données ENGIE/EDF : faites sur STAGING, PAS en PROD.** Le code `prefill_energy_matrices` + seed est déployé en prod mais **pas encore exécuté** (prod n'a aucune matrice seedée). Pour activer en prod : lancer via container `prefill_energy_matrices(db, city_id)` puis `seed_from_existing`, après validation. Idem la correction antenne DALKIA (UPDATE) : faite sur staging seulement.
- **Objectif probable prochaine session** : (1) décider si on **rejoue le setup matrices en prod** (DALKIA seed + ENGIE/EDF prefill) ; (2) **service/fonction best-effort** ne couvrent que ~10-18% des PRM (bâtiments typés) → la compta complète le reste via l'éditeur ; (3) **grille_9 CIRIL = pôle/direction « BÂTIMENTS »** — pas encore un axe de matrice, à intégrer si besoin ; (4) budget : réalisé fiable dépend toujours des extracteurs de lignes (PO2-FIN-001).
- **⚠️ Staging vs migrations** : la base staging était stampée `0066` par les déploiements de branche ; maintenant que `main` a `0066`, les déploiements staging depuis `main` sont cohérents.
- **À ne pas faire sans validation** : rejouer prefill/seed en prod sans accord ; confondre atterrissage financier et intéressement (`cpe_atterrissage.py`) ; toucher les fichiers Codex (`PRONO/*`, `knockout_mc.py`).
- **Niveau de confiance** : élevé (v1 codée et déployée conformément au cadrage validé ; reste la revue utilisateur sur staging avant merge).

## 🟢 Ce qui tourne en prod (https://patrimoineaucarre.com)

| Module | Route | État |
|---|---|---|
| Auth | `/login`, `/register`, `/account` | Stable |
| Patrimoine — liste / détail | `/buildings`, `/buildings/:id` | Stable ; rattachement manuel PRM/PCE/eau avec contexte fournisseur/contrat |
| Patrimoine — création / import hiérarchique | `/buildings/create-edit` | `SITE`→`Site`, `BATIMENT`→`Building.site_id`, `LOCAL`→`Local.building_id` |
| Patrimoine — rapprochements (file) | `/patrimoine/rapprochements` | PRM ENEDIS + PCE GRDF → candidat Bâtiment/Site, lien canonique |
| Gestion technique SYPEMI | `/buildings/technique` | Stable (310 équip.) + onglet Terrain (import CVC) |
| CVC fluides — cockpit F-Gaz / ESP | `/buildings/cvc-fluides` | Cockpit, Registre F-Gaz, Actions, ESP/DESP, Import |
| Énergie — vue / détail PRM / préconisations | `/energie`, `/energie/:prmId`, `/energie/preconisations` | Stable ; collecte ENEDIS sync de secours |
| Factures ENGIE/EDF | `/energie/factures`, `/energie/factures/:id` | Stable (parser XLSX ENGIE, contrôle BPU/TURPE/ENEDIS, décision, lots, 9 filtres facettes) |
| Factures gaz TotalEnergies | onglet Factures marché > Hérault Énergie | Import + contrôle cohérence/fourniture/acheminement/taxes |
| Facturation TURPE | `/energie/facturation` | Stable |
| CPE DALKIA | `/cpe` | Avancé : cockpit finance, contrôle factures, référentiel DALKIA, conso multi-fluides |
| BPU | `/energie/bpu` | Timeline · TURPE · Documents/Import · Édition tableau |
| Matrices comptables versionnées | API `/api/accounting-matrices/*` | Backend complet mergé `main` (schéma + XLSX + apply/snapshots) |
| Refonte React V1 (labo) | `/refonte-v1/*` | `/matrices` branché API réelle ; `/factures` **mergé `main`** (PR #32, auto-validation, contacts/réclamation) ; `/marches` (budget par marché) — PR #33, déployée staging, non mergée |

## 📦 Migrations alembic

HEAD code constaté : `0066_add_accounting_budget_lines` (budget par marché, maille opération, branche `feat/budget-marches` PR #33 — non encore sur `main`). Dernière migration sur `main` : `0065_add_supplier_contacts`.
Jalons : `0017` hiérarchie sites · `0041` seed CPE scope · `0048` CVC F-Gaz · `0056` rapprochements
patrimoine · `0057` gas_invoices · `0064` matrices. Liste complète prod → journal archivé.

## 🔥 Chantiers ouverts (présent)

| ID Backlog | Chantier | État / prochaine action |
|---|---|---|
| PO2-FIN-001 | Factures + matrice comptable + atterrissage | Backend matrices mergé ; reste extracteurs réels de lignes facture sur `apply`, droits par rôle. Bloque la fiabilité du réalisé du nouveau module Budget (PR #33) |
| PO2-FIN-002 | Budget par marché + suivi financier | v1 codée (PR #33, pilote DALKIA) : `accounting_budget_lines`, réalisé pro-rata, module « Marchés ». Reste : validation staging, merge, extension autres marchés, atterrissage physique doc 34 §F04 (v2) |
| PO2-UX-002 | Refonte frontend React V1 | Tranche `Factures & décisions` (doc 49) ; Phase 5 à brancher |
| PO2-CPE-001 | Contrôle factures DALKIA CPE | Reimport CSV, rattacher codes piscines, parser DPGF Lot 1/2 |
| PO2-FACT-001 | Audit facture ENGIE + socle EDF | Reimport XLSX force update, valider fiche liaison finance |
| PO2-PAT-003 | Rapprochements patrimoine | V1 livrée ; reste sources CPE/maintenance, cible Local, matching par adresse |
| PO2-ENEDIS-001 | ENEDIS async prod | Bloqué côté ENEDIS ; contournement sync de secours en place |
| PO2-GRDF-001 | Connecteur GRDF gaz | Scaffolding Phases 0-1 ; reste Phases 2-5 |

> Le détail complet des chantiers, dépendances et statuts vit dans `Backlog.md` (source de vérité du « quoi faire ensuite »).

## 📊 Données en prod (ordre de grandeur)

`cities` 1 (Sète) · `buildings` ~530 · `equipment_references` 310 · `bpu_documents` 17 / `bpu_price_components` 523 · `enedis_async_jobs` 0 (scheduler en attente du canal validé).

## ⚙️ Invariant gaz (2026-05-22)

- `BuildingMeterLink` = point central bâtiment → compteur multi-fluides.
- Le flux GRDF alimente PCE et consommations gaz quel que soit le fournisseur.
- BPU gaz HÉRAULT ÉNERGIE lot 7 importable comme référence `TOTALENERGIES` (compteurs Ville).
- La cotation OS3 gaz du P1 DALKIA reste dans le module CPE ; ne pas la fusionner avec la référence BPU TotalEnergies.

## 🔐 Secrets et accès

- **GitHub PAT** : `git credential fill` depuis la machine de l'utilisateur.
- **SSH VPS** : `~/.ssh/po2_vps2` → `ubuntu@135.125.152.112`.
- **Password FTP ENEDIS** : `/root/.ftp_password_enedis` sur le VPS (root only).
- **Clé AES ENEDIS** : `.env` prod `ENEDIS_DECRYPTION_KEY`. **Canal ENEDIS** : `506350699`.
- ⚠️ **Ne JAMAIS afficher de password/clé en clair** (chat, commit, vault).

## Liens utiles

- Pilotage : [[Backlog]] · [[03-Roadmap-fonctionnalites]]
- Tranche active : [[49-Spec-execution-refonte-Factures-Decisions-V1]]
- Décisions durables : [[Decisions/010-matrices-comptables-versionnees]] · [[Decisions/011-assistant-matrices-et-decisions-factures-V1]] · [[Decisions/012-auto-validation-et-semantique-controle-factures-V1]]
- Historique : `Archives/Journal-etat-dev-2026.md` · `Sessions/` *(ne pas lire par défaut)*
