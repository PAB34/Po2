# 2026-06-25 - Socle React V1

## Contexte

Démarrage de l’incrément 1 du plan 37 : poser le socle React V1 en parallèle de l’existant, sans remplacer les routes actives.

## Réalisé

- Création de `saas/frontend/src/design-system/tokens.css`.
- Création des composants communs `Button`, `Card`, `KpiCard`, `StatusBadge`, `Drawer`, `DataTable`, `FilterBar`, `SegmentControl`.
- Création de `saas/frontend/src/app/navigationV1.ts`.
- Création de `saas/frontend/src/app/AppShellV1.tsx`.
- Création de `saas/frontend/src/features/cockpit/CockpitPageV1.tsx` avec mocks typés.
- Import des tokens V1 dans `main.tsx`.
- Création de `pages/RefonteV1Page.tsx`.
- Ajout de la route protégée `/refonte-v1` dans `App.tsx` comme laboratoire non listé dans la navigation principale.

## Validation

`npm install` a été exécuté avec le Node/npm local `C:\Users\pa.borja\Documents\Analyse ENEDIS\node`. Un premier `npm install` a échoué car `node` n’était pas dans le PATH des scripts postinstall ; relance réussie avec PATH corrigé. `npm run build` a d’abord échoué dans le sandbox sur `spawn EPERM` esbuild, puis a réussi en escaladé. Avertissements restants : chunk Vite > 500 kB et 4 vulnérabilités hautes npm non corrigées automatiquement.

## Handoff suivant

1. Ouvrir `/refonte-v1` et contrôler le rendu du laboratoire V1 quand un contrôle visuel sera utile.
2. Porter Factures & décisions en React mocké avec les composants V1.
3. Prévoir plus tard un découpage dynamique pour réduire le chunk principal.


## Extension : Factures V1 mockées

- Création de `features/invoices` avec types, mocks et `InvoicesDecisionPageV1`.
- Création de `pages/RefonteV1InvoicesPage.tsx`.
- Ajout de la route protégée `/refonte-v1/factures`.
- Ajout d’un `routePrefix` à `AppShellV1` pour garder la navigation laboratoire dans `/refonte-v1`.
- Build frontend réussi après cette extension.


## Extension : Fluides et Sites V1 mockés

- Création de `features/fluids` avec types, mocks et `FluidsPortfolioPageV1`.
- Création de `features/sites` avec types, mocks et `SitesPortfolioPageV1`.
- Création de `pages/RefonteV1FluidsPage.tsx`.
- Création de `pages/RefonteV1SitesPage.tsx`.
- Ajout des routes protégées `/refonte-v1/fluides` et `/refonte-v1/sites`.
- Mise à jour de `AppShellV1` : le `routePrefix` mappe cockpit/factures/fluides/sites vers les routes du laboratoire.
- Build frontend réussi après extension.

## État final de la première tranche laboratoire

Routes disponibles :

- `/refonte-v1` : Cockpit V1 mocké ;
- `/refonte-v1/factures` : Factures & décisions V1 mocké ;
- `/refonte-v1/fluides` : Fluides V1 mocké ;
- `/refonte-v1/sites` : Sites 360° V1 mocké.

Build : `npm run build` OK avec Node/npm local `C:\Users\pa.borja\Documents\Analyse ENEDIS\node`, en ajoutant ce dossier au PATH de la commande.

Avertissements connus :

- Vite signale un chunk principal > 500 kB ; prévoir du lazy-loading plus tard.
- `npm audit` signale 4 vulnérabilités hautes ; ne pas lancer `npm audit fix --force` sans analyse, car cela peut modifier des versions majeures.
- Aucun contrôle visuel navigateur n’a été fait volontairement pour économiser les tokens.

## Handoff très concret pour la prochaine IA

1. Ne pas remplacer les routes historiques. Le laboratoire est sous `/refonte-v1*`.
2. Si contrôle visuel demandé : ouvrir `/refonte-v1`, `/refonte-v1/factures`, `/refonte-v1/fluides`, `/refonte-v1/sites`.
3. Prochaine vraie étape métier : raccorder progressivement `/refonte-v1/factures` aux API existantes, en gardant les mocks comme fallback.
4. Avant raccordement, définir un DTO commun Facture V1 : fournisseur, contrat/version, site, montant, statut décision, statut matrice, trace de contrôle, snapshot de preuves.
5. Garder `package-lock.json` versionné ; garder `node_modules` et `dist` ignorés.


## Extension : DTO Facture V1

- Création de `features/invoices/invoiceDecisionV1.types.ts`.
- Création de `features/invoices/invoiceDecisionV1.adapters.ts`.
- Adaptateurs disponibles : `adaptEnergyInvoiceImportToDecisionV1`, `adaptGasInvoiceToDecisionV1`, `adaptCpeFinanceInvoiceToDecisionV1`.
- Mise à jour des mocks et de `InvoicesDecisionPageV1` pour consommer `InvoiceDecisionV1`.
- Build frontend réussi après modification.

## Handoff raccordement Factures

Créer ensuite un hook ou service frontend, par exemple `features/invoices/useInvoiceDecisionsV1.ts`, qui appelle les API existantes et applique les adaptateurs. Ne pas mettre les appels API directement dans la page. Le raccordement prioritaire peut commencer par `fetchEnergyInvoiceImports` et `fetchGasInvoices`; DALKIA peut être branché ensuite via `fetchCpeFinanceInvoices`.


## Extension : hook Factures V1

- Création de `features/invoices/useInvoiceDecisionsV1.ts`.
- Le hook appelle `fetchEnergyInvoiceImports`, `fetchGasInvoices`, `fetchCpeFinanceInvoices` avec `Promise.allSettled`.
- Les réponses sont normalisées via les adaptateurs `InvoiceDecisionV1`.
- Si aucun token ou aucune donnée API exploitable, la page conserve `invoicesMock`.
- `InvoicesDecisionPageV1` affiche dans son eyebrow si elle utilise les mocks, synchronise ou consomme les données API.
- Build frontend réussi après ajout.

## Handoff technique final

Commande de build utilisée :

```powershell
$env:Path='C:\Users\pa.borja\Documents\Analyse ENEDIS\node;' + $env:Path
& 'C:\Users\pa.borja\Documents\Analyse ENEDIS\node\npm.cmd' run build
```

Le build nécessite une exécution autorisant le spawn esbuild. En sandbox simple, Vite peut échouer sur `spawn EPERM`.

Prochaine IA :

1. Faire un contrôle visuel ciblé seulement si l’utilisateur le demande.
2. Vérifier en runtime si les appels API de `useInvoiceDecisionsV1` remontent suffisamment de données réelles.
3. Créer ensuite le modèle/backend des matrices comptables versionnées, ou brancher provisoirement les matrices DALKIA/ENGIE existantes si on veut accélérer.
4. Ne pas lancer `npm audit fix --force` sans audit humain.
5. Ne pas versionner `node_modules`, `dist`, `*.tsbuildinfo`, `vite.config.js`, `vite.config.d.ts`.


## Extension : synthèse Matrices V1

- Création de `features/invoices/accountingMatrixV1.ts`.
- Agrégation frontend des codifications existantes : énergie et CPE DALKIA.
- Fallback conservé vers `accountingMatricesMock`.
- `InvoicesDecisionPageV1` consomme désormais `useAccountingMatricesV1`.
- Build frontend réussi après ajout.

## Handoff spécifique matrices

La synthèse actuelle est une couche UX de transition. Le backend durable reste à concevoir : tables matrices/version/règles/snapshots, import/export XLSX, écran de diff avant réimport, et lien immuable entre facture validée et version de matrice appliquée.

## Extension : cadrage backend Matrices V1

- Création de docs/38-Modele-backend-matrices-comptables-versionnees.md.
- Le document formalise le backend cible derrière Factures & décisions V1 : contrats matrices, versions, règles, import/export XLSX, preview de diff, snapshots facture et historique.
- Il confirme que useAccountingMatricesV1 est une couche UX de transition, pas le modèle durable.
- Il précise la stratégie de migration depuis energy_accounting_site_mappings / energy_accounting_nature_rules et cpe_accounting_site_mappings / cpe_accounting_nature_rules.

## Extension : backend matrices versionnées (tranche minimale)

Implémentation du backend minimal cadré par le doc 38, dans `saas/backend` :

- `app/models/accounting_matrix.py` : `AccountingMatrixContract`, `AccountingMatrixVersion`, `AccountingMatrixRule`, `InvoiceAccountingSnapshot`.
- `app/schemas/accounting_matrix.py`.
- `app/services/accounting_matrix.py` (invariants versionnés).
- `app/api/routes/accounting_matrix.py` : router `/api/accounting-matrices`.
- `alembic/versions/0064_add_accounting_matrices.py`.
- Modifs : `app/models/__init__.py` (export) + `app/api/router.py` (montage).

Invariant central appliqué : une version active n'est jamais modifiée en place. Évolution = créer une version (clone optionnel via `clone_from_version_id`), l'éditer en brouillon, puis l'activer ; l'activation archive automatiquement l'ancienne version active. Les règles ne sont éditables que sur une version `draft`/`candidate`.

Décision durable tracée : ADR `[[Decisions/010-matrices-comptables-versionnees]]`. Vault mis à jour : Backlog (PO2-FIN-001), 00-Index, Modules/Energie-Facturation, docs 04/37/38.

Validation : `python -m py_compile` OK. Import runtime FastAPI et migration Alembic non exécutés (FastAPI/SQLAlchemy absents du poste) → CI requise.

### Extension : seed de migration (étape 3 — fait)

- `app/services/accounting_matrix.py` : `seed_from_existing` + helpers `_seed_energy` / `_seed_cpe`.
- `app/api/routes/accounting_matrix.py` : `POST /api/accounting-matrices/seed`.
- `app/schemas/accounting_matrix.py` : `AccountingMatrixSeedOut`.
- Regroupement (arbitrage utilisateur) : énergie = une matrice par fournisseur ; CPE = une matrice par `contract_code`. Mappings site/PRM->axes dupliqués dans chaque matrice du domaine. Versions créées en `draft`. Idempotent.
- `py_compile` OK.

### Prochaine IA — phase suivante matrices

1. `alembic upgrade head` sur staging (migration `0064`).
2. ~~Seed~~ fait : appeler `POST /api/accounting-matrices/seed` sur staging et vérifier le récapitulatif + quelques matrices en `draft`.
3. Import/export XLSX (preview/diff + commit en brouillon), en gardant `stable_rule_key` stable (format colonnes = doc 35 §5).
4. `apply` + `validate-snapshot` : écrire `invoice_accounting_snapshots` à la décision (contrôle 100 % ventilation) + dédoublonnage des factures réimportées.
5. Droits par rôle (doc 35 §6) non encore appliqués sur le router.
6. Basculer `/refonte-v1/factures` de `useAccountingMatricesV1` vers `/api/accounting-matrices/*`.

## Handoff matrices pour la prochaine IA

1. Lire docs/38-Modele-backend-matrices-comptables-versionnees.md avant toute implémentation backend.
2. Créer les tables versionnées sans supprimer les tables énergie/CPE existantes.
3. Implémenter d'abord lecture/création/version/activation avant l'import XLSX complet.
4. Ne jamais écraser une version active par import direct.
5. Prévoir invoice_accounting_snapshots avant de considérer l'historique des factures comme fiable.


## Extension : import/export XLSX (PR #27, mergée)

- `app/services/accounting_matrix_xlsx.py` : export (feuille `Matrice` + `Lisez-moi`), `parse_xlsx`, `preview_import` (diff sans écriture), `commit_import` (version brouillon).
- Routes : `GET .../versions/{id}/export.xlsx`, `POST .../contracts/{id}/import-preview`, `POST .../contracts/{id}/import-commit`.
- Tests `tests/test_accounting_matrix_xlsx.py`.

## Extension : application + snapshots (PR #28, mergée)

- `app/services/accounting_matrix_apply.py` : moteur pur `apply_matrix(rules, lines)` + cycle de vie.
- Routes : `POST .../invoices/{source}/{id}/apply | validate-snapshot | manual-override | export-finance`.
- Tests `tests/test_accounting_matrix_apply.py` (moteur, immutabilité, dédoublonnage, validation bloquée par exceptions).

## État backend matrices : COMPLET

Les 3 PR (#26/#27/#28) sont mergées dans `main`, CI verte. Restent en intégration : brancher les extracteurs réels de lignes facture par source sur `apply` ; droits par rôle (doc 35 §6) ; faire atterrir le labo React V1 (`wip/codex-2026-06-25`) dans `main` puis brancher `/refonte-v1/factures` sur `/api/accounting-matrices/*`.
