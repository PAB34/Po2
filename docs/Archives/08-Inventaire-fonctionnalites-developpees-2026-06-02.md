# Inventaire des fonctionnalites developpees

> Audit transversal du depot au 2026-06-02.
> Objectif : lister ce qui existe reellement avant de conserver, fusionner, simplifier ou retirer.
> Cet inventaire decrit le code present. Il ne certifie pas que chaque fonction est deployee en production.

## 1. Photo generale

Le produit contient maintenant quatre ensembles significatifs :

1. un referentiel patrimonial hierarchique `Site -> Building -> Local` ;
2. une chaine energie electricite : ENEDIS, DJU, preconisations, TURPE, BPU et controle ENGIE ;
3. deux inventaires techniques complementaires : SYPEMI et inventaire terrain CVC ;
4. un module CPE DALKIA important : finances, controles, preuves PDF, formules/indices et referentiel
   contractuel importe depuis les fichiers XLSX d'acte d'engagement.

| Indicateur technique constate | Valeur |
|---|---:|
| Routes FastAPI declarees | 201 |
| Pages React | 21 |
| Modeles SQLAlchemy | 50 |
| Migrations Alembic | 37 (`0001` a `0037`) |
| Tests backend versionnes | 20+ (dont 6 suites CPE/DALKIA ajoutees le 2026-06-02) |

## 2. Legende

| Classement | Signification |
|---|---|
| **Coeur utile** | Valeur metier claire et workflow relie |
| **Utile a consolider** | Pertinent, mais raccordement ou ergonomie incomplet |
| **Recouvrement a arbitrer** | Deux representations proches ; ne pas supprimer avant decision metier |
| **Disponible non cable** | Backend ou helper present sans parcours frontend actif identifie |
| **Candidat au retrait** | Usage actif non identifie ; verifier la prod avant suppression |

## 3. Inventaire fonctionnel

### 3.1 Socle

| Fonctionnalite | Implementation | Interface | Classement |
|---|---|---|---|
| Healthcheck | `api/routes/health.py` | accueil, prod | **Coeur utile** |
| Auth JWT, profil, mot de passe | `auth.py`, `services/auth.py`, `core/security.py` | `/login`, `/register`, `/account` | **Coeur utile** |
| Multi-tenant commune | filtres `city_id` | transverse | **Coeur utile** |
| Scheduler ENEDIS async | `core/scheduler.py` | indirect | **Coeur utile** |
| Infra Docker/Caddy/Nginx | `saas/infra/` | n/a | **Coeur utile** |

### 3.2 Patrimoine

| Fonctionnalite | Implementation | Interface | Classement | Observations |
|---|---|---|---|---|
| Inventaire sites, batiments, locaux | `Site`, `Building`, `Local`, `services/buildings.py` | `/buildings`, `/buildings/list`, `/buildings/:id` | **Coeur utile** | Referentiel maitre |
| Import hierarchique | `services/building_naming.py`, `/api/buildings/import/*` | `/buildings/create-edit` | **Coeur utile** | Conserve `SITE`, `BATIMENT`, `LOCAL` |
| Rapprochement DGFiP / IGN / OSM | `services/building_naming.py` | cartes de selection | **Coeur utile** | Creation et correction geographique |
| CRUD patrimoine | `api/routes/buildings.py` | listes et fiches | **Coeur utile** | Sites, batiments, locaux |
| Trace IGN | `Building.ign_features_json`, migration `0023` | fiche patrimoine | **Utile a consolider** | Trace geographique |
| Compteurs manuels multi-fluides | `BuildingMeterLink`, migration `0021` | `/buildings/:id` | **Utile a consolider** | PRM, PCE, eau ; console de rapprochement absente |
| Baux locataires | aucun modele | aucune | Non developpe | `PO2-PAT-001` |

### 3.3 Energie et ENEDIS

| Fonctionnalite | Implementation | Interface | Classement |
|---|---|---|---|
| Portefeuille et fiche PRM | `services/energie.py` | `/energie`, `/energie/:prmId` | **Coeur utile** |
| Synchro ENEDIS synchrone | `enedis_sync.py`, `enedis_customer_sync.py` | endpoints `/api/energie/sync/*` | **Utile a consolider** |
| Synchro ENEDIS asynchrone FTP/AES | `enedis_async.py`, `enedis_common.py` | `EnergieAsyncJobsPanel` | **Coeur utile mais bloque externe** |
| Audit couverture donnees | `/api/energie/data-audit` | `/energie` | **Coeur utile** |
| Couplage DJU | `dju_sync.py` | fiche PRM | **Coeur utile** |
| Preconisations puissance | `power_recommendations.py` | `/energie/preconisations` | **Coeur utile** |

### 3.4 BPU, TURPE et configuration tarifaire

| Fonctionnalite | Implementation | Interface | Classement | Observations |
|---|---|---|---|---|
| Historique BPU normalise | 5 tables `bpu_*`, migration `0015` | `/energie/bpu` | **Coeur utile** | Historique EDF, ENGIE et gaz lot 7 |
| Import XLSX canonique BPU | `scripts/import_bpu_xlsx.py` | exploitation | **Coeur utile** | Strategie fiable retenue |
| Import gaz lot 7 | `scripts/import_bpu_gas_lot7.py` | exploitation | **Coeur utile** | TotalEnergies distinct du P1 DALKIA |
| Timeline et TURPE CRE | `/api/bpu/timeline`, `turpe.py` | `/energie/bpu` | **Coeur utile** | Evolution des composantes et contexte reglementaire |
| Tableau editable BPU | `/api/bpu/editable-rows`, CRUD `bpu_*` | `/energie/bpu` | **Utile a consolider** | UI surtout cablee pour modifier les composantes |
| Configuration courante | `BillingConfig`, `BillingPriceEntry`, `BillingHphcSlot`, `BillingBpuLine` | `/energie/facturation` | **Recouvrement a arbitrer** | Repli controle facture et calculs courants |
| Parser PDF BPU | `services/bpu.py`, `/api/bpu/import` | exploitation | **Utile secondaire** | En pause au profit du XLSX |

### 3.5 Factures ENGIE

| Fonctionnalite | Implementation | Interface | Classement |
|---|---|---|---|
| Import historique PDF | `invoice_parsers/engie_pdf.py` | parcours historique | **Utile secondaire** |
| Import XLSX asynchrone | `engie_xlsx.py`, `engie_xlsx_import.py` | `/energie/factures` | **Coeur utile** |
| Lots persistants | `EnergyInvoiceBatch`, `EnergyInvoiceBatchItem` | `/energie/factures` | **Coeur utile** |
| Normalisation facture | `EnergyInvoice`, `EnergyInvoiceSite`, `EnergyInvoicePeriod`, `EnergyInvoiceLine`, `EnergyInvoiceMeterRead`, `EnergyInvoiceCheck` | indirect | **Coeur utile** |
| Controle BPU historique puis repli courant | `invoice_bpu.py`, `invoice_analysis.py` | liste, detail, rapport | **Coeur utile** |
| Controles TURPE, ENEDIS, qualite et decision | `invoice_analysis.py` | `/energie/factures/:id` | **Coeur utile** |
| Filtres facettes et graphe mensuel | `EnergieInvoicesPage.tsx` | `/energie/factures` | **Coeur utile** |
| Proxy API ENGIE Entreprises | `engie_client.py`, `/api/engie/*` | aucune UI identifiee | **Disponible non cable** |

### 3.6 Gestion technique

| Fonctionnalite | Implementation | Interface | Classement |
|---|---|---|---|
| Referentiel SYPEMI | `EquipmentReference`, import CSV | `/buildings/technique` | **Coeur utile** |
| Assignations techniques synthetiques | `BuildingEquipment`, `equipment.py` | `/buildings/technique` | **Utile a consolider** |
| Inventaire terrain CVC | `CvcInventoryItem`, `cvc.py` | `/buildings/cvc-import`, onglet Terrain | **Coeur utile** |
| Separation CVC / enveloppe | filtre UI partiel | `/buildings/technique` | **Utile a consolider** |
| Occupation, programmation, BACS | aucun modele operationnel | aucune | Non developpe |

### 3.7 CPE DALKIA : socle et finances

| Fonctionnalite | Implementation | Interface | Classement |
|---|---|---|---|
| Sites CPE, releves, prix gaz, resultats | `CpeSite`, `CpeGazReleve`, `CpePrixGaz`, `CpeResultatAnnuel` | `/cpe`, `/cpe/sites/:id` | **Coeur utile** |
| Import CSV et bilan annuel | `cpe_import.py`, `cpe.py` | `/cpe` | **Coeur utile** |
| Import export finances DALKIA | `cpe_finance_preview.py`, `cpe_accounting.py` | `/cpe` | **Coeur utile** |
| Matrice comptable editable | `CpeAccountingNatureRule`, `CpeAccountingSiteMapping` | `/cpe` | **Coeur utile** |
| References contractuelles | `CpeContractReference` | `/cpe` | **Coeur utile** |
| Controles factures | `CpeFinanceControl`, `cpe_accounting.py` | `/cpe` > Controle factures | **Coeur utile** |
| Cockpit financier annuel | `CpeDalkiaPage.tsx` | `/cpe` > Factures | **Coeur utile** |
| Export liaison et rapport global XLSX | routes `/liaison.xlsx`, `/report.xlsx` | `/cpe` | **Coeur utile** |
| Formules, indices et preuves PDF | migrations `0025`, `0030`, `0031` | `/cpe` > Formules et indices | **Coeur utile** |

### 3.8 CPE DALKIA : moteur acte d'engagement XLSX

Cette partie recente est un sous-module a part entiere.

| Fonctionnalite | Implementation | Interface | Classement |
|---|---|---|---|
| Preview Lot 1 / Lot 2 | `services/cpe_dalkia_import.py` | `/cpe/dalkia-import` | **Coeur utile** |
| Referentiel versionne | tables `cpe_dalkia_ref_*`, migrations `0033` a `0036` | import DALKIA | **Coeur utile** |
| Parsing P2/P3 par site et annee | `CpeDalkiaRefP2P3` | preview + controle facture | **Coeur utile** |
| Parsing cibles GAZ/ELEC | `CpeDalkiaRefCible` | preview + bilan | **Coeur utile** |
| Parsing P1 gaz par site | `CpeDalkiaRefP1Gaz` | preview | **Utile a consolider** |
| Parsing tarifs et coefficients P1 (formule Pu) | `CpeDalkiaRefP1Tarif`, migration `0036` | preview onglet P1 | **Coeur utile** |
| Parsing RECAP MARCHE | `CpeDalkiaRefRecap` | preview + sync P1 | **Coeur utile** |
| Parsing travaux APE | `CpeDalkiaRefApe` | preview | **Utile a consolider** |
| Parsing BPU travaux P3 (Annexe 7) | `CpeDalkiaRefBpu`, migration `0037` (132 prestations + 7 taux + 4 coef) | preview onglet BPU, GET `/imports/{id}/bpu` | **Coeur utile (socle controle devis P3)** |
| Resolution annuelle NB | `resolve_nb_for_year_detailed()` | bilan `/cpe` (vide en prod, cf §9) | **Coeur utile mais sans donnees prod** |
| Controle base P2/P3 vs DALKIA | `_control_p2p3_base_against_dalkia()` (`p2p3_base_dpgf`) | controle factures | **Coeur utile** (mapping corrige le 2026-06-02 : 56 faux positifs -> 1 vrai ecart) |
| Controle prix gaz vs OS N°3 | `_control_p1_gaz_pu_os3()` (`p1_gaz_pu_os3`) | controle factures | **Coeur utile** (48 ok / 0 ecart en prod) |
| Sync acompte P1 depuis RECAP | `sync_p1_reference_from_recap()` | bouton import DALKIA | **Coeur utile** |

Voir [[energie/CPE-DALKIA/17-Referentiel-DALKIA-Import]].

## 4. Recouvrements a arbitrer

### 4.1 Deux sources BPU

| Source | Role | Decision recommandee |
|---|---|---|
| `bpu_*` | Historique contractuel fiable et multi-annees | Garder comme source de verite historique |
| `BillingConfig` / `BillingBpuLine` | Configuration courante et repli si aucun match historique exact | Garder provisoirement ; documenter la convergence |

Ce n'est pas encore un doublon supprimable : `invoice_analysis.py` utilise volontairement les deux.

### 4.2 Deux inventaires techniques

| Source | Role | Decision recommandee |
|---|---|---|
| `BuildingEquipment` | Vue synthetique editable et liee a SYPEMI | Garder pour le diagnostic agrege |
| `CvcInventoryItem` | Releve terrain detaille importe | Garder comme source terrain |

Il manque une regle explicite : un equipement terrain doit-il alimenter ou seulement suggerer une
assignation SYPEMI ?

### 4.3 Trois representations des sites

| Source | Role | Limite |
|---|---|---|
| `Site` patrimoine | Referentiel patrimonial maitre | Pas encore relie au CPE |
| `CpeSite` | Site operationnel du moteur CPE historique | Seed et codes propres |
| `CpeDalkiaRefSite` | Site contractuel versionne issu de l'acte d'engagement | Pas de FK patrimoine ou CPE |

La console `PO2-PAT-003` doit relier les objets sans les fusionner brutalement : un site patrimonial,
un site operationnel et une version contractuelle n'ont pas le meme cycle de vie.

### 4.4 Deux familles de factures

| Famille | Role | Decision recommandee |
|---|---|---|
| `EnergyInvoice*` | Factures fournisseurs generiques, aujourd'hui ENGIE | Garder pour ENGIE puis TotalEnergies/SUEZ |
| `CpeFinanceInvoice` / `CpeFinanceLine` | Factures DALKIA CPE et liaison finances | Garder separe : controles tres specifiques |

## 5. Disponible mais non cable ou partiellement cable

### 5.1 Proxy API ENGIE

`/api/engie/*` expose profils, sites, contrats, consommations, factures et demandes, mais aucun appel
frontend n'a ete identifie. Le flux actif facture passe par l'upload XLSX. Conserver seulement si l'acces
API est contractualise ou attendu ; sinon feature flag ou archivage apres verification prod.

### 5.2 Helpers frontend sans appelant React actuel

Le balayage statique de `src/lib/api.ts` signale notamment :

- anciens helpers de sync ENEDIS synchrone : `fetchSyncStatus`, `startSync`, `fetchMaxPowerSyncStatus`,
  `startMaxPowerSync`, `fetchLoadCurveSyncStatus`, `startLoadCurveSync` ;
- helpers de configuration facturation `fetchBilling*`, `setBilling*`, `patchBillingConfig` ;
- fonctions ponctuelles BPU, CVC et CPE facture par facture.

Cela ne prouve pas qu'un endpoint backend est inutile : certains servent a l'exploitation ou sont appeles
directement depuis une page. C'est une liste de revue manuelle.

### 5.3 CRUD BPU plus large que l'UI

Le backend sait creer, modifier et supprimer documents, segments, periodes, composantes et charges fixes.
Le tableau React expose surtout la modification des composantes existantes.

### 5.4 Detail DALKIA persiste non reconsultable

Apres confirmation d'un acte d'engagement, la preview affiche P2/P3, cibles, P1, APE et RECAP. Le backend
expose les endpoints persistants `/p2p3`, `/cibles`, `/ape`, `/recap`, mais l'interface ne les recharge pas.

### 5.5 Ecarts aux conventions frontend

Deux pages effectuent encore des `fetch()` directs hors de `src/lib/api.ts` :

- `CpeDalkiaImportPage.tsx` ;
- `EnergieBillingPage.tsx`.

## 6. Candidats au retrait ou a l'archivage

Ne rien supprimer sans verifier production, scripts d'exploitation et besoin utilisateur.

| Candidat | Pourquoi le revoir | Action conseillee |
|---|---|---|
| Proxy `/api/engie/*` | Aucun appel frontend actif identifie | Confirmer strategie API ENGIE ; feature flag ou archivage |
| Helpers sync ENEDIS synchrones non affiches | L'async est prioritaire | Garder services de secours, retirer seulement la surface morte confirmee |
| Parser PDF BPU automatique | Remplace en pratique par le XLSX | Conserver en maintenance, sans nouvel investissement |
| Helpers frontend non appeles | Dette de surface | Supprimer progressivement apres build et verification |
| Documentation centrale obsolete | Snapshot et roadmap sous-estiment le CPE DALKIA | Corriger les documents centraux |

## 7. Priorites de consolidation

### P0 - Cockpit documentaire fiable

1. Utiliser ce fichier comme inventaire transversal.
2. Mettre a jour [[04-Etat-actuel-du-dev]] apres chaque increment DALKIA.
3. Corriger progressivement [[03-Roadmap-fonctionnalites]], encore centree sur le 2026-05-19.

### P1 - Relier les referentiels

1. Implementer `PO2-PAT-003`.
2. Rapprocher `Site`, `CpeSite`, `CpeDalkiaRefSite`, PRM et PCE.
3. Conserver les objets ambigus dans une file `a_traiter`.

### P1 - Continuer le moteur DALKIA

1. Reconsulter les donnees persistees sans re-uploader le fichier.
2. Parser les feuilles restantes : P3.4 detaille, BPU/DQE Annexe 7, coefficients Annexe 1.
3. Creer le suivi operationnel APE.
4. Exploiter les coefficients P1 pour le controle detaille des revisions.

### P2 - Reduire les couches historiques

1. Decider la convergence `bpu_*` / `BillingBpuLine`.
2. Decider la consolidation `CvcInventoryItem` / `BuildingEquipment`.
3. Revoir le proxy ENGIE et les helpers non appeles.
4. Centraliser les appels frontend dans `src/lib/api.ts`.

## 8. Etat reel en production et ecarts d'operabilite (verifie 2026-06-02)

> Verifie directement sur la base de production (lecture seule + un recalcul des controles).
> But : separer **ce que le moteur sait faire** de **ce que l'utilisateur peut reellement faire ou voir
> depuis l'interface**. C'est ici que se loge l'essentiel du sentiment de « je ne saurais pas le faire ».

### 8.1 Photo des donnees en prod

| Domaine | Etat constate | Consequence UX |
|---|---|---|
| `cpe_sites` (intéressement) | **0 site** (seed jamais lance en prod) | Le bilan `/cpe`, le NB par annee et les badges DLK/SITE sont **vides** : rien a voir tant que les sites ne sont pas crees |
| Finances DALKIA | 625 factures, 5805 lignes, 75 mappings sites | Operationnel |
| Referentiel DALKIA | 2 imports actifs (Lot 1 + Lot 2), catalogues complets | Operationnel |
| Controle `p2p3_base_dpgf` | 349 ok / **1 ecart reel** (CCAS 04 P3.4 : 13 216 vs 14 641) / 10 bloques (codes `VDS-PSC` + 1 ligne sans code) | A exposer dans une file lisible |
| Controle `p1_gaz_pu_os3` | 48 ok / **0 ecart** | OK |
| Controle `p1_gaz_acompte_dpgf` | 40 ok / **21 ecarts** | Reference P1 pas encore synchronisee (ecart seed 341 293 vs RECAP 317 775) |

### 8.2 Operations faites « hors interface » qu'il faut rendre faisables dans l'UI

Lors de la verification, plusieurs actions n'ont ete possibles que par script / SQL / SSH. Ce sont les
trous d'operabilite a combler en priorite (renvoi vers [[09-Vision-produit-et-navigation-UX]]) :

| Operation realisee | Comment je l'ai faite | Disponible dans l'UI ? | Cible UX |
|---|---|---|---|
| Peupler `cpe_sites` (sites du marche) | script `seed_cpe_sites.py` (non lance en prod) | ❌ aucun ecran | `Administration > Imports > Contrats` : bouton « Initialiser les sites CPE depuis l'import DALKIA » |
| Recalculer tous les controles de factures | `build_finance_control_report(recalculate=True)` en conteneur | ⚠️ a verifier / rendre explicite | Bouton « Recalculer » visible sur `Controle factures DALKIA` |
| Lire le detail des controles (ok/ecart/bloque + message) | requete SQL `cpe_finance_controls` | ⚠️ partiel (cockpit) | File priorisee lisible : poste, site, attendu vs facture, motif |
| Reconcilier un code site desaligne (`VDS-PSC`, ligne sans code) | aucun outil | ❌ aucun ecran | Console `Rapprochements` + edition du mapping finance |
| Re-consulter les donnees DALKIA persistees (P2/P3, cibles, P1, APE, RECAP, BPU) | endpoints GET existants | ❌ non recharges par l'UI | Onglets de consultation sur l'import actif (cf §5.4) |
| Verifier la sante prod / le commit deploye | SSH + `curl /api/health` | ❌ hors produit | Bandeau d'etat / page diagnostic (optionnel) |
| Synchroniser la reference d'acompte P1 | bouton « Synchroniser la ref. P1 » | ✅ existant | OK (a confirmer apres seed) |

**Lecture** : le moteur DALKIA est puissant et correct, mais une partie de son pilotage vit encore
« sous le capot ». Tant que ces actions ne sont pas dans l'interface, l'utilisateur depend d'interventions
techniques — d'ou la perte de fluidite ressentie.

## 9. Methode

L'audit a croise `app/api/router.py`, les routes FastAPI, `app/models/__init__.py`, les migrations
`0001` a `0036`, les routes React, `src/lib/api.ts`, les `fetch()` directs et les notes du vault, notamment
[[Backlog]], [[04-Etat-actuel-du-dev]] et [[energie/CPE-DALKIA/17-Referentiel-DALKIA-Import]].

