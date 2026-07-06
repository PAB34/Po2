# Moteur métier « référentiels marchés » — trouvailles & historique

> Journal des découvertes de la session 2026-07-06 (mémoire durable). Complète le doc de décisions
> `moteur-metier-referentiels-decisions.md`, l'audit `moteur-metier-referentiels-marches-audit.md` et
> l'inventaire fidélité `moteur-metier-referentiels-fidelite-inventaire.md`.

## 1. Ce qui a été livré (en prod)
- **Hub central « Référentiels marchés »** (`/refonte-v1/referentiels`, section *Référentiels & admin*),
  qui **embarque les moteurs existants** (pas de réécriture) : 2 sous-onglets
  **DPGF DALKIA** (`CpeDalkiaImportPage`) + **BPU Hérault Énergies** (`EnergieBpuPage`, tous fournisseurs).
- PR #42 **mergée → prod** (2026-07-06). En-tête propre au hub retiré (les pages embarquées portent leur titre).
- Guard tests backend `saas/backend/tests/test_marches_referentiel_read.py` (contrat de lecture BPU élec + gaz).

## 2. Moteur d'historique BPU Hérault Énergies (important)
- **Source de vérité = un Excel d'extraction manuelle** :
  `saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/extraction_tarifs_BPU_herault.xlsx`
  (anciennement `extraction_tarifs_electricite_BPU.xlsx` — le script pointe encore l'ancien nom par défaut).
- **Script d'import** : `saas/backend/app/scripts/import_bpu_xlsx.py`. 5 onglets :
  `Synthese` (KPIs, ignoré) · `Sources_PDF` (1 ligne/PDF → `BpuDocument`) · `Prix_detailles`
  (~173 lignes wide → `BpuSegment`/`BpuTimePeriod`/`BpuPriceComponent`) · `Surcouts_fixes` (→ `BpuFixedCharge`) ·
  `Controle_qualite` (→ `extraction_notes`). Statut d'extraction = **`manual`**, confiance **1.0**.
- Ce script alimente **les mêmes tables** que la page BPU (`bpu_documents`, etc.). L'import PDF/OCR
  (`triggerBpuImport`) est un mécanisme **secondaire** (peut réintroduire des imprécisions OCR ; ne pas
  écraser les corrections du xlsx).
- Les **PDF sources** sont dans le même dossier `HISTORIQUE BPU/` (EDF/ENGIE 2021→2026).

## 3. Constat « ENGIE = 1 seul doc » → NON un bug
L'onglet `Sources_PDF` de l'Excel ne contient qu'**un seul PDF ENGIE**
(`2025_18_MS1_BPU_ENGIE_LOT_1.pdf`) ; tout le reste est **EDF** (+ le 2026 lots 1/2/7 gaz). Donc le fait
qu'ENGIE n'ait qu'un document en base **reflète la réalité de la source** (ENGIE n'a qu'un marché
subséquent), ce n'est **pas** un chargement incomplet. → rien à corriger côté ENGIE.

## 4. Actes DPGF DALKIA — l'UI existe déjà
- Qualifier un import (offre finale / mise au point / avenant / OS / DPGF / autre) se fait dans
  `CpeDalkiaImportPage`, section **« État en vigueur + journal du marché »** : bouton **« Qualifier »**
  par ligne → type / libellé / **date d'effet** → **« Enregistrer »** (`PATCH /cpe/dalkia-ref/imports/{id}/acte`).
- Les imports en base ont l'acte **vide** car rien ne le renseigne à l'import (pas d'auto-détection depuis
  le nom de fichier). **Décision user 2026-07-06** : pas de code, qualification **manuelle** via l'UI
  existante. Auto-détection depuis le nom de fichier = **écartée**.

## 5. Fidélité des données (gate allégée)
- BPU élec = **saisie manuelle validée** (`manual`, confiance 1.0) → pas d'OCR deviné, risque faible.
- Comparaison poste-par-poste aux sources **abandonnée** (moteur de confiance ; pas de docs à comparer).

## 6. Décisions structurantes déjà écartées / différées
- Réécriture au design-system V1 des pages référentiel : **écartée** au profit de l'embarquement.
- Renommage des préfixes API `/api/marches/...` : **différé** (les pages tapent les préfixes actuels).
- Onglet Référentiel **par tier** dans `/refonte-v1/marches` : **abandonné** au profit du **hub central**.

## 7. Prochain sujet (ouvert) : UX du hub, surtout l'onglet BPU
Le contenu de `EnergieBpuPage` (legacy, thème sombre) empile beaucoup de **pédagogie/indicatif** autour du
cœur (liste des BPU + prix). Cadrage dans `referentiel-bpu-ux-decisions.md`.
