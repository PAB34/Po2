# 002 — Schéma SQL normalisé en 5 tables pour les BPU

> **Statut** : Accepté
> **Date** : 2026-05-19
> **Décideur(s)** : PAB34 + IA (Claude Sonnet 4.5)
> **Session liée** : [[Sessions/2026-05-19 — BPU + Codespaces + Vault Obsidian]]

## Contexte

Po2 doit historiser les prix unitaires d'achat d'électricité issus des **Bordereaux de Prix Unitaires (BPU)** des marchés subséquents Hérault Énergies (17 PDFs, 2021 → 2026, fournisseurs EDF et ENGIE).

La formule de tarification est déjà fixée et utilisée dans `/energie/preconisations` (table `BillingBpuLine`) :

```
PU_total (€HTT/MWh) = PU_fourniture + PU_capacité + PU_CEE + PU_GO
```

Par segment tarifaire TURPE × poste horosaisonnier × année.

Question : faut-il une **table à plat** (un BPU = beaucoup de lignes "wide" avec colonnes par composante) ou un **schéma normalisé** (plusieurs tables liées) ?

## Décision

Schéma normalisé en **5 tables** :

```
bpu_documents (1) ─┬── (N) bpu_segments       (tension/site/usage)
                   │       │
                   │       └── (N) bpu_time_periods   (Base/HPH/HCH/...)
                   │              │
                   │              └── (N) bpu_price_components  (Fourniture/Capacité/CEE/GO)
                   │
                   └── (N) bpu_fixed_charges  (abonnements, branchement provisoire)
```

Voir [[Modules/Energie-BPU]] pour le détail.

## Conséquences

### Positives
- **Timeline d'une composante précise** : une simple jointure permet de tracer l'évolution 2021→2026 de la capacité sur le segment C4 → exactement ce que fait `/api/bpu/timeline`
- **Audit factures** : joindre `bpu_*` aux `EnergyInvoiceAnalysis` est direct (filtrer par segment + poste + composante)
- **Frais fixes séparés** : `bpu_fixed_charges` permet de gérer abonnements et branchement provisoire sans polluer la table des prix variables
- **Cohérence avec la formule existante** côté `BillingBpuLine` — pas de friction conceptuelle

### Négatives / coûts assumés
- Plus de tables = plus de jointures pour reconstituer un BPU complet (mitigé par `joinedload` côté SQLAlchemy)
- Migration alembic plus longue (cf. `0015_add_bpu_tables.py`)
- Le parser doit produire des objets imbriqués (pas une seule ligne plate) — légèrement plus complexe

### Alternatives écartées
- **Table à plat unique** (`bpu_lines` avec colonnes `pu_fourniture`, `pu_capacite`, ...) — Plus simple à parser mais perd la sémantique des frais fixes et empêche l'évolution future (si ENEDIS ajoute une 5e composante, schéma change)
- **JSONB unique** (`BpuDocument.payload JSONB`) — Maximal flexibilité mais requêtes timeline impraticables sans agg fonctions PG
- **Réutiliser `BillingBpuLine` existant** — Cette table est par-config-tenant, pas par-document-source. Mélanger les deux niveaux casserait la traçabilité du PDF source

## Liens

- Migration : `saas/backend/alembic/versions/0015_add_bpu_tables.py`
- Module : [[Modules/Energie-BPU]]
- Endpoints REST : `/api/bpu/formula`, `/api/bpu/documents`, `/api/bpu/timeline`
- PR : [#12](https://github.com/PAB34/Po2/pull/12) — `feat(bpu): pipeline complet historique des prix (Phases 2 + 3 + 4)`
- Commit migration : `f2b7e4c feat(bpu): add SQL models + alembic migration (#11)`
