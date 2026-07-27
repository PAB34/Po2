# /refonte-v1/matrices → rebrancher sur la vraie codification (système B) — décisions

Chantier A de la reprise « Demande comptable ». Règle « fil du dev » : ce document
(existant audité + décisions + **questions numérotées**) est écrit **AVANT de coder**.

Branche de travail prévue : `feat/matrices-systeme-b` (depuis `origin/main`).

---

## 1. Problème (rappel comptable)

La page `/refonte-v1/matrices` affiche le **système A** (matrices versionnées génériques),
qui **ne pilote pas** le rapport comptable. La comptable attend la matrice qui fait le
**lien élément facturé ↔ écriture comptable Ville** (service / fonction / nature /
opération si invest. / antenne) — c.-à-d. le **système B**, celui qu'alimente le V2 et
que lit le rapport. Une ancienne version de la page (système B) « était plus cohérente ».

---

## 2. Audit de l'existant (back ET front) — vérifié dans le code

### 2.1 Système A — versionné (affiché par /refonte-v1/matrices) — DÉCONNECTÉ du rapport
- **Back** : `models/accounting_matrix.py` (`AccountingMatrixContract/Version/Rule` +
  `invoice_accounting_snapshots`), services `accounting_matrix*.py`
  (`.py`, `_apply.py`, `_xlsx.py`, `_invoice_lines.py`), routes `routes/accounting_matrix.py`.
- **Front** : `pages/RefonteV1MatricesPage` → `features/matrices/MatrixAdminPageV1.tsx`
  + `MatrixEditorOverlayV1.tsx` + hook `useMatricesV1.ts` (endpoints `accounting-matrix-*`).
- **Constat** : `comptable_report.py` **n'importe rien** de `accounting_matrix`.
  → système A = mort vis-à-vis du besoin comptable.

### 2.2 Système B — la vraie codification (lue par le rapport) — DEUX sous-systèmes // 
Le rapport `services/comptable_report.py` consomme **exclusivement** :

a) **DALKIA** — tables `cpe_accounting_site_mappings` (site→service/fonction/antenne/
   opération) + `cpe_accounting_nature_rules` (poste→nature).
   - Service : `services/cpe_accounting.py` (`import_codification_workbook`, list/create/
     update/delete pour les 2 tables).
   - API : **CRUD complet déjà exposé** sous `/cpe/accounting/*`
     (`GET|POST /site-mappings`, `PATCH|DELETE /site-mappings/{id}`, idem `nature-rules`,
     `POST /import-codification`). Cf. `routes/cpe.py:207-364`.
   - Front existant : onglet « Imports / Codification » de la page **legacy /cpe**
     (`CpeDalkiaPage.tsx` → composant `CpeFinanceReference`). Il édite déjà sites +
     natures + import du classeur… **mais** dans un composant fourre-tout (~1300 lignes)
     qui mélange aussi imports finance, contrôles, indices de révision, preuves PDF.

b) **ENGIE / EDF (énergie)** — tables `energy_accounting_site_mappings` +
   `energy_accounting_nature_rules` (clé = PRM), service `services/energie_accounting.py`
   (`resolve_invoice_codification` = ce que lit le rapport), API sous `/billing/accounting/*`,
   front = composant `components/EnergieAccountingMatrix.tsx` (monté sur /factures legacy).

**Bilan** : tout le back (données + CRUD + import) du système B existe et fonctionne.
Ce qui manque = **une page refonte unique et lisible** qui expose la codification B
(DALKIA + énergie), à la place de la page système A actuelle.

---

## 3. Décisions proposées (à valider)

- **D1.** `/refonte-v1/matrices` doit afficher/éditer le **système B**, pas A.
- **D2.** Ne **pas** embarquer tel quel le composant legacy `CpeFinanceReference` :
  il traîne contrôles/indices/PDF hors sujet. Préférer une **page refonte légère
  dédiée** qui consomme les endpoints B déjà existants (aucun nouveau backend).
- **D3.** Réutiliser à 100 % les endpoints existants (`/cpe/accounting/*` +
  `/billing/accounting/*`) → chantier surtout **front**.
- **D4.** Exposer aussi le **bouton d'import du classeur V2** (`POST /cpe/accounting/
  import-codification`) depuis cette page, pour éviter le détour par /cpe.

---

## 3bis. Décisions actées (2026-07-27)

- **Q1 → Réécrire propre.** Nouvelle page refonte (design-system V1) branchée sur les
  endpoints B existants. Pas d'embarquement du composant legacy `CpeFinanceReference`.
- **Q2 → DALKIA + ENGIE/EDF unifié.** Une page, sections/onglets par tiers, couvrant les
  deux sous-systèmes B (`/cpe/accounting/*` + `/billing/accounting/*`) d'emblée.
- **Q3 → Débrancher système A, garder dormant.** La route `/refonte-v1/matrices` pointe
  sur la nouvelle page B ; code système A laissé en place mais inaccessible (nettoyage
  séparé plus tard).
- **Q4 → Oui**, les deux tables (Sites→codes et Poste→Nature) restent éditables + import
  du classeur V2 exposé sur la page.
- **Q5 → Afficher `operation_code`** (colonne du mapping site) avec une note « utilisé
  seulement en P3/P3.4 » ; ne pas le masquer.
- **Q6 → Réappliquer la grille de rôles** de `MatrixAdminPageV1` (allow ADMIN/FINANCE/
  COMPTA/DIRECTION…, deny FLUIDES) sur la nouvelle page. Vérifier au passage le garde
  backend des endpoints `/cpe/accounting/*` et `/billing/accounting/*`.

---

## 4. Questions d'intégration (historique — tranchées ci-dessus)

**Q1 — Legacy vs réécrire.** Option A = **réécrire** une page refonte propre (design-system
V1) branchée sur les endpoints B (recommandé : lisible, isolée du fourre-tout /cpe).
Option B = **embarquer** l'onglet legacy tel quel (rapide mais ramène contrôles/indices/
PDF et le style legacy). → **A ou B ?**

**Q2 — Périmètre d'une seule page.** La page doit-elle couvrir **DALKIA + ENGIE/EDF**
dans une vue unifiée (2 sections / onglets par tiers), ou **DALKIA d'abord** (le cas
remonté par la comptable) et énergie en incrément 2 ?

**Q3 — Sort du système A versionné.** Options : (a) **retirer** `/refonte-v1/matrices`
du système A et pointer la route sur la nouvelle page B (code A laissé dormant, supprimé
plus tard) ; (b) garder A accessible ailleurs (ex. `/refonte-v1/matrices-versionnees`) ;
(c) supprimer A (routes + page + services) dans la foulée. → **a / b / c ?**
(Recommandation : **a** — on débranche sans supprimer, nettoyage séparé.)

**Q4 — Deux niveaux d'édition.** La page B expose deux tables (Sites→codes et
Poste→Nature). On garde bien les **deux** éditables + l'import classeur ? (recommandé oui).

**Q5 — Antenne / opération.** Rappel décidé côté rapport : l'**opération** n'apparaît que
pour DALKIA P3/P3.4. Sur la page matrice, on **affiche** toujours `operation_code`
(colonne du mapping site) mais on documente qu'il n'est utilisé qu'en P3 ? Ou on le
masque ? → à préciser.

**Q6 — Rôles.** Le CRUD B côté /cpe est-il déjà gardé par rôle (ADMIN/COMPTA) ? Faut-il
réappliquer la même grille de rôles que `MatrixAdminPageV1` (allow ADMIN/FINANCE/COMPTA,
deny FLUIDES) sur la nouvelle page ?

---

## 5. Réalisation (2026-07-27) — DÉPLOYÉ STAGING

Branche `feat/matrices-systeme-b` (depuis `origin/main`). Commit `12da7b1`.
- **Front** : `features/matrices/MatrixCodificationPageV1.tsx` (page unifiée, onglets
  tiers DALKIA / ENGIE-EDF × vues Sites→codes / Poste→nature, édition en `Drawer`,
  import classeur V2 DALKIA, bootstrap PRM énergie) + hooks `useCodificationV1.ts`.
- **Route** : `RefonteV1MatricesPage` rend désormais la nouvelle page. Système A
  (`MatrixAdminPageV1`) laissé dormant (plus référencé).
- **API** : ajout des 3 fonctions énergie manquantes dans `lib/api.ts`
  (`createEnergySiteMapping`, `deleteEnergySiteMapping`, `deleteEnergyNatureRule`).
  Aucun backend nouveau (endpoints B déjà présents).
- ⚠️ **PATCH énergie = remplacement complet** (schéma `In` entier) → le drawer envoie
  toujours l'objet complet.
- **Typecheck** : validé par le build Docker `tsc -b && vite build` du déploiement
  staging (run OK). Déployé sur **staging** pour validation comptable.
- **Reste** : validation comptable sur staging, puis merge prod (accord utilisateur).

### 5bis. Export / import gabarit finance (2026-07-27, commit `3f67bef`, staging)

Besoin : aller-retour pour le service finance (export → il modifie → réimport), dans
un **gabarit dédié plus lisible** que le V2, vocation à **remplacer** le V2 à terme.
Décisions : **nouveau gabarit finance-friendly** (import accepte nouveau + V2) ;
**DALKIA seulement** (périmètre du V2).
- **Export** : `GET /cpe/accounting/codification/export.xlsx` →
  `build_codification_finance_workbook` (feuilles « Sites », « Postes », « Mode d'emploi »,
  colonnes lisibles + Actif/Opération/Notes, reflet de la matrice en base).
- **Import** : `import_codification_workbook` étendu — détecte les feuilles « Sites » /
  « Postes » du nouveau gabarit **en plus** du V2. `_upsert_nature_rule` prend un
  paramètre `active`. Round-trip complet (Actif/Opération/Notes).
- **Front** : boutons « Exporter (gabarit finance) » + « Importer (V2 ou gabarit finance) »
  sur les onglets DALKIA.
- ⚠️ **Upsert only** : une ligne retirée du fichier Excel n'est PAS supprimée en base
  (suppression via l'interface). Documenté dans la feuille « Mode d'emploi ».
- **Tests** : `tests/test_codification_finance_roundtrip.py` (aller-retour + upsert) verts ;
  import V2 inchangé (75 sites / 43 natures / 0 erreur) ; suite CPE + app boot verts.

### 5quater. Périmètre marché Ville EN COURS (2026-07-27)

Retour utilisateur : dans le V2, plusieurs codes contrats existent (feuille « Codes
contrat - marchés »), mais **on ne doit garder que le marché Ville en cours =
`C00190116O` (Lot 1) + `C00190155J` (Lot 2)**. Les autres (ancien marché
`C00025811F`/`C00025812G`, Agglo CREM `C00032657J`, réseaux thalasso
`C00107051V`/`C00157795L`) sont hors périmètre.

Mécanisme retenu = le **même que le rapport / budget / suivi** :
`get_current_cpe_contract_codes` (référentiel éditable `cpe_contract_scope`). Pas de
codes en dur.

**Où appliquer le filtre — décision : au NIVEAU AFFICHAGE + EXPORT uniquement**, pas à
l'import.
- `list_accounting_nature_rules(..., only_current_scope=True)` filtre par périmètre.
- Page `/refonte-v1/matrices` (onglet Postes DALKIA) : `useCpeNatureRules` appelle
  l'endpoint avec `?only_current_scope=true`.
- Export gabarit finance : ne contient que les contrats en cours.
- **Import inchangé** : la base garde toutes les règles (l'import et le rapprochement
  finance `import_finance_workbook` reposent dessus — filtrer à l'import cassait le
  matching, 2047→1259, et les tests). Les règles hors périmètre restent en base mais
  **n'apparaissent plus** dans la matrice finance ni l'export. Sécurité : si
  `cpe_contract_scope` est vide, aucun filtrage (on ne vide pas la matrice).
- Sites NON filtrés (les 75 sites = bâtiments Ville, sans code contrat).
- Option non retenue pour l'instant : purger les règles hors périmètre de la base
  (destructif) — à décider séparément si besoin.

Règles du rapport réutilisées / vérifiées : LC = `gestionnaire-nature-[opération P3]-
service-antenne` (sans fonction) ; opération d'investissement calculée **depuis le site**
(`_cpe_p3_operation_fallback` : P3.4→98023, sinon par fonction/service) → l'opération du
V2 (niveau poste) n'a pas besoin d'être persistée dans la matrice.

Tests : `test_only_current_scope_filters_display`, `test_export_contains_only_current_scope`,
`test_no_scope_reference_shows_everything` (+ round-trip + upsert). Import V2 réel
inchangé (75 sites / 43 natures).

### 5ter. Audit de fidélité V2 (2026-07-27)
Voir `docs/refonte-v1/matrices-audit-fidelite-v2.md`. La matrice produite correspond au
V2. Le `98004`/`ATBA` vus autrefois = donnée prod périmée (le V2 n'a pas de colonne
opération sur les sites). Nuances : marché déduit du poste ; opération P3 non persistée
dans la matrice (le rapport la calcule à part) ; coquilles source à nettoyer.
