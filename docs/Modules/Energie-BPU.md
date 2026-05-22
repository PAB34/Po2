# Module — Énergie / BPU (Bordereaux de Prix Unitaires)

> Suivi temporel des prix d'achat via marchés Hérault Énergies : électricité historique et référence gaz TotalEnergies lot 7.

## Statut

✅ **Pipeline complet en prod** depuis PR #12 (2026-05-19) — Phases 1, 2, 3, 4 livrées.
🟡 **Parser fin à améliorer** — 16/17 PDFs en `ocr_review` (peu de prix extraits).

## La formule de tarification

Identique à celle déjà utilisée par `/energie/preconisations` (table `BillingBpuLine`) :

```
PU_total (€HTT/MWh) = PU_fourniture + PU_capacité + PU_CEE + PU_GO
```

Par tranche tarifaire TURPE × poste horosaisonnier.

### Composantes
| Code | Label | Description |
|---|---|---|
| `fourniture` | Fourniture | Prix de l'énergie pure facturée par EDF/ENGIE. Volatile, suit le marché de gros. |
| `capacite` | Capacité | Mécanisme de capacité — droit à soutirer en pointe. Fixé par RTE annuellement. |
| `cee` | CEE | Certificats d'Économies d'Énergie — obligation réglementaire du fournisseur. |
| `cee_precarite` | CEE précarité | Composante gaz distincte quand le BPU la sépare du CEE classique. |
| `cpb` | CPB | Composante gaz exposée par le BPU lot 7. |
| `go` | Garanties d'Origine | Option Renouvelable — surcoût pour énergie verte certifiée. |

### Segments TURPE
| Code | Label |
|---|---|
| CU | Courte Utilisation (BT ≤ 36 kVA, base) |
| LU | Longue Utilisation (BT ≤ 36 kVA, base) |
| CU4 | Courte Utilisation 4 plages (HPH/HCH/HPE/HCE) |
| MU4 | Moyenne Utilisation 4 plages |
| MUDT | Moyenne Utilisation Double Tarif (HP/HC) |
| C4 | BT > 36 kVA 4 plages |
| C2 | HTA 5 plages (Pointe + 4 plages) |
| EP | Éclairage Public |
| T1/T2/T3/T4 | Profils gaz lot 7 selon le niveau annuel de consommation |

### Postes horosaisonniers
BASE, POINTE, HPH (heures pleines hiver), HCH, HPE (été), HCE, HP, HC

## Schéma SQL

5 tables normalisées (migration `0015_add_bpu_tables`) :

```
bpu_documents (1) ─┬── (N) bpu_segments       (tension/site/usage)
                   │       │
                   │       └── (N) bpu_time_periods   (Base/HPH/HCH/...)
                   │              │
                   │              └── (N) bpu_price_components  (Fourniture/Capacité/CEE/GO)
                   │
                   └── (N) bpu_fixed_charges  (abonnements, branchement provisoire, etc.)
```

### Clé unique sur `bpu_documents`
`(supplier, valid_year, market_subsequent, lot_number, amendment_number)` — empêche les doublons sur ré-import.

### Statuts d'extraction (`bpu_documents.extraction_status`)
- `ok` : parser pdftotext a réussi (BPU textuels modernes)
- `ocr_ok` : OCR tesseract a réussi avec confiance ≥ 0.55
- `ocr_review` : OCR a tourné mais confiance < 0.55 → revue manuelle
- `manual` : saisie manuelle (fallback)
- `pending` / `error`

## Pipeline d'ingestion

`saas/backend/app/services/bpu.py` (~700 lignes)

### Référence gaz lot 7

Le fichier `saas/energie/HERAULT ENERGIE/BPU_2026_Lots_1_2_et_7.xlsx` contient la feuille `Lot 7 - Gaz`.

- import ciblé : `python -m app.scripts.import_bpu_gas_lot7 --xlsx "<chemin du xlsx>"` ;
- fournisseur stocké : `TOTALENERGIES`, lot `7`, année `2026` ;
- segments : profils `T1`, `T2`, `T3`, `T4` ;
- composantes : fourniture ferme, CEE classique, CEE précarité, CPB, GO ;
- observation source conservée : les CEE de janvier-février 2026 sont provisoires puis révisables/régularisables.

Cette référence sert au futur audit factures gaz TotalEnergies des PCE Ville. Elle ne doit pas être confondue avec la cotation gaz OS3 du P1 DALKIA documentée dans `docs/energie/CPE-DALKIA/12-OS3-Prix-gaz.md`.

```
1. parse_filename_metadata(filename)
     → extrait supplier/year/MS/lot/avenant via regex sur le nom de fichier
2. extract_text_pdftotext(pdf_path)
     → essai rapide avec poppler. Si texte trop pauvre :
3. extract_text_ocr(pdf_path) via pdf2image + pytesseract -l fra
     → 300 DPI, mode PSM 6 (uniform block of text)
4. parse_bpu_text(text, metadata, method)
     → segments via regex TURPE (C1-C5, BT, HTA, usage)
     → postes via _detect_period
     → composantes via _extract_components_from_line (mot-clé → prix)
5. persist_parsed_bpu(session, parsed, ...)
     → idempotent (find_existing_document avant insert)
     → force=True remplace tout via cascade DELETE
```

### Confidence calculée
Heuristique sur le nombre de composantes extraites :
- 0 composante → 0.0
- < 5 → 0.25
- 5-19 → 0.55
- 20-49 → 0.75
- ≥ 50 → 0.90

## API REST

`saas/backend/app/api/routes/bpu.py`

| Route | Description |
|---|---|
| `GET /api/bpu/formula` | Définition formule + nomenclature segments/postes/composantes |
| `GET /api/bpu/documents` | Liste filtrable (supplier/year/lot/MS/status) |
| `GET /api/bpu/documents/{id}` | Détail complet avec segments + composantes + frais fixes |
| `DELETE /api/bpu/documents/{id}` | Admin |
| `GET /api/bpu/timeline` | Série temporelle pour graphique (filtres composante/poste/segment/supplier/lot) |
| `POST /api/bpu/import` | Re-déclenche l'ingestion (admin) |

## Frontend

- **Page** : `/energie/bpu` → `EnergieBpuPage.tsx`
- **Composant graphique** : `BpuTimelineChart.tsx` — Recharts LineChart, 1 ligne par composante, optionnellement courbe `PU_total` en gras
- **Filtres UI** : segment / poste / supplier / lot (séparés des filtres "liste documents")

## État des données en prod (2026-05-19)

| Métrique | Valeur |
|---|---|
| BPU stockés | 15 (sur 17 fichiers source) |
| Erreurs (métadonnées) | 1 (`BPU 2024 LOT 3 Elec.pdf` — supplier indétectable) |
| Doublons clé unique | 1 (LOT3 V2 vs LOT3 sans V2 ont même identité) |
| Segments | 18 |
| Postes | 3 |
| Composantes prix | 4 ← **Très faible**, parser à améliorer |

## Chantiers ouverts

### A. Améliorer le parser (priorité)
**Problème** : le parser regex matche mal les tableaux multi-colonnes des BPU (chaque ligne contient 4-5 composantes alignées en colonnes que pdftotext rend en concatenation difficile à parser).

**Phase 1 + 2 en cours** : voir [[Chantiers/PO2-BPU-001-Parser-BPU-fiable]]. Le parser sait maintenant memoriser un en-tete de tableau (`Fourniture / Capacite / CEE / GO`), mapper les montants des lignes suivantes vers les bonnes composantes, puis tenter une extraction cellule par cellule avec `pdfplumber` cote backend.

**Solution en cours de validation** : utiliser `pdfplumber` qui détecte les tableaux et retourne directement les cellules.

```python
# Pseudo-code
import pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        for table in page.extract_tables():
            # table = liste de listes de strings
            # Identifier les en-têtes (Fourniture, Capacité, CEE, GO)
            # Mapper chaque ligne (segment, poste) → prix par colonne
```

**Localisation** : `saas/backend/app/services/bpu.py` `_extract_segments` ≈ ligne 350.

**Important** : garder le pipeline pdftotext+OCR comme fallback, et `raw_text` toujours stocké pour re-parsing futur.

### A.1 Mesurer la qualite d'import apres reparse

Un script de diagnostic DB a ete ajoute :

```bash
python -m app.scripts.report_bpu_import_quality --min-components 20
```

Il affiche :
- total documents / segments / postes / prix unitaires ;
- repartition par statut d'extraction ;
- nombre de prix par BPU ;
- liste des documents sous le seuil attendu.

Commande cible apres rebuild backend :

```bash
python -m app.scripts.import_bpu_documents --source-dir "/workspace/saas/energie/HERAULT ENERGIE/HISTORIQUE BPU" --force --no-ocr
python -m app.scripts.report_bpu_import_quality --min-components 20
```

### B. UI de saisie corrective pour `ocr_review`
Quand un BPU est en `ocr_review`, l'utilisateur devrait pouvoir saisir manuellement les prix via l'UI :
- Bouton "Saisir manuellement" sur `/energie/bpu/{id}`
- Formulaire pré-rempli avec ce que l'OCR a sorti
- Validation → upsert dans `bpu_price_components` + statut → `manual`

### C. Croisement avec factures
Quand le parser fonctionnera mieux, brancher l'audit factures :
- Pour chaque ligne de `EnergyInvoiceAnalysis`, chercher le `BpuPriceComponent` applicable
- Calculer l'écart prix facturé vs BPU
- Voir [[Modules/Energie-Facturation]]

### D. Seed prix 2026 depuis `bpu_templates.py`
Le fichier `services/bpu_templates.py` contient des prix 2026 saisis en dur (lot 1 et lot 2). Au lieu d'attendre que le parser sorte ces prix du PDF, on peut ingérer directement la donnée structurée. À envisager comme amorçage rapide.

## Fichiers clés

- `saas/backend/app/models/bpu.py` (492 lignes)
- `saas/backend/app/schemas/bpu.py` (199 lignes)
- `saas/backend/app/services/bpu.py` (~700 lignes)
- `saas/backend/app/scripts/import_bpu_documents.py` (CLI)
- `saas/backend/app/api/routes/bpu.py`
- `saas/backend/alembic/versions/0015_add_bpu_tables.py`
- `saas/frontend/src/pages/EnergieBpuPage.tsx`
- `saas/frontend/src/components/BpuTimelineChart.tsx`
- Section BPU de `saas/frontend/src/lib/api.ts` (lignes ≈ 1744-1960)
