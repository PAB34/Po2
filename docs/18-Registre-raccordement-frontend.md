# 18 - Registre de raccordement frontend

> Date : 2026-06-16.
> Objectif : se mettre d'accord sur la nouvelle interface et sur ce que l'on raccorde dessus parmi les fonctionnalites deja developpees.
> Ce registre complete [[17-Refonte-frontend-capacites-metier]].

## 1. Pourquoi ce document existe

Les documents precedents donnent deja beaucoup de matiere :

- [[08-Inventaire-fonctionnalites-developpees-2026-06-02]] liste ce qui existe dans le code ;
- [[13-Matrice-routes-fonctionnalites-refonte-api]] liste les endpoints ;
- [[14-Catalogue-fonctionnalites-commentees-et-reaffectation]] explique l'utilite metier ;
- [[17-Refonte-frontend-capacites-metier]] pose la logique de refonte front.

Il manquait la piece de raccordement :

```text
Nouvelle interface cible
-> fonctionnalites deja developpees
-> pages / services / endpoints actuels a reutiliser
-> decision : brancher, refondre, cacher, garder expert, sortir du produit
```

Ce document devient donc le plan de cablage de la refonte frontend.

## 2. Regle de lecture

Statuts utilises :

| Statut | Sens |
|---|---|
| Brancher | fonctionnalite utile, deja assez exploitable pour etre raccordee au nouvel ecran |
| Refondre | fonctionnalite utile, mais experience actuelle a reconstruire |
| Garder expert | utile, mais a placer en Administration ou sous-ecran avance |
| Cacher | socle technique ou connecteur non pret, a ne pas mettre dans la navigation principale |
| A cadrer | besoin metier ou donnees pas encore assez clairs |
| Hors produit | ne doit pas entrer dans PatrimoineOp |

Regle :

```text
On ne supprime pas les anciennes routes tant que les nouveaux parcours ne sont pas operationnels.
On construit les nouveaux ecrans au-dessus des services existants, puis on nettoie progressivement.
```

## 3. Interface cible a valider

Navigation principale recommandee :

| Domaine | Route cible front | Role |
|---|---|---|
| Tableau de bord | `/` | cockpit des files a traiter |
| Patrimoine | `/patrimoine` | sites, batiments, locaux, fiches et rattachements |
| Fluides & consommations | `/energie` | electricite, gaz, eau, donnees distributeurs, prix |
| Marches & contrats | `/marches` | CPE DALKIA, SPIE, contrats, factures marche |
| Technique | `/technique` | inventaires CVC, equipements, fluides, rapport technique |
| Administration | `/administration` | imports experts, connecteurs, referentiels, diagnostics |

Les routes actuelles peuvent rester comme alias ou sous-routes pendant la migration :

- `/buildings/*`
- `/energie/*`
- `/factures/*`
- `/cpe/*`
- `/account`

## 4. Registre de raccordement par ecran

### 4.1 Tableau de bord

| Ecran cible | Fonctionnalites a raccorder | Code actuel | Action |
|---|---|---|---|
| Cockpit principal | KPI patrimoine, fluides, factures marche, preconisations, rattachements, CPE | `HomePage`, `fetchEnergieOverview`, `fetchEnergyInvoiceImports`, `fetchMeterMatches`, fonctions CPE | Refondre |
| File factures marche a controler | imports factures, decisions, ecarts | `FacturesPage`, `EnergieInvoicesPage`, `/api/billing/invoices/*` | Brancher |
| File factures CPE bloquees | controles finance CPE, rapport global | `CpeDalkiaPage`, `fetchCpeFinanceControlReport` | Brancher |
| File compteurs non rattaches | matching PRM/PCE/eau | `MeterMatchingPage`, `fetchMeterMatches` | Brancher |
| File donnees distributeur incompletes | audit ENEDIS, GRDF status | `EnergiePage`, `EnergieDataOpsPage`, `EnergieGazPage` | Brancher |
| File technique | F-Gaz, ESP, couverture technique | `CvcRefrigerantsPage`, `CvcTechnicalReportPage` | Brancher/P1 |

Decision UX : le tableau de bord doit devenir une vraie table de travail. Chaque carte doit ouvrir directement l'ecran qui permet de corriger ou decider.

### 4.2 Patrimoine

| Ecran cible | Fonctionnalites a raccorder | Code actuel | Action |
|---|---|---|---|
| Patrimoine > Vue d'ensemble | synthese sites, batiments, locaux, qualite de base | `BuildingsLandingPage`, `BuildingsListPage` | Refondre |
| Patrimoine > Sites et batiments | liste, recherche, filtres, fiche | `BuildingsListPage`, `BuildingDetailPage`, `fetchBuildings`, `fetchSites`, `fetchAllLocals` | Brancher |
| Patrimoine > Fiche site/batiment/local | infos, locaux, compteurs, equipements, liens fluides/contrats | `BuildingDetailPage`, `fetchBuilding`, `fetchBuildingLocals`, `fetchBuildingMeterLinks`, equipements | Refondre |
| Patrimoine > Rattachements compteurs | PRM/PCE/eau non rattaches, application de mappings | `MeterMatchingPage`, `fetchMeterMatches`, `applyMeterMappings` | Brancher |
| Patrimoine > Imports patrimoine | import hierarchique, DGFiP/IGN/OSM, creation/correction | `BuildingCreateEditPage`, `building_naming`, import endpoints | Garder expert |

Point d'accord a valider : l'import patrimoine doit etre accessible, mais il ne doit pas etre l'entree principale du domaine Patrimoine.

### 4.3 Fluides & consommations

| Ecran cible | Fonctionnalites a raccorder | Code actuel | Action |
|---|---|---|---|
| Fluides > Vue d'ensemble | portefeuille PRM/PCE/eau, couverture, conso, anomalies | `EnergiePage`, `fetchEnergieOverview`, `fetchDataAudit` | Refondre |
| Fluides > Electricite | detail PRM, conso, courbes, puissance max, DJU | `EnergieDetailPage`, fonctions `fetchPrm*`, `fetchDju*` | Brancher |
| Fluides > Gaz | PCE, GRDF, conso mensuelle, rapprochement P1 | `EnergieGazPage`, fonctions `fetchGrdf*` | Brancher/P1 |
| Fluides > Eau | consommations eau, pertes possibles, futur SUEZ | a cadrer | A cadrer |
| Fluides > Donnees distributeurs | sync ENEDIS, async FTP/AES, GRDF sync, qualite des donnees | `EnergieDataOpsPage`, `fetchSyncStatus`, `fetchEnedisAsyncJobs`, `fetchGrdfConsoStatus` | Garder expert |
| Fluides > Preconisations | puissance, pertes, couts reels, recommandations | `EnergieRecommendationsPage`, `fetchPowerRecommendations` | Brancher |
| Fluides > Prix contractuels | BPU, TURPE, timeline, edition | `EnergieBpuPage`, `EnergieBillingPage`, fonctions `fetchBpu*`, `fetchTurpeVersions`, billing config | Refondre |

Decision UX : separer clairement `donnees mesurees` (ENEDIS/GRDF/eau) et `prix contractuels`. Les factures sont un parcours marche transversal, pas un sous-bloc Fluides.

### 4.4 Marches & contrats > Factures marche

| Ecran cible | Fonctionnalites a raccorder | Code actuel | Action |
|---|---|---|---|
| Factures marche > Etat | imports, lots, montants, ecarts, decisions | `FacturesPage`, `EnergieInvoicesPage`, `fetchEnergyInvoiceImports`, `fetchEnergyInvoiceBatches` | Refondre/P0 |
| Factures marche > ENGIE | import XLSX, controle BPU/TURPE/ENEDIS, decision | `uploadEngieXlsxExport`, `analyzeEnergyInvoiceImport`, `updateEnergyInvoiceDecision` | Brancher/P0 |
| Factures marche > EDF | import CSV eclairage public, controles dedies | `uploadEdfCsvExport` | Brancher/P0 |
| Factures marche > TotalEnergies gaz | PCE, GRDF, fourniture gaz Herault Energie | `EnergieGazPage`, `fetchGrdf*`, BPU gaz partiel | A cadrer |
| Factures marche > DALKIA | P1/P2/P3, controle CPE, liaison finance | `CpeDalkiaPage`, fonctions `fetchCpeFinance*` | Refondre/P0 |
| Factures marche > SPIE | P2/P3 maintenance, a construire | inventaires/reference SPIE a cadrer | A cadrer |
| Factures marche > Detail facture | lignes, checks, decision, liaison XLSX | `EnergieInvoiceDetailPage`, `fetchEnergyInvoiceImport`, `downloadInvoiceLiaison` | Refondre/P0 |
| Factures marche > Export finance | matrice comptable multi-lots, liaison Excel | `fetchInvoiceCodification`, `downloadInvoiceLiaison`, `energie_accounting`, `cpe_accounting` | Refondre/P0 |

Decision UX : ce parcours sort de Fluides & consommations et devient un parcours marche transversal. Le nouvel ecran doit guider `importer -> controler -> comprendre -> decider -> exporter` pour les lots fournisseurs et prestataires.

### 4.5 Marches & contrats

| Ecran cible | Fonctionnalites a raccorder | Code actuel | Action |
|---|---|---|---|
| Marches > Vue d'ensemble | synthese contrats, alertes, factures, sites non relies | `CpeDalkiaPage`, fonctions CPE, futur SPIE | Refondre |
| Marches > CPE DALKIA > Vue marche | sites, lots, montant, perimetre, KPIs | `CpeDalkiaPage`, `fetchCpeSites`, `fetchCpeBilan` | Brancher |
| CPE DALKIA > Factures | import, controle P1/P2/P3, decision, liaison finance | `CpeDalkiaPage`, `previewCpeFinanceExport`, `importCpeFinanceExport`, `fetchCpeFinanceControls`, `downloadCpeFinanceInvoiceLiaison` | Refondre/P0 |
| CPE DALKIA > Performance | consommations, DJU, cibles, interessement | `CpeDalkiaPage`, `CpeSiteDetailPage`, `fetchCpeConsoSynthese`, `fetchCpeAtterrissage` | Brancher/P0 |
| CPE DALKIA > Referentiel | acte d'engagement, DPGF, cibles, versions, diff | `CpeDalkiaImportPage`, endpoints `/api/cpe/dalkia-ref/*` | Garder expert + exposer resume |
| CPE DALKIA > Travaux P3/P6 | devis, BPU, atterrissage P3 | `fetchCpeP3Devis`, `importCpeP3Devis`, `fetchCpeP3Atterrissage` | Brancher/P0 |
| CPE DALKIA > Indices & preuves | revisions, preuves PDF, formules | `fetchCpeRevisionIndices`, `uploadCpeRevisionEvidencePdf`, `fetchCpeRevisionEvidences` | Brancher/P0 |
| Marches > SPIE | maintenance P2, inventaires terrain, futures factures | CVC provider SPIE, pas de moteur facture complet | A cadrer |

Decision UX : DALKIA reste un moteur complet. SPIE aura son propre parcours maintenance, avec composants partages mais sans copier le CPE.

### 4.6 Technique

| Ecran cible | Fonctionnalites a raccorder | Code actuel | Action |
|---|---|---|---|
| Technique > Vue d'ensemble | couverture technique, risques, inventaires | `BuildingTechniquePage`, `CvcTechnicalReportPage` | Refondre |
| Technique > Inventaire CVC | import terrain DALKIA/SPIE, items, edition | `CvcImportPage`, `fetchCvcImportItems`, `updateCvcItem` | Brancher/P1 |
| Technique > Rattachement sites CVC | mapping source terrain -> patrimoine | `CvcSiteMappingPage`, `fetchCvcImportSiteMatches`, `applyCvcImportSiteMappings` | Brancher/P1 |
| Technique > Equipements | referentiel SYPEMI, equipements batiment | `BuildingTechniquePage`, fonctions `fetchEquipment*` | Brancher/P1 |
| Technique > F-Gaz / ESP | F-Gaz, ESP, CO2eq, plan action | `CvcRefrigerantsPage`, `fetchCvcRefrigerantDashboard`, `fetchCvcRefrigerantItems` | Brancher/P1 |
| Technique > Rapport | couverture technique par batiment/source | `CvcTechnicalReportPage`, `fetchCvcTechnicalCoverageReport` | Brancher/P1 |

Decision UX : la technique sort de `buildings/*` visuellement. Les anciennes routes peuvent rester en alias, mais la navigation doit dire `Technique`.

### 4.7 Administration

| Ecran cible | Fonctionnalites a raccorder | Code actuel | Action |
|---|---|---|---|
| Administration > Profil | compte utilisateur, mot de passe | `AccountPage`, `fetchMe`, `updateMeRequest`, `changePasswordRequest` | Brancher |
| Administration > Imports | patrimoine, BPU, DALKIA ref, CVC, codifications | pages existantes d'import, fonctions import | Garder expert |
| Administration > Connecteurs | ENEDIS sync/async, GRDF, ENGIE API potentiel | `EnergieDataOpsPage`, `EnergieGazPage`, routes `/api/engie/*` | Garder expert / cacher ENGIE API |
| Administration > Referentiels | prix, TURPE, matrices comptables fluides/CPE | `EnergieBpuPage`, `EnergieBillingPage`, accounting CPE/energie | Garder expert |
| Administration > Diagnostics | health, jobs, erreurs techniques | `/api/health`, jobs async | Cacher ou expert |
| Administration > Ville | city/tenant | `fetchCities`, `city_id` backend | Cacher pour mono-admin actuel |

Decision UX : Administration ne doit pas devenir une decharge. Elle sert aux actions rares, pas aux parcours quotidiens.

### 4.8 Hors produit

| Bloc | Code actuel | Decision |
|---|---|---|
| Pronostics | `routes/pronostics.py`, `services/pronostics.py`, pages absentes du front principal | Hors produit, ne pas raccorder |
| Proxy ENGIE API direct | `/api/engie/*`, `services/engie_client.py` | Cacher en connecteur potentiel tant que l'usage n'est pas prouve |
| Scripts ponctuels | scripts backend/imports manuels | Garder en outillage tant qu'un parcours UX n'est pas defini |

## 5. Paquet de refonte numero 1

Le premier paquet a coder doit poser le squelette sans casser l'existant.

Livrable recommande :

| Element | Contenu |
|---|---|
| Nouvelle config navigation | domaines, sous-domaines, routes cibles, aliases actuels |
| Nouveau shell | topbar/sidebar produit, layout stable, titres de domaine |
| Cockpit | files a traiter branchees sur donnees deja disponibles |
| Pages conteneurs | Patrimoine, Fluides & consommations, Marches, Technique, Administration |
| Redirections/aliases | anciennes routes conservees |

Definition de fini :

- l'utilisateur voit la nouvelle logique produit des la connexion ;
- aucune ancienne fonctionnalite utile ne disparait ;
- chaque domaine a au moins une page conteneur claire ;
- les premiers raccordements visibles sont `factures marche`, `CPE DALKIA`, `patrimoine`, `rattachements compteurs`.

## 6. Paquet de refonte numero 2

Le deuxieme paquet doit reconstruire le parcours le plus critique :

```text
Facture -> controle -> decision -> export finance
```

Sous-parcours :

| Parcours | Priorite |
|---|---|
| ENGIE electricite batiments | P0 |
| EDF eclairage public | P0 |
| Fiche detail facture | P0 |
| Liaison XLSX finance | P0 |
| CPE DALKIA factures | P0 |
| Gaz fourniture Herault Energie | P1, a cadrer |

## 7. Decisions a valider avant code

1. Valider les six domaines de navigation.
2. Confirmer que `/` devient le cockpit metier.
3. Confirmer que les imports experts partent dans Administration, avec resume dans les domaines metier.
4. Confirmer que `Factures marche` et `CPE DALKIA > Factures` sont les deux parcours finance P0.
5. Confirmer que les anciennes routes restent accessibles pendant la migration.

Recommandation :

```text
On valide ce registre comme plan de cablage,
puis on implemente le paquet 1 : shell + cockpit + pages conteneurs + aliases.
```
