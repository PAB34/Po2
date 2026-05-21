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

- **Lots 1-6** : segmentation par tension et profil d'usage (cf. [[Modules/Energie-BPU]])
- **Optimisation puissance** : pas de **0,1 kVA** pour EP (Éclairage Public), pas de **1 kVA** pour les autres tarifs
- **Refacturation acheminement à l'euro** (sauf C1) : le fournisseur EDF/ENGIE refacture **strictement** ce qu'a coûté l'acheminement, sans marge → c'est pour ça que le contrôle TURPE est si important ([[Modules/Energie-TURPE]])
- **Chiffrage annuel obligatoire** : toute préconisation de modification de puissance doit être chiffrée en € sur 12 mois ([[Modules/Energie-Preconisations]])

Cette spec est la **légitimité métier** du produit côté audit factures.

## Architecture transversale

### Modèle commun : `EnergyInvoiceImport`
Migration 0010, table `energy_invoice_imports` :
- Upload PDF/Excel → analyse immédiate → résultat structuré
- Statuts séparés : import, analyse technique, contrôle métier, décision utilisateur
- Champs utiles aujourd'hui : fichier source, hash, fournisseur, numéro/date facture, période, regroupement, titulaire du contrat, TTC, kWh, compteurs de contrôle

### Analyse actuellement persistée
Les migrations 0011-0012 enrichissent `energy_invoice_imports` :
- `analysis_result_json` conserve l'extraction ENGIE détaillée ;
- `control_report_json` conserve les contrôles BPU, TURPE, taxes, périodes, ENEDIS et puissance ;
- le détail PRM/FIC/lignes est déjà affiché sur `/energie/factures/:invoiceImportId`.

La trajectoire suivante est de projeter ces données dans les tables normalisées déjà décrites par `saas/specs/04_mapping_facture_engie.md` pour permettre les requêtes d'historique dépenses/tarifs et la future alimentation par API ENGIE.

### Service : `invoice_analysis.py`
Croise les factures importées avec :
1. Les `BillingBpuLine` (prix par segment tarifaire × poste)
2. Les consos ENEDIS (pour vérifier les quantités facturées)
3. Calcule l'écart prix facturé vs prix BPU attendu

### Routes API reelles : `/api/billing/invoices/imports/*`
- `GET /api/billing/invoices/imports` : liste des imports factures
- `GET /api/billing/invoices/imports/{invoice_import_id}` : detail
- `POST /api/billing/invoices/imports` : upload + analyse
- `POST /api/billing/invoices/imports/{invoice_import_id}/analyze` : relancer l'analyse
- `PATCH /api/billing/invoices/imports/{invoice_import_id}/decision` : decision utilisateur
- `DELETE /api/billing/invoices/imports/{invoice_import_id}` : suppression

### Routes frontend utilisateur
- `/energie/factures` : liste des factures importees
- `/energie/factures/:invoiceImportId` : detail, controles et decision

### UI : `EnergieInvoicesPage` + `EnergieInvoiceDetailPage`
- `/energie/factures` contient déjà l'import manuel multi-fichiers, les KPI de revue, la liste facture, les statuts de contrôle et les décisions.
- La liste principale expose le titulaire du contrat lu dans les PDF ENGIE afin de distinguer les factures Ville / Agglomération lors de la revue.
- Les filtres de revue couvrent le titulaire, le statut de contrôle, la décision, le regroupement et les catégories/types de problèmes issus du rapport de contrôle.
- Un rapport fournisseur éditable est construit depuis les factures filtrées avec synthèse des points à clarifier, périmètre retenu et sortie imprimable en PDF.
- Le bloc `Lots d'import` est replié par défaut pour garder la revue des factures prioritaire lorsque le lot historique contient plusieurs dizaines de PDF.
- `/energie/factures/:invoiceImportId` contient déjà l'identité facture, le résumé simple, les familles de contrôle, les PRM/FIC, les lignes extraites et le commentaire de décision.
- Le chantier d'historique ENGIE doit prolonger cette expérience, pas créer un deuxième module facture.

## Historique ENGIE PDF avant API

Un premier lot réel de **83 PDF ENGIE** est disponible dans `saas/energie/ENGIE/FACTURES`.

Stratégie retenue :
- PDF manuel maintenant pour constituer l'historique et qualifier le moteur ;
- import par lot persistant depuis `/energie/factures` afin de suivre doublons, erreurs et factures à revoir ;
- modèle facture normalisé indépendant de la source ;
- API ENGIE ensuite vers le même pipeline de normalisation, contrôle et décision.

La V1 reste centrée sur ENGIE électricité. Le lien fin facture → PRM → compteur → bâtiment viendra avec le chantier de rattachement compteurs ; il ne doit pas bloquer l'intégration de l'historique financier et tarifaire.

Point de revue ajouté le 2026-05-21 : le libellé brut `Titulaire du contrat` est conservé et filtrable. Si la valeur doit devenir un axe analytique stable au-delà des libellés ENGIE, prévoir ensuite une normalisation explicite du type de porteur (`ville`, `agglomeration`, `autre`) sans perdre la valeur source.

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
- Probablement le même parser que pour la conso (cf. [[Modules/Energie-Consommation]] section SUEZ)
- Une facture eau contient consommation + tarif + total → les 3 ingrédients pour l'audit

## Workflow audit de facture (générique)

```
1. Utilisateur upload PDF/Excel facture sur /energie/factures
2. POST /api/billing/invoices/imports → EnergyInvoiceImport.status = "analyzing"
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

- [[Modules/Energie-BPU]] — Source des prix attendus
- [[Modules/Energie-Preconisations]] — Calcul prix unitaires
