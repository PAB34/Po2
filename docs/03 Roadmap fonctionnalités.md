# Roadmap fonctionnalités

> Source : fichier `Fonctionnalités.xlsx` fourni par l'utilisateur.
> Croisement avec l'existant à date : **2026-05-19**.
>
> Légende statut :
> - ✅ **Fait** — fonctionnalité en prod sur https://patrimoineaucarre.com
> - 🟡 **Partiel** — base technique en place, manque finitions ou couverture cible
> - 🔴 **Todo** — pas commencé
> - 🟣 **Bonus** — non listé dans la grille initiale mais implémenté en plus

## 1 · PATRIMOINE

### 1.1 Inventaire bâtiment / Propriétaire / DGFIP
- **Source de données** : Open data (MAJIC fiscal + IGN + OSM)
- **Objectif utilisateur** : Permettre à l'utilisateur de constituer sa base patrimoniale
- **Statut** : ✅ **Fait**
- **Implémentation** :
  - Backend : `services/buildings.py`, `services/building_naming.py`, `services/cities.py`
  - Modèles : `Building`, `Local`, `City` (avec PostGIS)
  - Routes : `/api/buildings`, `/api/cities`
  - Frontend : `BuildingsLandingPage`, `BuildingsListPage`, `BuildingCreateEditPage`, `BuildingDetailPage`
  - Carte interactive : `BuildingPortfolioMap`, `BuildingNamingMap`, `BuildingSelectionWorkspace`
- **Détails** : Le workflow `building_naming.py` réconcilie les imports MAJIC/DGFiP avec les géodonnées IGN/OSM (matching par adresse + proximité géographique)
- **Voir aussi** : [[Modules/Patrimoine]]

### 1.2 Inventaire bâtiment / Locataire / Baux
- **Source** : PDF à uploader sur la plateforme
- **Objectif** : Insérer dans la base patrimoniale les locaux que la ville **loue** (et non détient)
- **Statut** : 🔴 **Todo**
- **Notes pour l'IA suivante** :
  - Aucun modèle `Bail` / `Lease` / `Tenancy` n'existe encore
  - Réutiliser le modèle `Local` existant en ajoutant un flag `is_rented: bool` + champs bail (`lease_start`, `lease_end`, `lease_doc_id`, `landlord_name`)
  - Prévoir un endpoint `POST /api/buildings/{id}/leases` avec upload PDF (multipart) + un parser PDF best-effort (réutiliser approche `services/bpu.py` : pdftotext + regex)
  - Cf. [[Modules/Patrimoine]] section "Pistes baux locataires"

## 2 · PATRIMOINE / GESTION TECHNIQUE

### 2.1 CVC / inventaire maintenance
- **Source** : Excel (référentiel SYPEMI `durees_vie_powerbi_base_wide.csv`, 310 lignes)
- **Objectif** : Liste des équipements CVC du patrimoine + état + PPT (Plan Pluriannuel de Travaux)
- **Statut** : 🟡 **Partiel** — la base est là, le filtre CVC n'est pas isolé
- **Implémentation** :
  - Modèles : `EquipmentReference` (référentiel 310 lignes), `BuildingEquipment` (assignation bâtiment × équipement avec état + quantité + durée vie résiduelle)
  - Service : `services/equipment.py` (calculs score santé, coefficients état)
  - Routes : `/api/equipment/*`
  - Frontend : `BuildingTechniquePage` (page unique pour tous les équipements, pas séparée CVC/Enveloppe)
  - Migration : `0014_add_equipment_tables.py`
- **Notes pour l'IA suivante** :
  - Le CSV référence comporte les niveaux 1 à 5 (hiérarchie SYPEMI) — `code_niveau_1` permet de filtrer "CVC" vs "Enveloppe"
  - Couplages avec PPT à imaginer (probablement séparer en 2 vues : équipements CVC, matériaux enveloppe)
- **Voir aussi** : [[Modules/Gestion technique]]

### 2.2 Enveloppe / inventaire technicien
- **Source** : Excel (même référentiel SYPEMI)
- **Objectif** : Liste des matériaux d'enveloppe + état + PPT
- **Statut** : 🟡 **Partiel** — partage la même UI que CVC, à scinder
- **Notes** : voir 2.1 — séparer côté UI par `code_niveau_1`

### 2.3 Occupation / périodes d'occupation
- **Source** : Excel
- **Objectif** : Connaître l'occupation réelle des bâtiments pour conjuguer avec HC/HP des contrats d'énergie
- **Statut** : 🔴 **Todo**
- **Notes pour l'IA suivante** :
  - Modèle à créer : `BuildingOccupancy` (building_id, day_of_week, start_time, end_time, period_label, season?)
  - Possible réutilisation de la structure `BillingHphcSlot` qui existe déjà (`models/billing.py`) — voir s'il y a une logique commune
  - L'analytics critique = comparer le profil d'occupation aux postes tarifaires pour identifier les surconsos hors présence

### 2.4 CVC / Température et programmation
- **Source** : Excel
- **Objectif** : Aperçu des températures + programmation pour conjuguer avec occupation, repérer anomalies
- **Statut** : 🔴 **Todo**
- **Notes** :
  - Probable IoT / GTB à intégrer (Sauter, Trend, Schneider…) — donc API externe à choisir avec utilisateur
  - Ou import Excel manuel comme MVP

## 3 · FLUIDES / CONSOMMATION

### 3.1 Électricité / ENEDIS (API)
- **Source** : ENEDIS API (OAuth2 client_credentials)
- **Objectif** : Conso + courbes de charge compteur par compteur, couplé DJU
- **Statut** : ✅ **Fait** (sync + async)
- **Implémentation** :
  - **Sync** : `services/enedis_sync.py` (1226 lignes) — conso quotidienne, P max, courbe de charge avec rate limiter (5 req/s, 950/h, 5 concurrent), TokenManager thread-safe
  - **Async** : `services/enedis_async.py` (~700 lignes) — POST `commanderPublicationPonctuelle`, FTP polling, AES decrypt, parsers JSON → CSV
  - **Scheduler** : `core/scheduler.py` (APScheduler poll FTP toutes les 5 min)
  - **DJU** : `services/dju_sync.py` (couplage conso × DJU pour normaliser la perf énergétique)
  - **Models** : `EnedisAsyncJob`
  - **Routes** : `/api/energie/sync/*` et `/api/energie/sync/async/*`
  - **Frontend** : `EnergiePage`, `EnergieDetailPage`, `EnergieAsyncJobsPanel`
- **Voir aussi** : [[Modules/Énergie - Consommation]]

### 3.2 Gaz / GRDF (API)
- **Source** : GRDF API
- **Objectif** : Conso + CDC gaz par compteur, couplé DJU
- **Statut** : 🔴 **Todo** (présent dans la roadmap MEMORY.md mais pas codé)
- **Notes pour l'IA suivante** :
  - L'API GRDF (GRDF Adict / GRDF DataConso) suit un modèle proche d'ENEDIS — OAuth2 + endpoints REST
  - Réutiliser `services/enedis_common.py` (RateLimiter, TokenManager) pour la partie commune
  - Dossier `saas/energie/GRDF/` existe (vide) — y déposer les documents API GRDF

### 3.3 Eau / SUEZ (PDF)
- **Source** : PDF à uploader sur la plateforme
- **Objectif** : Conso eau compteur par compteur, couplé à la pluviométrie
- **Statut** : 🔴 **Todo**
- **Notes** :
  - Pas d'API SUEZ standard — donc upload PDF + parser
  - Réutiliser l'architecture `EnergyInvoiceImport` (existante pour les factures) en adaptant
  - Pluviométrie : extension naturelle de `dju_sync.py` (Météo France / Open-Meteo)

## 4 · FLUIDES / FACTURATION

### 4.1 Électricité / ENGIE (API ou Excel)
- **Source** : ENGIE (Excel upload, futur API si disponible)
- **Objectif** : Vérifier les éléments de facturation
- **Statut** : 🟡 **Partiel**
- **Implémentation existante** :
  - `services/engie_client.py`, `services/invoice_parsers/engie_pdf.py`
  - Modèles : `EnergyInvoiceImport`, `EnergyInvoiceAnalysis` (migrations 0010-0012)
  - Routes : `/api/engie/*`, `/api/energie/factures/*`
  - Frontend : `EnergieInvoicesPage`, `EnergieInvoiceDetailPage`
- **Notes pour l'IA suivante** :
  - Le parser PDF ENGIE existe ; il faudrait étendre à l'Excel ENGIE si format différent
  - L'analyse audit (vérification prix BPU vs facturé) est ébauchée — à enrichir avec la table `bpu_*` créée en PR #12

### 4.2 Électricité / DALKIA (Excel)
- **Statut** : 🔴 **Todo**
- **Notes pour l'IA suivante** :
  - Créer `services/invoice_parsers/dalkia_excel.py` (proche du modèle ENGIE)
  - DALKIA est un fournisseur de chaleur urbaine + élec, donc factures souvent multi-fluides — attention au modèle de données

### 4.3 Gaz / TOTAL ENERGIE
- **Statut** : 🔴 **Todo**
- **Notes** : créer `services/invoice_parsers/total_energie.py`

### 4.4 Eau / SUEZ
- **Statut** : 🔴 **Todo**
- **Notes** : créer `services/invoice_parsers/suez.py` (probablement le même parser que 3.3)

## 🟣 BONUS — Implémentations non listées dans la grille initiale

### B.1 BPU — Historique des prix d'achat (Hérault Énergies)
- **Statut** : ✅ **Fait** (PR #12, mergée 2026-05-19)
- **Quoi** : Suivi temporel des prix unitaires de l'électricité achetée via marchés subséquents (EDF/ENGIE 2021→2026)
- **5 tables** : `bpu_documents`, `bpu_segments`, `bpu_time_periods`, `bpu_price_components`, `bpu_fixed_charges`
- **Pipeline** : pdftotext + OCR tesseract pour 17 PDFs, parser regex tolérant
- **UI** : page `/energie/bpu` avec graphique Recharts par composante (Fourniture / Capacité / CEE / GO)
- **Limite actuelle** : 15 BPU stockés, 16 en `ocr_review` (parser trop conservateur sur les tableaux complexes)
- **Voir** : [[Modules/Énergie - BPU]]

### B.2 Préconisations puissance
- **Statut** : ✅ **Fait** (page `/energie/preconisations`)
- **Quoi** : Recommandations augmenter/baisser/maintenir la puissance souscrite par PRM
- **Implémentation** : `services/power_recommendations.py`, page `EnergieRecommendationsPage`
- **Voir** : [[Modules/Énergie - Préconisations]]

### B.3 Facturation TURPE
- **Statut** : ✅ **Fait** (page `/energie/facturation`)
- **Quoi** : Configuration tarifaire par fournisseur (lot BPU, plages HPHC, prix unitaires)
- **Implémentation** : `services/billing.py`, `services/bpu_templates.py`, page `EnergieBillingPage`
- **Modèles** : `BillingConfig`, `BillingPriceEntry`, `BillingHphcSlot`, `BillingBpuLine` (avec `pu_fourniture`, `pu_capacite`, `pu_cee`, `pu_go`, `pu_total`)

## Récap synthétique

| Bloc | Total | ✅ Fait | 🟡 Partiel | 🔴 Todo |
|---|---|---|---|---|
| Patrimoine | 2 | 1 | 0 | 1 |
| Gestion technique | 4 | 0 | 2 | 2 |
| Consommation | 3 | 1 | 0 | 2 |
| Facturation | 4 | 0 | 1 | 3 |
| Bonus | 3 | 3 | 0 | 0 |
| **TOTAL grille initiale** | **13** | **2** | **3** | **8** |

**Priorité suggérée pour la prochaine session** (à valider avec l'utilisateur) :
1. **Améliorer le parser BPU** (passer à `pdfplumber` qui détecte les colonnes des tableaux) → débloquerait les 16 BPU en `ocr_review`
2. **Module Baux locataires** (1.2) → grosse valeur métier, faisable rapide avec le pattern d'upload PDF existant
3. **Connecteur GRDF** (3.2) → réutilise massivement l'architecture ENEDIS

Voir aussi : [[04 État actuel du dev]] pour le détail des derniers commits / PRs.
