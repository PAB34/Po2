# PO2-BPU-001 - Parser BPU fiable

> Statut : En cours
> Priorite : P0
> Module : [[Modules/Energie-BPU]]
> Contrainte : [[07-Environnement-poste-entreprise]] - aucune installation locale utilisateur

## Objectif

Exploiter l'historique complet des BPU electricite Hérault Energie charge dans `saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/`, afin de suivre l'evolution des tarifs d'achat en gros et d'alimenter ensuite :

- l'audit des factures ENGIE ;
- les ecarts prix facture vs prix attendu ;
- les preconisations chiffrees.

## Probleme constate

Le schema SQL et l'UI existent, mais le parser historique extrait trop peu de prix unitaires.

Cause principale : les BPU sont souvent des tableaux multi-colonnes. L'ancien parser ligne par ligne ne savait extraire une composante que si le mot-cle (`Fourniture`, `Capacite`, `CEE`, `GO`) et le prix etaient sur la meme ligne. Dans un tableau, les mots-cles sont souvent en en-tete, puis les lignes suivantes ne contiennent que le poste et les montants.

## Phase 1 - faite

Fichiers modifies :

- `saas/backend/app/services/bpu.py`
- `saas/backend/tests/test_bpu_parser.py`

Changements :

- detection d'en-tete de tableau `Fourniture / Capacite / CEE / GO` ;
- memorisation de l'ordre des composantes ;
- mapping des lignes suivantes `HPH 142,50 4,10 8,25 1,70` vers les composantes attendues ;
- detection plus fine des segments tarifaires : `CU4`, `MU4`, `MUDT`, `CU`, `LU`, `C1-C5`, `EP` ;
- preference pour l'option tarifaire (`CU4`) quand une ligne contient aussi la famille de tension (`BT <= 36 kVA`) ;
- tests unitaires ajoutes pour cette logique pure.

Validation locale possible :

- `python -m compileall saas/backend/app/services/bpu.py saas/backend/tests/test_bpu_parser.py` : OK.

Validation locale non possible :

- `pytest` indisponible sur le poste utilisateur ;
- `sqlalchemy` indisponible sur le poste utilisateur ;
- conforme a la contrainte zero installation locale.

## Phase 2 - implementee, a verifier en CI/conteneur/VPS

Fichiers modifies :

- `saas/backend/requirements.txt`
- `saas/backend/app/services/bpu.py`
- `saas/backend/app/scripts/report_bpu_import_quality.py`
- `saas/backend/tests/test_bpu_parser.py`

Changements :

- ajout de `pdfplumber==0.11.9` aux dependances backend ;
- extraction optionnelle des tableaux PDF via `pdfplumber.open(...).pages[].extract_tables()` ;
- lecture cellule par cellule des lignes BPU ;
- fusion des segments/prix extraits par `pdfplumber` avec ceux extraits par `pdftotext` ;
- fallback conserve : si `pdfplumber` est absent ou echoue, le pipeline `pdftotext/OCR` continue ;
- script de diagnostic DB ajoute pour mesurer la qualite apres import ;
- aucune installation locale utilisateur requise.

Source version dependance : PyPI indique `pdfplumber` version `0.11.9`, publiee le 2026-01-05.

Commandes de reference, a executer hors poste utilisateur :

```bash
cd saas/backend
pytest tests/test_bpu_parser.py
python -m app.scripts.import_bpu_documents --source-dir "/workspace/saas/energie/HERAULT ENERGIE/HISTORIQUE BPU" --force --no-ocr
python -m app.scripts.report_bpu_import_quality --min-components 20
```

Critere d'acceptation :

- augmentation nette du nombre de `bpu_price_components` ;
- plusieurs composantes par poste (`fourniture`, `capacite`, `cee`, `go`) ;
- moins de documents en `ocr_review` uniquement a cause d'un nombre de prix trop faible ;
- timeline `/api/bpu/timeline` exploitable sur plusieurs annees.

## Phase 3 - option si necessaire

Si la phase 2 reste insuffisante sur les PDFs historiques :

- ajouter des fixtures anonymisees issues des vrais BPU ;
- ajuster les heuristiques par fournisseur/lot/annee ;
- envisager une UI de saisie corrective pour les BPU restant en `ocr_review`.

## Risques

- Les tableaux BPU peuvent changer de structure selon EDF/ENGIE, lot, annee ou avenant.
- Certains PDFs scannes resteront dependants de l'OCR.
- Les lignes avec totaux ou notes peuvent contenir des nombres parasites ; les tests doivent couvrir les formats reels progressivement.
