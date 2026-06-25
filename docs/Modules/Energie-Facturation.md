# Module — Énergie / Facturation

> Vérification automatique des factures des fournisseurs (ENGIE, DALKIA, TOTAL, SUEZ).

## Périmètre

| Fonctionnalité roadmap | Statut |
|---|---|
| 4.1 Électricité ENGIE | 🟡 Partiel (parser PDF existant, audit à enrichir) |
| 4.2 Électricité DALKIA | 🔴 Todo |
| 4.3 Gaz TOTAL ENERGIE | 🔴 Todo |
| 4.4 Eau SUEZ | 🔴 Todo |

## Cadre contractuel Hérault Énergies

> Source : `saas/specs/03_plan_facturation_optimisation_energie.md`

Hérault Énergies est la **centrale d'achat groupé** d'électricité pour les collectivités de l'Hérault. Le CCTP impose des règles que le moteur de facturation **DOIT** respecter :

- **Lots 1-6** : segmentation par tension et profil d'usage (cf. [[Modules/Energie-BPU]])
- **Optimisation puissance** : pas de **0,1 kVA** pour EP (Éclairage Public), pas de **1 kVA** pour les autres tarifs
- **Refacturation acheminement à l'euro** (sauf C1) : le fournisseur EDF/ENGIE refacture **strictement** ce qu'a coûté l'acheminement, sans marge → c'est pour ça que le contrôle TURPE est si important ([[Modules/Energie-TURPE]])
- **Chiffrage annuel obligatoire** : toute préconisation de modification de puissance doit être chiffrée en € sur 12 mois ([[Modules/Energie-Preconisations]])

Cette spec est la **légitimité métier** du produit côté audit factures.

## Architecture transversale

### Modèle commun : `EnergyInvoiceImport`
Migration 0010, table `energy_invoice_imports` :
- Upload PDF/Excel → analyse immédiate → résultat structuré
- Statuts séparés : import, analyse technique, contrôle métier, décision utilisateur
- Champs utiles aujourd'hui : fichier source, hash, fournisseur, numéro/date facture, période, regroupement, titulaire du contrat, TTC, kWh, compteurs de contrôle

### Analyse actuellement persistée
Les migrations 0011-0012 enrichissent `energy_invoice_imports` :
- `analysis_result_json` conserve l'extraction ENGIE détaillée ;
- `control_report_json` conserve les contrôles BPU, TURPE, taxes, périodes, ENEDIS et puissance ;
- le détail PRM/FIC/lignes est déjà affiché sur `/energie/factures/:invoiceImportId`.

La trajectoire suivante est de projeter ces données dans les tables normalisées déjà décrites par `saas/specs/04_mapping_facture_engie.md` pour permettre les requêtes d'historique dépenses/tarifs et la future alimentation par API ENGIE.

### Service : `invoice_analysis.py`
Croise les factures importées avec :
1. Les `BillingBpuLine` (prix par segment tarifaire × poste)
2. Les consos ENEDIS (pour vérifier les quantités facturées)
3. Calcule l'écart prix facturé vs prix BPU attendu

### Reference BPU historique

Depuis le 2026-05-22, le controle BPU tente d'abord un raccordement historique
dans les tables `bpu_*` via `services/invoice_bpu.py` :

- fournisseur normalise `EDF` ou `ENGIE` ;
- annee de la periode facturee ;
- segment facture exact quand il est defendable (`C1` a `C4`, ou `C5_EP`) ;
- poste horosaisonnier et composante (`fourniture`, `capacite`, `cee`, `go`).

Si cette cle historique est absente ou ambigue, le moteur se replie sur les
grilles courantes `BillingConfig` / `BillingBpuLine`. Cette prudence evite
d'utiliser un mauvais BPU avant le futur modele de contexte marche explicite.

### Routes API reelles : `/api/billing/invoices/imports/*`
- `GET /api/billing/invoices/imports` : liste des imports factures
- `GET /api/billing/invoices/imports/{invoice_import_id}` : detail
- `POST /api/billing/invoices/imports` : upload + analyse
- `POST /api/billing/invoices/imports/{invoice_import_id}/analyze` : relancer l'analyse
- `PATCH /api/billing/invoices/imports/{invoice_import_id}/decision` : decision utilisateur
- `DELETE /api/billing/invoices/imports/{invoice_import_id}` : suppression

### Routes frontend utilisateur
- `/energie/factures` : liste des factures importees
- `/energie/factures/:invoiceImportId` : detail, controles et decision

### UI : `EnergieInvoicesPage` + `EnergieInvoiceDetailPage`
- `/energie/factures` contient déjà l'import manuel multi-fichiers, les KPI de revue, la liste facture, les statuts de contrôle et les décisions.
- La liste principale expose le titulaire du contrat lu dans les PDF ENGIE afin de distinguer les factures Ville / Agglomération lors de la revue.
- Les filtres de revue couvrent le titulaire, le statut de contrôle, la décision, le regroupement et les catégories/types de problèmes issus du rapport de contrôle ; ils acceptent plusieurs valeurs à la fois pour constituer un périmètre dynamique.
- Un rapport fournisseur éditable est construit depuis les factures filtrées avec synthèse des points à clarifier, périmètre retenu et sortie imprimable en PDF ; les sélections multiples actives y sont reprises.
- Depuis le 2026-05-22, le rapport fournisseur agrège les points **par famille** (Périodes, Prix contractuels, etc.) plutôt que par code, expose la **liste exhaustive des scopes** (PRM/FIC/période) en grille, ajoute une colonne **PRM impactés** par facture, et fait apparaître une section **« Estimation impact des écarts BPU »** quand des `BPU_PRICE_MISMATCH` sont retenus : récupération des détails facture (`invoice_lines`), parsing des prix dans les messages, calcul `(prix_facturé − prix_BPU) × quantité_MWh` par ligne et total HT estimé. Voir [[Sessions/2026-05-22 — Rapport fournisseur agrégat et recalcul BPU]].
- Le bloc `Lots d'import` est replié par défaut pour garder la revue des factures prioritaire lorsque le lot historique contient plusieurs dizaines de PDF.
- `/energie/factures/:invoiceImportId` contient déjà l'identité facture, le résumé simple, les familles de contrôle, les PRM/FIC, les lignes extraites et le commentaire de décision.
- Le chantier d'historique ENGIE doit prolonger cette expérience, pas créer un deuxième module facture.

## Import XLSX ENGIE — voie alternative (depuis 2026-05-22)

L'export ENGIE Entreprise « Mes Factures » (XLSX 1 an glissant, ~150 bordereaux par fichier) est désormais importable via `POST /api/billing/invoices/imports/xlsx`. Le pipeline interne :
- parser `services/invoice_parsers/engie_xlsx.py` → liste de bordereaux structurés (un par n° FMC/FUM)
- orchestrateur `services/engie_xlsx_import.py` → dédup par invoice_number + création d'un `EnergyInvoiceImport` par bordereau
- finalisation factorisée `apply_parsed_to_invoice_import()` → mêmes contrôles BPU/TURPE/taxes/périodes que les PDF

L'avantage : prix unitaires et quantités par poste exacts (pas d'OCR), 1 fichier = 1 an d'historique multi-segments (C2/C3/C4/C5). Voir [[Sessions/2026-05-22 — Import XLSX ENGIE]].

## Historique ENGIE PDF avant API

Un premier lot réel de **83 PDF ENGIE** est disponible dans `saas/energie/ENGIE/FACTURES`.

Stratégie retenue :
- PDF manuel maintenant pour constituer l'historique et qualifier le moteur ;
- import par lot persistant depuis `/energie/factures` afin de suivre doublons, erreurs et factures à revoir ;
- modèle facture normalisé indépendant de la source ;
- API ENGIE ensuite vers le même pipeline de normalisation, contrôle et décision.

La V1 reste centrée sur ENGIE électricité. Le lien fin facture → PRM → compteur → bâtiment viendra avec le chantier de rattachement compteurs ; il ne doit pas bloquer l'intégration de l'historique financier et tarifaire.

Point de revue ajouté le 2026-05-21 : le libellé brut `Titulaire du contrat` est conservé et filtrable. Si la valeur doit devenir un axe analytique stable au-delà des libellés ENGIE, prévoir ensuite une normalisation explicite du type de porteur (`ville`, `agglomeration`, `autre`) sans perdre la valeur source.

## ENGIE — état actuel

Point de revue ajoute le 2026-05-22 : l'historique BPU est maintenant une
source possible du controle facture, mais seulement en rapprochement exact.
Avant de lancer l'audit EDF massif, il reste a modeliser le contexte
contractuel qui decide entre anciens lots EDF, nouveau lot ENGIE batiments et
lot EDF eclairage public.

### Parser : `services/invoice_parsers/engie_pdf.py`
- Extrait : période de facturation, PRM concernés, consommations par poste (HPH/HCH/...), prix unitaires, totaux HT/TTC
- Limitations connues : variations de mise en page entre les modèles de facture ENGIE

### Documents de référence — à consulter avant toute évolution du parser

> **Mapping facture ENGIE** : `saas/specs/04_mapping_facture_engie.md` (553 lignes)
> Tableau complet des colonnes page 3, codes index HPSH/HCSH/HPSB/HCSB/Base/Pointe, conversion EUR/kWh ↔ EUR/MWh. Contient un modèle de tables (`energy_invoices` / `energy_invoice_sites` / `energy_invoice_periods`) plus fin que l'`EnergyInvoiceAnalysis` actuel — utile quand on étendra à DALKIA / TOTAL.

> **Matrice de contrôles** : `saas/specs/05_matrice_controles_factures_energie.md` (157 lignes)
> 40+ codes d'erreur normalisés (`BPU_PRICE_MISMATCH`, `TURPE_VERSION_MISSING`, `POWER_LOAD_CURVE_OVERRUN`, etc.), statuts de décision (`valid` / `review` / `invalid`), tolérances chiffrées (0,05 EUR sur les totaux, 0,05 EUR/MWh sur les prix unitaires), règles exactes de rapprochement BPU (ex: `BT <= 36 kVA SDT CU4/MU4` → `CU/base`). Doc canonique du moteur de décision.

### Endpoints proxy ENGIE
- `services/engie_client.py` : client OAuth ENGIE Entreprise
- Routes `/api/engie/*`
- Données contractuelles + factures via API (quand disponibles)

## DALKIA — 🔴 Todo

### Notes
- DALKIA est un fournisseur de **chaleur urbaine** (réseaux de chaleur) ET d'électricité
- Factures multi-fluides possible → ajouter `fuel_type` à `EnergyInvoiceImport`
- Format Excel attendu : modèle propriétaire à reverse-engineer sur 1-2 fichiers d'exemple

### Architecture cible
1. Créer `services/invoice_parsers/dalkia_excel.py` (utiliser `openpyxl`)
2. Mapping colonnes Excel → champs `EnergyInvoiceAnalysis`
3. Tester sur un échantillon de fichiers réels (à demander à l'utilisateur)

## TOTAL ENERGIE Gaz — 🔴 Todo

### Notes
- TOTAL fournit gaz et élec — focus ici sur gaz
- Pas de format standard, mais format PDF probablement assez stable
- Pattern : `services/invoice_parsers/total_energie_pdf.py` calqué sur `engie_pdf.py`
- Le BPU HERAULT ENERGIE lot 7 gaz est importable dans les tables `bpu_*` via `app.scripts.import_bpu_gas_lot7`. Il constitue la référence de prix du marché Ville/TotalEnergies, pas le prix P1 DALKIA.

## SUEZ Eau — 🔴 Todo

### Notes
- Probablement le même parser que pour la conso (cf. [[Modules/Energie-Consommation]] section SUEZ)
- Une facture eau contient consommation + tarif + total → les 3 ingrédients pour l'audit

## Workflow audit de facture (générique)

```
1. Utilisateur upload PDF/Excel facture sur /energie/factures
2. POST /api/billing/invoices/imports → EnergyInvoiceImport.status = "analyzing"
3. Tâche async : invoice_parsers.{supplier} extrait les champs
4. Pour chaque ligne extraite :
   a. Cherche le BPU applicable (supplier × year × lot)
   b. Cherche le BpuPriceComponent pour (segment, period, component)
   c. Calcule écart facturé vs attendu
   d. Si écart > seuil → flag pour revue manuelle
5. EnergyInvoiceImport.status = "success"
6. Utilisateur consulte le détail dans /energie/factures/{id} et valide/conteste
```

## Voir aussi

- [[Modules/Energie-BPU]] — Source des prix attendus
- [[Modules/Energie-Preconisations]] — Calcul prix unitaires
- [[38-Modele-backend-matrices-comptables-versionnees]] — Imputation comptable versionnée par contrat (en aval du contrôle facture)

## Imputation comptable versionnée (backend posé 2026-06-25)

L'imputation comptable des factures (quel service/fonction/nature/opération/antenne pour chaque ligne) ne vit plus seulement dans les tables à plat `energy_accounting_*` / `cpe_accounting_*`. Un référentiel **versionné par contrat** a été ajouté (migration `0064`) : `accounting_matrix_contracts` → `accounting_matrix_versions` → `accounting_matrix_rules`, plus `invoice_accounting_snapshots` qui fige l'imputation appliquée à une facture au moment de la décision. Router `/api/accounting-matrices/*`. Invariant : une version active n'est jamais écrasée (clone → édition → activation). Cadrage : [[38-Modele-backend-matrices-comptables-versionnees]] ; décision : [[Decisions/010-matrices-comptables-versionnees]]. Les tables à plat existantes restent la source du seed initial.

## Note de consolidation - 2026-05-26

### Ce qui a ete developpe recemment

- Import XLSX ENGIE `MesFactures_*.xlsx` depuis `/energie/factures`, avec traitement en arriere-plan pour eviter les timeouts.
- Bascule UI vers le flux XLSX-only pour les nouveaux imports, tout en conservant le code PDF pour l'historique.
- Upsert des bordereaux deja presents avec option `force_update`, en preservant les decisions utilisateur.
- Acceleration du parser XLSX `services/invoice_parsers/engie_xlsx.py` pour traiter l'export complet sans blocage.
- Filtres facture multi-criteres : controle, decision, regroupement, titulaire, categorie de probleme, type de probleme, recherche.
- Rapport fournisseur imprime depuis les factures filtrees, avec points de controle retenus et recalcul des ecarts BPU quand le detail `mismatches_detail` est disponible.
- Correction du rapport : les points BPU non chiffrables ne rendent plus le rapport vide.
- Filtres BPU fixes : la categorie `Prix contractuels` et les types BPU restent visibles meme si aucun ecart BPU n'est present dans les factures courantes.
- Suivi mensuel de facturation en tete de `/energie/factures` : consommation facturee ENGIE vs releve ENEDIS, nombre de factures, nombre de PRM factures, alerte de trou potentiel.
- Synthese contractuelle locale : `saas/energie/HERAULT ENERGIE/SYNTHESE_FACTURATION.md` pour documenter frequence, delais, penalites et controles attendus.

### Controle tarifaire direct du 2026-05-26

Fichier controle : `saas/energie/ENGIE/EXPORTS/MesFactures_20260522150740.xlsx`.

BPU controle : `saas/energie/HERAULT ENERGIE/BPU_2026_Lots_1_2_et_7.xlsx`.

Resultat Lot 1 - Batiment :

| Indicateur | Valeur |
|---|---:|
| Lignes tarifaires candidates | 5368 |
| Lignes OK | 5355 |
| Ecarts potentiels | 13 |
| References BPU manquantes | 0 |
| Prix BPU manquants | 0 |

Contre-epreuve Lot 2 - EP : 5323 ecarts sur 5368 lignes. Conclusion : le fichier analyse releve bien du Lot 1 - Batiment, pas du Lot 2 - EP.

Les 13 ecarts restants sont uniquement sur `Fourniture/base` : 10 lignes `CU/base`, souvent sur tres petites consommations avec impact HT estime a 0,00 EUR, et 3 lignes `LU/base` sur `BORNE FIXE MARCHE DU BARROU` avec impacts estimes 0,04 / 0,14 / 0,23 EUR HT.

Artefacts locaux generes mais ignores par Git car le dossier `saas/energie/ENGIE/` est gitignore :

- `saas/energie/ENGIE/RAPPORTS/rapport_ecarts_tarification_bpu_2026.md`
- `saas/energie/ENGIE/RAPPORTS/rapport_ecarts_tarification_bpu_2026_detail_lignes.csv`
- `saas/energie/ENGIE/RAPPORTS/rapport_ecarts_tarification_bpu_2026_anomalies.csv`

### Regles de matching BPU ajoutees / confirmees

- C5 sans differenciation temporelle + `Version d'Utilisation = CU` -> `CU/base`.
- C5 sans differenciation temporelle + `Version d'Utilisation = LU` -> `LU/base`.
- C5 4 plages avec postes saisonniers -> `CU4` ou `MU4` selon version.
- C5 libelle 4 plages mais facture uniquement en `BASE` + version `CU` -> `CU/base`, pas `CU4/base`.
- CEE et garantie d'origine sont des composantes transverses : quand le fichier ne porte pas de poste horosaisonnier, utiliser le prix BPU applicable au tarif si le prix est identique sur les postes.

### Limites connues

- Les rapports de controle deja stockes en BDD ne se recalculent pas seuls apres correction du code : il faut reimporter le XLSX avec `Forcer la mise a jour des bordereaux deja importes`.
- Les derniers commits sont pousses sur `main`, mais le deploy OVH etait bloque par un probleme externe Docker Hub (`TLS handshake timeout`) au moment de la documentation.
- Les 13 ecarts potentiels doivent etre relus apres reimport force, pour verifier s'ils apparaissent encore en application ou s'ils relevent seulement du rapport local calcule a partir de montants arrondis.

### Complement filtres - 2026-05-26

Audit direct du fichier `MesFactures_20260522150740.xlsx` :

- 1069 lignes site/FIC, 144 bordereaux, 268 PRM/PCE.
- Les filtres initiaux etaient coherents pour controle, decision, regroupement, titulaire, categorie et type de probleme.
- Ils etaient insuffisants pour une relecture metier complete du XLSX.

Filtres ajoutes sur `/energie/factures` et propages a la liste, au rapport fournisseur et au graphique mensuel :

- mois de facture ;
- PRM/PCE ;
- FIC ;
- nom de site ;
- commune ;
- segment distributeur ;
- version tarifaire ;
- libelle tarifaire ;
- type de document.

Point d'attention : pour le graphique mensuel, les filtres site/PRM/FIC/segment/tarif n'additionnent que les sites correspondants dans un bordereau, pas tout le bordereau.
