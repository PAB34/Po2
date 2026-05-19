# Module — Énergie / Facturation

> Vérification automatique des factures des fournisseurs (ENGIE, DALKIA, TOTAL, SUEZ).

## Périmètre

| Fonctionnalité roadmap | Statut |
|---|---|
| 4.1 Électricité ENGIE | 🟡 Partiel (parser PDF existant, audit à enrichir) |
| 4.2 Électricité DALKIA | 🔴 Todo |
| 4.3 Gaz TOTAL ENERGIE | 🔴 Todo |
| 4.4 Eau SUEZ | 🔴 Todo |

## Cadre contractuel Hérault Énergies

> Source : `saas/specs/03_plan_facturation_optimisation_energie.md`

Hérault Énergies est la **centrale d'achat groupé** d'électricité pour les collectivités de l'Hérault. Le CCTP impose des règles que le moteur de facturation **DOIT** respecter :

- **Lots 1-6** : segmentation par tension et profil d'usage (cf. [[Modules/Énergie - BPU]])
- **Optimisation puissance** : pas de **0,1 kVA** pour EP (Éclairage Public), pas de **1 kVA** pour les autres tarifs
- **Refacturation acheminement à l'euro** (sauf C1) : le fournisseur EDF/ENGIE refacture **strictement** ce qu'a coûté l'acheminement, sans marge → c'est pour ça que le contrôle TURPE est si important ([[Modules/Énergie - TURPE]])
- **Chiffrage annuel obligatoire** : toute préconisation de modification de puissance doit être chiffrée en € sur 12 mois ([[Modules/Énergie - Préconisations]])

Cette spec est la **légitimité métier** du produit côté audit factures.

## Architecture transversale

### Modèle commun : `EnergyInvoiceImport`
Migration 0010, table `energy_invoice_imports` :
- Upload PDF/Excel → analyse async → résultat structuré
- Statut : `pending`, `analyzing`, `success`, `error`
- Champs : `pdf_filename`, `supplier`, `period_start`, `period_end`, `total_amount`, `raw_text`

### Modèle d'analyse : `EnergyInvoiceAnalysis`
Migration 0011-0012, table `energy_invoice_analyses` :
- Une ligne d'analyse par PRM × période détectée
- Champs : `prm_id`, `consumption_kwh`, `amount_eur`, `unit_price_billed`, `unit_price_expected` (depuis BPU), `decision` (accepté/contesté/à revoir), `notes`

### Service : `invoice_analysis.py`
Croise les factures importées avec :
1. Les `BillingBpuLine` (prix par segment tarifaire × poste)
2. Les consos ENEDIS (pour vérifier les quantités facturées)
3. Calcule l'écart prix facturé vs prix BPU attendu

### Routes : `/api/energie/factures/*`
- `GET /api/energie/factures` : liste paginée
- `GET /api/energie/factures/{import_id}` : détail
- `POST /api/energie/factures/upload` : upload + analyse
- `DELETE /api/energie/factures/{import_id}` : suppression (ajouté par session précédente)

### UI : `EnergieInvoicesPage` + `EnergieInvoiceDetailPage`

## ENGIE — état actuel

### Parser : `services/invoice_parsers/engie_pdf.py`
- Extrait : période de facturation, PRM concernés, consommations par poste (HPH/HCH/...), prix unitaires, totaux HT/TTC
- Limitations connues : variations de mise en page entre les modèles de facture ENGIE

### Documents de référence — à consulter avant toute évolution du parser

> **Mapping facture ENGIE** : `saas/specs/04_mapping_facture_engie.md` (553 lignes)
> Tableau complet des colonnes page 3, codes index HPSH/HCSH/HPSB/HCSB/Base/Pointe, conversion EUR/kWh ↔ EUR/MWh. Contient un modèle de tables (`energy_invoices` / `energy_invoice_sites` / `energy_invoice_periods`) plus fin que l'`EnergyInvoiceAnalysis` actuel — utile quand on étendra à DALKIA / TOTAL.

> **Matrice de contrôles** : `saas/specs/05_matrice_controles_factures_energie.md` (157 lignes)
> 40+ codes d'erreur normalisés (`BPU_PRICE_MISMATCH`, `TURPE_VERSION_MISSING`, `POWER_LOAD_CURVE_OVERRUN`, etc.), statuts de décision (`valid` / `review` / `invalid`), tolérances chiffrées (0,05 EUR sur les totaux, 0,05 EUR/MWh sur les prix unitaires), règles exactes de rapprochement BPU (ex: `BT <= 36 kVA SDT CU4/MU4` → `CU/base`). Doc canonique du moteur de décision.

### Endpoints proxy ENGIE
- `services/engie_client.py` : client OAuth ENGIE Entreprise
- Routes `/api/engie/*`
- Données contractuelles + factures via API (quand disponibles)

## DALKIA — 🔴 Todo

### Notes
- DALKIA est un fournisseur de **chaleur urbaine** (réseaux de chaleur) ET d'électricité
- Factures multi-fluides possible → ajouter `fuel_type` à `EnergyInvoiceImport`
- Format Excel attendu : modèle propriétaire à reverse-engineer sur 1-2 fichiers d'exemple

### Architecture cible
1. Créer `services/invoice_parsers/dalkia_excel.py` (utiliser `openpyxl`)
2. Mapping colonnes Excel → champs `EnergyInvoiceAnalysis`
3. Tester sur un échantillon de fichiers réels (à demander à l'utilisateur)

## TOTAL ENERGIE Gaz — 🔴 Todo

### Notes
- TOTAL fournit gaz et élec — focus ici sur gaz
- Pas de format standard, mais format PDF probablement assez stable
- Pattern : `services/invoice_parsers/total_energie_pdf.py` calqué sur `engie_pdf.py`

## SUEZ Eau — 🔴 Todo

### Notes
- Probablement le même parser que pour la conso (cf. [[Énergie - Consommation]] section SUEZ)
- Une facture eau contient consommation + tarif + total → les 3 ingrédients pour l'audit

## Workflow audit de facture (générique)

```
1. Utilisateur upload PDF/Excel facture sur /energie/factures
2. POST /api/energie/factures/upload → EnergyInvoiceImport.status = "analyzing"
3. Tâche async : invoice_parsers.{supplier} extrait les champs
4. Pour chaque ligne extraite :
   a. Cherche le BPU applicable (supplier × year × lot)
   b. Cherche le BpuPriceComponent pour (segment, period, component)
   c. Calcule écart facturé vs attendu
   d. Si écart > seuil → flag pour revue manuelle
5. EnergyInvoiceImport.status = "success"
6. Utilisateur consulte le détail dans /energie/factures/{id} et valide/conteste
```

## Voir aussi

- [[Énergie - BPU]] — Source des prix attendus
- [[Énergie - Préconisations]] — Calcul prix unitaires
