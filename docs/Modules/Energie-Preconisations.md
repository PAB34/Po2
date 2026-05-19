# Module — Énergie / Préconisations

> Recommandations sur la puissance souscrite par PRM + audit calibrage contrat.

## Statut

✅ **En prod** (page `/energie/preconisations`).

## Logique métier

### Recommandations puissance
`services/power_recommendations.py` :

Pour chaque PRM :
1. Récupère P max historique (12 derniers mois) via `enedis_max_power.csv`
2. Récupère puissance souscrite (depuis `enedis_contracts.csv` ou config user)
3. Calcule statistiques : P_max_p99, P_max_p95, taux de dépassement
4. Recommande :
   - **`increase`** si dépassements fréquents (> seuil) → augmenter la puissance souscrite pour éviter pénalités
   - **`decrease`** si P max stable bien en dessous → réduire puissance souscrite pour économiser l'abonnement
   - **`maintain`** si calibrage cohérent
   - **`insufficient_data`** si historique trop court ou trop de trous
5. Score de confiance : `high`/`medium`/`low`
6. Score de priorité (utilisé pour le tri) basé sur l'économie potentielle

### Seuils V1 (canoniques)

> Source : `saas/specs/06_preconisation_abonnement_v1.md`

| Marge | Action | Sens |
|---|---|---|
| **20 %** | `increase` | Sécurité : recommande +X kVA dès que P max p99 dépasse `subscribed × 0.80` (= 80 % de la souscription) |
| **12 %** | `decrease` | Prudent : ne recommande de baisser que si P max p99 < `subscribed × 0.88` |
| **5 %** | `maintain` | Tolérance : entre 0.88 × subscribed et le `decrease` |

**Conditions pour confidence = `high`** :
- ≥ **10 mois** de données P max consécutifs disponibles
- ≥ **240 jours** réellement utilisés dans le calcul (filtre des trous et jours non-significatifs)

**Garde-fou TURPE** : la projection annuelle utilise les coefficients fixes du référentiel ([[Modules/Energie-TURPE]]) pour éviter de sur-promettre une économie.

### Sortie
`get_power_recommendations()` retourne :
- KPI agrégés (`total`, `increase`, `decrease`, `maintain`, `insufficient_data`, `high_confidence`, etc.)
- Liste de `recommendations` triée par `priority_score` décroissant

### Détail par PRM
`get_prm_power_recommendation(prm_id)` :
- `action`, `confidence`, `recommended_kva`, `subscribed_kva`
- `data_quality.status` (ok/partial/insufficient)
- Statistiques détaillées : `p_max_actuelle`, `p_max_p99`, `mois_depassement`, etc.

## Calibrage contrat

`services/turpe.py` + `services/billing.py` :
- Configuration tarifaire par fournisseur (`BillingConfig`)
- Plages HPHC (`BillingHphcSlot`)
- Prix unitaires par composante × année (`BillingPriceEntry`, `BillingBpuLine`)

L'UI `/energie/facturation` permet :
- Sélectionner un fournisseur dans la liste détectée (auto-pop depuis `enedis_contracts.csv`)
- Définir le lot BPU (lot1, lot2, ...)
- Saisir/modifier les prix
- Précharger depuis template `bpu_templates.py` (données 2026 hard-codées pour lot1/lot2)

## API

| Route | Description |
|---|---|
| `GET /api/energie/preconisations` | Liste complète + KPIs |
| `GET /api/energie/preconisations/{prm_id}` | Détail PRM (recommandation + calibrage contrat) |

## Frontend

- **Page** : `/energie/preconisations` → `EnergieRecommendationsPage`
- Affichage tableau + filtres par action / par confiance
- Drill-down sur un PRM → `EnergieDetailPage` avec graphiques P max × période contractuelle

## Couplage avec [[Modules/Energie-BPU]]

Les prix unitaires utilisés pour estimer le coût d'une modification de contrat viennent de `BillingBpuLine` (saisis via `/energie/facturation`).

À terme, ces prix viendront automatiquement du nouveau module `bpu_*` (table normalisée alimentée par les PDFs), via une jointure :
- `BillingConfig.supplier`, `.year`, `.lot` → résolution `BpuDocument`
- `BillingConfig.tariff_code` → résolution `BpuSegment`
- Pour chaque poste → moyenne pondérée des composantes

Voir [[Modules/Energie-BPU]] section "Croisement avec factures" pour le pattern.

## Fichiers clés

- `saas/backend/app/services/power_recommendations.py`
- `saas/backend/app/services/turpe.py`
- `saas/backend/app/services/billing.py`
- `saas/backend/app/services/bpu_templates.py` (prix 2026 hard-codés lot1/lot2)
- `saas/frontend/src/pages/EnergieRecommendationsPage.tsx`
- `saas/frontend/src/pages/EnergieBillingPage.tsx`
