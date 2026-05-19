# Module — Énergie / Facturation

> Vérification automatique des factures des fournisseurs (ENGIE, DALKIA, TOTAL, SUEZ).

## Périmètre

| Fonctionnalité roadmap | Statut |
|---|---|
| 4.1 Électricité ENGIE | 🟡 Partiel (parser PDF existant, audit à enrichir) |
| 4.2 Électricité DALKIA | 🔴 Todo |
| 4.3 Gaz TOTAL ENERGIE | 🔴 Todo |
| 4.4 Eau SUEZ | 🔴 Todo |

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
