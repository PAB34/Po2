# 2026-06-09 — Analyse et scaffolding API GRDF ADICT

> IA : Claude Opus 4.8
> Durée approximative : 1h
> Précédente session : `[[Sessions/2026-06-08 — CVC cockpit fluides F-Gaz ESP]]`

## 🎯 Objectif de la session

Préparer la visio GRDF (déploiement API ADICT) : analyse complète pour rendre l'API
opérationnelle sur Po2 — collecte conso gaz + rapprochement factures P1 GAZ DALKIA + suivi
temporel des bâtiments. Tâche rattachée à `PO2-GRDF-001` et au cadre gaz posé le 2026-05-22.

## ✅ Ce qui a été fait

### Chantier — Analyse opérationnelle GRDF

- Vérifié le swagger v1.9 (`saas/energie/GRDF/.../swagger_fusionné B2B_PROD_v1.9.json`) :
  les 9 endpoints sont **conformes** à `[[Modules/GRDF-API]]`.
- Découverte clé : `modele-donnees.xlsx` = **fichier de déclaration de droits en masse rempli**
  (~50 PCE Commune de Sète, consentement 01/05/2026→2029, accès depuis 01/01/2024). Donc on est
  en phase d'**implémentation**, pas de découverte. Le chemin de consentement = déclaration en
  masse (`PUT droit_acces`), pas Client Connect web.
- Points sensibles relevés : PCE de formats mixtes (14 chiffres / `GI+6`) ; email de validation
  consentement = adresse `@dalkia` (mandataire vs titulaire mairie à clarifier).
- Checklist de 11 questions GRDF pour la visio → consignée dans `[[Modules/GRDF-API]]` §13.

### Chantier — Scaffolding Phases 0-1

- `app/core/config.py` : bloc `grdf_*` (auth url SOFIT, base url `/adict/v2`, scope, quotas
  rps/concurrent/hourly, sync 24h, history 1825j).
- `app/services/grdf_auth.py` : `GrdfTokenManager` (cache token API ~4h) + réutilisation du
  `RateLimiter` de `enedis_common` (zéro duplication de la mécanique éprouvée ENEDIS).
- `app/models/gas.py` : `GasPce` (PCE + droit d'accès + données contractuelles/techniques en
  cache) et `GasConsumption` (relevés publiées/informatives, energie kWh principale). Enregistrés
  dans `app/models/__init__.py`.
- `alembic/versions/0049_add_gas_pce_consumption.py` (down_revision `0048`).
- Fichiers principaux touchés : `app/core/config.py`, `app/services/grdf_auth.py`,
  `app/models/gas.py`, `app/models/__init__.py`, `alembic/versions/0049_*.py`,
  `docs/Modules/GRDF-API.md`.

## 🛠️ Validation

- `python -m compileall` OK sur les 4 fichiers backend.
- Import modèles + settings + auth OK via `DATABASE_URL=sqlite:///:memory:` (GasPce 26 colonnes,
  TokenManager/RateLimiter instanciables).
- `alembic upgrade head` non exécuté localement (à passer en CI/prod). Frontend non concerné à ce stade.

## 🚧 Ce qui reste à faire / handoff

### ⚡ Tournant — droits déjà ACTIVE (export réel reçu en cours de session)
- L'utilisateur a fourni `liste_droit_d_acces_GRDF (1).xlsx` : **66 PCE tous `Active`**
  (49 AUTORISE périmètres complets + 17 DETENTEUR). La collecte conso est donc **débloquée**,
  pas besoin de déclarer les consentements.
- **Livré** : `app/scripts/import_grdf_droits.py` (upsert `gas_pces`, `--dry-run`, idempotent).
  Validé sur fichier réel : 66 créés, 2e run 0/0/66.
- Pièges traités : matcher d'en-tête en mode ET (sinon « accès » matchait « Etat du droit
  d'accès ») ; glyphes ASCII (console Windows cp1252).

### Phase 3-4 — ✅ FAITE (collecte conso)
- `grdf_client.py` (HTTP token+rate-limit+retries+ndjson), `grdf_gda.py` (`list_droits`/
  `sync_droits` API source de vérité/`revoke_droit`), `grdf_conso.py` (backfill 5 ans + sync
  incrémentale + upsert idempotent + état /status), `grdf_contractuel.py` (enrichissement),
  job `_grdf_conso_sync_job` (24h) dans `core/scheduler.py`, routes `api/routes/grdf.py` (6).
- Validé : compileall, app boot + 6 routes, backfill E2E (upsert + idempotence) SQLite.

### Phase 5 — ✅ FAITE (rapprochement P1 + suivi temporel)
- `services/gas_analytics.py` : `monthly_series()` (suivi mensuel kWh/MWh PCS par PCE/bâtiment)
  et `reconcile_p1()` (conso GRDF vs `cpe_dalkia_ref_p1_gaz.qt_mwhpcs`, écart, statut ok/ecart/blocked).
- Routes `GET /api/grdf/conso/monthly` et `GET /api/grdf/rapprochement-p1/{year}`.
- **Unités tranchées** : GRDF kWh PCS ↔ P1 MWh PCS comparables direct (÷1000) ; coeff PCI (1,1068)
  seulement pour cible NB. Config `grdf_pcs_to_pci`, `grdf_ecart_tolerance_pct` (5%).
- Validé E2E SQLite : 120 vs 110 MWh → +9,09% statut `ecart` ; serialization dataclass→Pydantic OK.

### Frontend — ✅ FAIT (page `/energie/gaz`)
- `pages/EnergieGazPage.tsx` (KPI + actions sync + rapprochement P1 + suivi mensuel),
  types/fonctions `lib/api.ts`, route App.tsx (avant `/energie/:prmId`), lien sidebar « Gaz GRDF ».
- Non buildé localement (npm/node absents) → **validation CI**. Conformité vérifiée main :
  RQ v5 (`isPending`, `refetchInterval` fonction), classes CSS existantes, génériques explicites.

### Reste (post-visio / 1er appel live)
- Valider forme réelle réponses conso/droits (credentials PROD) ; question DÉTENTEUR.
- Optionnel : lier `gas_pces.building_id` au patrimoine pour le filtre par bâtiment.

### Côté visio / 1er appel réel
- Q DÉTENTEUR : périmètres vides → conso/contract/tech lisibles ? (sinon seuls 49 AUTORISE).
- Vérifier forme réelle des réponses conso (objet vs liste) et champs `GET /droits_acces` :
  parseurs tolérants mais non validés contre l'API live (credentials PROD requis).

### Priorité 2 — Phases 3-4 : collecte + sync
- `grdf_conso.py` (publiées/informatives) + backfill 2024-01-01→aujourd'hui (n'insérer que
  `statut_conso = "Définitive"`) ; `grdf_contractuel.py` (CAR/tarif/profil/technique).
- Job `_grdf_conso_sync_job` dans `core/scheduler.py` (interval 24h, no-op si credentials vides).

### Priorité 3 — Phase 5 : rapprochement métier (la valeur)
- Conso GRDF ↔ factures **P1 GAZ DALKIA** (`gas_pces.id_pce` ↔ `cpe_dalkia_ref_p1_gaz.pce`).
- Suivi temporel par bâtiment via `BuildingMeterLink`. Conversion kWh↔MWh PCI à tracer.

### Côté utilisateur — Pending validations externes
- Visio GRDF : poser les 11 questions §13 de `[[Modules/GRDF-API]]` (surtout consentement Q3-Q6).
- Récupérer/confirmer `GRDF_CLIENT_ID` + `GRDF_CLIENT_SECRET` actifs en PROD → `.env` prod
  **sans jamais les committer** (cf. `[[Decisions/006-secrets-jamais-en-chat-IA]]`).
