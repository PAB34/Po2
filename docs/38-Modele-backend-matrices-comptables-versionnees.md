# 38 — Modèle backend des matrices comptables versionnées

> Date : 2026-06-25  
> Statut : cadrage technique avant implémentation  
> Périmètre : Factures & décisions V1, matrices comptables par contrat, import/export XLSX, snapshots de validation.

## Pourquoi ce document existe

La refonte V1 affiche déjà une synthèse des matrices comptables dans le laboratoire React /refonte-v1/factures. Cette synthèse consomme, quand elles sont disponibles, les codifications existantes énergie et CPE DALKIA.

Ce n'est pas encore suffisant pour le frontend définitif. Le besoin métier exprimé est plus robuste : pour chaque contrat ou marché, la comptabilité doit pouvoir relire, corriger, importer/exporter et valider une matrice comptable. Une facture validée doit ensuite conserver la version de matrice utilisée au moment de la décision.

Autrement dit : la matrice ne doit pas être seulement une table de correspondance modifiable. Elle doit devenir un référentiel versionné, traçable et auditable.

## État existant à préserver

### Énergie / fourniture électricité-gaz

Éléments déjà présents :

- energy_accounting_site_mappings ;
- energy_accounting_nature_rules ;
- appels frontend existants : fetchEnergySiteMappings, fetchEnergyNatureRules, importEnergyAccountingCodification et bootstrap des mappings sites.

Ces briques permettent déjà de rattacher des PRM/sites et des lignes de facturation à des natures comptables.

Limite actuelle : pas de version de matrice, pas de workflow brouillon/active/archivée, pas de snapshot immuable au niveau de la facture.

### CPE DALKIA

Éléments déjà présents :

- cpe_accounting_site_mappings ;
- cpe_accounting_nature_rules ;
- rattachement des lignes cpe_finance_lines vers site/règle comptable ;
- finance_exported_at sur les factures CPE ;
- appels frontend existants : fetchCpeAccountingSiteMappings, fetchCpeAccountingNatureRules et import de codification CPE.

Limite actuelle : les règles existent, mais elles ne forment pas encore un référentiel versionné manipulable comme un objet métier contractuel.

### Gaz TotalEnergies

Éléments déjà présents :

- factures gaz importées ;
- trace de contrôle control_detail_json ;
- finance_exported_at ;
- référentiels gaz datés.

Limite actuelle : les règles comptables gaz doivent pouvoir s'intégrer au même mécanisme V1 que les autres fournisseurs.

## Principe cible

Une matrice comptable V1 est définie par :

1. un contrat ou marché ;
2. une version ;
3. un ensemble de règles de ventilation ;
4. un état de vie ;
5. des preuves d'import/export ;
6. des snapshots figés appliqués aux factures validées.

Règle centrale : une version active ne doit jamais être écrasée directement par un import XLSX. Un import produit un aperçu de différences, puis une nouvelle version brouillon ou candidate. La bascule en actif est un acte explicite.

## Modèle de données proposé

### accounting_matrix_contracts

Objet racine : une matrice par contrat, lot ou marché.

| Champ | Rôle |
|---|---|
| id | Identifiant interne |
| city_id | Isolation multi-tenant |
| domain | fluides, cpe, maintenance, travaux, futur |
| supplier | EDF, ENGIE, TotalEnergies, DALKIA, SPIE, SUEZ... |
| contract_code | Code contrat ou marché |
| contract_label | Libellé lisible |
| lot_label | Lot si applicable |
| starts_on / ends_on | Dates contractuelles |
| contact_name | Interlocuteur entreprise |
| contact_email | Adresse pour préparer une réclamation |
| status | active, inactive, draft, archived |
| created_at / updated_at | Traçabilité |

Notes :

- domain = fluides doit couvrir EDF, ENGIE, TotalEnergies et plus tard l'eau.
- DALKIA peut rester en domain = cpe pour distinguer P1/P2/P3.
- SPIE pourra être maintenance ou technique selon le découpage final.

### accounting_matrix_versions

Version datée d'une matrice.

| Champ | Rôle |
|---|---|
| id | Identifiant interne |
| matrix_contract_id | Contrat matrice |
| version_label | Ex. V3 - validée compta 2026 |
| status | draft, candidate, active, archived |
| effective_from / effective_to | Période d'effet |
| source | manuel, import XLSX, migration énergie, migration CPE |
| source_filename / source_sha256 | Preuve du fichier source |
| created_by_user_id | Auteur |
| validated_by_user_id / validated_at | Validation |
| change_summary_json | Synthèse des différences |
| created_at / updated_at | Traçabilité |

Contraintes recommandées :

- une seule version active par contrat matrice ;
- pas de suppression physique d'une version appliquée à une facture ;
- un import ne modifie jamais la version active en place.

### accounting_matrix_rules

Règles de ventilation et de rattachement.

| Champ | Rôle |
|---|---|
| id | Identifiant interne |
| matrix_version_id | Version concernée |
| stable_rule_key | Identifiant stable pour import/export/diff |
| scope | site, meter, billed_item, subscription, tax, p1, p2, p3, other |
| site_code | Code site comptable si connu |
| building_id | Lien patrimoine si disponible |
| meter_id | PRM/PCE/compteur eau si applicable |
| billed_item_pattern | Libellé ligne facture ou motif normalisé |
| supplier_item_code | Code fournisseur si disponible |
| accounting_service | Service comptable |
| accounting_function | Fonction |
| accounting_antenna | Antenne |
| operation_number | Numéro d'opération budget |
| accounting_nature | Nature comptable |
| accounting_label | Libellé nature |
| allocation_percent | Pourcentage de ventilation, 100 par défaut |
| priority | Arbitrage si plusieurs règles matchent |
| is_active | Règle active dans la version |
| comment | Commentaire comptabilité |

Contraintes recommandées :

- allocation_percent entre 0 et 100 ;
- total par groupe de ventilation = 100 % si une facture/ligne est éclatée ;
- pas de doublon actif sur la même clé de matching dans une version ;
- stable_rule_key obligatoire pour que l'aller-retour XLSX reste fiable.

### invoice_accounting_snapshots

Instantané appliqué à une facture au moment de la décision.

| Champ | Rôle |
|---|---|
| id | Identifiant interne |
| city_id | Isolation multi-tenant |
| invoice_source | energy_import, gas_totalenergies, cpe_dalkia, futur |
| invoice_id | Identifiant de la facture source |
| matrix_contract_id | Matrice utilisée |
| matrix_version_id | Version exacte utilisée |
| status | proposed, validated, manual_override, blocked, exported |
| snapshot_json | Résultat complet de l'imputation appliquée |
| exceptions_json | Lignes non imputées ou arbitrages |
| validated_by_user_id / validated_at | Validation |
| exported_at | Date de transmission finances |
| created_at / updated_at | Traçabilité |

C'est cette table qui garantit l'historique : si une facture a été traitée en juin avec la matrice V3, elle reste liée à V3 même si V4 est créée ensuite.

### accounting_matrix_import_batches optionnelle

Utile si on veut tracer fortement chaque import XLSX.

| Champ | Rôle |
|---|---|
| id | Identifiant interne |
| city_id | Isolation multi-tenant |
| matrix_contract_id | Contrat ciblé |
| filename / sha256 | Preuve du fichier importé |
| status | previewed, committed, rejected |
| preview_json | Diff calculé |
| errors_json | Erreurs de structure |
| created_by_user_id / created_at | Auteur et date |

## API cible proposée

### Lecture et synthèse

- GET /api/accounting-matrices/contracts : liste des matrices par contrat, avec version active et couverture.
- GET /api/accounting-matrices/contracts/{id} : détail contrat, interlocuteur, versions.
- GET /api/accounting-matrices/versions/{id}/rules : règles d'une version.
- GET /api/accounting-matrices/invoices/{source}/{invoice_id}/snapshot : snapshot appliqué à une facture.

### Cycle de vie

- POST /api/accounting-matrices/contracts : créer une matrice contrat.
- POST /api/accounting-matrices/contracts/{id}/versions : créer une version brouillon depuis zéro ou depuis active.
- POST /api/accounting-matrices/versions/{id}/activate : activer explicitement une version candidate.
- POST /api/accounting-matrices/versions/{id}/archive : archiver une version non active.
- PATCH /api/accounting-matrices/contracts/{id} : modifier libellés, contact entreprise, dates, statut.

### Règles

- POST /api/accounting-matrices/versions/{id}/rules.
- PATCH /api/accounting-matrices/rules/{rule_id}.
- DELETE logique ou désactivation d'une règle.

En pratique, la suppression physique est déconseillée si la version a déjà été utilisée pour générer un snapshot.

### Import/export XLSX

- GET /api/accounting-matrices/versions/{id}/export.xlsx : export lisible et réimportable.
- POST /api/accounting-matrices/contracts/{id}/import-preview : charge un XLSX et retourne les différences sans écrire en actif.
- POST /api/accounting-matrices/import-batches/{id}/commit : transforme le preview en nouvelle version brouillon ou candidate.
- GET /api/accounting-matrices/import-batches/{id} : détail du lot importé et erreurs.

Diff minimal attendu : règles ajoutées, modifiées, supprimées, ambiguës, lignes sans identifiant stable, ventilation différente de 100 %, sites ou compteurs inconnus.

### Application à une facture

- POST /api/accounting-matrices/apply : produit une proposition d'imputation à partir d'une facture.
- POST /api/accounting-matrices/invoices/{source}/{invoice_id}/validate-snapshot : fige la proposition.
- POST /api/accounting-matrices/invoices/{source}/{invoice_id}/manual-override : fige une correction manuelle motivée.
- POST /api/accounting-matrices/invoices/{source}/{invoice_id}/export-finance : marque la transmission finances et produit le fichier d'export si nécessaire.

## Format XLSX recommandé

Le fichier doit rester confortable pour la comptabilité. Colonnes minimales :

| Colonne | Obligatoire | Commentaire |
|---|---:|---|
| stable_rule_key | Oui | Ne doit pas changer entre exports/imports |
| contract_code | Oui | Contrat ou lot |
| supplier | Oui | Fournisseur/prestataire |
| site_code | Selon règle | Code site comptable |
| site_label | Non | Lisible pour contrôle humain |
| meter_id | Selon fluide | PRM, PCE, compteur eau |
| billed_item_pattern | Selon règle | Libellé ligne facture ou motif normalisé |
| scope | Oui | site, meter, billed_item, p1, p2, p3... |
| accounting_service | Non | Service |
| accounting_function | Non | Fonction |
| accounting_antenna | Non | Antenne |
| operation_number | Non | Numéro d'opération budget |
| accounting_nature | Oui | Nature comptable |
| accounting_label | Non | Libellé nature |
| allocation_percent | Oui | 100 par défaut |
| priority | Non | Priorité de matching |
| comment | Non | Commentaire comptabilité |
| is_active | Oui | Oui/non |

Recommandation : l'export doit contenir un onglet Lisez-moi expliquant les colonnes, et un onglet Erreurs lors d'un preview rejeté.

## Workflow utilisateur cible

1. Import facture : la plateforme détecte fournisseur, contrat, site, période, montant, lignes facturées et doublon éventuel.
2. Association contrat/matrice : recherche de la matrice active correspondant au fournisseur, contrat, lot et période.
3. Application de la matrice : rapprochement des lignes facture aux règles site, compteur, nature, opération, ventilation.
4. Revue comptabilité : validation, correction ou retour XLSX. Une correction commune crée une nouvelle version candidate.
5. Décision facture : validation, blocage ou préparation d'une réclamation.
6. Snapshot : écriture de invoice_accounting_snapshots au moment de la validation.
7. Export finances : V1 en transmission manuelle, avec marquage exported_at.

## Historique et dédoublonnage des factures

Sujet exprimé par l'utilisateur : il pourra importer un export annuel complet contenant des factures déjà traitées.

Règle cible :

- une facture déjà connue doit être reconnue par fournisseur + numéro facture + contrat + montant + période ;
- si elle possède déjà un snapshot validé ou exporté, elle doit remonter comme déjà traitée ;
- la réimportation ne doit pas recréer une nouvelle décision ;
- si le fichier réimporté diffère fortement de la facture historisée, la plateforme doit signaler une divergence plutôt qu'écraser l'historique.

## Contacts entreprise et réclamations

Chaque matrice contrat doit porter au minimum : interlocuteur entreprise, mail de contact, objet type et modèle de mail optionnel.

Pour la V1, il n'est pas nécessaire d'envoyer réellement le mail depuis la plateforme. Une solution sobre suffit : bouton Préparer une réclamation qui ouvre ou copie destinataire, objet, corps du mail, facture concernée, anomalies et preuves.

L'envoi direct pourra venir plus tard si le domaine/mail OVH est clarifié.

## Stratégie de migration depuis l'existant

### Étape 1 — lecture unifiée

Conserver les tables existantes et les exposer dans une synthèse V1, comme commencé côté frontend avec useAccountingMatricesV1.

### Étape 2 — créer les tables versionnées

Ajouter les nouvelles tables sans supprimer les anciennes. Les anciennes deviennent les sources de migration initiale.

### Étape 3 — seed initial

Créer automatiquement :

- une matrice ENGIE/EDF - Électricité depuis energy_accounting_* ;
- une matrice DALKIA - CPE depuis cpe_accounting_* ;
- une matrice TotalEnergies - Gaz si les règles comptables sont disponibles ou à compléter.

Chaque seed doit créer une version V0 - migration existant en draft ou candidate, pas forcément active sans validation.

### Étape 4 — brancher /refonte-v1/factures

Remplacer la synthèse frontend transitoire par les endpoints accounting-matrices/*.

### Étape 5 — appliquer aux factures

Brancher l'application de matrice sur les factures énergie, gaz et CPE, puis écrire les snapshots lors de la validation.

## Critères de recette

La brique est considérée prête quand :

- une matrice peut être créée pour un contrat ;
- une version peut être créée depuis un import XLSX ;
- le preview affiche les différences avant validation ;
- une version peut être activée sans écraser l'ancienne ;
- une facture déjà validée garde son snapshot même après modification de la matrice ;
- une facture réimportée est reconnue comme déjà traitée ;
- les exceptions comptables sont visibles dans /refonte-v1/factures ;
- un export XLSX peut être relu sans perte d'identifiants stables ;
- l'ancien parcours énergie/CPE reste fonctionnel pendant la migration.

## Risques à éviter

1. Modifier directement une règle active utilisée par des factures historisées.
2. Laisser l'import XLSX écraser silencieusement une version.
3. Perdre les identifiants stables de règles dans l'aller-retour Excel.
4. Mélanger fournisseur, distributeur et contrat dans une même clé ambiguë.
5. Confondre validation métier facture et validation comptable de la matrice.
6. Forcer l'envoi mail réel avant d'avoir clarifié l'adresse/domaine.
7. Créer une seule matrice globale au lieu d'une matrice par contrat ou lot.

## Prochaine action recommandée

Implémenter d'abord le backend minimal des matrices versionnées : modèles SQLAlchemy, migration Alembic, schémas Pydantic et endpoints de lecture/création/version. L'import XLSX peut venir juste après, mais la structure versionnée doit être posée avant de raccorder définitivement le frontend Factures V1.

## Implémentation backend minimale - 2026-06-25

La structure versionnée est posée dans `saas/backend`.

Fichiers créés :

- `app/models/accounting_matrix.py` : `AccountingMatrixContract`, `AccountingMatrixVersion`, `AccountingMatrixRule`, `InvoiceAccountingSnapshot` ;
- `app/schemas/accounting_matrix.py` : schémas de lecture, création et mise à jour ;
- `app/services/accounting_matrix.py` : invariants métier (une seule version active par contrat, pas d'édition de règle sur version active/archivée, clonage de version, activation explicite qui archive l'ancienne active) ;
- `app/api/routes/accounting_matrix.py` : router `/api/accounting-matrices` ;
- `alembic/versions/0064_add_accounting_matrices.py` : migration des 4 tables.

Fichiers modifiés : `app/models/__init__.py` (export) et `app/api/router.py` (montage du router).

Endpoints livrés (tranche minimale lecture/création/version) :

- `GET /api/accounting-matrices/contracts` (filtres `domain`, `supplier`) ;
- `POST /api/accounting-matrices/contracts` ;
- `GET /api/accounting-matrices/contracts/{id}` (détail + versions) ;
- `PATCH /api/accounting-matrices/contracts/{id}` ;
- `POST /api/accounting-matrices/contracts/{id}/versions` (avec `clone_from_version_id` optionnel) ;
- `POST /api/accounting-matrices/versions/{id}/activate` ;
- `POST /api/accounting-matrices/versions/{id}/archive` ;
- `GET /api/accounting-matrices/versions/{id}/rules` ;
- `POST /api/accounting-matrices/versions/{id}/rules` ;
- `PATCH /api/accounting-matrices/rules/{rule_id}` ;
- `GET /api/accounting-matrices/invoices/{source}/{invoice_id}/snapshot` (lecture seule).

Règle d'or respectée dans le service : une version `active` n'est jamais modifiée en place. Pour faire évoluer une matrice active, on crée une version clonée (`clone_from_version_id`), on l'édite, puis on l'active ; `activate_version` archive automatiquement l'ancienne version active.

Validation : `python -m py_compile` OK sur les 7 fichiers. L'import runtime FastAPI et le test de migration Alembic ne sont pas exécutés localement (FastAPI/SQLAlchemy absents du poste) ; validation via CI/GitHub Actions requise. Aucun build frontend concerné.

### Seed de migration depuis l'existant (étape 3 — fait 2026-06-25)

Ajouté dans `app/services/accounting_matrix.py` (`seed_from_existing`) + endpoint `POST /api/accounting-matrices/seed`. Idempotent (saute les matrices déjà présentes), scopé `city_id`, ne crée que des versions `V0 - migration existant` en `draft` (jamais active).

Regroupement retenu (arbitrage utilisateur 2026-06-25) :

- **Énergie** : une matrice par fournisseur (`domain=fluides`), règles de nature suivant leur `supplier` ; les mappings PRM->axes (non rattachés à un fournisseur dans l'existant) sont dupliqués dans chaque matrice énergie.
- **CPE DALKIA** : une matrice par `contract_code` (`domain=cpe`, `supplier=DALKIA`) ; les mappings site->axes (sans `contract_code`) sont dupliqués dans chaque matrice CPE.

Renvoie un récapitulatif `{energy, cpe, versions_created}` (contrats créés/ignorés, règles).

### Différé à la phase suivante (volontairement hors tranche minimale)

- table `accounting_matrix_import_batches` + endpoints import/export XLSX (`import-preview`, `commit`, `export.xlsx`) ;
- endpoints d'application à la facture qui **écrivent** les snapshots : `apply`, `validate-snapshot`, `manual-override`, `export-finance` ;
- contrôle « somme des ventilations = 100 % » et droits par rôle (comptabilité / responsable marché / admin, cf. doc 35 §6) ;
- bascule du frontend `/refonte-v1/factures` de `useAccountingMatricesV1` (synthèse transitoire) vers `/api/accounting-matrices/*`.

### Handoff très concret pour la prochaine IA

1. Exécuter la migration `0064` sur staging puis vérifier `alembic upgrade head`.
2. Appeler `POST /api/accounting-matrices/seed` sur staging et vérifier le récapitulatif ; contrôler quelques matrices créées (énergie par fournisseur, CPE par contrat), toutes en version `draft`.
3. Implémenter l'import XLSX (preview/diff puis commit en version brouillon) en respectant `stable_rule_key` pour l'aller-retour, format colonnes = doc 35 §5.
4. Implémenter `apply` + `validate-snapshot` pour écrire `invoice_accounting_snapshots` au moment de la décision (avec contrôle 100 % de ventilation), et le dédoublonnage des factures réimportées (doc 35 §2 et critères 2/5).
5. Ne pas oublier les contraintes de recette du présent document (section « Critères de recette »).
