# 007 — Stratégie BPU : schema-on-read (CSV manuel) plutôt que parser automatique

> **Statut** : Accepté
> **Date** : 2026-05-19
> **Décideur(s)** : PAB34 + IA (Claude Sonnet 4.5)
> **Session liée** : [[Sessions/2026-05-19 — Outillage schema-on-read BPU]]

## Contexte

Sur 17 PDFs de BPU à ingérer dans Po2 (marchés Hérault Énergies 2021-2026), les multiples itérations du parser automatique (regex naïf → pdfplumber → parser EDF pivoté) ont permis d'extraire seulement **65 prix sur 2 BPU complets**, soit ≈ 12 % de la donnée cible.

L'audit `pdfplumber` montre que :
- 3 PDFs ont des tables natives détectables → parser OK pour 2/3, partiel pour le 3e
- 1 PDF a une structure atypique non reconnue par le parser EDF (LOT2 av5 31×6)
- **12 PDFs** sont des scans purs sans aucun caractère de texte natif (0-13 chars) → tesseract ressort du bruit ininterprétable

Continuer à itérer sur le parser donnerait un ROI très faible : preprocessing image + OCR avancé est très incertain (les scans EDF 2021-2024 sont visiblement des photocopies de documents signés, qualité dégradée), et même en améliorant marginalement on parsera peut-être 1-2 PDFs de plus.

## Décision

**Pivot d'approche** : abandonner provisoirement le parser PDF automatique au profit d'une stratégie **schema-on-read** :

1. Chaque PDF est analysé **un par un** (humain ou IA Vision selon disponibilité) en remplissant le template `docs/Templates/Analyse-BPU-PDF.md`
2. Les données extraites sont consignées dans **2 CSV** versionnés :
   - `saas/backend/data/bpu_documents.csv` : 1 ligne par BPU (métadonnées : supplier, year, MS, lot, avenant, dates, signataire)
   - `saas/backend/data/bpu_lines.csv` : 1 ligne par mesure (prix unitaire ou frais fixe)
3. Un script déterministe `python -m app.scripts.import_bpu_csv` ingère ces CSV dans la BDD (statut `extraction_status='manual'`)
4. Lorsqu'un nouveau PDF révèle des champs / composantes / segments **non couverts** par le schéma actuel → on adapte les constantes (`COMPONENT_TYPES`, `PERIOD_CODES`, `SEGMENT_TYPES`) ou les colonnes des tables et on relance l'import

Le parser PDF automatique (`services/bpu.py`) reste en place mais passe en chantier `En pause` (`PO2-BPU-001`). Il pourra être réactivé après la phase manuelle si on identifie un sous-ensemble de PDFs où l'automatisation a un ROI clair.

## Conséquences

### Positives
- **Données fiables à 100 %** sur les BPU saisis manuellement (vs ≈ 80 % de fiabilité estimée sur le parser auto, avec validation humaine nécessaire de toute façon)
- **Évolution incrémentale du schéma** : on découvre les vrais besoins du modèle au fil des PDFs au lieu de tout prévoir d'avance
- **Effort raisonnable** : 17 PDFs × ~20 min d'analyse = ~6 h de travail réparti (vs des jours d'itération sur l'OCR avec gain incertain)
- **CSV versionné** : l'historique git devient le journal des évolutions de la donnée — auditable
- **Compatible avec l'existant** : le schéma SQL 5 tables (cf. [[Decisions/002-bpu-schema-normalise-5-tables]]) est déjà conçu pour absorber l'élargissement progressif
- **Réutilisable pour DALKIA, TOTAL, SUEZ et autres fournisseurs** futurs si le pattern marche

### Négatives / coûts assumés
- **Charge humaine** : ~6 h d'analyse à fournir (mais réparties, et peuvent être déléguées à une IA Vision)
- **Pas d'automatisation pour les nouveaux BPU futurs** : chaque BPU à venir devra repasser par l'analyse manuelle (à moins que le parser auto soit relancé sur les PDFs textuels modernes)
- **Risque de drift entre PDFs sources et CSV** : si quelqu'un édite le CSV sans toucher au PDF, l'historique git devient la source de vérité

### Alternatives écartées
- **OCR avancé** (preprocessing image, paddleocr, modèles Vision) : gain trop incertain pour le ROI (2-3h dev pour potentiellement 0 résultat sur les 9 PDFs avec 0 char de texte)
- **UI saisie manuelle assistée intégrée à Po2** (formulaire avec aperçu PDF) : ~4-5h dev pour reproduire ce qu'Excel/un éditeur CSV fait déjà nativement. À garder en option future si l'utilisateur veut une UX intégrée.
- **API LLM Vision (Claude, GPT-4V)** : pourrait extraire la donnée mais coûteux à l'usage, dépendance externe, et reste à valider manuellement de toute façon. L'utilisateur peut s'en servir comme outil d'analyse en amont du CSV s'il le souhaite.

## Outils livrés

| Outil | Chemin | Rôle |
|---|---|---|
| Source canonique | `saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/extraction_tarifs_electricite_BPU.xlsx` | Fichier xlsx d'extraction manuelle assistée IA (5 onglets : Synthese, Prix_detailles 173 lignes, Surcouts_fixes 9 lignes, Sources_PDF 17 lignes, Controle_qualite 6 points). Reste **local et SCP-uploadé** sur le VPS, gitignored car *.xlsx. |
| Script d'import | `saas/backend/app/scripts/import_bpu_xlsx.py` | Lit directement le xlsx via pandas, mappe les 3 onglets vers `BpuDocument` / `BpuSegment` / `BpuTimePeriod` / `BpuPriceComponent` / `BpuFixedCharge`. Idempotent, `--force` pour reset. Gère les unités (HTT/HTVA), les codes verbeux (HPH/HCH avec libellés français), les doublons volontaires (PDF V2 + Annexe AE pour les marchés 2021-2022). Statut d'extraction = `manual`. |
| Template d'analyse PDF | `docs/Templates/Analyse-BPU-PDF.md` | Grille structurée optionnelle pour les **futurs BPU** qui arriveront (autres fournisseurs, années suivantes). Plus indispensable pour l'historique 2021-2026 (déjà couvert par le xlsx canonique). |

## Prochaine étape — UI tableau éditable

La donnée étant maintenant ingérée en BDD, la suite est de la rendre **éditable depuis le frontend** (sous-onglet dans `/energie/bpu`, style Excel cliquable + save par bouton). Chantier ouvert dans le Backlog (`PO2-BPU-003`).

## Liens

- [[Backlog]] — `PO2-BPU-002 Analyse PDF par PDF + ingestion CSV manuelle`
- [[Modules/Energie-BPU]] — Module BPU et son contexte technique
- [[Decisions/002-bpu-schema-normalise-5-tables]] — Le schéma SQL qui absorbe l'évolution
- [[Sessions/2026-05-19 — Phase 2 BPU finalisee (parser EDF pivote)]] — Session qui a clos la phase parser auto
