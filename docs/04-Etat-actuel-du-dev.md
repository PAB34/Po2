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

> Mis à jour : 2026-07-01 — PR #32 mergée sur `main`. Branche `feat/budget-marches` (PR #33, CI verte, déployée sur staging, **non mergée** — en attente de validation utilisateur). Détail de la session → journal `Archives/Journal-etat-dev-2026.md` (2026-07-01).

- **État** : (a) tranche `Factures & décisions V1` **mergée sur `main`** (PR #32 — UX, auto-validation énergie + CPE ADR 012, contacts fournisseurs + réclamation pré-remplie) ; (b) **tranche Suivi financier / Budget par marché codée v1** (PR #33, pilote CPE/DALKIA), déployée sur staging, en attente de revue utilisateur avant merge.
- **Décisions §7 du cadrage tranchées (2026-07-01)** : marché pilote v1 = **DALKIA (CPE)** ; granularité temporelle = **annuelle seule** ; atterrissage v1 = **pro-rata temporel simple** (moteur physique doc 34 §F04 reporté en v2).
- **Ce qui a été livré (PR #33)** : table `accounting_budget_lines` (migration 0066, maille opération, rattachée au `matrix_contract_id`) ; service `accounting_budget.py` (CRUD + calcul du réalisé par opération depuis `invoice_accounting_snapshots` avec résolution d'année facture CPE/DALKIA + imports fluides, et comptage explicite des snapshots exclus faute d'année résolue — pas de chiffre trompeur tant que PO2-FIN-001 n'est pas complet) ; API `/api/accounting-budget/*` ; module front « Marchés » (`/refonte-v1/marches`).
- **Objectif probable prochaine session** : (1) valider sur staging le module Marchés (`/refonte-v1/marches`) avec de vraies données DALKIA, puis merger la PR #33 si OK ; (2) si des lignes de budget réelles existent déjà côté finances, prévoir un import (pas fait en v1, saisie manuelle uniquement) ; (3) étendre le réalisé à d'autres sources de facture (gaz TotalEnergies) si le marché pilote suivant en a besoin.
- **⚠️ Pré-requis toujours ouvert** : réalisé par opération = extracteurs de lignes facture (PO2-FIN-001) + `operation_number` réellement renseigné. Le service `accounting_budget.py` gère déjà l'incomplétude proprement (note de complétude affichée), mais le chiffre ne sera fiable qu'une fois les extracteurs branchés sur toutes les sources utiles.
- **Fichiers/modules concernés** : `app/models/accounting_budget.py`, `app/services/accounting_budget.py`, `app/api/routes/accounting_budget.py`, `saas/frontend/src/features/marches/`. Existant à relire si besoin : `app/models/accounting_matrix.py`, `invoice_accounting_snapshots`, `app/services/cpe_atterrissage.py` (≠ atterrissage financier).
- **Tests ciblés probables** : `pytest tests/test_accounting_budget.py` ; `npx tsc -b` / `npm run build` (front, CI uniquement — pas d'install npm locale sur ce poste).
- **À ne pas faire sans validation** : confondre atterrissage **financier** et atterrissage **intéressement** (`cpe_atterrissage.py`) ; merger la PR #33 sans validation staging ; toucher les fichiers Codex hors tâche (`PRONO/*`, `knockout_mc.py`).
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
