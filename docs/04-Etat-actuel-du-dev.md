# État actuel du développement
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
