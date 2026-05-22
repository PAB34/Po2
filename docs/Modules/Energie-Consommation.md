# Module — Énergie / Consommation

> Synchronisation des consommations électricité (ENEDIS), gaz (GRDF), eau (SUEZ).

## Périmètre

| Fonctionnalité roadmap | Statut |
|---|---|
| 3.1 Électricité ENEDIS API | ✅ Fait |
| 3.2 Gaz GRDF API | 🔴 Todo |
| 3.3 Eau SUEZ PDF | 🔴 Todo |

## ENEDIS — état actuel

### Deux modes coexistent

**Sync (quotidien)** — `services/enedis_sync.py` (1226 lignes)
- 3 pipelines : `run_daily_consumption_sync`, `run_max_power_sync`, `run_load_curve_sync`
- Rate limiting commun : 5 req/s, 5 concurrent, 950 req/h max (cf. `enedis_common.py::RateLimiter`)
- Token OAuth2 partagé : `enedis_common.py::TokenManager` (thread-safe, refresh auto)
- Sortie : CSVs dans `saas/energie/output/`
  - `enedis_data.csv` (conso quotidienne)
  - `enedis_max_power.csv` (P max quotidienne)
  - `enedis_load_curve.csv` (courbe de charge 10 min ou 30 min)
- Triggered par scheduler ou bouton UI dans `/energie`

**Async (backfills profonds)** — `services/enedis_async.py` (~700 lignes)
- POST `commanderPublicationPonctuelle` (1 appel pour ≤ 1000 PRM × profondeur max)
- ENEDIS publie un JSON chiffré sur le FTP du VPS (`vsftpd`, user `enedis_ftp`, chroot `/srv/ftp/enedis/upload`)
- Scheduler APScheduler poll le FTP toutes les 5 min (`core/scheduler.py::poll_and_process`)
- Pipeline : download → AES-256 decrypt → JSON parse → upsert CSV
- Profondeur max : CDC = 2 ans, ENERGIE/PMAX/IDX = 3 ans (per kit de portage ENEDIS)
- Modèle : `EnedisAsyncJob` (migration 0013)
- Routes : `/api/energie/sync/async/*`
- UI : `EnergieAsyncJobsPanel`

### Couplage DJU
- `services/dju_sync.py` : récupère les DJU depuis Open-Meteo
- Endpoint : `fetchPrmDjuPerformance`, `fetchPrmDjuSeasonal`
- Visualisation : `EnergieDetailPage` graphique conso × DJU saisonnier

### Audit PRM
- 529 PRM en BDD (Sète)
- Endpoint : `fetchDataAudit` retourne diagnostic par PRM (consumption / load_curve / max_power)
- Codes : `ok`, `non_communicant_structural`, `cdc_activation_needed`, etc.

## Dette technique ENEDIS Async — à traiter

> Source : `saas/specs/08_enedis_async_kit_analysis.json` (analyse kit portage ENEDIS vs implémentation Po2)

Gaps identifiés entre le kit officiel et notre code :

| Code gap | Sévérité | Description | État |
|---|---|---|---|
| `CDC_WINDOW_TOO_LARGE` | High | Fenêtre CDC > 7 jours rejetée par l'API | Probablement traité par `d784882` + `38ab484` — à confirmer |
| `UNFILTERED_PRM_BATCH` | Medium | On envoie tous les PRM même ceux non-communicants | Ouvert |
| `ALL_OR_NOTHING_PUBLICATION` | Medium | Une publication async échoue si **un seul** PRM est invalide → perd tout le batch | Ouvert |
| `NO_PMAX_ASYNC` | Low | Pas d'implémentation async pour P max (reste en sync) | Choix produit assumé (cf. plan ENEDIS dans `.claude/plans/`) |

**Limites plateforme ENEDIS** (à respecter pour tout nouveau call) :
- 5 req/s par application cliente
- 1000 appels/h par API (par application)
- 10 appels simultanés (tous clients confondus)
- CDC : fenêtre max 7 jours par appel, profondeur max **2 ans**
- ENERGIE / PMAX / IDX : profondeur max **3 ans**

**IP allowlist prod ENEDIS** (à whitelister côté UFW VPS) : `192.196.114.95`, `163.116.11.145`.

## GRDF — 🔴 Todo

Le connecteur GRDF doit rester le socle compteur gaz : un PCE, ses données techniques et ses consommations. Le contexte de fourniture est rattaché autour de ce PCE mais ne change pas sa provenance distributeur : `HERAULT ENERGIE / TotalEnergies` pour les compteurs Ville, `P1 DALKIA` pour les compteurs fournis dans le CPE. Le premier lien manuel passe par `BuildingMeterLink` dans la fiche bâtiment. Voir [[Modules/Energie-Gaz]].

### Notes pour l'IA suivante
- L'API GRDF s'appelle **GRDF Adict** ou **GRDF DataConso** selon l'environnement
- Architecture similaire à ENEDIS : OAuth2 client_credentials, endpoints REST
- **Réutiliser** `services/enedis_common.py` : la classe `RateLimiter` et `TokenManager` sont indépendantes du fournisseur
- Créer `services/grdf_sync.py` calqué sur `enedis_sync.py` :
  ```python
  from app.services.enedis_common import RateLimiter, TokenManager, get_oauth_token
  # Adapter les URLs, payloads, parsers JSON aux specs GRDF
  ```
- Le dossier `saas/energie/GRDF/` est prévu pour les docs source

### Critères d'acceptation
- [ ] Page `/energie` ajoute un onglet "Gaz"
- [ ] PCE (Point de Comptage Estimation) listés
- [ ] Conso quotidienne synchronisée
- [ ] Couplage DJU (probablement DJU "chauffage" car gaz souvent chauffage)

## SUEZ Eau — 🔴 Todo

### Pas d'API SUEZ standard
- Solution : upload PDF mensuel + parser
- Architecture cible : réutiliser `EnergyInvoiceImport` (table existante) en étendant `type_fluide` (elec/gaz/eau)
- Migration nécessaire pour ajouter `water_consumption_*` champs OU une table séparée `WaterConsumption`

### Couplage pluviométrie
- Météo France ou Open-Meteo (extension de `dju_sync.py`)
- Hypothèse : l'eau d'arrosage espaces verts corrèle avec déficit pluviométrique

## Routes API actuelles

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/energie` | Overview (KPI + supplier distribution) |
| GET | `/api/energie/audit` | Audit PRM par PRM |
| GET | `/api/energie/ranges` | Bornes temporelles des données |
| GET | `/api/energie/{prm_id}` | Détail d'un PRM |
| GET | `/api/energie/{prm_id}/conso` | Conso quotidienne |
| GET | `/api/energie/{prm_id}/pmax` | P max quotidienne |
| GET | `/api/energie/{prm_id}/cdc` | Courbe de charge |
| GET | `/api/energie/{prm_id}/dju` | Performance × DJU |
| POST | `/api/energie/sync/customer` | Sync référentiel contractuel |
| POST | `/api/energie/sync/conso` | Sync conso (sync mode) |
| POST | `/api/energie/sync/pmax` | Sync P max |
| POST | `/api/energie/sync/cdc` | Sync CDC |
| POST | `/api/energie/sync/async/start` | Lancer un backfill async |
| POST | `/api/energie/sync/async/backfill-full` | Backfill complet (CDC 2 ans + Conso 3 ans) |
| GET | `/api/energie/sync/async/jobs` | Liste des jobs async |
| POST | `/api/energie/sync/async/poll-now` | Poll FTP immédiat |
