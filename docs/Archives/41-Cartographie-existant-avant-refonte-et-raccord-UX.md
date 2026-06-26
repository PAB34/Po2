# 41 - Cartographie de l'existant avant refonte et raccord UX

Date : 2026-06-25  
Objet : répondre à la question "a-t-on bien pris connaissance de tout ce qui a déjà été développé avant refonte ?" et fixer le garde-fou de raccordement entre l'existant, les réponses utilisateur et la V1.

## 1. Réponse courte

Oui, l'existant a été repris sur une base concrète : documentation centrale, routes frontend, routeur backend, services métier, contrats d'écran V1, analyse des vraies factures et réponses utilisateur du document 39.

Mais la bonne posture n'est pas de considérer que tout est "connu une fois pour toutes". La plateforme contient déjà beaucoup de moteurs. Pour chaque nouvel écran de refonte, il faut appliquer la règle suivante :

1. identifier les capacités déjà développées ;
2. vérifier les données réelles et les modèles existants ;
3. décider ce qui est réutilisé, refondu, masqué ou complété ;
4. seulement ensuite coder l'UX définitive.

La refonte doit donc être une absorption progressive de l'existant, pas une reconstruction parallèle qui oublierait les moteurs déjà livrés.

## 2. Sources relues pour cette cartographie

Documents structurants :

- `docs/04-Etat-actuel-du-dev.md`
- `docs/08-Inventaire-fonctionnalites-developpees-2026-06-02.md`
- `docs/14-Catalogue-fonctionnalites-commentees-et-reaffectation.md`
- `docs/18-Registre-raccordement-frontend.md`
- `docs/20-Cap-direction-2026-factures-budget-CVC-maintenance.md`
- `docs/34-Contrat-ecran-Fluides-V1.md`
- `docs/35-Contrat-ecran-Factures-Decisions-V1.md`
- `docs/36-Contrat-ecran-Cockpit-Sites-V1.md`
- `docs/37-Plan-migration-React-refonte-V1.md`
- `docs/39-Questions-avant-raccord-factures-matrices-V1.md`
- `docs/40-Analyse-factures-reelles-pour-matrice-comptable.md`

Code inspecté :

- routes React dans `saas/frontend/src/App.tsx` ;
- pages historiques dans `saas/frontend/src/pages/` ;
- laboratoire V1 dans `saas/frontend/src/features/` ;
- design system V1 dans `saas/frontend/src/design-system/` ;
- routeur backend dans `saas/backend/app/api/router.py` ;
- services métier dans `saas/backend/app/services/` ;
- modèles et schémas backend dans `saas/backend/app/models/` et `saas/backend/app/schemas/`.

## 3. Carte réelle des grands domaines existants

### 3.1 Patrimoine, sites, bâtiments, locaux

Capacités déjà développées :

- référentiel `Site`, `Building`, `Local` ;
- imports DGFiP / MAJIC et logique de nommage bâtiment ;
- rattachements IGN / OSM / coordonnées ;
- compteurs rattachés aux bâtiments ;
- file de rapprochement patrimoine pour PRM/PCE vers bâtiment ou site.

Code principal :

- backend : `services/buildings.py`, `services/building_naming.py`, `services/meter_matching.py`, `services/patrimoine_match.py` ;
- routes : `/api/buildings`, `/api/patrimoine/matches` ;
- frontend : `BuildingsListPage`, `BuildingDetailPage`, `BuildingCreateEditPage`, `MeterMatchingPage`, `PatrimoineMatchPage`.

Statut refonte :

- à réutiliser comme socle maître ;
- à repositionner en "Sites 360°" côté UX ;
- ne pas recréer un second référentiel site ;
- priorité : relier proprement site/bâtiment/compteur/contrat/facture/équipement.

### 3.2 Fluides : électricité ENEDIS, gaz GRDF, futur eau

Capacités déjà développées :

- portefeuille PRM ;
- données de consommation journalière ;
- courbes de charge ;
- puissance maximale ;
- profils annuels ;
- DJU mensuels, performance DJU et saisonnalité ;
- audit de couverture et fraîcheur des données ;
- collecte ENEDIS synchrone de secours et collecte async ;
- référentiel PCE GRDF ;
- consommations gaz mensuelles ;
- enrichissement contractuel GRDF ;
- rapprochement GRDF/P1 DALKIA.

Code principal :

- backend : `services/energie.py`, `services/enedis_sync.py`, `services/enedis_async.py`, `services/dju_sync.py`, `services/power_recommendations.py`, `services/grdf_*`, `services/gas_analytics.py` ;
- routes : `/api/energie`, `/api/energie/sync/*`, `/api/energie/sync/async/*`, `/api/grdf/*` ;
- frontend : `EnergiePage`, `EnergieDetailPage`, `EnergieDataOpsPage`, `EnergieRecommendationsPage`, `EnergieGazPage`, `features/fluids/FluidsPortfolioPageV1.tsx`.

Statut refonte :

- le libellé UX doit devenir `Fluides` ;
- les noms techniques `energie` peuvent rester temporairement en backend ;
- les données ENEDIS/GRDF sont réutilisables ;
- l'eau est à construire ;
- la surveillance des abonnements doit utiliser les courbes de charge et les paramètres contractuels ;
- les DJU doivent rester transversaux et explicités selon usage.

### 3.3 Factures électricité ENGIE / EDF

Capacités déjà développées :

- import XLSX ENGIE ;
- import CSV EDF ;
- lots d'import ;
- normalisation en facture / site / période / ligne ;
- contrôles BPU ;
- contrôles TURPE ;
- contrôles de période, doublons, qualité, consommation, puissance et décision ;
- détail facture ;
- export liaison finances existant pour certaines sources.

Code principal :

- backend : `services/engie_xlsx_import.py`, `services/edf_csv_import.py`, `services/invoice_normalization.py`, `services/invoice_analysis.py`, `services/invoice_bpu.py`, `services/energie_accounting.py` ;
- modèles : `invoice.py` ;
- frontend : `FacturesPage`, `EnergieInvoicesPage`, `EnergieInvoiceDetailPage`.

Ce que l'analyse des vraies factures a confirmé :

- ENGIE : parser solide, 185 factures et 1267 lignes site/FIC dans l'export analysé ;
- EDF : parser opérationnel mais attention aux avoirs, périodes anciennes et périodes manquantes ;
- les composants récurrents existent déjà et sont utilisables pour la future matrice comptable.

Statut refonte :

- réutiliser les parseurs et contrôles ;
- déplacer l'expérience vers `Factures & décisions` ;
- transformer la liste historique en file opérationnelle ;
- brancher l'imputation comptable sur les matrices versionnées ;
- gérer historique/réimport sans retraiter les factures déjà validées/exportées.

### 3.4 Gaz TotalEnergies

Capacités déjà développées :

- import factures gaz TotalEnergies ;
- portefeuille par site/PCE ;
- rapprochement PCE vers bâtiment ;
- contrôle structurel HT / TVA / TTC ;
- contrôles BPU gaz, ATRD/ATRT, accise/TICGN, CTA, TVA éditable ;
- fiche de vérification détaillée par facture ;
- lignes synthétiques déjà extractibles pour matrice comptable.

Code principal :

- backend : `services/gas_invoice.py`, `services/gas_analytics.py`, `models/gas_invoice.py`, `models/gas_bpu.py`, `models/gas_network_tariff.py`, `models/gas_tax.py`, `models/gas_revisable.py` ;
- route : `/api/gas/invoices/*` ;
- frontend : `EnergieGazPage`, composants gaz associés dans les pages factures.

Ce que l'analyse des vraies factures a confirmé :

- 58 lignes/factures ;
- 53 factures, 5 avoirs ;
- 10 PCE ;
- structure HT/TTC cohérente ;
- quelques sites sans nom mais PCE présent.

Statut refonte :

- très bon candidat pour le premier raccord facture gaz ;
- intégrer dans `Fluides > Gaz` pour les consommations et dans `Factures & décisions` pour le contrôle/validation ;
- prévoir contacts fournisseur et brouillon de mail en cas d'anomalie.

### 3.5 CPE DALKIA et factures DALKIA

Capacités déjà développées :

- sites CPE ;
- relevés, prix gaz, DJU, bilan annuel ;
- import finances DALKIA ;
- matrice comptable historique CPE ;
- contrôles de factures CPE ;
- export liaison finance ;
- preuves PDF et indices ;
- suivi marché ;
- import acte d'engagement Lot 1 / Lot 2 ;
- référentiel versionné DALKIA : P1, P2/P3, cibles, APE, RECAP, BPU P3 ;
- atterrissage CPE.

Code principal :

- backend : `services/cpe.py`, `services/cpe_accounting.py`, `services/cpe_finance_preview.py`, `services/cpe_market_tracking.py`, `services/cpe_dalkia_import.py`, `services/cpe_dpgf_p1.py`, `services/cpe_atterrissage.py`, `services/cpe_p3_devis.py` ;
- routes : `/api/cpe/*`, `/api/cpe/dalkia-ref/*` ;
- frontend : `CpeDalkiaPage`, `CpeSiteDetailPage`, `CpeDalkiaImportPage`.

Ce que l'analyse des vraies factures a confirmé :

- 4941 lignes finance ;
- 353 factures ;
- 4 contrats présents dans l'export analysé ;
- matrice bêta majoritairement exploitable mais avec trous importants ;
- lignes non couvertes, à ventiler, à arbitrer ou en attente fournisseur ;
- les périodes avant le nouveau marché autour du 11 octobre 2025 doivent être ignorées/isolées pour le marché actuel.

Statut refonte :

- ne pas fusionner brutalement avec les factures ENGIE/EDF ;
- afficher DALKIA dans la file commune Factures & décisions, mais garder ses contrôles spécifiques ;
- construire une configuration de matrice DALKIA par tiers/contrat/poste/service vendu ;
- bloquer toute validation si une ligne récurrente identifiée n'est pas couverte ou cohérente.

### 3.6 Matrices comptables versionnées

Capacités déjà développées :

- modèle backend durable `accounting_matrix_contracts`, `accounting_matrix_versions`, `accounting_matrix_rules`, `invoice_accounting_snapshots` ;
- version active jamais écrasée ;
- import/export XLSX ;
- preview de diff avant commit ;
- seed depuis l'existant ;
- moteur d'imputation ;
- snapshots immuables ;
- validation, correction manuelle, export finance ;
- extraction automatique de lignes facture depuis ENGIE/EDF, TotalEnergies gaz et CPE DALKIA ;
- page laboratoire `/refonte-v1/matrices` connectée au vrai backend.

Code principal :

- backend : `services/accounting_matrix.py`, `services/accounting_matrix_apply.py`, `services/accounting_matrix_xlsx.py`, `services/accounting_matrix_invoice_lines.py` ;
- route : `/api/accounting-matrices/*` ;
- frontend : `features/matrices/MatrixAdminPageV1.tsx`, `features/invoices/useInvoiceAccountingSnapshotsV1.ts`.

Écart majeur détecté grâce aux réponses utilisateur :

- la matrice ne doit pas seulement être appliquée depuis une facture ;
- il faut un écran de configuration par tiers facturant ;
- l'écran doit importer un fichier de factures, détecter les données récurrentes, proposer une table éditable, permettre export/import XLSX, contrôler la couverture, puis enregistrer/refuser avec motif ;
- une facture future doit ensuite hériter automatiquement de la matrice validée.

Statut refonte :

- backend très avancé ;
- UX de configuration à concevoir maintenant ;
- règles de rôles à corriger : décision utilisateur = tous les rôles sauf `fluides` et `technicien CVC`, alors que le backend actuel autorise surtout admin/finance/compta ;
- le bouton d'application automatique ne doit pas être activé tant que le choix contrat/matrice et les règles de couverture ne sont pas clairs.

### 3.7 BPU, TURPE et référentiels tarifaires

Capacités déjà développées :

- référentiel BPU normalisé ;
- import XLSX canonique ;
- historique EDF/ENGIE/gaz lot 7 ;
- timeline ;
- TURPE CRE pédagogique ;
- tableau éditable ;
- configuration courante de facturation.

Code principal :

- backend : `services/bpu.py`, `services/billing.py`, `services/billing_bpu_sync.py`, `services/bpu_templates.py`, `services/turpe.py` ;
- routes : `/api/bpu/*`, `/api/billing/*` ;
- frontend : `EnergieBpuPage`, `EnergieBillingPage`.

Statut refonte :

- à conserver comme référentiels de preuve ;
- à présenter dans une logique pédagogique "à la TURPE" ;
- à relier aux contrôles facture et aux atterrissages financiers ;
- clarifier la coexistence entre BPU historique et configuration courante.

### 3.8 Technique, CVC, F-Gaz, ESP, PPT

Capacités déjà développées :

- référentiel équipement ;
- équipement bâtiment ;
- import inventaire terrain CVC ;
- matching site/bâtiment/local ;
- références de durée de vie ;
- recalcul de références ;
- cockpit F-Gaz / ESP ;
- actions et conformité ;
- rapport technique.

Code principal :

- backend : `services/cvc.py`, `services/equipment.py` ;
- routes : `/api/cvc/*`, `/api/equipment/*` ;
- frontend : `BuildingTechniquePage`, `CvcImportPage`, `CvcSiteMappingPage`, `CvcRefrigerantsPage`, `CvcTechnicalReportPage`.

Statut refonte :

- le socle est réel ;
- l'UX doit devenir "Technique & PPT" avec décisions chiffrées ;
- relier équipements, criticité, coût prévisionnel et couverture maintenance ;
- éviter de mélanger le domaine "Fluides énergie/eau/gaz" avec "fluides frigorigènes".

### 3.9 Maintenance DALKIA / SPIE et couverture des sites

Capacités déjà développées :

- côté DALKIA : périmètre et référentiel contractuel très avancés ;
- côté patrimoine : sites/bâtiments/compteurs disponibles ;
- côté CVC : équipements et inventaire terrain disponibles ;
- rapprochements patrimoine déjà amorcés.

Manques :

- SPIE absent faute de corpus réel ;
- modèle générique de contrat de maintenance à finaliser ;
- matrice de couverture maintenance par site/bâtiment/équipement à construire ;
- détection claire des sites non entretenus à raccorder à Sites 360°.

Statut refonte :

- DALKIA peut alimenter le raisonnement ;
- SPIE ne doit pas être inventé ;
- priorité UX : une vue "couverture maintenance" lisible, puis drill-down site.

### 3.10 Refonte React V1 et design system

Capacités déjà développées :

- design tokens PO2 ;
- thème automatique clair/sombre ;
- composants communs : bouton, carte, KPI, badge, drawer, table, filtres, segments ;
- shell V1 ;
- routes laboratoire :
  - `/refonte-v1`
  - `/refonte-v1/factures`
  - `/refonte-v1/fluides`
  - `/refonte-v1/sites`
  - `/refonte-v1/matrices`
- pages mockées cockpit, factures, fluides, sites ;
- page matrices connectée au vrai backend ;
- hook factures V1 avec fallback API/mocks ;
- lecture de snapshot comptable dans le drawer facture.

Code principal :

- `saas/frontend/src/design-system/`
- `saas/frontend/src/app/AppShellV1.tsx`
- `saas/frontend/src/features/*`
- `saas/frontend/src/pages/RefonteV1*.tsx`

Statut refonte :

- base saine mais encore laboratoire ;
- ne remplace pas les pages historiques ;
- prochaines tranches : configuration matrice par tiers, file factures réelle, puis Fluides/Sites raccordés.

## 4. Ce qui est déjà suffisamment connu pour avancer

Les points suivants sont assez consolidés pour être codés sans nouvelle grande question :

1. Le domaine visible doit être `Fluides`, pas `Énergie`, quand on parle électricité/gaz/eau.
2. Les factures doivent être traitées dans une file commune opérationnelle avec filtres contrat/anomalies.
3. La fiche facture doit afficher synthèse courte puis détails dépliables.
4. Une facture avec exception d'imputation ne doit pas être validée.
5. Une facture identique déjà validée/exportée doit devenir historique et non retraitée.
6. Le brouillon de mail fournisseur doit être généré sans envoi direct en V1.
7. Plusieurs contacts fournisseur doivent être possibles par contrat.
8. Les matrices doivent être versionnées et ne jamais écraser une version active.
9. Les vraies factures DALKIA imposent de gérer contrat, poste, service vendu, période et statut de règle.
10. Les données ENEDIS/GRDF/DJU existent déjà assez pour préparer le portefeuille Fluides, mais l'eau reste à construire.

## 5. Points où la refonte ne doit surtout pas repartir de zéro

| Domaine | Ne pas refaire | Réutiliser / raccorder |
|---|---|---|
| Patrimoine | un nouveau référentiel site | `Site`, `Building`, `Local`, rapprochements |
| Électricité | un nouveau parser ENGIE/EDF | parsers et normalisation existants |
| Gaz | un nouveau moteur TotalEnergies | `gas_invoice.py` + référentiels gaz |
| DALKIA | une matrice simplifiée fournisseur/nature | contrats, postes, services vendus, référentiel DALKIA |
| Matrices | une table plate non versionnée | backend matrices versionnées déjà créé |
| BPU/TURPE | des valeurs en dur dans le front | référentiels backend et style pédagogique TURPE |
| CVC | une fiche équipement isolée | inventaire terrain, SYPEMI, F-Gaz/ESP |
| Refonte UI | un prototype déconnecté permanent | laboratoire React raccordé tranche par tranche |

## 6. Ce qui reste à vérifier avant chaque gros écran

Même après cette cartographie, chaque écran doit passer par une mini-revue :

1. route/API déjà existante ;
2. service métier existant ;
3. modèle de donnée et statut de qualité ;
4. page historique utile à préserver ;
5. source de vérité métier ;
6. données réelles disponibles ;
7. droits et rôles ;
8. état vide / historique / erreur ;
9. preuve visible pour l'utilisateur ;
10. action finale attendue.

Ce rituel est important parce que le projet a déjà beaucoup de couches historiques utiles, mais pas toujours rangées dans l'expérience cible.

## 7. Écarts détectés entre V1 actuelle et décisions utilisateur

### 7.1 Matrice comptable

Décision utilisateur : la configuration de matrice doit être faite par tiers facturant à partir des données récurrentes détectées dans les exports de factures.

État actuel : le backend matrice est avancé, mais l'UX `/refonte-v1/matrices` reste encore centrée contrat/version/règles.

Action à faire :

- créer un parcours "Configurer une matrice depuis un export facture" ;
- détecter les composants récurrents ;
- afficher la table à compléter ;
- exporter/importer XLSX ;
- contrôler que tout élément récurrent est couvert ;
- refuser l'activation si une donnée récurrente reste non couverte.

### 7.2 Rôles

Décision utilisateur : tous les rôles sauf `fluides` et `technicien CVC` peuvent valider/exporter.

État actuel : le backend autorise surtout `ADMIN`, `SUPERADMIN`, `FINANCE`, `COMPTA`, `COMPTABILITE`.

Action à faire :

- vérifier les rôles réellement présents en base ;
- traduire la décision utilisateur dans une règle backend stable ;
- aligner l'UX lecture seule.

### 7.3 Historique et réimport

Décision utilisateur : une facture identique déjà validée/exportée doit être affichée en historique et non retraitée.

État actuel : le modèle snapshot existe, mais le comportement complet de dédoublonnage/historique doit être branché dans les imports et la file V1.

Action à faire :

- calculer une empreinte stable facture ;
- marquer historique si déjà traitée ;
- alerter si même facture mais contenu différent.

### 7.4 Fluides

Décision utilisateur : Énergie devient Fluides dès que le périmètre couvre électricité/gaz/eau.

État actuel : les routes et beaucoup de noms techniques restent `energie`.

Action à faire :

- renommer l'expérience visible ;
- garder alias technique temporaire ;
- préparer l'eau sans casser l'électricité/gaz existants.

### 7.5 DALKIA nouveau marché

Décision utilisateur : le nouveau marché est opérationnel autour du 11 octobre 2025 ; ce qui est antérieur ne doit pas polluer le contrôle courant.

État actuel : les données et contrôles existent, mais l'UX doit rendre cette coupure explicite.

Action à faire :

- ajouter un contrôle "période facturée vs période de marché actif" ;
- isoler/archiver l'ancien périmètre ;
- ne pas bloquer la V1 actuelle avec les contrats thalassothermie hors marché Ville.

## 8. Prochaine étape recommandée

La prochaine étape logique n'est pas de faire un nouvel écran décoratif. C'est de brancher le premier parcours sensible avec la bonne profondeur métier :

1. créer le parcours V1 de configuration de matrice par tiers facturant ;
2. commencer par DALKIA car c'est le plus complexe et le plus structurant ;
3. utiliser les vraies données analysées dans le document 40 ;
4. ensuite appliquer le même modèle à ENGIE, EDF et TotalEnergies ;
5. puis raccorder la file Factures & décisions à ces matrices activées.

Cela respecte le cap direction : facture -> contrôle -> décision -> matrice comptable -> export/historique, sans perdre l'existant.

## 9. Conclusion de garde-fou

À partir de maintenant, toute nouvelle tranche de refonte doit citer explicitement :

- les pages historiques concernées ;
- les services backend existants ;
- les documents de cadrage ;
- les données réelles disponibles ;
- ce qui est réutilisé ou abandonné.

Si cette preuve n'est pas produite, il faut considérer que la tranche n'est pas prête à coder.

