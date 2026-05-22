# 2026-05-22 — Import XLSX ENGIE « Mes Factures »

tags: #énergie #factures #engie #xlsx #import

> Page concernée : `/energie/factures` → nouveau panneau **« Import export ENGIE (XLSX) »**
> Fichier type : `MesFactures_YYYYMMDDHHMMSS.xlsx` exporté depuis l'espace ENGIE Entreprise.

---

## Pourquoi

Le parser PDF ENGIE marche mais souffre de :
- variations de mise en page entre modèles de facture
- OCR/extraction de texte parfois bruitée
- regex fragile sur les libellés (HCH/HPH/postes saisonniers)

L'export XLSX ENGIE est **structuré** : 159 colonnes par segment tarifaire avec
les valeurs exactes (consommations, prix unitaires, montants, taxes, index
relevés). Sur un seul fichier on récupère **jusqu'à 1 an d'historique**
multi-sites avec une fiabilité bien supérieure au parsing PDF.

Sur l'exemple fourni (`saas/energie/ENGIE/EXPORTS/MesFactures_20260522150740.xlsx`) :
- 6 feuilles : Gaz (vide), C2 sur index, C2 sur courbe (vide), C3 (vide), C4, C5
- 1 069 lignes de données → **144 bordereaux uniques**, 1 069 FIC, 268 sites
- 3 segments tarifaires couverts (C2 index : 11 sites, C4 : 56 sites, C5 : 201 sites)

---

## Architecture

```
Frontend                              Backend
────────                              ─────────
[Upload .xlsx]
     │
     ▼
uploadEngieXlsxExport(token, file)
     │  POST /api/billing/invoices/imports/xlsx
     ▼
                               ┌── route billing.py
                               │   upload_engie_xlsx_export()
                               ▼
                  engie_xlsx_import.import_engie_xlsx()
                               │
                               ├── _persist_file()           ← stocke le XLSX une seule fois
                               ├── parse_engie_xlsx()        ← engie_xlsx.py
                               │     └─ list[parsed_bordereau]
                               │         (1 entrée par n° FMC/FUM/Bordereau)
                               │
                               └── pour chaque bordereau :
                                     ├─ dédup invoice_number en base ?
                                     │   → oui : skip + trace doublon
                                     │   → non : créer EnergyInvoiceImport
                                     │           + apply_parsed_to_invoice_import()
                                     │             └─ pipeline standard
                                     │                (BPU + TURPE + taxes + périodes)
```

L'astuce clé : `apply_parsed_to_invoice_import()` factorise la partie
« contrôles + persistance » de `analyze_invoice_import()`. PDF et XLSX
partagent désormais la même finalisation — l'analyse aval (BPU, TURPE, etc.)
est strictement identique.

---

## Parser XLSX — `services/invoice_parsers/engie_xlsx.py`

### Conventions ENGIE → Po2

| ENGIE colonne | Po2 champ |
|---|---|
| `N° FMC/FUM/Bordereau` (col 4) | `invoice_number` |
| `N° Facture ou Avoir` (col 1) | `fic_number` (équivalent FIC PDF) |
| `PCE/PDL` (col 21) | `prm_id` |
| `Libellé du CCC` (col 7) | `regroupement` |
| `Raison Sociale Payeur` (col 10) | `contract_holder` |
| `Tarif d'acheminement` (col 26) | `tariff_option_label` |
| `Version d'Utilisation` (col 27) | `tariff_code` (CU/LU/MU…) |
| `Segment distributeur` (col 25) | `segment` (C2/C3/C4/C5) |
| `Consommation X` + `Prix unitaire X` + `Montant facturé X` | une ligne facture supply par poste |
| `Quantité capacité X` + `Prix capacité X` + `Montant capacité X` | une ligne capacity par poste |
| `Contribution CEE / CEE CLASSIQUES / CEE PRECARITE` | lignes cee (3 sous-types) |
| `Electricité d'origine renouvelable` | ligne green_energy |
| `Composante de gestion` | ligne network_management |
| `Composantes de comptage` | ligne network_counting |
| `Composante de Soutirage part fixe` | ligne network_withdrawal |
| `Composante de Soutirage - part variable X` | ligne network_variable par poste |
| `CSPE / TICFE / CTA / taxes communales-départementales` | lignes taxes |

### Conversion postes XLSX → BPU

ENGIE distingue les postes HPB/HCB (basse saison) alors que la convention BPU
utilise hpe/hce (été). Mapping :

```python
POSTE_XLSX_TO_BPU = {
    "BASE": "base", "HP": "hp", "HC": "hc",
    "HPH": "hph", "HCH": "hch",
    "HPB": "hpe", "HCB": "hce",
}
```

### Variations entre feuilles

128 colonnes communes sur les 3 feuilles actives (C2 idx / C4 / C5). Spécifiques :
- **C2 sur index** : énergie réactive, dépassement quadratique (énergie réactive)
- **C5** : postes BASE/HP/HC sans saison (les compteurs basse tension < 36 kVA n'ont souvent pas la distinction haute/basse saison)
- **C4** : dépassement durée en heures

Le mapping par **nom de colonne** (non par index) gère ces variations
transparentement — les colonnes absentes produisent simplement des lignes vides.

---

## Dédoublonnage

À chaque bordereau parsé, requête :
```sql
SELECT id, source FROM energy_invoice_imports
WHERE city_id = :city AND invoice_number = :bordereau_id LIMIT 1;
```

Si trouvé → skip + trace dans `duplicates_detail`. La logique est volontairement
simple : un n° de bordereau ENGIE est unique par fournisseur. Pas de fenêtre
temporelle ni de hash de contenu — un PDF déjà importé + son XLSX seront
parfaitement dédoublonnés.

---

## Sortie de l'endpoint

```json
{
  "source": "engie_xlsx_export",
  "filename": "MesFactures_20260522150740.xlsx",
  "total_bordereaux": 144,
  "created": 130,
  "duplicates": 12,
  "errors": 2,
  "imports": [
    {"id": 1234, "invoice_number": "150000066930", "control_status": "review", "site_count": 1, "total_ttc": 62.38},
    ...
  ],
  "duplicates_detail": [
    {"invoice_number": "150000058810", "existing_import_id": 987, "existing_source": "manual_upload"},
    ...
  ],
  "errors_detail": [
    {"invoice_number": "...", "message": "..."}
  ]
}
```

Le frontend affiche le résumé compact dans le panneau d'upload.

---

## Limitations connues (V1)

- **Gaz exclu** : la feuille gaz n'est pas parsée. Le module CPE DALKIA gère
  déjà le gaz avec son BPU lot 7 dédié. À traiter dans une V2 si besoin
  d'analyse fournisseur gaz hors-CPE.
- **Compatibilité PDF/XLSX** : un bordereau qui existe à la fois en PDF
  (déjà importé) et en XLSX (nouveau import) garde sa version PDF. Si la
  version XLSX est plus structurée et qu'on veut l'utiliser, il faut
  supprimer manuellement la version PDF d'abord. Pas de bascule automatique
  pour ne pas écraser l'historique de décision utilisateur.
- **Test non exécuté localement** : l'environnement de dev (Windows
  entreprise) restreint Python, le parser n'a pas été exécuté localement.
  Premier test à faire sur la prod : importer le fichier exemple et
  vérifier les `mismatches_detail` BPU produits.

---

## Trajectoire

1. **API ENGIE Entreprise (Maileva ?)** : à terme, remplacer l'upload XLSX
   manuel par un fetch automatique périodique de l'export. Mêmes étapes
   downstream (parser → finalize) → effort UI ~zéro.
2. **Gaz** : ajouter le parsing de la feuille Gaz quand on aura besoin du
   contrôle BPU lot 7 sur les factures TotalEnergies hors-CPE.
3. **Index relevés** : les colonnes 145-159 contiennent ancien/nouvel index
   par poste. À exploiter pour un contrôle « cohérence index ↔ consommation »
   indépendant de la cohérence ENEDIS courbe de charge.

---

## Voir aussi

- [[Modules/Energie-Facturation]] — module facturation (à mettre à jour avec ce nouveau pipeline)
- [[Sessions/2026-05-22 — Rapport fournisseur agrégat et recalcul BPU]] — moteur de contrôle BPU réutilisé tel quel
- [[Sessions/2026-05-21 — Historique factures ENGIE]] — première implémentation parsing PDF
