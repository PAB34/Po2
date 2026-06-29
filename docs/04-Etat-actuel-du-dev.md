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

> Mis à jour : 2026-06-29 — branche `feat/phase-5-drawer-actions` (PR #32, non mergée)

- **Fait cette session** : refonte UX `/refonte-v1/factures` + auto-validation backend (commits `9f8c0d1` front, `42ca294` back, déployés et recalculés sur staging) :
  - Header opérationnel compact (titre + actions + chips KPI cliquables + barre de répartition par état + montant HT) à la place du hero ; **nomenclature KPI figée** : À traiter · Traitées · Écarts · À expliquer · Bloquées · Expliquées.
  - Filtre « résultat de contrôle » ; en-tête de colonnes **sticky** ; tiroir : section « Éléments expliqués · non bloquants » avec libellés métier par code.
  - **Auto-validation énergie** (`_auto_validate_if_clean` dans `apply_parsed_to_invoice_import`) : facture au contrôle entièrement `valid` ET encore `to_review` → `approved`, sans jamais écraser une décision humaine. Vérifié staging : 178 auto-validées, 1 décision humaine préservée.
  - **Auto-validation CPE/DALKIA** (`_should_auto_validate_cpe` dans `build_finance_control_report(recalculate=True)`) : critère strict symétrique (aucun contrôle `error` ni `blocked`), `a_controler` → `valide` + note, jamais une décision humaine. Vérifié staging : 70/72 auto-validées (2 exclues : 1 écart, 1 bloqué).
  - **Graphe/dates** : clic-mois → filtre tableau, sélecteur d'année sur le graphe, affichage période de consommation (factures émises pour période antérieure), dépassement de puissance masqué (calcul backend conservé pour future section Fluides). Glossaire comptable : `docs/refonte-v1/factures-glossaire-controles.md`.
  - **Tri colonnes + période numérique** ; **contacts fournisseurs** (table `supplier_contacts`, migration **0065**, API `/billing/supplier-contacts`) + bouton « Préparer une réclamation » opérationnel (brouillon e-mail pré-rempli, copier/mailto, aucun envoi).
- **Objectif probable prochaine session** : brancher « Préparer une réclamation » (pré-rempli, pas d'envoi) ; uniformiser Montant HT ; totaux/tri tableau ; préparer le merge de la PR #32.
- **Fichiers/modules concernés** : `saas/frontend/src/features/invoices/InvoicesDecisionPageV1.tsx` ; backend `app/services/invoice_analysis.py` + `app/services/cpe_accounting.py`.
- **Tests ciblés probables** : `npx tsc -b` (frontend) ; `pytest tests/test_invoice_analysis_bpu_mapping.py tests/test_cpe_auto_validation.py` (15 passed).
- **À ne pas faire sans validation** : envoyer un mail fournisseur directement (V1 = copié/pré-rempli) ; merger sur `main` sans validation staging ; toucher les fichiers Codex hors tâche (`PRONO/*`, `knockout_mc.py`, docs non liées).
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

HEAD code constaté : `0065_add_supplier_contacts` (contacts fournisseurs pour réclamations).
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
