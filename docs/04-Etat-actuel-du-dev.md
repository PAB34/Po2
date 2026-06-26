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

> Mis à jour : 2026-06-26 — branche `chore/optimisation-docs-ia`

- **Objectif probable** : doc 49 §8 **Phase 5** — brancher les vraies actions du drawer facture (valider / mettre en attente / préparer réclamation / exporter finance / réimport), après la restructuration documentaire en cours.
- **Pourquoi prioritaire** : la tranche verticale `Factures & décisions` est le parcours pilote ; Phases 1→4 posées, il reste à rendre les actions du drawer réellement opérationnelles (et non simulées).
- **Fichiers/modules concernés** : `saas/frontend/src/features/invoices/*` (`InvoicesDecisionPageV1.tsx`, hooks `useInvoiceDecisionsV1`, `useInvoiceAccountingSnapshotsV1`), `saas/frontend/src/lib/api.ts` ; backend `app/api/routes/{billing,gas_invoice,cpe_dalkia,accounting_matrix}.py`.
- **Tests ciblés probables** : `npx tsc -b` (frontend) ; backend `pytest tests/test_accounting_matrix_apply.py` + tests décision facture si ajoutés.
- **Décisions à confirmer avant de coder** : rôles exacts autorisés pour `validate-snapshot` / `export-finance` (ADR 011) ; formulation `historique` vs `revision` ; `apply` envoie encore `invoice_lines: []` par défaut → confirmer extracteurs réels par source.
- **À ne pas faire sans validation** : envoyer un mail fournisseur directement (V1 = copié/pré-rempli) ; écraser une version de matrice active ; merger sur `main` sans validation staging.
- **Niveau de confiance** : élevé.

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
| Refonte React V1 (labo) | `/refonte-v1/*` | `/matrices` branché API réelle ; `/factures` tranche active (PR #30, validée staging) |

## 📦 Migrations alembic

HEAD code constaté : `0064_add_accounting_matrices` (matrices comptables versionnées).
Jalons : `0017` hiérarchie sites · `0041` seed CPE scope · `0048` CVC F-Gaz · `0056` rapprochements
patrimoine · `0057` gas_invoices · `0064` matrices. Liste complète prod → journal archivé.

## 🔥 Chantiers ouverts (présent)

| ID Backlog | Chantier | État / prochaine action |
|---|---|---|
| PO2-FIN-001 | Factures + matrice comptable + atterrissage | Backend matrices mergé ; reste extracteurs réels de lignes facture sur `apply`, droits par rôle, bascule front `/refonte-v1/factures` |
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
- Décisions durables : [[Decisions/010-matrices-comptables-versionnees]] · [[Decisions/011-assistant-matrices-et-decisions-factures-V1]]
- Historique : `Archives/Journal-etat-dev-2026.md` · `Sessions/` *(ne pas lire par défaut)*
