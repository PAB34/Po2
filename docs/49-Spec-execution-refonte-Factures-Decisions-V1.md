# 49 - Spec execution refonte Factures & decisions V1

Date : 2026-06-26  
Statut : cadrage pret pour implementation progressive  
Perimetre : premiere tranche verticale de refonte React raccordee, depuis la maquette jusqu'aux API existantes.

## 1. Decision de cap

La premiere tranche de refonte definitive doit etre `Factures & decisions`.

Pourquoi ce choix :

- c'est le parcours le plus visible pour la direction et la comptabilite ;
- il relie les moteurs deja developpes : imports factures, controles, matrices comptables, historique, export finance ;
- il force a stabiliser le design system sur un cas reel et exigeant ;
- il donne un modele UX reutilisable pour `Fluides`, `Marches & contrats`, `Maintenance`, `Technique & PPT` et `Budget`.

L'objectif n'est pas de refaire un prototype decoratif. L'objectif est de transformer la maquette validee en ecran React raccordable, avec donnees reelles quand elles existent et fallback propre quand un endpoint manque.

## 2. Sources relues avant cadrage

Documents :

- `docs/35-Contrat-ecran-Factures-Decisions-V1.md`
- `docs/38-Modele-backend-matrices-comptables-versionnees.md`
- `docs/40-Analyse-factures-reelles-pour-matrice-comptable.md`
- `docs/Archives/41-Cartographie-existant-avant-refonte-et-raccord-UX.md` *(archivé)*
- `docs/Archives/48-Preview-Factures-decisions-V1.md` *(archivé)*
- `docs/prototype-refonte-v1/index.html`, `app.js`, `styles.css`

Code frontend :

- `saas/frontend/src/features/invoices/InvoicesDecisionPageV1.tsx`
- `saas/frontend/src/features/invoices/useInvoiceDecisionsV1.ts`
- `saas/frontend/src/features/invoices/useInvoiceAccountingSnapshotsV1.ts`
- `saas/frontend/src/features/invoices/accountingMatrixV1.ts`
- `saas/frontend/src/pages/RefonteV1InvoicesPage.tsx`
- `saas/frontend/src/lib/api.ts`
- `saas/frontend/src/design-system/*`

Code backend / API :

- `saas/backend/app/api/routes/billing.py`
- `saas/backend/app/api/routes/gas_invoice.py`
- `saas/backend/app/api/routes/cpe_dalkia.py`
- `saas/backend/app/api/routes/accounting_matrix.py`
- `saas/backend/app/services/invoices.py`
- `saas/backend/app/services/invoice_analysis.py`
- `saas/backend/app/services/gas_invoice.py`
- `saas/backend/app/services/cpe_*`
- `saas/backend/app/services/accounting_matrix*.py`
- `saas/backend/app/services/accounting_matrix_invoice_lines.py`

## 3. Existant a reutiliser, pas a refaire

| Brique | Existant | Decision refonte |
|---|---|---|
| Imports ENGIE | `/api/billing/invoices/imports/xlsx`, parser XLSX | Reutiliser ; presenter dans une file unique |
| Imports EDF | `/api/billing/invoices/imports/edf-csv`, parser CSV | Reutiliser ; traiter avoirs/periodes anciennes explicitement |
| Gaz TotalEnergies | `/api/gas/invoices`, controles gaz, trace detaillee | Reutiliser ; brancher dans file commune et fiche facture |
| CPE/DALKIA | `/api/cpe/finances/invoices`, lignes, controles, liaison | Reutiliser ; garder logique P1/P2/P3 specifique |
| Decisions facture energie | `PATCH /api/billing/invoices/imports/{id}/decision` | Reutiliser court terme ; harmoniser avec snapshot matrice |
| Decisions gaz | `PATCH /api/gas/invoices/{id}/decision` | Reutiliser court terme ; harmoniser statut UI |
| Matrices versionnees | `/api/accounting-matrices/*` | Source cible pour imputation comptable V1 |
| Snapshots facture | `/api/accounting-matrices/invoices/{source}/{id}/snapshot` | Source d'historique comptable et export finance |
| Liaison finance ENGIE | `/api/billing/invoices/imports/{id}/liaison.xlsx` | Garder jusqu'a export unifie |
| Liaison finance CPE | `/api/cpe/finances/invoices/{id}/liaison.xlsx` | Garder jusqu'a export unifie |
| Design maquette | `docs/prototype-refonte-v1` | Reference visuelle, pas source applicative definitive |

## 4. Parcours utilisateur cible

### 4.1 Arrivee sur la page

L'utilisateur arrive sur une page qui repond a trois questions en moins de dix secondes :

1. Qu'est-ce qui attend une decision ?
2. Qu'est-ce qui bloque la transmission aux finances ?
3. Quelle preuve justifie l'action proposee ?

La page doit donc afficher dans cet ordre :

1. entete clair : `Importer, controler, imputer, decider` ;
2. barre de statut du dernier lot importe ;
3. quatre KPI comptabilite ;
4. cartes de matrices contractuelles ;
5. file des factures priorisee ;
6. drawer ou panneau detail facture.

### 4.2 KPI V1 comptabilite

La page doit reprendre les KPI du profil `Comptable` :

| KPI | Valeur attendue | Sens |
|---|---:|---|
| A controler | nombre + montant | Factures nouvelles, en anomalie ou a decision |
| Conformes | nombre + montant | Factures techniquement validables |
| Avec anomalie | nombre + montant | Factures avec ecart fournisseur, matrice, periode ou controle |
| Pretes a transmettre | nombre + montant | Factures dont controle + imputation sont validables/exportables |

Regle UX : les cartes doivent avoir la meme hauteur. Pas de carte visuellement plus petite car un libelle est plus court.

### 4.3 File des factures

Colonnes minimales :

| Colonne | Source cible | Remarque |
|---|---|---|
| Fournisseur / facture | source normalisee | ENGIE, EDF, TotalEnergies, DALKIA |
| Site | site, PCE/PRM, CPE site mapping | Afficher `site a confirmer` si non rattache |
| Marche / contrat | contrat ou lot | Indispensable pour matrice |
| Montant TTC/HT | selon source | TTC pour fluides, HT utile CPE |
| Emission / echeance | facture | Alerter echeance proche |
| Controle | moteur de controle | Conforme, a revoir, anomalie, info |
| Matrice | snapshot ou proposition | Validee, proposee, a completer, a arbitrer |
| Decision | decision utilisateur | A decider, validee, litige, transmise, historique |

Tri par defaut :

1. anomalies bloquantes ;
2. echeances proches ;
3. factures nouvelles ;
4. factures conformes non transmises ;
5. historique / deja traitees.

### 4.4 Fiche facture

La fiche facture doit etre le coeur de la refonte. Elle doit presenter une synthese simple puis des details depliyables.

Sections obligatoires :

1. **Synthese** : fournisseur, numero facture, site, contrat, periode, montant, echeance, statut.
2. **Verdict** : phrase courte expliquant l'action recommandee.
3. **Trace de controle** : lignes controlees, reference, montant facture, verdict.
4. **Matrice comptable** : version appliquee, statut snapshot, axes produits, exceptions.
5. **Historique** : import initial, reimport, validation, export finance, reouverture.
6. **Actions** : valider, mettre en attente, preparer reclamation, exporter finance, reouvrir si droit.

Regle UX : aucun bouton `Valider` ne doit apparaitre sans dire exactement ce qui est valide : controle fournisseur, imputation comptable, decision de transmission, ou correction manuelle.

## 5. Statuts cibles

### 5.1 Statut de controle fournisseur

| Statut | Sens | Couleur |
|---|---|---|
| `conforme` | Pas d'ecart bloquant | vert |
| `a_revoir` | Controle incomplet ou tolerance a verifier | orange |
| `anomalie` | Ecart fournisseur ou donnees incoherentes | rouge |
| `info` | Non controle ou hors perimetre | bleu/gris |

### 5.2 Statut matrice comptable

| Statut | Sens | Action attendue |
|---|---|---|
| `validee` | Snapshot comptable valide | Peut partir finance |
| `proposee` | Imputation automatique complete | Validation comptabilite |
| `a_completer` | Axe ou regle manquante | Corriger matrice ou facture |
| `a_arbitrer` | Plusieurs regles possibles / ventilation | Arbitrage comptabilite |
| `non_applicable` | Document sans ecriture | Justifier et archiver |

### 5.3 Statut decision facture

| Statut | Sens |
|---|---|
| `nouvelle` | Importee, pas encore instruite |
| `a_decider` | Controle disponible, decision attendue |
| `validee` | Controle + imputation acceptes |
| `litige` | Reclamation fournisseur a preparer/suivre |
| `mise_en_attente` | Blocage interne ou piece manquante |
| `transmise` | Export finance realise ou marque |
| `historique` | Deja traitee / reimport identique |
| `revision` | Meme facture mais contenu different |

## 6. Donnees/API a raccorder

### 6.1 Lecture de la file commune

Etat actuel : `useInvoiceDecisionsV1` agrege deja :

- `fetchEnergyInvoiceImports` -> `/api/billing/invoices/imports` ;
- `fetchGasInvoices` -> `/api/gas/invoices` ;
- `fetchCpeFinanceInvoices` -> `/api/cpe/finances/invoices`.

Decision : conserver cette aggregation au depart, mais enrichir l'adapter plutot que creer une nouvelle API globale tout de suite.

A faire :

- harmoniser les champs : source, sourceId, invoiceNumber, supplier, siteLabel, contractLabel, amount, dueAt, issuedAt, period, status, controlStatus, matrixStatus ;
- ajouter `isHistorical`, `isDuplicate`, `isRevision`, `financeExportedAt`, `snapshotStatus` ;
- brancher les filtres fournisseur, statut, matrice, periode, recherche.

### 6.2 Details facture

Sources possibles :

- Energie : `/api/billing/invoices/imports/{id}` ;
- Gaz : detail depuis `GasInvoice` + `control_detail_json` ;
- CPE : lignes et controles via `/api/cpe/finances/invoices/{id}/lines` et `/controls`.

A faire : creer une couche frontend `invoiceDetailV1.adapters.ts` qui normalise le detail pour le drawer :

```ts
type InvoiceDetailV1 = {
  source: 'energy_import' | 'gas_totalenergies' | 'cpe_dalkia';
  sourceId: string;
  summary: InvoiceSummary;
  controlLines: ControlLine[];
  accountingSnapshot?: InvoiceAccountingSnapshotV1;
  parsedLines: ParsedInvoiceLine[];
  history: InvoiceHistoryEvent[];
  availableActions: InvoiceAction[];
}
```

### 6.3 Matrices et snapshots

APIs deja disponibles :

- `GET /api/accounting-matrices/contracts`
- `GET /api/accounting-matrices/contracts/{id}`
- `GET /api/accounting-matrices/versions/{id}/rules`
- `GET /api/accounting-matrices/invoices/{source}/{invoice_id}/snapshot`
- `POST /api/accounting-matrices/invoices/{source}/{invoice_id}/apply`
- `POST /api/accounting-matrices/invoices/{source}/{invoice_id}/validate-snapshot`
- `POST /api/accounting-matrices/invoices/{source}/{invoice_id}/export-finance`

Point d'attention : `applyAccountingMatrixToInvoice` envoie encore `invoice_lines: []` par defaut. Il faut brancher les extracteurs reels cote backend ou alimenter explicitement les lignes normalisees selon la source.

### 6.4 Imports et dedoublonnage

Imports existants :

- ENGIE XLSX : `/api/billing/invoices/imports/xlsx` ;
- EDF CSV : `/api/billing/invoices/imports/edf-csv` ;
- TotalEnergies gaz : `/api/gas/invoices/import` ;
- DALKIA : imports CPE/finance deja existants.

Regle UX : un import annuel complet est autorise. Le rapport de lot doit separer :

- nouvelles factures ;
- factures deja traitees identiques ;
- factures revisees ;
- erreurs de parsing ;
- factures sans contrat/matrice ;
- factures avec controles bloquants.

## 7. Ecarts detectes dans le frontend V1 actuel

| Ecart | Impact | Action |
|---|---|---|
| `InvoicesDecisionPageV1.tsx` contient encore des textes mojibake | Risque visuel et perte de confiance | Nettoyage UTF-8 avant prochaine demo |
| KPI React encore `Nouvelles / Imputation complete / Exceptions / Transmises` | Diverge de la maquette comptabilite corrigee | Remplacer par `profiles.finances.kpis` cible ou calcul API |
| `accountingMatrixV1.ts` lit encore les anciennes codifications energy/cpe | Utile transitoire mais pas cible | Basculer vers `/api/accounting-matrices/contracts` |
| Detail facture encore trop leger | Pas assez de profondeur metier | Creer drawer detail V1 normalise |
| Actions drawer non branchees | Peut donner illusion de fonctionnement | Brancher ou afficher clairement `simulation` |
| Pas de rapport de lot dans l'ecran V1 | Import annuel mal explique | Ajouter panneau `Dernier lot` avec resume |
| Pas de distinction historique/revision dans la table | Risque de retraiter les factures closes | Ajouter statuts visibles |

## 8. Ordre de developpement recommande

### Phase 1 - Hygiene et alignement visuel

1. Nettoyer l'encodage des fichiers frontend V1 concernes.
2. Reprendre la structure visuelle de la maquette statique dans `InvoicesDecisionPageV1`.
3. Remplacer les KPI React par les KPI comptabilite cible.
4. Verifier mode sombre automatique.
5. Garder la preview statique comme reference, mais travailler dans React.

Livrable : `/refonte-v1/factures` ressemble a la maquette et ne fait plus peur visuellement.

### Phase 2 - File commune reelle

1. Consolider `useInvoiceDecisionsV1`.
2. Enrichir les adapters ENGIE/EDF, gaz, CPE.
3. Ajouter filtres fournisseur/statut/matrice/historique.
4. Calculer KPI depuis les lignes reelles quand API disponible.
5. Gerer fallback uniquement si API absente, avec badge explicite.

Livrable : l'utilisateur voit les vraies factures, meme si le detail complet n'est pas encore raccorde.

### Phase 3 - Drawer detail facture

1. Creer `useInvoiceDetailV1`.
2. Normaliser les preuves de controle par source.
3. Afficher `control_detail_json` gaz.
4. Afficher controle BPU/TURPE energie.
5. Afficher controles CPE/DALKIA.
6. Afficher snapshot comptable si present.

Livrable : drill-down lisible du global vers la fiche, conforme a la demande utilisateur.

### Phase 4 - Matrice et snapshot

1. Remplacer `useAccountingMatricesV1` transitoire par `/api/accounting-matrices/contracts`.
2. Selectionner automatiquement la matrice active du contrat.
3. Brancher `apply` avec lignes reelles.
4. Afficher exceptions d'imputation.
5. Valider snapshot uniquement si aucune exception bloquante.

Livrable : une facture peut etre imputee et validee sans boite noire.

### Phase 5 - Decision et export finance

1. Harmoniser les statuts de decision entre energie, gaz, CPE et snapshot.
2. Ajouter bouton `Preparer reclamation` avec destinataire/objet/corps, pas envoi direct.
3. Ajouter `Exporter finance` si snapshot valide.
4. Marquer `transmise` / `exported_at`.
5. Ajouter historique de reimport.

Livrable : parcours complet facture -> controle -> imputation -> decision -> export.

## 9. Definition de termine pour cette tranche

La tranche `Factures & decisions` est consideree prete quand :

- la page React ne depend plus de la maquette statique pour l'usage quotidien ;
- les textes sont propres et coherents en clair/sombre ;
- la file affiche ENGIE, EDF, TotalEnergies et DALKIA si donnees presentes ;
- les factures deja traitees sont visibles comme historiques ;
- la fiche facture expose les controles et preuves ;
- une exception matrice bloque la validation ;
- un snapshot comptable valide est lisible ;
- l'export finance est marque et tracable ;
- les actions non branchees ne sont jamais presentees comme operationnelles ;
- la documentation de handoff explique quoi raccorder ensuite.

## 10. Questions restantes, mais non bloquantes pour demarrer

Ces questions peuvent etre traitees en cours de Phase 2/3, elles ne bloquent pas la refonte visuelle de Phase 1.

1. Quels roles exacts peuvent `valider snapshot`, `manual override`, `export finance` en base ?
2. Quelle formulation exacte utiliser pour le statut `historique` vs `revision` ?
3. Quel format final de fiche liaison finance est attendu a moyen terme : unifie ou conserve par fournisseur ?
4. DALKIA : veut-on separer visuellement P1, P2, P3 dans la file ou seulement dans la fiche ?
5. TotalEnergies : les factures sans `NOM SITE` mais avec PCE doivent-elles etre affiches sous le PCE ou sous `site a rattacher` ?
6. EDF : les avoirs doivent-ils etre dans la meme file avec badge ou dans un filtre dedie ?

## 11. Prochaine action de code proposee

Commencer par la Phase 1 :

1. nettoyer l'encodage de `saas/frontend/src/features/invoices/*` et des commentaires mojibake dans `api.ts` ;
2. aligner `InvoicesDecisionPageV1.tsx` sur la maquette corrigee ;
3. remplacer les KPI par la logique comptabilite ;
4. garder les hooks actuels mais rendre explicite fallback/API ;
5. lancer `tsc -b`.

Cette etape est petite, visible, et ne risque pas de casser les moteurs backend. Elle remettra la confiance sur l'interface avant de brancher plus profond.

## Avance Phase 1 - 26/06/2026

Apres creation de cette spec, un premier correctif React a ete applique :

- `saas/frontend/src/features/invoices/InvoicesDecisionPageV1.tsx` utilise maintenant les KPI comptabilite cibles : `À contrôler`, `Conformes`, `Avec anomalie`, `Prêtes à transmettre`.
- Verification TypeScript : `tsc -b` OK avec le Node portable.

Reste pour Phase 1 : aligner davantage le layout React sur la maquette statique et expliciter visuellement le mode API/fallback.

## Avance Phase 1 bis - 26/06/2026

La page React `saas/frontend/src/features/invoices/InvoicesDecisionPageV1.tsx` a ete alignee plus fortement sur la maquette statique :

- ajout d'un entete avec actions `Rapports d'import` et `Importer des factures` ;
- ajout d'un bandeau visible indiquant le mode de donnees : API, synchronisation ou demonstration ;
- ajout d'une chaine de traitement `Importer -> Dedoublonner -> Controler -> Imputer -> Decider -> Exporter` ;
- conservation de la file factures et du drawer existants ;
- ajout de styles dedies dans `saas/frontend/src/design-system/tokens.css` ;
- verification encodage sur les fichiers modifies : pas de marqueurs mojibake detectes ;
- validation TypeScript : `tsc -b` OK.

Prochaine action : raccorder le calcul des KPI aux vraies lignes agregees au lieu de valeurs statiques, puis enrichir le drawer detail facture par source.

### Avancement code - 2026-06-26 - KPI reels de file factures

La page React `InvoicesDecisionPageV1.tsx` ne porte plus des KPI fixes de maquette sur la ligne principale. Les quatre indicateurs `A controler`, `Conformes`, `Avec anomalie` et `Pretes a transmettre` sont maintenant calcules depuis la file agregee `useInvoiceDecisionsV1`.

Regles appliquees a ce stade :

- `A controler` : factures en decision, en anomalie, ou dont la matrice est a completer / a arbitrer ;
- `Conformes` : factures dont le controle est conforme ;
- `Avec anomalie` : factures en anomalie ou portant une matrice incomplete / a arbitrer ;
- `Pretes a transmettre` : factures conformes avec matrice validee.

Les montants affiches sont des sommes issues des factures adaptees. Pour le CPE/DALKIA, l'agregat utilise provisoirement `total_ht` car la source expose un total HT ; le libelle de ligne reste `HT` pour ne pas mentir a l'utilisateur. Un champ cible plus propre devra distinguer explicitement montant HT, TVA et TTC.

Validation locale : `npx tsc -b` OK avec le Node portable.

### Avancement code - 2026-06-26 - Drawer facture contextualise par source

Le drawer de dossier facture commence a porter une lecture differenciee selon l'origine :

- `energy-import` : dossier fournisseur fluides, controle BPU/TURPE/taxes/abonnement/consommation/doublons ;
- `gas-totalenergies` : dossier gaz TotalEnergies, controle ATRD/CTA/accise/TVA et lignes explicites non controlees ;
- `cpe-dalkia` : dossier CPE/DALKIA, controle contrat, periode, prestation facturee, justificatifs et ecarts ;
- `mock` : dossier de demonstration pour la validation UX.

Objectif : eviter une fiche facture generique qui ne parle pas metier. La prochaine evolution doit brancher ces blocs sur des donnees plus fines quand les endpoints exposent la trace detaillee par source.

Validation locale : `npx tsc -b` OK.
