# Contrôle factures ENGIE + fiche de liaison finances

tags: #energie #factures #ENGIE #comptabilité #liaison

> Statut : ✅ Phases 1 & 2 implémentées (2026-06-09) — non encore poussé/déployé.
> Calqué sur le contrôle DALKIA (`services/cpe_accounting.py`).

## Besoin

Contrôler les factures ENGIE (marché Hérault Énergie) contre le BPU signé **et** éditer, pour chaque
facture, une **fiche de liaison** transmise aux finances pour validation — comme pour DALKIA.

Le contrôle (analyse vs BPU/TURPE/taxes/puissance + décision valider/rejeter) **existait déjà**
(`EnergyInvoiceImport.control_status/decision_status`, `analyze_existing_invoice_import`, page détail).
Manquaient : la **matrice comptable** (codification) et l'**export fiche de liaison**.

## Ce qui a été ajouté

### Matrice comptable (autonome ENGIE, plan comptable distinct de DALKIA)
- Modèles `EnergyAccountingSiteMapping` (clé **PRM** → service/fonction/antenne/opération) et
  `EnergyAccountingNatureRule` (poste facturé → nature comptable). `models/invoice.py`, migration `0050`.
- `services/energie_accounting.py` :
  - `import_codification_workbook` : importe un xlsx **de même structure que le fichier DALKIA**
    (`saas/energie/DALKIA/COMPTABILITE/analyse_codification_dalkia_*.xlsx`), onglets « Sites vers
    codes » (clé PRM) + « Poste facturé vers Nature ». Détection d'onglets/colonnes tolérante.
  - `bootstrap_site_mappings_from_invoices` : pré-remplit la matrice avec les PRM vus dans les
    factures (les finances n'ont qu'à compléter les codes).
  - CRUD site-mappings / nature-rules.

### Fiche de liaison
- `resolve_invoice_codification` : pour chaque ligne facture → codes analytiques (via PRM) + nature
  (via poste/normalized_code). Statut `blocked` si PRM ou poste absent de la matrice (détecteur de trous).
- `build_energy_liaison_workbook` : xlsx (en-tête facture + 1 ligne/ligne facturée avec codes + nature
  + montant), calqué sur `build_finance_liaison_workbook` (DALKIA).

### Routes (`/billing/*`)
- `POST /billing/accounting/import-codification` (upload xlsx)
- CRUD `/billing/accounting/site-mappings` + `/nature-rules`
- `POST /billing/accounting/site-mappings/bootstrap`
- `GET /billing/invoices/imports/{id}/codification` (aperçu codification par ligne)
- `GET /billing/invoices/imports/{id}/liaison.xlsx` (export fiche de liaison)

### Frontend (`/energie/factures`)
- Bouton **« Matrice comptable »** → modale `components/EnergieAccountingMatrix.tsx` (import xlsx,
  pré-remplissage, tables éditables Sites/PRM et Postes→Nature).
- Page détail facture (`EnergieInvoiceDetailPage.tsx`) : panneau **« Fiche de liaison finances »**
  (aperçu codification + alerte lignes à codifier + bouton export xlsx). La décision valider/rejeter
  **existante** est conservée.

## Tests
`tests/test_energie_accounting.py` (4/4) : import upsert + ré-import, résolution ok/bloqué,
bootstrap, génération xlsx liaison. (`DATABASE_URL=sqlite`.)

## Reste à faire / points ouverts
- **Phase 3 (confort)** : export liaison en lot par mois/batch ; filtre « PRM non codifiés » ;
  statut « transmise aux finances ».
- Caler le format exact de l'onglet « Sites vers codes » ENGIE (clé PRM) avec un vrai fichier finances.
- L'import lit le xlsx **uploadé** (pas de chemin serveur gitignoré) → pas de souci de déploiement.
- Migration `0050` à appliquer en prod (`alembic upgrade head`).
