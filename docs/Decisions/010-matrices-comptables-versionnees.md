# 010 — Matrices comptables versionnées par contrat

> **Statut** : Accepté
> **Date** : 2026-06-25
> **Décideur(s)** : PAB34 + IA (Claude Opus 4.8)
> **Session liée** : `[[Sessions/2026-06-25 - Socle React V1]]`

## Contexte

Jusqu'ici, la codification comptable des factures vivait dans des tables « à plat » par domaine : `energy_accounting_site_mappings` / `energy_accounting_nature_rules` côté fourniture électricité-gaz, `cpe_accounting_site_mappings` / `cpe_accounting_nature_rules` côté CPE DALKIA. Ces tables permettent de rattacher PRM/sites et lignes de facturation à des natures comptables, mais elles n'ont **ni version, ni workflow de validation, ni instantané immuable** au niveau de la facture.

Le besoin métier exprimé (contrat d'écran `[[35-Contrat-ecran-Factures-Decisions-V1]]`, cadrage backend `[[38-Modele-backend-matrices-comptables-versionnees]]`) est plus robuste : pour chaque contrat/lot, la comptabilité doit pouvoir relire, corriger, importer/exporter et **valider** une matrice ; une facture validée doit conserver la **version exacte** de matrice appliquée au moment de la décision, même si une nouvelle version est créée ensuite. Un import XLSX ne doit jamais écraser silencieusement une version active.

## Décision

Introduire un référentiel de matrices comptables **versionné par contrat** — tables `accounting_matrix_contracts` → `accounting_matrix_versions` → `accounting_matrix_rules`, plus `invoice_accounting_snapshots` figeant l'imputation appliquée à chaque facture — où une version `active` n'est jamais modifiée en place : toute évolution crée une nouvelle version (clone possible) explicitement activée, l'activation archivant l'ancienne version active.

## Conséquences

### Positives
- Historique et auditabilité : une facture reste liée à la version de matrice utilisée à la décision (`invoice_accounting_snapshots.matrix_version_id`).
- Aller-retour XLSX fiable grâce à `stable_rule_key` (identifiant stable de règle).
- Les tables existantes `energy_accounting_*` / `cpe_accounting_*` sont **conservées** : elles deviennent la source du seed initial, sans rupture de l'existant.
- Une matrice par contrat/lot, pas une matrice globale ambiguë (axes V1 : service, fonction, nature, n° opération, antenne).

### Négatives / coûts assumés
- Deux référentiels coexistent pendant la migration (ancien à plat + nouveau versionné) → discipline de seed puis de bascule du frontend `/refonte-v1/factures`.
- La garantie « pas d'écrasement » impose une logique de cycle de vie (clone/activate/archive) plus lourde qu'un simple CRUD.
- Le contrôle « somme des ventilations = 100 % » et les droits par rôle (comptabilité/responsable marché/admin) restent à implémenter dans la phase d'application des snapshots.

### Alternatives écartées
- **Versionner les tables `*_accounting_*` existantes en place** — Mélangerait codifications historiques et enveloppe contractuelle, et compliquerait l'isolation par contrat/lot.
- **Une matrice globale unique** — Rend les clés ambiguës entre fournisseur, distributeur et contrat (risque listé au doc 38 §Risques).
- **Stocker l'imputation directement sur la facture sans snapshot dédié** — Empêcherait de conserver l'historique après évolution de la matrice (critère d'acceptation 5 du doc 35).

## Liens

- Cadrage backend : `[[38-Modele-backend-matrices-comptables-versionnees]]`
- Contrat d'écran : `[[35-Contrat-ecran-Factures-Decisions-V1]]`
- Code : `saas/backend/app/models/accounting_matrix.py`, `app/services/accounting_matrix.py`, `app/api/routes/accounting_matrix.py`, migration `alembic/versions/0064_add_accounting_matrices.py`
- Backlog : `[[Backlog]]` PO2-FIN-001, PO2-FACT-003, PO2-MKT-003
