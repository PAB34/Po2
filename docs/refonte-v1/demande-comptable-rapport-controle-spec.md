# Spec maîtresse — « Demande comptable » (rapport de contrôle multi-marchés) + extensions import

> Doc « fil du dev » — 2026-07-10. Rédigé en **effort max (analyse + architecture)** pour handoff vers
> effort moyen puis Codex. **Source de vérité de ces chantiers.** Ne pas coder avant lecture + validation
> des questions ouvertes (§3.6, §4.4).
>
> Branche de travail factures en cours : `feat/factures-import-ui` (PR #56, import ENGIE xlsx + EDF csv).
> ⚠️ Décision utilisateur : **ne PAS merger #56 en prod tant que DALKIA + gaz + ENGIE csv ne sont pas dans
> le tiroir** (cf. Chantier 2).

---

## 0. Ordre par urgence (demandé par l'utilisateur)

Urgence pilotée par : **« contrôle de facture avec rapport à fournir à la comptable »**.

| # | Chantier | Urgence | Dépendances |
|---|---|---|---|
| **C1** | **Volet « Demande comptable » + rapport de contrôle Excel multi-marchés** | 🔴 haute | s'appuie sur imports existants + atterrissages + export finance |
| C2 | Import drawer : ajouter **ENGIE csv**, **DALKIA**, **gaz TE** | 🟠 (bloque le merge prod de #56) | parseurs back existants |
| C3 | Réimport **matrice comptable V2** (codification à jour) | 🟢 | endpoint import matrice existant |

Découpage exécutable en §6.

---

## 1. Process comptable identifié (le « pourquoi »)

La comptable de la Ville exporte, depuis le **logiciel financier** (type e-GF/CIRIL), sa **liste de
factures « transmises aux services, en attente de rapprochement »**, un fichier **par fournisseur/marché**,
et l'envoie pour validation. Le besoin : **confronter cette liste aux factures déjà importées + contrôlées
dans la plateforme**, et lui **rendre un rapport Excel unique** (synthèse + une feuille par marché) qui :
- pose l'**état des dépenses** par marché (atterrissage + réalisé à date) ;
- pour chaque facture de sa liste : rapprochement, contrôle, **codification comptable** (nature/section/
  fonction/opération) et **révision de prix** si applicable.

Fichiers réels fournis (dans le repo) :
- `saas/energie/COMPTA/FACTURES DALKIA 2IEME TRIMESTRE.xlsx` (worklist DALKIA)
- `saas/energie/COMPTA/FACTURES ENGIE.xlsx` (worklist ENGIE)
- `saas/energie/DALKIA/COMPTABILITE/MATRICE_DALKIA-COMPATBILITE V2.xlsx` (matrice comptable, cf. §2.2)

---

## 2. Analyse des fichiers fournis

### 2.1 Worklist comptable (DALKIA & ENGIE) — MÊME format

Une feuille `_ShowList-NNN`, 22 colonnes. Colonnes utiles :

| Colonne | Contenu | Usage rapport |
|---|---|---|
| Exercice | année (2026) | filtre période |
| Numéro | n° **interne** compta (202605379) | id compta (affichage) |
| Etat facture / Etat liquidation | « Transmise aux services » / « En attente de rapproch. » | statut compta |
| **Libellé** | `FAC. <N° FOURNISSEUR> DU <date>` (ex. `FAC. 0001E2607QRY8 DU`, `FAC. 150000071294 DU`) | **CLÉ de rapprochement** → extraire le n° fournisseur |
| TTC | montant TTC | confronter au TTC plateforme |
| Date facture / Arrivée le | dates | affichage |
| Tiers (code) / Tiers (Nom) | fournisseur (DALKIA / ENGIE) | fournisseur |
| Marché | code engagement (DALKIA: `24BT039`) — **vide chez ENGIE** | indicatif, NE PAS s'y fier pour le marché |
| Section / Nb d'écritures / Engagement… | axes compta | secondaire |

**Extraction du n° fournisseur (clé de jointure)** : regex sur `Libellé` →
`^FAC\.\s*(?P<num>\S+)\s+DU` (récupérer le token entre « FAC. » et « DU »). Normaliser (trim, upper).
Exemples : `0001E2607QRY8` (DALKIA), `150000071294`, `120009890042` (ENGIE).
⚠️ À valider : le format stocké côté plateforme dans `invoice_number` (energy) / `cpe_finance_invoices`
doit correspondre après normalisation (Q3.6-1).

**Identification du marché** : ne PAS déduire du fichier (colonne Marché absente chez ENGIE). →
**l'utilisateur choisit le marché à l'upload** (un fichier = un marché), cf. §3.1.

### 2.2 Matrice comptable V2 (`MATRICE_DALKIA-COMPATBILITE V2.xlsx`)

4 feuilles (= classeur canonique déjà connu de la plateforme, cf. mémoire matrice multi-tiers / PR #34) :

| Feuille | Rôle |
|---|---|
| `Sites vers codes` (76×11) | Code site → Nom, Famille, Gestionnaire, **Service, Fonction, Antenne** (axes analytiques) |
| `Poste facturé vers Nature ctpab` (47×14) | **Code contrat + Poste facturé (P1, P2-11, ABT, CTA…) → Nature comptable (60612, 6156…)** + Opération si investissement + Statut + Règle + Validation comptable |
| `Signification poste facturés` (34×2) | Dictionnaire des postes (ABT=Abonnement, CTA=Contribution Tarifaire d'Acheminement…) |
| `Codes contrat - marchés` (8×6) | Code contrat → Libellé, Marché présumé, Types de marché, Clients |

→ **Chantier C3** = réimporter cette V2 via l'endpoint existant (§5). C'est ce classeur qui alimente la
**codification comptable** affichée dans le rapport C1 (nature/section/fonction/opération par ligne).

---

## 3. CHANTIER 1 (URGENT) — Volet « Demande comptable » + rapport Excel

### 3.1 UX

Sur `/refonte-v1/factures`, ajouter une action **« Demande comptable »** à côté des existantes
(`InvoicesDecisionPageV1.tsx`, barre `po2-prototype-actions` : Contacts fournisseurs, Purger les doublons,
Recalculer les contrôles, Importer des factures). Au clic → **tiroir (`Drawer`)** :

1. **Zone d'upload par marché** — une ligne par marché avec sélecteur de fichier :
   - DALKIA (CPE), ENGIE (élec), EDF (élec), TotalEnergies (gaz).
   - chaque ligne accepte le worklist xlsx compta (format §2.1) ; l'utilisateur dépose 1 fichier/marché.
   - état par marché : « fichier chargé (N lignes) » ou « — ».
2. Bouton **« Générer le rapport de contrôle »** → télécharge **un seul .xlsx** (§3.2).
   - marché sans fichier chargé → feuille « Aucune facture à analyser ».

Pas de persistance obligatoire en v1 : l'upload peut être **transient** (fichiers postés à la génération
du rapport, pas stockés). À trancher Q3.6-4.

### 3.2 Structure du rapport Excel

**Feuille 1 — « Synthèse » (soignée)** : un bloc/tableau par marché avec, repris de `/refonte-v1/marches`
(sous-vue « Atterrissage »), **uniquement** :
- **Atterrissage** (réalisé + reste projeté) ;
- **Réalisé à date**.
→ pose l'état actuel des dépenses. Mise en forme soignée (titres, €, couleurs par marché). Total général.

**Feuilles suivantes — une par marché** (`DALKIA`, `ENGIE`, `EDF`, `TotalEnergies`) :
- Si aucun fichier chargé : une cellule « Aucune facture à analyser ».
- Sinon : **toutes les factures du worklist compta**, chacune **confrontée** aux factures plateforme
  (rapprochement par n° fournisseur, §3.3), avec les colonnes du **« Exporter XLSX finance » /cpe**
  (`build_detailed_finance_liaison_workbook`) : décomposition comptable (poste → nature/section/fonction/
  opération via matrice), montants, **révision de prix** si elle existe (§3.3), + résultat de contrôle
  plateforme (sans écart / écart / à expliquer / informatif / bloqué) et statut de rapprochement.

### 3.3 Logique de rapprochement (par feuille marché)

Pour chaque ligne du worklist :
1. extraire n° fournisseur du `Libellé` (§2.1) ;
2. chercher la facture plateforme correspondante :
   - marchés énergie → `energy_invoice_imports.invoice_number` (city 303) ;
   - DALKIA → `cpe_finance_invoices.invoice_number` ;
3. statut de rapprochement : **Rapprochée** (trouvée, TTC cohérent), **Écart TTC** (trouvée, montant ≠),
   **Absente plateforme** (pas importée → à importer d'abord via « Importer des factures »),
   **En trop plateforme** (présente plateforme, absente worklist — à lister en fin de feuille) ;
4. si rapprochée : joindre la **codification comptable** (matrice) + le **contrôle** + la **révision de prix**.

**Révision de prix par marché** (important comptable) — sources :
- DALKIA P1 gaz : prix OS3 / coefficients (services `cpe_p1_gaz_revise`, référentiel DALKIA) ;
- DALKIA P2/P3 : indices de révision (`marches_indices_variables`) ;
- élec ENGIE/EDF : ratio BPU par typologie + TURPE (`engie_elec_budget_revise`, champs `bpu_ratio`/`turpe_ratio`) ;
- gaz TE : ratio PEG + climat (`gas_budget_revise`, `peg_ratio`).
→ afficher le **coefficient/indice appliqué et sa valeur**, sinon « pas de révision applicable ».

### 3.4 Backend (proposé)

Nouvel endpoint, ex. `POST /billing/comptable/rapport-controle.xlsx` (ou sous `/accounting/`), qui :
- reçoit N fichiers (multipart) tagués par marché (`dalkia`, `engie`, `edf`, `totalenergies`) ;
- parse chaque worklist (openpyxl, format §2.1) ;
- construit le classeur (openpyxl) : feuille Synthèse + feuilles marché ;
- renvoie le .xlsx (StreamingResponse).

Service dédié `services/comptable_report.py` qui **orchestre en réutilisant** (§5) : parsers worklist,
atterrissages (synthèse), builders de fiche liaison (feuilles marché), moteur matrice (codification),
services de révision (prix).

### 3.5 Existant réutilisable (pointeurs précis — À AUDITER avant de coder)

| Besoin | Où |
|---|---|
| Export « fiche liaison » DALKIA (contenu des feuilles marché) | `api/routes/cpe.py:672` `export_finance_invoice_liaison` → `cpe_accounting.build_detailed_finance_liaison_workbook` (`services/cpe_accounting.py:~2884`) |
| Rapport de contrôle finance CPE (déjà multi-facture) | `api/routes/cpe.py:587` `/cpe/finances/controls/report.xlsx` ; `market-tracking.xlsx` (`:614`) |
| Construction workbook openpyxl (exemple) | `services/cpe_accounting.py:2403` (`openpyxl.Workbook()`) |
| Atterrissage élec (Atterrissage + Réalisé) | `services/engie_elec_budget_revise.py` → `build_engie/edf_elec_budget_revise` (totals.atterrissage / totals.realise) |
| Atterrissage gaz | `services/gas_budget_revise.py` → `build_gas_budget_revise` |
| Atterrissage/budget DALKIA | `services/accounting_contract_budget.py` ; `/cpe/.../atterrissage` |
| Révision indices/variables | `services/marches_indices_variables.py` |
| Codification comptable (matrice) | `api/routes/accounting_matrix.py` ; modèle `models/accounting_matrix.py` ; `invoice_accounting_snapshots` |
| Factures énergie importées | table `energy_invoice_imports` (invoice_number, total_ttc, control_report_json, decision_status) |
| Factures DALKIA | table `cpe_finance_invoices` |
| Front — barre d'actions + pattern Drawer | `features/invoices/InvoicesDecisionPageV1.tsx` (Drawer Contacts fournisseurs = modèle) |

### 3.6 Questions ouvertes (à trancher avant de coder C1)

- **Q1** — Format exact de `invoice_number` côté plateforme (energy + CPE) vs n° extrait du worklist :
  vérifier sur données réelles que le rapprochement matche (normalisation à définir).
- **Q2** — Périmètre v1 des marchés dans le rapport : les 4 (DALKIA/ENGIE/EDF/TE) d'emblée, ou DALKIA+ENGIE
  d'abord (les 2 fichiers réels fournis) ?
- **Q3** — Synthèse : année de référence (dernière année significative comme l'atterrissage marchés ?) et
  faut-il aussi « Prévision de référence » ou strictement Atterrissage + Réalisé (comme demandé) ?
- **Q4** — Upload transient (rapport à la volée) ou persister les worklists (historique des demandes) ?
- **Q5** — « En trop plateforme » (factures plateforme absentes du worklist) : les lister, ou hors périmètre ?
- **Q6** — Droits : réservé à un rôle (compta/admin) ou ouvert ?

### 3.7 Incréments C1 (chacun livrable + testable staging)

1. Parser worklist compta (`services/comptable_report.py` : lecture xlsx + extraction n° fournisseur) + tests.
2. Endpoint + service : feuilles marché (rapprochement + codification + contrôle), SANS révision ni synthèse.
3. Ajouter la **révision de prix** par marché dans les feuilles.
4. Ajouter la **feuille Synthèse** (atterrissage + réalisé).
5. Front : volet « Demande comptable » (upload par marché + bouton rapport).
6. Validation staging avec les 2 fichiers réels (DALKIA + ENGIE).

---

## 4. CHANTIER 2 — Import drawer : ENGIE csv + DALKIA + gaz TE

### 4.1 Existant
Tiroir actuel (`InvoicesDecisionPageV1.tsx`, `InvoiceImportKind = "engie_xlsx" | "edf_csv"`) : 2 types.
Parsers/endpoints back existants : ENGIE xlsx (`/billing/invoices/imports/xlsx`), EDF csv
(`/billing/invoices/imports/edf-csv`), gaz TE (`/gas/invoices/import`), DALKIA (`/cpe/dalkia-ref/preview`
+ `/confirm`, flux 2 étapes).

### 4.2 À faire
- **ENGIE csv** (point B — l'utilisateur récupère ENGIE **nativement en csv**, pas xlsx) :
  vérifier si un parser ENGIE csv existe ; sinon en écrire un (calqué sur `edf_csv_import` /
  `engie_xlsx_import`) + endpoint `/billing/invoices/imports/engie-csv` ; ajouter le type au tiroir.
  ⚠️ **Obtenir un échantillon réel du csv ENGIE** avant de coder le parser (Q4.4-1).
- **Gaz TotalEnergies** : ajouter au tiroir (endpoint `/gas/invoices/import` existant).
- **DALKIA** : flux 2 étapes (aperçu → confirmation) — soit intégrer dans le tiroir (aperçu puis bouton
  confirmer), soit lien vers `/cpe/dalkia-import`. À trancher Q4.4-2.

### 4.3 Impact prod
Décision utilisateur : **ces ajouts doivent être dans #56 avant merge prod**. Donc élargir la branche
`feat/factures-import-ui` (au moins ENGIE csv + gaz ; DALKIA selon Q4.4-2) puis re-tester, puis merger.

### 4.4 Questions ouvertes
- **Q1** — Échantillon réel du **csv ENGIE** (colonnes/séparateur) — indispensable pour le parser.
- **Q2** — DALKIA dans le tiroir (aperçu/confirm intégrés) ou renvoi vers `/cpe/dalkia-import` ?
- **Q3** — Le tiroir devient multi-type (5 types) : garder le sélecteur simple ou grouper par famille ?

---

## 5. CHANTIER 3 — Réimport matrice comptable V2

Fichier : `saas/energie/DALKIA/COMPTABILITE/MATRICE_DALKIA-COMPATBILITE V2.xlsx` (§2.2).
Endpoint : `POST /accounting-matrices/contracts/{contract_id}/import-preview` puis `import-commit`
(`api/routes/accounting_matrix.py:175/192`). Versionné (jamais écrasé).
- Vérifier le mapping des 4 feuilles vs le parser d'import matrice (peut nécessiter un ajustement si la V2
  a changé de colonnes vs V1).
- Réimporter par contrat, activer la nouvelle version, contrôler la couverture (aucune ligne récurrente
  non couverte).
- **Validation lecture seule prod** avant activation (cf. AGENTS.md).

---

## 6. Découpage pour effort moyen / Codex

**Effort moyen (moi, prochaine session)** — le mieux cadré, à faire d'abord :
- C2 (ENGIE csv + gaz dans le tiroir) → débloque le merge prod de #56 (après échantillon csv ENGIE).
- C1 incréments 1–2 (parser worklist + feuilles marché du rapport).

**Codex (quand tokens limités)** — tâches mécaniques bien spécifiées :
- C1 incréments 3–5 (révision de prix, synthèse, front volet) en suivant §3.2/§3.3/§3.5.
- C3 (réimport matrice V2) en suivant §5.

**Règles handoff** : worktree neuf off origin/main ; repo partagé Codex (git status, pathspecs, pas de
force-push) ; ne pas toucher PRONO/*, knockout_mc.py ; staging avant prod ; merge prod = accord explicite.
Chaque incrément : un commit + test ciblé + validation staging.
