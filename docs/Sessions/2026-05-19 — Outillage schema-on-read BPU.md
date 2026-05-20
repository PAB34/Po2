# 2026-05-19 — Outillage schema-on-read BPU (préparation pour demain)

> IA : Claude Sonnet 4.5
> Durée : ~45 min
> Précédente session : [[Sessions/2026-05-19 — Phase 2 BPU finalisee (parser EDF pivote)]]

## 🎯 Objectif

Pivot d'approche sur le chantier BPU. Après la Phase 2 parser auto (gain limité à 65 prix sur 2 BPU complets, 12 scans EDF historiques inexploitables), l'utilisateur propose une stratégie **schema-on-read** : analyser chaque PDF un par un, consigner dans un CSV, ingérer en BDD via un script déterministe, et adapter le schéma au fil des découvertes.

Cette session prépare **tout l'outillage** pour qu'il puisse démarrer l'analyse demain sans friction.

## ✅ Ce qui a été fait

### 1. Décision formalisée
- **ADR** : [[Decisions/007-bpu-schema-on-read-vs-parser]]
- Justifie le pivot, liste les alternatives écartées (OCR avancé, UI saisie manuelle intégrée, LLM Vision), explicite les conséquences positives et coûts assumés.

### 2. Template d'analyse PDF
- **Fichier** : `docs/Templates/Analyse-BPU-PDF.md`
- Sections obligatoires : Identification document, Segments tarifaires, Postes horosaisonniers, Composantes de prix, Frais fixes, Clauses spéciales, **Nouvelles découvertes**, Métriques d'analyse.
- Note : finalement non utilisé pour la 1ère vague (l'utilisateur a produit un xlsx d'extraction complet via une autre IA). Conservé pour les **futurs BPU** qui arriveront (ENGIE 2026 LOT 2/3, autres fournisseurs).

### 3. Pivot vers xlsx canonique
- L'utilisateur a livré en parallèle un fichier xlsx complet : `saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/extraction_tarifs_electricite_BPU.xlsx`
- 5 onglets : `Synthese` (KPI), `Prix_detailles` (173 lignes), `Surcouts_fixes` (9), `Sources_PDF` (17), `Controle_qualite` (6)
- Données numériquement validées (sample CU/BASE/fourniture 75.29 €/MWh matche `bpu_templates.py`)
- Les CSV stubs initialement prévus (`bpu_documents.csv` + `bpu_lines.csv`) ont été abandonnés au profit d'un script qui lit directement le xlsx.

### 4. Script d'ingestion xlsx (final)
- **Fichier** : `saas/backend/app/scripts/import_bpu_xlsx.py`
- **Usage** : `docker exec infra-backend-1 python -m app.scripts.import_bpu_xlsx --force`
- Idempotent (sauf `--force` qui reset).
- Reporte explicitement les codes inconnus (component_type / period_code / segment_type) → liste à ajouter dans `app/models/bpu.py` constants si pertinent.
- Statut d'extraction = `manual`, confidence = 1.0 (donnée saisie main, fiable par construction).
- Tolère "75,29" ou "75.29" pour les décimales, "2026-05-19" ou "19/05/2026" pour les dates.
- Ignore les lignes commentées (`#`) et les lignes vides.

### 5. Backlog mis à jour
- `PO2-BPU-001` (parser auto) → passe en `En pause`, priorité P2
- **Nouveau `PO2-BPU-002`** : "Analyse PDF par PDF + ingestion CSV manuelle", `Prêt à démarrer`, priorité P0

## 🚧 Pour demain — workflow recommandé

### Avant de commencer
1. Ouvre Obsidian sur le coffre `C:\Users\pa.borja\Documents\Po2`
2. Lis [[Decisions/007-bpu-schema-on-read-vs-parser]] pour avoir le contexte
3. Lis [[Templates/Analyse-BPU-PDF]] pour comprendre la grille de saisie

### Par PDF (×17)
1. Ouvrir le PDF (dans `saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/`)
2. Copier `docs/Templates/Analyse-BPU-PDF.md` → `docs/Templates/_analyses-completes/<nom-pdf-sans-extension>.md` (créer le dossier si besoin)
3. Remplir le template en lisant le PDF — soit toi-même, soit en demandant à une IA Vision de le faire
4. Reporter les lignes dans `saas/backend/data/bpu_lines.csv` :
   - 1 ligne par prix unitaire (segment × poste × composante)
   - 1 ligne par frais fixe
5. Si tu rencontres un **élément non couvert par le schéma** (nouvelle composante, nouveau poste, nouveau type de segment) → note-le en section "Nouvelles découvertes" du template, puis adapte :
   - `app/models/bpu.py` : ajouter au set correspondant (`COMPONENT_TYPES`, `PERIOD_CODES`, `SEGMENT_TYPES`)
   - Le script `import_bpu_csv.py` tolère les codes inconnus (les liste en warning) donc tu peux commencer la saisie même sans avoir mis à jour les constants — tu les ajoutes dans la foulée.

### Après chaque PDF (ou en fin de session)
6. Lancer l'ingestion en prod :
   ```bash
   ssh -i ~/.ssh/po2_vps2 ubuntu@135.125.152.112 \
     "docker exec infra-backend-1 python -m app.scripts.import_bpu_csv --force"
   ```
7. Vérifier le rapport (segments / postes / composantes / charges créés + codes inconnus à intégrer)
8. Aller sur https://patrimoineaucarre.com/energie/bpu pour voir le rendu (la timeline va s'enrichir)

### En fin de journée
9. `git add docs/ saas/backend/data/ && git commit -m "data(bpu): ..." && git push` pour propager le travail.

## 📝 Notes & décisions

- **Pourquoi 2 CSV séparés (documents + lines) au lieu d'un seul format long avec metadata répétées ?**
  Plus rapide à remplir (pas de redondance), plus simple à éditer dans Excel (1 onglet par type), plus lisible. Le script fait la jointure par `pdf_filename`.

- **Pourquoi conserver le parser auto en pause au lieu de le supprimer ?**
  1) Pour les BPU futurs (ENGIE 2026, autres fournisseurs) qui pourraient avoir une mise en page propice à pdfplumber, le parser auto reste un outil rapide.
  2) Le code parser est documenté et n'a pas de coût d'entretien tant qu'on n'y touche pas.

- **Pourquoi `extraction_status='manual'` et pas `ocr_review` pour les imports CSV ?**
  Une donnée saisie à la main par l'utilisateur ou validée par IA Vision est **plus fiable** qu'un OCR douteux. Le statut `manual` indique au reste du système qu'on peut faire confiance.

## 🔁 Pour la prochaine IA — entrée en matière

```
J'ai lu :
- docs/00-Index.md
- docs/07-Environnement-poste-entreprise.md
- docs/Backlog.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-05-19 — Outillage schema-on-read BPU.md
- docs/Decisions/007-bpu-schema-on-read-vs-parser.md
- docs/Templates/Analyse-BPU-PDF.md

Je sais que le poste utilisateur est verrouille entreprise : je ne demanderai aucune installation locale.

Le chantier PO2-BPU-002 est pret a demarrer : l'utilisateur va analyser les
17 PDFs un par un en remplissant le template et en completant les 2 CSV
saas/backend/data/bpu_*.csv. Je l'assiste pour :
- Lire un PDF specifique et extraire son contenu structure si demande
- Mettre a jour les constants app/models/bpu.py quand de nouveaux codes
  emergent
- Lancer `docker exec infra-backend-1 python -m app.scripts.import_bpu_csv --force`
  pour reporter le travail en BDD
- Verifier le resultat sur https://patrimoineaucarre.com/energie/bpu

Quel PDF veux-tu attaquer en premier ?
```
