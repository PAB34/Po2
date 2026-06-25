# État actuel du développement
> **Reorientation produit** : 2026-06-22 (cap direction)
> Les briques developpees convergent maintenant vers cinq preuves P0 : factures contre contrats signes ;
> budget/realise/atterrissage selon la matrice comptable ; etat CVC et PPT chiffre ; couverture DALKIA/SPIE
> avec detection des sites non entretenus ; consommations ENEDIS/GRDF, DJU et atterrissage annuel. La refonte frontend devient transverse : design system, parcours de
> decision et decomposition des pages/API/CSS monolithiques. Cadrage : [[20-Cap-direction-2026-factures-budget-CVC-maintenance]].
>
> **Diagnostic** : moteurs ENGIE, TotalEnergies et DALKIA avances mais dossier contractuel multi-marches incomplet ;
> budget initial et atterrissage global non modelises ; inventaire CVC sans PPT chiffre consolide ; referentiel
> generique de contrats et matrice de couverture absents ; SPIE a cadrer depuis ses pieces reelles.
>
> **Mise a jour complementaire** : 2026-06-25 (backend matrices comptables versionnées — COMPLET, mergé `main`)
> Le backend des matrices comptables versionnées est livré et mergé dans `main` en trois PR (CI verte) :
> #26 schéma + service + router + seed + ADR [[Decisions/010-matrices-comptables-versionnees]] ; #27 import/export
> XLSX (round-trip `stable_rule_key`, diff preview, commit en version brouillon) ; #28 moteur d'imputation +
> snapshots immuables (`apply`/`validate-snapshot`/`manual-override`/`export-finance`, dédoublonnage, contrôle
> ventilation). Tests pytest pour XLSX et application. Restent (intégration) : extracteurs réels de lignes facture
> par source en entrée de `apply`, droits par rôle (doc 35 §6), bascule du frontend `/refonte-v1/factures`.
> Le labo frontend React V1 et le reste du vault Codex sont sauvegardés sur la branche `wip/codex-2026-06-25` (non
> mergée). Détail : [[Sessions/2026-06-25 - Socle React V1]].
>
> **Mise a jour complementaire** : 2026-06-25 (backend matrices comptables versionnées — tranche minimale)
> Pose de la structure backend durable cadrée dans [[38-Modele-backend-matrices-comptables-versionnees]].
> Nouvelles tables (migration `0064_add_accounting_matrices`) : `accounting_matrix_contracts`,
> `accounting_matrix_versions`, `accounting_matrix_rules`, `invoice_accounting_snapshots`. Nouveau router
> `/api/accounting-matrices/*` (lecture, création contrat/version, activation/archivage, règles, snapshot facture
> en lecture). Invariant clé respecté : une version active n'est jamais modifiée en place ; on clone -> on édite ->
> on active (l'ancienne active est archivée). Différé phase suivante : import/export XLSX, application/écriture des
> snapshots, seed depuis `energy_accounting_*`/`cpe_accounting_*`, bascule du frontend `/refonte-v1/factures`.
> Validation : `py_compile` OK ; import runtime FastAPI et migration non joués localement (deps absentes du poste) ->
> validation CI requise. Détail : `[[Sessions/2026-06-25 - Socle React V1]]`.
>
> **Mise a jour complementaire** : 2026-06-22 (seconde passe d'audit fonctionnel)
> Comparaison du code reel (routes, services, modeles, pages et migrations) aux cadrages 20-22. Les cinq axes
> restent valides. Fondations a expliciter : patrimoine maitre, qualite/provenance, documents/versions/preuves,
> workflow/securite/audit. Angles morts principaux : execution effective de maintenance, engagements/mandats,
> taches/notifications et mesure des gains travaux. Detail : [[23-Seconde-passe-audit-fonctionnel-et-angles-morts]].
>
> **Mise a jour complementaire** : 2026-06-22 (factures gaz TotalEnergies — contrôle v1)
> Nouveau module gaz dedie : import + controle de coherence des factures gaz TotalEnergies
> (marche Herault Energie). Backend `gas_invoices` (migration 0057), `services/gas_invoice.py`
> (parser xlsx + controles prix×kWh / Σ=HT / HT+TVA=TTC / conversion m³→kWh / TVA), endpoints
> `/api/gas/invoices/*`. Frontend : onglet Factures marche > Herault Energie > TotalEnergies
> (import, portefeuille, table par site/PCE, controle, decision). L'import alimente `gas_pces`
> -> boite de rapprochement (rattachement PCE→batiment). Valide sur staging contre le vrai
> fichier : 58 factures, 22 717 € HT / 257 418 kWh, 10 PCE crees. v2 = controle prix (BPU gaz
> lot 7, ATRD/ATRT, TICGN). Detail : `[[Sessions/2026-06-22 - Factures gaz TotalEnergies]]`.
>
> **Mise a jour complementaire** : 2026-06-22 (boite de rapprochement patrimoine — PO2-PAT-003 v1)
> Nouveau : file de rapprochement compteurs externes -> referentiel Site/Batiment.
> Backend : `patrimoine_match_items` (migration 0056), `services/patrimoine_match.py`,
> endpoints `/api/patrimoine/matches/*`. Frontend : page `/patrimoine/rapprochements`
> (menu Patrimoine > « Rapprochements (file) »). Sources v1 = PRM ENEDIS + PCE GRDF ;
> cible = Batiment (repli Site). Le moteur collecte, propose un candidat par similarite
> de libelle (score), et « Lier » ecrit le lien canonique (`building_meter_links` /
> `gas_pces.building_id`). Valide de bout en bout sur le staging contre la copie prod :
> 496 PRM, 97 candidats, lien + lien-en-masse (>=90) OK. Detail :
> `[[Sessions/2026-06-22 - Boite de rapprochement patrimoine]]`.
>
> **Mise a jour complementaire** : 2026-06-16 (environnement de staging EN SERVICE)
> Staging operationnel sur le meme VPS, isole (projet docker `po2-staging`, base = copie prod) :
> <https://staging.135-125-152-112.sslip.io> (sslip.io, aucun DNS a gerer ; protege par mot de passe).
> Redeploy d'une branche : GitHub Actions -> « Deploy staging » -> saisir la branche.
> Detail : `[[Decisions/009-environnement-staging]]`. Permet desormais de tester toute branche sans toucher la prod.
> PR #14 mergee dans main ; factures (consolidation finances) deployee en prod via PR #13.
>
> **Mise a jour complementaire** : 2026-06-16 (parcours Factures marché : consolidation finances transversale)
> **Branche** : `codex/refonte-frontend-shell` (suite PR #13). Build frontend non exécuté localement (npm absent) -> validation CI.
>
> Refonte du parcours `Marchés & contrats > Factures marché`. Constat : le stepper
> `importer -> contrôler -> comprendre -> décider` existait déjà dans `EnergieInvoicesPage`
> (`StepTab` / `ControlStep` : Données & import, Contrôle contractuel, Rapport fournisseur, Liaison finance).
> Livrable de la session = sortir la consolidation/export finances au niveau supérieur (arbitrage utilisateur) :
> - `EnergieAccountingMatrix` : nouveau mode `variant="inline"` (en plus du modal existant) ;
> - `FacturesPage` : onglet transversal `Consolidation finances` (au-dessus des marchés) avec cartes de suivi,
>   tableau de transmission par marché et matrice comptable partagée inline.
> Détail : `docs/Sessions/2026-06-16 - Parcours Factures marche et consolidation finances.md`.
>
> **Mise a jour complementaire** : 2026-06-16 (refonte frontend : shell produit + atelier de cartographie)
> **Etat PR** : PR #13 verte dans GitHub Actions, branche `codex/refonte-frontend-shell`.
>
> Premiere brique de refonte frontend livree sans casser les routes existantes :
> ajout des conteneurs produit `/patrimoine`, `/marches`, `/technique`, `/administration`,
> conservation de `/buildings/*`, `/energie/*`, `/factures/*`, `/cpe/*`, et ajout de
> `ProductDomainPage`.
>
> Atelier local ajoute dans `docs/atelier-cartographie-frontend.html` pour raccorder les fonctionnalites
> existantes aux sections/sous-sections cibles et decrire les ecrans futurs. Documentation associee :
> `docs/17-Refonte-frontend-capacites-metier.md`, `docs/18-Registre-raccordement-frontend.md`,
> `docs/19-Atelier-cartographie-frontend.md` et note de session
> `docs/Sessions/2026-06-16 - Refonte frontend shell et atelier cartographie.md`.
>
> Decision produit actee : le domaine visible `Energie` devient `Fluides & consommations`
> (electricite, gaz, eau, donnees distributeurs, prix contractuels, preconisations).
> Les factures fournisseurs sortent de ce domaine et deviennent `Marches & contrats > Factures marche`.
> La section technique `Fluides et conformite` devient `F-Gaz / ESP` pour eviter l'ambiguite.
>
> Prochaine action recommandee : refondre le premier parcours raccorde
> `Marches & contrats > Factures marche` avec la chaine `importer -> controler -> comprendre -> decider -> exporter`.
>
> **Mise a jour complementaire** : 2026-06-15 (preuves de validation API P0)
> **Etat documentation/outillage local** : `docs/13-Matrice-routes-fonctionnalites-refonte-api.md` contient maintenant
> les colonnes `Statut validation` et `Preuve`, generees par `saas/backend/app/scripts/build_api_catalog.py`.
>
> Les statuts possibles sont : `inventorié`, `import app OK`, `test service OK`, `test endpoint HTTP OK`,
> `validé front`, `validé prod`, `à corriger`. Le diagramme `docs/api-cartographie/index.html` affiche aussi
> ces champs dans l'inspecteur endpoint et la liste.
>
> Premier perimetre P0 documente dans `docs/15-Validation-P0-factures-finance.md` :
> facture energie -> controle BPU/TURPE -> decision -> matrice comptable -> export XLSX finance.
> Validation locale ciblee : `python -m pytest tests/test_energie_accounting.py tests/test_engie_xlsx_parser.py
> tests/test_invoice_batches.py tests/test_invoice_analysis_bpu_mapping.py tests/test_billing_bpu_sync.py` = 21 tests OK.
> La decision facture energie reste seulement `import app OK` faute de test dedie. Plusieurs endpoints CPE/DJU/codification
> restent marques `à corriger`.
>
> **Mise a jour complementaire** : 2026-06-15 (catalogue fonctionnel commente)
> **Etat documentation locale** : ajout de `docs/14-Catalogue-fonctionnalites-commentees-et-reaffectation.md`.
>
> La cartographie technique `Routeur -> Prefixe -> Endpoints` est completee par une lecture metier :
> utilite de chaque fonctionnalite developpee, decision aidee, utilisateurs concernes, code/routes actuels,
> reaffectation cible dans la navigation (`Tableau de bord`, `Patrimoine`, `Energie`, `Marches & contrats`,
> `Technique`, `Administration`) et niveau de confiance. Le document rappelle que la matrice d'endpoints sert
> a organiser la refonte, mais ne certifie pas encore le fonctionnement de chaque API ; les echecs de tests
> CPE/DJU/codification observes localement restent a traiter avant migration.
>
> **Mise a jour complementaire** : 2026-06-15 (cartographie API en diagramme editable)
> **Etat code local** : outil `docs/api-cartographie/index.html` transforme en graphe dynamique Routeur -> Prefixe -> Endpoints.
>
> Reprise de la cartographie livree par l'IA precedente : l'ancienne vue arbre/liste est remplacee par un diagramme
> `vis-network` offline, avec edition des noeuds (libelle, type, chemin, routeur, prefixe, statut, commentaire),
> edition/suppression des relations, creation de noeuds/relations, vue Liste de secours, onglet Frictions conserve
> et export/import JSON `api_cartographie_graph.json`. Validation locale : dossier servi temporairement sur
> `http://127.0.0.1:8765/index.html`, chargement OK (279 endpoints / 17 routeurs), canvas present, vue Liste OK,
> selection d'un endpoint OK, aucune erreur console.
>
> **Mise a jour complementaire** : 2026-06-11 (reprise collecte ENEDIS synchrone de secours)
> **Etat code local** : UI `/energie` restructuree pour distinguer collecte synchrone et collecte async ENEDIS.
>
> Le moteur ENEDIS synchrone etait encore present mais partiellement masque cote front. La page Energie expose
> maintenant un panneau "Collecte de donnees ENEDIS" avec deux etapes : prerequis/referentiels (sync contractuelle
> ENEDIS + DJU) puis collecte synchrone de secours (conso journaliere, puissance max, courbe de charge). Les endpoints
> synchrones acceptent un `prm_limit` pour tester sur les 5 premiers PRM avant une reprise large ; ce mode test
> n'avance pas l'etat global de reprise. La courbe de charge synchrone evite maintenant les doublons en n'ajoutant
> que les points PRM/horodatage absents. Validation locale : `python -m compileall app` OK. Build frontend non execute
> localement : `npm` absent et `node_modules` absent ; validation CI requise.
>
> **Mise a jour complementaire** : 2026-06-09 (controle factures ENGIE vs BPU canonique)
> **Etat code local** : controle BPU facture recale sur `extraction_tarifs_electricite_BPU.xlsx`.
>
> Diagnostic sur `saas/energie/ENGIE/FACTURES/MesFactures_20260609132103.xlsx` : 185 bordereaux,
> 1 267 sites, BPU courant ENGIE 2026 = `2025_18_MS1_BPU_ENGIE_LOT_1.pdf` (Lot 1) depuis le xlsx
> canonique. Reproduction locale : 5 996 lignes tarifaires controlees, 0 ecart prix BPU, 0 reference
> manquante. Les nombreuses erreurs observees etaient des faux positifs de referentiel/mapping
> (mauvais lot/configuration ou C2/C5 mal derives), pas des erreurs ENGIE averees sur les prix unitaires.
> Le moteur de controle charge maintenant les lignes courantes par fournisseur depuis le xlsx canonique
> (ENGIE -> Lot 1, EDF -> Lot 2), expose le document canonique dans le resume BPU, conserve le controle
> historique quand une reference exacte existe, et invalide le cache apres reimport BPU xlsx. Tests cibles :
> `python -m pytest tests/test_billing_bpu_sync.py tests/test_invoice_analysis_bpu_mapping.py` OK.
>
> **Mise a jour complementaire** : 2026-06-08 (CVC fluides : cockpit F-Gaz / ESP)
> **Etat code local** : premiere centrale de pilotage `/buildings/cvc-fluides` implementee.
>
> La page Fluides frigorigenes & ESP n'est plus seulement un ecran d'import/rattachement : elle devient un cockpit
> inspire du classeur `saas/energie/CVC/modele_GMAO_suivi_fluides_collectivite_simple.xlsx`. Ajouts locaux :
> migration additive `0048_add_cvc_refrigerant_pilotage_fields.py`, champs de suivi sur `cvc_refrigerant_items`
> (detection permanente, dernier controle, prochaine echeance, titulaire, responsable, statut action, commentaire),
> endpoint `/api/cvc/refrigerants/dashboard`, calculs serveur F-Gaz (seuils 5/50/500 t eq. CO2, frequence, conformite,
> priorite, preuve attendue), plan d'action derive et signaux ESP/DESP separes. Le front expose 5 onglets :
> Cockpit, Registre F-Gaz, Actions, ESP/DESP, Import.
> Validation locale : `python -m compileall app` OK. Build frontend non execute localement : `npm` et `node_modules`
> absents du poste ; validation CI requise.
>
> **Mise a jour complementaire** : 2026-06-05 (CVC referentiel terrain fiabilise)
> **Etat code local** : moteur de rattachement CVC corrige et endpoint de recalcul de lot ajoute.
>
> L'audit du dernier import `import_d0791486` a montre que la collecte brute est saine mais que le fuzzy matching
> vers `equipment_references` produisait de nombreux faux positifs (`Split system` -> `Plieuse`, `Compteur` -> `Pompe`,
> `CTA` -> videosurveillance, `Cassette` -> `Chaussee`). Le moteur utilise maintenant des alias metier prioritaires,
> limite le fuzzy aux domaines `A.2.1`, `A.2.2`, `A.2.3`, et laisse certaines familles generiques non rattachees
> plutot que de creer une fausse duree de vie. Un bouton front `Recalculer les references` appelle
> `POST /api/cvc/imports/{import_batch}/recompute-references` pour corriger un lot deja importe.
> Validation locale : `compileall` OK et `tests/test_cvc_reference_matching.py` OK avec SQLite in-memory.
>
> **Mise a jour complementaire** : 2026-06-04 (CVC import + matching sites separes)
> **Etat code local** : increment UX sur `/buildings/cvc-import` et nouvelle route `/buildings/cvc-import/sites`.
>
> Le flux CVC terrain est recadre : l'utilisateur uploade d'abord le fichier pour obtenir une preview non persistante,
> puis utilise un bouton separe pour enregistrer l'inventaire. Le matching des sites importes vers le referentiel
> patrimoine est deplace dans une page dediee, avec detection des correspondances evidentes, selection/correction
> Site + Batiment, puis application en masse a toutes les lignes du lot. Le tableau inventaire affiche ensuite les
> colonnes Site/Batiment issues de ce mapping, garde l'affinage Local et reference duree de vie ligne par ligne, et
> utilise un gabarit pleine largeur pour reduire le scroll horizontal.
> Validation locale : `python -m compileall app` OK. Build frontend non execute localement : `npm` absent sur le poste.
>
> **Mise a jour complementaire** : 2026-06-03 (CVC terrain workflow persistant + durees de vie)
> **Etat code local** : migration Alembic ajoutee `0042_extend_cvc_inventory_workflow.py` apres `0041`.
>
> Le chantier `/buildings/cvc-import` est reouvert pour corriger le workflow terrain :
> l'upload enregistre maintenant l'inventaire brut meme avant rattachement patrimoine, puis expose un tableau editable.
> Chaque ligne peut etre rattachee a un Site, Batiment et Local du referentiel patrimoine, puis associee au referentiel
> `equipment_references` importe depuis `durees_vie_powerbi_base_wide.csv`. Le tableau expose les durees mini/reference/maxi,
> la duree restante calculee, et un champ quantite de fluide frigorigene uniquement pour les references dont `niveau_3`
> vaut `Production de froid :` ou `Pompes a chaleur Air/Air, Air/Eau, Eau/Eau`.
> Validation locale : `python -m compileall app` OK. Import runtime FastAPI et build frontend non executes localement faute de
> dependances (`fastapi`, `npm`/`node_modules`) sur le poste ; validation CI requise.
>
> **Mise a jour complementaire** : 2026-06-03 (CPE DALKIA consommations multi-fluides consolidees)
> **Etat code constate** : migrations Alembic jusqu'a `0041_seed_cpe_contract_scope_references.py`.
>
> Le module CPE DALKIA exploite maintenant l'export "consommation detaillee" multi-fluides :
> stockage `cpe_conso_releves`, import GAZ/ELEC/ECS/EAU/CHALEUR par site x mois, affichage sur fiche site,
> endpoint de synthese annuelle `/api/cpe/consommations/synthese/{annee}` et panneau portefeuille dans
> `/cpe` > `Performance et consommations` avec totaux par fluide, couverture des sites actifs et codes
> DALKIA non rattaches.
> Le perimetre contrat CPE Ville n'est plus porte par une constante Python : les contrats actifs
> sont lus depuis `cpe_contract_references` via des lignes editables `reference_kind = cpe_contract_scope`.
>
> **Mise a jour complementaire** : 2026-06-02 (inventaire transversal + moteur referentiel DALKIA acte d'engagement)
> **Etat code constate** : migrations Alembic jusqu'a `0036_add_cpe_dalkia_p1_tarifs.py`, 201 routes FastAPI, 21 pages React, 50 modeles SQLAlchemy.
> **Inventaire complet** : [[08-Inventaire-fonctionnalites-developpees-2026-06-02]]
>
> Le module CPE DALKIA comprend maintenant un moteur de referentiel contractuel importe depuis les XLSX
> d'acte d'engagement Lot 1 / Lot 2 : preview classifiee, tables `cpe_dalkia_ref_*`, RECAP MARCHE,
> cibles NB annuelles, controle des bases P2/P3, synchronisation de la reference P1 depuis le RECAP et
> parsing des tarifs/coefficient de revision P1. Voir [[energie/CPE-DALKIA/17-Referentiel-DALKIA-Import]].
>
> **Mise a jour complementaire** : 2026-05-28 (CPE DALKIA finance : perimetre contrats, export liaison enrichi, controle acompte P1 gaz Lot 1)
> **Dernier commit pousse sur `main`** : `add8d71` (feat(cpe): control DALKIA P1 acompte scope)
> **Prod OVH** : API OK apres deploy GitHub Actions reussi. Healthcheck `https://patrimoineaucarre.com/api/health` = `status: ok`.

> **Mise a jour complementaire** : 2026-05-26 (9 filtres facettes /energie/factures + graphe mensuel per-site)
> **Dernier commit pousse sur `main`** : `9b2c8ca` (feat(invoices): add 9 facet filters on billing page and monthly graph)
> **Prod OVH** : API OK, mais derniers deploys GitHub Actions en echec transitoire Docker Hub (`TLS handshake timeout` sur images `nginx`, `python`, `node`). Relancer Deploy avant de considerer les derniers commits visibles en prod.

> **Mise à jour** : 2026-05-22 (socle rattachement compteurs fluides + BPU gaz TotalEnergies lot 7)
> **Mainteneur principal** : PAB34 + assistance IA (Claude Sonnet 4.6)
> **Dernière commit en prod** : `00af844` (fix(cvc-import): dropdown mapping complet avec tous les bâtiments)

## 🟢 Ce qui tourne en prod (https://patrimoineaucarre.com)

| Module | Route | État |
|---|---|---|
| Auth | `/login`, `/register`, `/account` | Stable |
| Patrimoine — liste | `/buildings`, `/buildings/list` | Stable |
| Patrimoine — détail | `/buildings/:id` | Stable |
| Patrimoine — compteurs | `/buildings/:id` | Nouveau : rattachement manuel PRM/PCE/eau avec contexte fournisseur/contrat |
| Patrimoine — création / import | `/buildings/create-edit` | Stable |
| Patrimoine — import hiérarchique | `/buildings/create-edit` | `SITE` -> `Site`, `BATIMENT` -> `Building.site_id`, `LOCAL` -> `Local.building_id` |
| Gestion technique SYPEMI | `/buildings/technique` | Stable (310 équip. importés) |
| **Inventaire terrain CVC** | `/buildings/technique` (onglet Terrain) + `/buildings/cvc-import` | **Nouveau (2026-05-20)** — wizard import Excel 3 étapes, fuzzy match sites↔bâtiments, rattachement SYPEMI, badges vétusté |
| Énergie — vue d'ensemble | `/energie` | Stable |
| Énergie — détail PRM | `/energie/:prmId` | Stable |
| Préconisations puissance | `/energie/preconisations` | Stable |
| Factures | `/energie/factures`, `/energie/factures/:id` | Stable en prod pour parser ENGIE, controle/decision et import lot ; le controle BPU tente une reference historique exacte dans `bpu_*` avant le repli `BillingBpuLine` |
| Facturation TURPE | `/energie/facturation` | Stable |
| CPE DALKIA | `/cpe` | En cours avance : cockpit finance, controle factures, referentiel DALKIA et synthese consommations multi-fluides GAZ/ELEC/ECS/EAU/CHALEUR avec codes non rattaches |
| **BPU — Timeline** | `/energie/bpu` (onglet Timeline) | Stable — graphe dual-axe Y (fourniture vs accessoires), légende composantes avec exemples chiffrés |
| **BPU — TURPE** | `/energie/bpu` (onglet TURPE) | Refonte 2026-05-21 — 4 blocs : définition · barre empilée facture · courbe évolution · tableau CRE |
| **BPU — Documents & Import** | `/energie/bpu` (onglet Documents) | Nouveau 2026-05-21 — stats + table BPU filtrée + import admin (séparé de Timeline) |
| **BPU — Édition tableau** | `/energie/bpu` (onglet Édition) | Stable (2026-05-20) — tableau Excel cliquable, batch save, 14 endpoints CRUD |
| **CVC import — mapping** | `/buildings/cvc-import` (étape 2) | Fix 2026-05-21 — dropdown complet (suggestions fuzzy + tous les bâtiments du patrimoine) |

## 📦 Migrations alembic appliquées en prod
```
0001_create_users
0002_create_cities_buildings_locals
0003_extend_buildings_for_naming_workflow
0004_add_external_source_fields_for_imports
0005_add_code_postal_to_buildings
0006_add_billing_config
0007_add_lot_to_billing_config
0008_make_tariff_code_nullable
0009_add_billing_bpu_lines
0010_add_energy_invoice_imports
0011_add_energy_invoice_analysis
0012_add_invoice_decision_fields
0013_add_enedis_async_jobs
0014_add_equipment_tables
0015_add_bpu_tables
0016_add_cvc_inventory
0017_add_sites_hierarchy
0018_add_invoice_batches_and_normalized_history
0019_add_cpe_tables
0020_add_cpe_tarif_pce
0021_add_building_meter_links
0022_seed_cpe_prix_gaz_os3
0023_add_building_ign_features_json
0024_add_cpe_finance_accounting
0025_add_cpe_revision_controls
0026_add_cpe_control_fsd2
0027_add_cpe_accounting_contract_code
0028_add_cpe_contract_references
0029_seed_cpe_contract_references
0030_add_cpe_invoice_evidences
0031_generalize_cpe_revision_evidences
0032_add_cpe_finance_exported_at
0033_add_cpe_dalkia_ref_tables
0034_drop_dalkia_cibles_unique
0035_add_cpe_dalkia_recap
0036_add_cpe_dalkia_p1_tarifs
0037_add_pronostics_game
0038_add_cpe_dalkia_bpu
0039_add_pronostics_password_resets
0040_add_cpe_conso_releves
0041_seed_cpe_contract_scope_references      <- HEAD code constate 2026-06-03
```

## 🔧 PRs récentes
| # | Titre | Branche | Statut |
|---|---|---|---|
| 12 | `feat(bpu): pipeline complet historique des prix (Phases 2 + 3 + 4)` | `claude/bpu-phase2` | ✅ Mergée 2026-05-19 |
| 11 | `feat(bpu): add SQL models + alembic migration` | `claude/bpu-feature` | ✅ Mergée |
| 10 | `fix(buildings): adapt BuildingTechniquePage colors for dark mode` | | ✅ Mergée |
| 9 | `feat(energie): UI panneau async ENEDIS (Phase C)` | | ✅ Mergée |

## 🪵 Derniers commits sur `main`
```
fe84fca  feat(billing): add invoice holder and issue filters
00af844  fix(cvc-import): dropdown mapping complet avec tous les bâtiments du patrimoine
9674d50  feat(bpu): ajout exemples chiffrés sur chaque composante Timeline
f29db99  refactor(bpu): Timeline définitions lisibles + TURPE 3 blocs restructurés
cc34a8f  refactor(bpu): refonte UI page /energie/bpu — 4 onglets, Timeline épurée
2f3229f  feat(pat): import patrimoine hiérarchique site/bâtiment/local (PO2-PAT-002)
324d053  feat(bpu): double axe Y dans Timeline (fourniture vs accessoires)
ea53a9f  docs(vault): session PO2-CVC-001 + MAJ module Gestion-technique
fff24e1  fix(cvc): corriger TS7053 referenceCounts manque clé terrain
fd192fe  feat(cvc): import inventaire CVC terrain + rattachement SYPEMI
```

## 📚 Specs historiques

L'inventaire complet des specs `saas/specs/` est dans [[Specs]]. Résumé :

- **4 specs canoniques** à consulter avant tout dev sur le sujet :
  - `04_mapping_facture_engie.md` — mapping PDF facture
  - `05_matrice_controles_factures_energie.md` — codes erreur + tolérances
  - `06_preconisation_abonnement_v1.md` — marges 20/12/5 %
  - `07_referentiel_turpe_7.md` — référentiel CRE
  - `08_enedis_async_kit_analysis.json` — gaps kit ENEDIS async
- **1 spec archivée** : `_archives/02_architecture_technique_v01_obsolete.md` (état v0.1 obsolète)
- **3 specs partielles** dont les pépites ont été synthétisées dans les modules

## 🔥 Chantiers ouverts (en cours / à reprendre)

### 1. ✅ ~~Parser BPU → remplacé par import xlsx canonique~~ (PO2-BPU-002 + PO2-BPU-003 — Livrés 2026-05-20)
- **Stratégie finale** : source de vérité = `extraction_tarifs_electricite_BPU.xlsx` (saisie manuelle validée par l'utilisateur), `extraction_status=manual`, `confidence=1.0`
- **BDD prod** : 17 docs / 49 segments / 138 périodes / **523 composantes** / 36 charges
- **UI** : tableau éditable dans `/energie/bpu` (onglet "Édition tableau"), édition cellule par cellule, batch save
- **Script** : `app.scripts.import_bpu_xlsx` — relancer avec `--force` si re-import xlsx nécessaire
- **Parser PDF** : en pause (PO2-BPU-001) — `raw_text` stocké sur chaque doc pour re-parsing futur éventuel
- **Voir** : [[Sessions/2026-05-20 — Import xlsx BPU + tableau editable]] et [[Modules/Energie-BPU]]

### 2. Module Baux locataires (1.2 de la roadmap)
- Aucun code n'existe encore — c'est le prochain gros chantier "rapidement faisable"
- Pattern à réutiliser : upload PDF côté Frontend + `services/invoice_parsers/` côté Backend
- Modèle à créer : étendre `Local` avec champs bail, OU créer une nouvelle table `Lease`
- À discuter avec l'utilisateur sur le schéma (1-N entre Building et Lease ?)

### 2b. Import patrimoine hiérarchique Site -> Bâtiment -> Local
- **Livre et documente** : migration `0017_add_sites_hierarchy`, modele `Site`, `buildings.site_id`, endpoints `/api/buildings/sites`
- Objectif : importer les fichiers patrimoine avec colonne `Typologie` sans aplatir sites / batiments / locaux
- Flux vise : lignes `SITE` -> table `sites`, lignes `BATIMENT` -> `buildings.site_id`, lignes `LOCAL` -> table `locals` rattachee au batiment parent
- Point de cadrage 2026-05-22 : cette liste doit devenir le referentiel maitre auquel se rattachent PRM ENEDIS, PCE/GRDF, sites CPE DALKIA et contrats de maintenance.
- Prochaine brique structurante : une boite de rapprochement qui conserve les objets introuvables/ambigus au lieu de les perdre ou de creer de faux batiments.
- Voir [[Sessions/2026-05-20 — Import patrimoine hierarchique]]

### 2c. Historique factures ENGIE dans `/energie/factures`
- **En cours** : intégrer le lot réel de 83 PDF ENGIE depuis `saas/energie/ENGIE/FACTURES`
- Point atteint : l'UI facture couvre l'import multi-fichiers, les lots persistants, le résumé simple, PRM/FIC, lignes extraites, contrôles BPU/TURPE/ENEDIS et décision utilisateur
- Revue améliorée : le titulaire du contrat est exposé dans la liste et filtrable ; les catégories/types de problèmes remontent du détail facture vers la page principale
- Clarification controles : le rapport fournisseur ne reprend plus les limites internes TURPE/BPU/ENEDIS ; les corrections PDF locales couvrent les lignes negatives, les FIC creditrices et les faux ecarts `quantite x PU` sur depassement de puissance
- Socle historique : les controles prix peuvent utiliser une ligne `bpu_*` exacte par fournisseur/annee/segment/poste/composante ; les cas ambigus restent volontairement hors match jusqu'au contexte marche explicite
- Flux visé ensuite : qualifier le lot complet, cadrer les anciens PDF EDF et le contexte marche multi-lots, puis alimenter le meme pipeline par la future API ENGIE
- Voir [[Sessions/2026-05-21 — Historique factures ENGIE]]

### 3. Backfill prod ENEDIS async
- **Pending côté utilisateur** : mettre à jour le canal SETE_ENERGIE (506350699) côté portail ENEDIS pour utiliser le nouveau user FTP `enedis_ftp` + nouveau password (récupérable via `ssh ... "sudo cat /root/.ftp_password_enedis"`)
- Tant que ce n'est pas fait, le scheduler async tourne à vide
- Une fois le canal validé : lancer backfill complet (CDC 2 ans + Conso 3 ans) via `POST /api/energie/sync/async/backfill-full`

### 4. Dette technique ENEDIS async
Cf. spec `saas/specs/08_enedis_async_kit_analysis.json` (synthèse dans [[Modules/Energie-Consommation]]) :
- `UNFILTERED_PRM_BATCH` (medium) — filtrer les PRM non-communicants avant publication
- `ALL_OR_NOTHING_PUBLICATION` (medium) — découper en sous-batchs pour qu'un PRM invalide ne tue pas tout
- `CDC_WINDOW_TOO_LARGE` — probablement traité par les fixes `d784882` + `38ab484`, à confirmer

### 5. Refresh TURPE annuel
- Prochain refresh CRE : **2026-08-01**
- À ce moment, mettre à jour `saas/specs/07_referentiel_turpe_7.md` avec la nouvelle version + adapter les prix dans `services/turpe.py`
- La page `/energie/bpu` expose aussi l'historique moyen TURPE HTA-BT via `list_turpe_evolution_events()` : ajouter le point 2026 dans cette serie si la CRE publie l'indexation attendue.
- Voir [[Modules/Energie-TURPE]]

### 4. Codespaces — devcontainer "à vide"
- Le `.devcontainer/devcontainer.json` minimal a été créé uniquement pour faire passer le prebuild GitHub
- Si l'utilisateur veut vraiment utiliser Codespaces un jour, il faudra enrichir `postCreateCommand` pour installer backend + frontend (pip + npm)

## 📊 Données en prod

| Table | Lignes |
|---|---|
| `users` | (inconnu, mais l'utilisateur principal est créé) |
| `cities` | 1 (Sète) |
| `buildings` | ~530 (audit PRM mentionne 529 PRM) |
| `enedis_async_jobs` | 0 (scheduler en attente du canal validé) |
| `equipment_references` | 310 |
| `building_equipments` | (variable, dépend des saisies utilisateur) |
| `bpu_documents` | **17** (importés 2026-05-20, xlsx canonique) |
| `bpu_segments` | **49** |
| `bpu_time_periods` | **138** |
| `bpu_price_components` | **523** (extraction_status=manual) |
| `bpu_fixed_charges` | **36** |

## Cadre gaz posé le 2026-05-22

- `BuildingMeterLink` devient le premier point central du lien bâtiment -> compteur multi-fluides.
- Le futur flux GRDF doit alimenter les PCE et consommations gaz, quel que soit le fournisseur.
- Le BPU gaz HERAULT ENERGIE lot 7 est importable comme référence `TOTALENERGIES` pour les compteurs Ville.
- La cotation OS3 gaz du P1 DALKIA reste dans le module CPE ; ne pas la fusionner avec la référence BPU TotalEnergies.

## 🔐 Secrets et accès

- **GitHub PAT** : récupérable via `git credential fill` depuis la machine de l'utilisateur (gho_*)
- **SSH VPS** : `~/.ssh/po2_vps2` → `ubuntu@135.125.152.112`
- **Password FTP ENEDIS** : `/root/.ftp_password_enedis` sur le VPS (chmod 600, root only)
- **Clé AES déchiffrement ENEDIS** : dans `.env` prod variable `ENEDIS_DECRYPTION_KEY`
- **Canal contact ENEDIS** : `506350699` (SETE_ENERGIE)
- ⚠️ **Ne JAMAIS afficher de password ou de clé en clair dans une conversation, un commit, ou ce vault** — l'utilisateur a déjà rotaté un mot de passe à cause de ça

## Mise a jour facturation ENGIE - 2026-05-26

Chantier concerne : `PO2-FACT-001`.

Travaux recents documentes :

- Import XLSX ENGIE `MesFactures_*.xlsx` asynchrone et bascule UI XLSX-only pour les nouveaux imports.
- Upsert avec preservation des decisions utilisateur via option `force_update`.
- Parser XLSX optimise et controles BPU/TURPE/ENEDIS reutilises par le meme pipeline que les PDF.
- Filtres facture consolides : controle, decision, regroupement, titulaire, categorie/type de probleme.
- Rapport fournisseur filtre : les points BPU restent visibles, et les ecarts chiffrables sont recalcules sur base BPU.
- Filtres `Prix contractuels` corriges : la categorie et les types BPU restent disponibles meme quand aucun ecart BPU n'est present.
- Suivi mensuel en tete de `/energie/factures` : consommation facturee ENGIE, releve ENEDIS, nombre de factures, nombre de PRM factures, alerte de trou potentiel.
- Synthese contractuelle creee : `saas/energie/HERAULT ENERGIE/SYNTHESE_FACTURATION.md`.
- Controle tarifaire local complet : `MesFactures_20260522150740.xlsx` vs BPU 2026 Lot 1 = 5368 lignes, 5355 OK, 13 ecarts potentiels, 0 reference manquante.

Commits associes :

```text
9e36f19 fix(invoices): match base-only C5 tariffs
a18ef4c fix(invoices): keep BPU filters visible
6a1e1f2 feat(invoices): show monthly billing coverage
56a1843 fix(invoices): match ENGIE XLSX BPU tariffs
e0b69ef feat(invoices): add monthly consumption tracking
b899ad3 fix(invoices): include tariff BPU issues in report
3eba12c fix(invoices): speed up ENGIE XLSX parsing
22c7ff7 fix(invoices): run XLSX imports in background
01b94b1 feat(invoices): bascule XLSX-only — upsert avec préservation décisions utilisateur
```

Commit 9 filtres facettes - 2026-05-26 :

```text
9b2c8ca feat(invoices): add 9 facet filters on billing page and monthly graph
```

Ajouts :
- `filter_facets` property sur `EnergyInvoiceImport` : extrait mois, PRM/PCE, FIC, site, commune, segment, code tarif, libelle tarif, type document depuis `analysis_result`.
- Schema `EnergyInvoiceImportOut` expose `filter_facets: dict[str, list[str]]`.
- Endpoint monthly graph accepte 9 nouveaux parametres Query.
- Service `get_monthly_invoice_consumption()` filtre per-site quand des filtres site/PRM/segment sont actifs (correction graphe qui additionnait toute la facture au lieu des seuls sites concernes).
- Frontend : 9 `useState` + `useMemo` + `InvoiceMultiFilter` dans `EnergieInvoicesPage.tsx`, bouton reset, integration dans l'index de recherche.

A faire juste apres deploy OVH reussi :

1. Reimporter `MesFactures_20260522150740.xlsx` avec `Forcer la mise a jour des bordereaux deja importes`.
2. Verifier que `Prix contractuels` et les types BPU sont visibles dans les filtres.
3. Filtrer sur `Prix contractuels` puis `Ecart prix facture / BPU`, editer le rapport, verifier le recalcul BPU.
4. Relire les 13 ecarts potentiels restants, surtout `BORNE FIXE MARCHE DU BARROU` en `LU/base`.

## Mise a jour CPE DALKIA finance - 2026-05-28

Chantier concerne : module `/cpe`, factures DALKIA et fiche liaison finances.

Travaux livres et pousses :

- Navigation finance `/cpe` clarifiee en sous-vues : imports, sites, matrice, indices, factures.
- Matrice de codification DALKIA importable et editable : sites finance, natures comptables par code contrat / marche / service / poste facture.
- Historique des factures DALKIA supprimable via action dediee.
- Liste "Factures archivees recentes" corrigee : elle affiche toutes les factures et dispose de filtres facture / contrat / statut.
- Export XLSX fiche liaison enrichi : `Synthese`, `Lignes finance`, `Controles`, `Donnees source`.
- Controle facture renforce : nature comptable, site finance, type de facture, total HT, coherence des periodes, P2, P3/P3.4 et P2.4 objectifs.
- Correction de perimetre : les contrats DALKIA hors CPE Ville cible (ex. CREM Piscine Fonquerne `C00032657J`, thalassothermie, anciens marches) ne sont plus bloques par l'absence de site VDS/CCAS.
- Controle P1 gaz Lot 1 ajoute pour `C00190116O` :
  - lignes incluses : `P1`, `ABT`, `CTA`, `CPB`, `LOCATION`, `STOCKAGE`, `TERME FIXE` ;
  - reference 2026 : DPGF Lot 1, synthese `P1 gaz Rev Temp`, total annuel `341 293,06 EUR HT` ;
  - regle : acompte trimestriel = `1/4` du P1 annuel revise, tolerance `1%` ou `100 EUR`.

Commits associes :

```text
695c0bd feat(cpe): clarify finance navigation
5b0ecbf feat(cpe): improve DALKIA finance exports
25e6bba feat(cpe): strengthen DALKIA invoice controls
2419f9d fix(cpe): show all archived DALKIA invoices
add8d71 feat(cpe): control DALKIA P1 acompte scope
```

Validation :

- `python -m compileall app` OK localement.
- Tests unitaires locaux non executes : environnement Codex sans `pytest`/`sqlalchemy` installes.
- GitHub Actions `CI` OK pour `add8d71`.
- GitHub Actions `Deploy` OK pour `add8d71`.
- Healthcheck prod OK.

Prochaines etapes recommandees :

1. Reimporter la matrice codification enrichie puis l'export finances DALKIA dans `/cpe`.
2. Relancer les controles sur les factures du contrat `C00190116O`.
3. Verifier une facture P1 acompte T1 2026 : le controle doit comparer le total P1 gaz du lot importe a `85 323,27 EUR HT`.
4. Completer les contrats cible si DALKIA confirme officiellement `C00190155J` comme Lot 2 et ses regles propres.
5. Remplacer progressivement les constantes P1 DPGF par un referentiel editable en base : contrat, annee, poste, formule, total annuel, tolerance.
6. Ajouter le rapprochement automatique fin vers site quand une facture contient plusieurs sites : code VDS/CCAS explicite, puis mapping detail DALKIA -> site, puis ecran de reconciliation des lignes non rattachees.
7. Etendre P1 au decompte definitif : volumes GRDF/DALKIA, prix gaz fournisseur, ecart entre acompte et definitif, pieces justificatives.

## Cadrage CPE DALKIA - Formules, indices et travaux P3 - 2026-06-01

Le workflow PDF livre par la migration `0030_add_cpe_invoice_evidences.py` constitue une premiere
preuve utile, mais il est trop lie a la facture : `cpe_invoice_evidences.invoice_id` est obligatoire.

Decision :

- conserver `0030` intacte car elle peut deja etre deployee ;
- creer une migration additive pour generaliser les preuves documentaires ;
- renommer `/cpe` > `Referentiel finance` > `Indices` en `Formules et indices` ;
- centraliser dans cet ecran les formules P1/P2/P3, indices, bases contractuelles, coefficients observes,
  preuves PDF, valeurs DALKIA declarees et valeurs officielles verifiees ;
- brancher les alertes de nouveau coefficient detecte pendant l'import XLSX vers l'import PDF centralise ;
- developper ensuite le module `Travaux P3` et son catalogue BPU versionne.

Note detaillee :

- `docs/energie/CPE-DALKIA/15-Formules-indices-et-travaux-P3.md`

Increment 1 implemente :

- migration `0031_generalize_cpe_revision_evidences.py` ;
- preuves PDF de revision importables depuis `Formules et indices`, meme sans facture preselectionnee ;
- rattachement multi-factures par `cpe_invoice_evidence_links` ;
- auto-rattachement lorsque le numero de facture est extrait du PDF ;
- preservation des preuves lors de la suppression d'un historique de factures ;
- affichage des formules P1/P2/P3 et registre central des justificatifs dans `/cpe`.

## Mise a jour CPE DALKIA - pilotage financier annuel et controle global - 2026-06-01

Travaux livres :

- `/cpe` > `Factures` recentre sur le suivi financier de l'exercice courant du 01/01 au 31/12 ;
- contrats hors perimetre CPE Ville decoches par defaut ;
- KPI annuel, graphique mensuel P1/P2/P3, repartition par statut, top postes et graphique par type de
  facture `AC`, `AJ`, `DE`, `EC`, `RE` ;
- nouvelle entree `/cpe` > `Controle factures` ;
- endpoint de recalcul global des controles sur les contrats actifs Ville ;
- reporting consolide : conformes, ecarts, blocages, montant controle, familles d'anomalies et file
  priorisee par facture.

Reste a faire :

1. parser et versionner les enveloppes DPGF Lot 1 / Lot 2 pour alimenter un vrai suivi realise / prevu ;
2. afficher l'ecart budgetaire par famille, poste et site ;
3. completer le suivi du compte P3 avec engagements reserves et travaux realises.

Note detaillee :

- `docs/energie/CPE-DALKIA/16-Pilotage-financier-et-controle-global.md`

Increment calendrier et transmission finances :

- exploitation des dates edition, echeance, debut et fin de periode de l'export DALKIA ;
- `/cpe` > `Factures` devient une vue analytique en lecture seule ;
- KPI et graphique emission / echeance ;
- actions decision, justificatif PDF et export XLSX deplacees dans `Controle factures` ;
- migration `0032_add_cpe_finance_exported_at.py` ;
- horodatage de la remise au service finance lors de l'export XLSX ;
- controle `invoice_timeline` pour les dates absentes ou incoherentes.

## Mise a jour CPE DALKIA - consommations multi-fluides - 2026-06-03

Chantier concerne : `PO2-CPE-001`.

Travaux livres :

- migration `0040_add_cpe_conso_releves.py` et modele `CpeConsoReleve` ;
- import du vrai export DALKIA `consommation detaillee` avec les fluides `GAZ`, `ELEC`, `ECS`, `EAU`, `CHALEUR` ;
- filtre contrats CPE Ville via `cpe_contract_references.reference_kind = cpe_contract_scope`, avec exclusion des contrats hors perimetre type Fonquerne ;
- conservation des codes sites non rattaches dans `cpe_conso_releves` (`cpe_site_id = null`) pour ne rien perdre ;
- endpoint fiche site `/api/cpe/sites/{site_id}/consommations` et tableau annuel par fluide dans `/cpe/sites/{id}` ;
- endpoint portefeuille `/api/cpe/consommations/synthese/{annee}` ;
- panneau `/cpe` > `Performance et consommations` : totaux par fluide, couverture sites actifs, codes DALKIA non rattaches et sites actifs sans consommation.

Validation :

- `python -m compileall app` OK.
- `python -m pytest tests/test_cpe_import_conso_detaillee.py` OK avec `DATABASE_URL=sqlite:///:memory:` : 6 tests passes.
- `npm run build` non lance localement : `npm` et `node_modules` absents sur le poste ; validation frontend a faire via CI/GitHub Actions.

Handoff suivant :

1. Reimporter le CSV DALKIA detaille depuis `/cpe`.
2. Verifier dans `/cpe` > `Performance et consommations` les totaux par fluide et les codes non rattaches.
3. Rattacher les 3 codes piscines / codes DALKIA non alignes au referentiel CPE ou a la future boite de rapprochement patrimoine.
4. Maintenir le perimetre contrat depuis `cpe_contract_references` et ajouter/retirer les contrats via l'ecran Referentiel finance si le marche evolue.

## Mise a jour atelier V1 - arbitrages avant refonte - 2026-06-24

Le modele V1 de l atelier BPMN porte maintenant un registre de decisions utilisateur :

- 26 questions reliees aux cadres concernes ;
- 13 arbitrages structurants marques `◆` en rouge, apres reclassement de la matrice comptable A26 ;
- 13 choix de conception marques `◇` en ambre ;
- passage en `✓` vert apres validation ;
- filtre dedie dans la barre d outils ;
- question, proposition et reponse modifiables dans la fiche du cadre ;
- preservation des reponses utilisateur pendant les fusions non destructives et dans l export JSON ;
- compteur et liste dans la vue Couverture UX.

Le registre de lecture et la sequence d ateliers sont documentes dans `docs/28-Questions-arbitrage-avant-refonte-V1.md`. Aucun code fonctionnel SaaS ni deploiement production n est concerne par cette mise a jour.

Validation locale : syntaxe JavaScript valide ; 16 diagrammes, 230 cadres, 26 arbitrages uniques (12 structurants, 14 conception) ; test de preservation d une reponse validee reussi.
## Mise a jour prototype frontend V1 sans backend - 2026-06-24

Un premier jet autonome de la refonte est disponible dans `docs/prototype-refonte-v1/`.

Perimetre :

- cockpit adapte aux profils Direction, Fluides, Technique/CVC, Finances et Patrimoine ;
- vue Factures et decisions multi-fournisseurs ;
- drill-down facture avec trace de controle et actions simulees ;
- fiche Site 360 avec onglets Fluides, Contrats, Technique, Budget/PPT et Documents ;
- recherche globale, filtres, navigation responsive et donnees simulees.

Aucune API, authentification ou base de donnees n est raccordee. Le prototype sert uniquement a valider le langage visuel, la densite, la navigation et la hierarchie des preuves.

Estimation de preparation : 80 % pour prototyper l experience ; 55-60 % pour construire immediatement le frontend definitif raccorde au reel.

Validation : syntaxe JavaScript OK ; rendu controle dans le navigateur ; changement de profil, recherche, factures, panneau de detail, Site 360 et onglets testes sans erreur console.
## Mise a jour registre vers 100 pourcent de preparation frontend - 2026-06-24

Le fichier `docs/30-Questions-pour-atteindre-100-pourcent-refonte-frontend.md` transforme l ecart de preparation en registre mesurable :

- socle acquis : 57 points ;
- 29 questions ou preuves restantes : 43 points ;
- total cible : 100 points pour lancer et raccorder proprement la premiere tranche ;
- distinction entre decisions metier, fichiers/preuves et travaux Codex ;
- blocs profils/droits, factures-CIRIL-comptabilite, contrats-maintenance-technique, UX et recette/migration.

Le score 100 ne signifie pas que toutes les fonctionnalites futures sont developpees. Il signifie que le perimetre, les contrats d ecran, les donnees, les cas de recette et la strategie de migration de la premiere tranche sont fermes.
## Mise a jour charte graphique PO2 - 2026-06-24

La charte texte et la planche de logo fournies sont conservees dans `docs/branding/`. L analyse `docs/31-Analyse-charte-graphique-et-alignement-prototype.md` confirme que la structure UX du prototype est compatible avec la marque, mais que les tokens visuels doivent etre corriges : bleu nuit `#1D3150`, vert accent limite `#74B44A`, gris techniques et titres Montserrat.

La planche PNG regroupe plusieurs variantes et n est pas un actif de production. Le DOCX ne contient aucun media integre. Il reste a obtenir les variantes SVG/PNG transparentes separees avant integration definitive du logo.

La chronologie fonctionnelle MVP/V1.5/V2 de la charte est historique et ne remplace pas la V1 produit actuelle ; la charte reste la reference visuelle uniquement.

## Mise à jour consolidation des arbitrages et audit DALKIA - 2026-06-24

Le questionnaire du document 30 est traité. Le score d’arbitrage et de preuves disponibles atteint **95/100** :

- gouvernance et profils : 10/10 ;
- factures et comptabilité : 13/13 ;
- contrats et technique : 4/7 ;
- expérience utilisateur : 6/6 ;
- recette et migration : 5/7.

Décisions principales : Responsable de service maintenance transverse, portail DALKIA en phase 2, CIRIL hors intégration V1, transmission manuelle aux finances, budget porté par le numéro d’opération, circuit P3 avec accord automatique sous 1 000 € si conforme, priorité ordinateur, portefeuille Sites 360° avant la fiche détaillée et première tranche Facturation/Cockpit/Sites/Fluides.

Audit du classeur comptable DALKIA : 75 sites, 7 contrats et 43 couples contrat/poste. La structure couvre service, fonction, antenne, opération et nature, mais aucune des 43 validations comptables n’est renseignée ; 9 règles restent à ventiler ou arbitrer et 4 marchés sont encore à confirmer. Les conclusions et clés cibles figurent dans le document 32.

Le prototype a été mis à jour : `Transmises CIRIL` devient `Transmises aux finances` avec lecture mensuelle ; Sites 360° s’ouvre sur une vue portefeuille puis permet le drill-down. L’atelier V1 reprend les décisions CIRIL, profils, budget, P3 et Sites. Vérification navigateur réussie, sans erreur console.

Points ouverts : revalidation séparée DALKIA P1/P2/P3, corpus SPIE, jeux de recette réels et contrat d’écran détaillé Fluides.


## Mise à jour clarification des actions utilisateur restantes - 2026-06-24

Le document `docs/33-Dernieres-questions-utilisateur-avant-contrats-ecran.md` réduit explicitement le travail encore demandé à Pascal : six choix d'usage concernant Fluides, puis la fourniture du corpus SPIE lorsque ce module sera ouvert et la relecture des audits DALKIA.

Codex prend en charge sans nouvelle question générale les contrats d'écran, la cartographie API, l'extension du prototype, les états d'interface, la recette initiale depuis les fichiers présents et la migration progressive du frontend. Le corpus SPIE, l'eau et le portail tiers DALKIA ne bloquent pas le démarrage de Facturation/Cockpit/Sites/Fluides.


## Mise à jour contrat et prototype Fluides V1 - 2026-06-24

Les six réponses du document 33 sont consolidées. Le contrat d'écran `docs/34-Contrat-ecran-Fluides-V1.md` fixe : portefeuille → site → compteur, électricité/gaz/eau visible, comparaisons N-1/N-2/N-3, hiver/été, journalier et courbe de charge 30 minutes, scénario central avec fourchette et corrections métier versionnées.

Correction méthodologique : DJU chauffage pour les usages de chauffage, DJU froid pour la climatisation électrique, aucune correction DJU par défaut pour l'eau ou l'électricité non thermosensible.

Audit du raccordement : ENEDIS expose déjà portefeuille PRM, consommations journalières, courbes de charge, DJU, profils, puissance et qualité ; GRDF expose PCE, collecte et séries mensuelles. Restent portefeuille multi-fluides unifié, agrégations site, détection de dérives CDC, moteurs d'atterrissage et scénarios, valorisation contractuelle et eau.

Le prototype `docs/prototype-refonte-v1/` possède maintenant une page Fluides détaillée : filtres Tous/Électricité/Gaz/Eau, KPI, trajectoire, atterrissage filtré, saisons, dérives, qualité et sites prioritaires. L'eau affiche explicitement `À construire`. Navigation vers Site 360° testée ; aucune erreur console.


## Mise à jour surveillance des abonnements et thème sombre - 2026-06-24

Le contrat d’écran Fluides inclut désormais la surveillance du calibrage des abonnements. La règle métier distingue explicitement les distributeurs et sources de mesure (ENEDIS, GRDF, futur distributeur d’eau) des fournisseurs et contrats (EDF, ENGIE, TotalEnergies). L’électricité s’appuie sur les courbes de charge ENEDIS au pas de 30 minutes et la puissance souscrite ; le gaz utilise le profil GRDF, la CAR et les paramètres contractuels ; l’eau dépend de la télérelève, des index, du débit de pointe et de la structure tarifaire réellement disponibles.

Le prototype Fluides affiche une file `Abonnements à recalibrer` avec périmètre, source de mesure, fournisseur, nombre de compteurs, diagnostic, potentiel et niveau de confiance. Les valeurs sont simulées et servent à valider l’expérience utilisateur avant raccordement aux moteurs.

Le prototype gère maintenant trois thèmes : `Automatique`, `Sombre` et `Clair`. Le mode automatique suit `prefers-color-scheme`, le choix manuel est accessible dans la barre supérieure et conservé localement. Le thème sombre automatique a été observé avec la préférence Windows sombre ; le sélecteur manuel a également été contrôlé.


## Mise à jour drill-down de calibrage des abonnements - 2026-06-24

La file Fluides ne s’arrête plus à une synthèse agrégée. Chaque exemple d’abonnement ouvre une fiche latérale avec diagnostic, paramètre contractuel actuel, mesure de référence, recommandation, impact, confiance, courbe ou profil source, détail des étapes du calcul et actions d’instruction.

Quatre cas sont simulés pour valider le parcours : puissance électrique surdimensionnée, puissance électrique à sécuriser, CAR gaz à revoir et compteur d’eau sans données assez fines. Le cas Eau interdit explicitement toute recommandation chiffrée tant que la télérelève ou une granularité suffisante n’est pas disponible.


## Mise à jour Factures & décisions et matrices comptables - 2026-06-24

Le contrat d’écran `docs/35-Contrat-ecran-Factures-Decisions-V1.md` fixe la matrice comptable au niveau du contrat/lot dans une version datée. Les factures héritent de cette matrice et conservent un instantané immuable après validation ; la comptabilité traite les exceptions et corrections motivées.

Le prototype affiche désormais la chaîne import → dédoublonnage → parsing → association contractuelle → imputation → décision/export. Quatre matrices simulées ENGIE, EDF, TotalEnergies et DALKIA présentent couverture, règles et exceptions. Chaque matrice s’ouvre dans un éditeur en masse. L’export/import XLSX est modélisé avec identifiants stables et aperçu des différences ; aucun réimport ne peut écraser directement une version active.


## Mise à jour Cockpit Direction et Sites 360° - 2026-06-25

Le contrat d’écran `docs/36-Contrat-ecran-Cockpit-Sites-V1.md` fixe le rôle du cockpit : transformer les signaux en décisions, avec source, preuve, responsable et action suivante. Le cockpit ne doit pas être une collection de KPI isolés.

Le prototype `docs/prototype-refonte-v1/` affiche maintenant une Chaîne de décision V1 reliant Factures, Fluides, Technique, Budget et Sites 360° aux preuves et aux écrans métier correspondants. La fiche Site 360° ajoute une file de décisions reliées au site : facture, abonnement, maintenance et budget, chacune avec sa preuve attendue.

Cette passe ferme le cadrage UX des quatre surfaces de première tranche : Cockpit, Factures & décisions, Fluides et Sites 360°. Les données restent simulées ; la prochaine étape est la validation utilisateur puis la migration progressive en React avec contrats de données typés.


## Mise à jour plan de migration React V1 - 2026-06-25

Le document `docs/37-Plan-migration-React-refonte-V1.md` fixe l’ordre de passage du prototype HTML vers le frontend React réel. La stratégie retenue est une migration progressive en parallèle de l’existant : socle visuel, composants communs, mocks typés, puis raccordement tranche par tranche.

Première tranche retenue : shell moderne, cockpit, Factures & décisions, Fluides et Sites 360°. Les routes historiques restent accessibles tant que les nouveaux écrans ne sont pas validés sur cas réels. Le plan prévoit explicitement les composants `AppShellV1`, `KpiCard`, `Drawer`, `StatusBadge`, `DataTable`, `FilterBar`, ainsi que les features `cockpit`, `invoices`, `fluids` et `sites`.

Prochaine action : démarrer l’incrément 1 dans `saas/frontend/src` en créant les tokens, composants communs et shell V1 sans casser `App.tsx`, `api.ts` ni les pages historiques.


## Mise à jour socle React V1 - 2026-06-25

L’incrément 1 de la migration React est démarré. Un socle non intrusif a été ajouté dans `saas/frontend/src` : tokens PO², composants communs, navigation V1, `AppShellV1` et première page `CockpitPageV1` mockée. Le fichier `main.tsx` importe les tokens V1 avant le CSS historique.

Aucune route existante n’a été remplacée : `App.tsx`, les pages historiques et les appels API restent le chemin actif. Une route laboratoire protégée `/refonte-v1` affiche `AppShellV1` + `CockpitPageV1` pour tester le socle sans bascule production. Cette prudence permet de construire la refonte à côté de l’existant avant raccordement.

Validation : `npm install` effectué dans `saas/frontend`, puis `npm run build` réussi après relance escaladée pour autoriser le spawn esbuild. Vite signale un chunk principal supérieur à 500 kB ; `npm audit` signale 4 vulnérabilités hautes non corrigées automatiquement.


## Mise à jour Factures React V1 mockées - 2026-06-25

La route laboratoire `/refonte-v1/factures` affiche désormais une première version React mockée de Factures & décisions : KPI, matrices comptables par contrat, table de factures, filtre de recherche et drawer de preuve facture.

Le shell `AppShellV1` accepte un préfixe de route pour maintenir la navigation laboratoire sous `/refonte-v1`. Les routes historiques `/factures` et les pages métier existantes ne sont pas remplacées.

Validation : `npm run build` réussi. Vite conserve un avertissement de chunk principal supérieur à 500 kB, à traiter plus tard par découpage dynamique.


## Mise à jour Fluides et Sites React V1 mockés - 2026-06-25

Le laboratoire de refonte React couvre maintenant les quatre surfaces de première tranche :

- `/refonte-v1` : cockpit mocké ;
- `/refonte-v1/factures` : Factures & décisions mocké ;
- `/refonte-v1/fluides` : Fluides mocké ;
- `/refonte-v1/sites` : Sites 360° mocké.

Fluides présente KPI, dérives, atterrissage et abonnements à recalibrer, avec distinction distributeur/fournisseur. Sites 360° présente portefeuille, recherche, sélection d’un site et décisions reliées au site.

Validation : `npm run build` réussi après ces ajouts. Le laboratoire reste non raccordé au backend et ne remplace pas les routes historiques. Avertissement Vite restant : chunk principal > 500 kB.


## Mise à jour DTO Facture React V1 - 2026-06-25

La préparation du raccordement réel de `/refonte-v1/factures` a commencé. Un DTO commun `InvoiceDecisionV1` et des adaptateurs frontend ont été ajoutés pour normaliser les sources existantes : imports factures énergie ENGIE/EDF, factures gaz TotalEnergies et factures CPE DALKIA.

La page Factures V1 mockée consomme maintenant ce DTO commun. Cela permet de remplacer progressivement les mocks par des données React Query sans réécrire l’interface.

Validation : `npm run build` réussi. Avertissement restant : chunk principal Vite > 500 kB.


## Mise à jour hook Factures React V1 - 2026-06-25

La page laboratoire `/refonte-v1/factures` utilise maintenant un hook `useInvoiceDecisionsV1`. Il tente de charger les factures énergie, gaz et CPE via les API existantes, applique les adaptateurs vers `InvoiceDecisionV1`, puis retombe sur les mocks si les sources sont indisponibles.

Cette étape amorce le raccordement réel sans rendre la page dépendante d’un backend complet et sans remplacer la route historique `/factures`. Les matrices comptables restent simulées.

Validation : `npm run build` réussi. Avertissement restant : chunk principal Vite > 500 kB.


## Mise à jour synthèse Matrices React V1 - 2026-06-25

La page laboratoire `/refonte-v1/factures` affiche désormais une synthèse des matrices comptables issue des codifications existantes lorsque les API répondent : énergie (site mappings + nature rules) et CPE DALKIA (site mappings + nature rules). À défaut, elle conserve les matrices mockées.

Cette couche frontend prépare le raccordement UX mais ne constitue pas encore le modèle backend cible de matrice contractuelle versionnée.

Validation : `npm run build` réussi. Avertissement restant : chunk principal Vite > 500 kB.

## Mise à jour cadrage backend Matrices V1 - 2026-06-25

Le document docs/38-Modele-backend-matrices-comptables-versionnees.md a été créé pour transformer la demande utilisateur sur les matrices comptables en modèle backend actionnable.

Il fixe le principe suivant : les codifications actuelles énergie et CPE sont conservées, mais la V1 cible doit ajouter une enveloppe contractuelle versionnée avec contrats, versions, règles, import/export XLSX, preview de différences et snapshots facture immuables. Une facture validée doit rester reliée à la version de matrice appliquée au moment de sa décision, même si une nouvelle version est créée ensuite.

Le document couvre aussi l'historique des factures déjà traitées, la réimportation d'un export annuel complet, les contacts entreprise pour préparer une réclamation, et la migration progressive depuis energy_accounting_* et cpe_accounting_*.

Prochaine étape technique logique : créer modèles SQLAlchemy, migration Alembic, schémas Pydantic et endpoints de base /api/accounting-matrices avant l'import XLSX complet.
