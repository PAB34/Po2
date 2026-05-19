# 2026-05-19 — Phase 2 BPU finalisée : parser EDF pivoté

> IA : Claude Sonnet 4.5
> Durée : ~1h
> Précédente session : [[Sessions/2026-05-19 — Logs diagnostic FTP-ENEDIS]]

## 🎯 Objectif de la session

[[Backlog]] `PO2-BPU-001` : valider la Phase 2 `pdfplumber` (déjà committée par l'utilisateur via `af69e93`) sur la prod, mesurer le gain réel d'extraction par rapport au baseline de 4 prix unitaires, et patcher si nécessaire pour débloquer davantage de BPU.

## ✅ Ce qui a été fait

### Chantier 1 — Validation Phase 2 initiale (commit `af69e93`)

Re-import `--force` des 17 PDFs en prod, comparaison avec baseline.

| Mesure | Baseline (regex naïf) | Phase 2 initiale | Gain |
|---|---|---|---|
| Composantes prix | 4 | 36 | ×9 |
| BPU "OK" | 0 | 1 (ENGIE 2025 LOT1) | +1 |

→ Phase 2 fonctionne **uniquement** sur les PDFs textuels avec tables structurées (ENGIE). Les 3 BPU EDF 2025 textuels (avenants 5/6) restent à 0 prix malgré leur structure tabulaire native.

### Chantier 2 — Diagnostic : pourquoi EDF 2025 textuels échouent

POC sur 3 PDFs EDF 2025 avenants → pdfplumber détecte **9, 1 et 4 tables natives** parfaitement structurées (libellés sites + postes + unités + prix). Le problème est ailleurs.

**Cause racine 1** (corrigée par commit `2c7d6ef`) : la pipeline `import_pdf` testait `_looks_textual` sur le texte pdftotext **avant** de tenter pdfplumber. Comme pdftotext rend mal les BPU EDF (texte bruité, lots de symboles `[os | se [os [os`), le test échouait et la pipeline basculait en OCR → l'OCR ressort encore plus de bruit → pdfplumber ne trouve rien.

Patch : appeler `extract_segments_pdfplumber` **avant** la décision OCR. Si pdfplumber sort des prix exploitables, on évite l'OCR.

**Effet du commit `2c7d6ef`** : ENGIE 2025 passe de `tesseract+pdfplumber` à `pdftotext+pdfplumber` (plus rapide). EDF 2025 avenants restent à 0 prix → le problème n'est pas seulement dans la pipeline, mais aussi dans le parser.

**Cause racine 2** (corrigée par commit `ca6f92b`) : `extract_segments_pdfplumber` ne reconnaît qu'**un seul layout de table** :

| Layout ENGIE (déjà géré) | Layout EDF (pas géré) |
|---|---|
| Header = composantes (Fourniture / Capacité / CEE / GO) | Header = postes (Pointe / HPH / HPE / HCH / HCE) |
| Lignes = postes | Lignes = composantes (Electricité, CEE, Mécanisme de capacité, Option Energie renouvelable) |

Exemple table EDF 2025 LOT1 avenant 6, Sites C2 :
```
R1: ['Sites C2', 'Pointe', 'HPH', 'HPE', 'HCH', 'HCE']
R3: ['Electricité', '8,447', '8,447', '8,447', '8,447', '8,447']
R4: ['CEE (...)', '0,628', None, None, None, None]
R5: ['Mécanisme de capacité', '0,070', '0,070', '0,070', '0,070', '0,070']
R6: ['Option Energie renouvelable', '0,231', None, None, None, None]
```

Patch : nouveau parser `_parse_edf_pivoted_table` + helper `_detect_edf_component_in_row_label` (mappe "Electricité"→fourniture, "CEE"→cee, "Mécanisme de capacité"→capacite, "Option Energie renouvelable"→go). Le parser est appelé en premier sur chaque table par `extract_segments_pdfplumber` ; si le pattern EDF n'est pas reconnu, fallback sur le parsing ligne par ligne (layout ENGIE).

### Chantier 3 — Validation finale après les 2 patches

| Mesure | Baseline | Après `af69e93` | Après `2c7d6ef` | Après `ca6f92b` |
|---|---|---|---|---|
| Composantes prix | 4 | 36 | 36 | **65** |
| Postes | 3 | 20 | 20 | 37 |
| BPU "OK" | 0 | 1 | 1 | **2** |

**Le gagnant** : `EDF_MS1_LOT_1_AVENANT_6_BPU_2025.pdf` passe de 0 → **26 prix, confidence 0.75, méthode `pdftotext+pdfplumber`**.
`EDF_MS1_LOT_3_AVENANT_5_BPU_2025.pdf` extrait 3 prix partiels (reste en `ocr_review`).

### Commits poussés sur main

| Commit | Sujet | Effet |
|---|---|---|
| `2c7d6ef` | `feat(bpu): tenter pdfplumber direct avant la decision OCR` | ENGIE passe sans OCR, gain de performance, pas de gain en prix |
| `ca6f92b` | `feat(bpu): parser EDF pivote (postes en colonnes, composantes en lignes)` | +29 prix sur EDF 2025 avenants, 2e BPU complet |

## 🚧 Ce qui reste à faire / handoff

Phase 2 BPU n'est pas "terminée" au sens 100% — il reste 2 catégories de PDFs à traiter :

### Priorité A — EDF 2025 LOT2 avenant 5 (structure 31×6 atypique)

Ce PDF a **1 seule grande table** de 31 lignes × 6 colonnes au lieu de plusieurs tables comme LOT1/LOT3. Le parser EDF actuel cherche un header `Sites Cx + codes postes` sur une ligne unique — peut-être qu'ici les libellés s'étalent sur plusieurs lignes. À investiguer :

```bash
ssh -i ~/.ssh/po2_vps2 ubuntu@135.125.152.112 "docker exec infra-backend-1 python -c \"
import pdfplumber
fname = '/workspace/saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/EDF_MS1_LOT_2_AVENANT_5_BPU_2025.pdf'
with pdfplumber.open(fname) as pdf:
    for table in pdf.pages[0].extract_tables() or []:
        for r in table:
            print(r)
\""
```

### Priorité B — 12 scans EDF 2021-2024 (OCR-only)

Tous les BPU EDF antérieurs à 2025 (2021-2024) sont des **PDFs scannés** dont l'OCR tesseract ressort du bruit. Aucune voie pdfplumber possible. Options :

1. **Saisie manuelle assistée** : UI dans Po2 pour saisir les prix avec aperçu du PDF côte-à-côte → fiable mais long (~3-4h dev + 30 min/PDF × 12 = ~10h utilisateur)
2. **OCR avancé** : preprocessing image (déskew, denoise, binarize), DPI 600, `--psm 4` (table mode), ou modèle paddleocr/Google Vision → ~2-3h dev, gain incertain
3. **Accepter la limite** : ces 12 BPU resteront en `ocr_review` indéfiniment, leur `raw_text` est stocké pour re-parsing futur si un meilleur OCR émerge

### Côté utilisateur — Pending validations externes

Aucun bloquant côté utilisateur. ENEDIS reste en pause (1753 fantômes, cf. session précédente).

## 📝 Notes & décisions

- **Pas de nouvelle ADR** : on a juste appliqué un pattern technique standard (reconnaître plusieurs layouts de tables avant de tomber en fallback).
- **Données extraites validées** : sample CU/BASE/fourniture = 75.29 (depuis ENGIE 2025) correspond exactement à la valeur hard-codée `bpu_templates.py:20`. Donc l'extraction est **numériquement correcte**, pas juste "quantité de valeurs".
- **Choix d'architecture confirmé** : le schéma 5 tables (cf. [[Decisions/002-bpu-schema-normalise-5-tables]]) permet désormais des requêtes timeline réelles sur 2 BPU complets (ENGIE 2025 + EDF 2025 LOT1 av6). L'UI `/energie/bpu` devrait afficher des courbes non triviales.

## 🔁 Pour la prochaine IA — entrée en matière

```
J'ai lu :
- docs/00-Index.md
- docs/07-Environnement-poste-entreprise.md
- docs/Backlog.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-05-19 — Phase 2 BPU finalisee (parser EDF pivote).md

Je sais que le poste utilisateur est verrouille entreprise : je ne demanderai aucune installation locale.

Le chantier PO2-BPU-001 a livre 65 prix sur 2 BPU OK (gain +1525% vs
baseline). Reste : EDF 2025 LOT2 av5 (structure 31x6 atypique) +
12 scans EDF historiques (OCR-only).

Pour la suite je peux :
- Continuer BPU : investigation EDF LOT2 av5 puis UI saisie manuelle
  pour les 12 scans
- Passer à PO2-FACT-001 : 2 BPU complets en BDD suffisent pour
  demarrer l'audit factures ENGIE
- Autre chantier P1 selon ton souhait (CVC/Enveloppe, baux locataires)

Quelle priorite veux-tu ?
```
