# Module — Énergie / TURPE 7

> Référentiel des tarifs d'utilisation du réseau public d'électricité, utilisé par les modules **Facturation** (contrôle des composantes acheminement) et **Préconisations** (chiffrage des modifications de puissance).
>
> Source canonique : `saas/specs/07_referentiel_turpe_7.md`

## Cadre réglementaire

| Sigle | Source | Validité |
|---|---|---|
| **TURPE 7 HTA-BT** | CRE 2025-78 | 2025-08-01 → 2026-07-31 |
| Avenant | CRE 2026-33 | 2026-08-01 → ... |

Cycle de mise à jour : **2026-08-01** prochaine décision CRE → spec à refresher.

## Composantes TURPE 7 (mapping libellés facture)

| Code interne | Libellé facture | Description |
|---|---|---|
| `network_management` | "Gestion réseau" | Gestion du réseau (forfait annuel par segment tarifaire) |
| `counting` | "Comptage" | Comptage (forfait annuel) |
| `withdrawal` | "Soutirage / Puissance souscrite" | Composante puissance souscrite (€/kVA/an) |
| `variable` | "Acheminement variable" | Part variable (€/kWh, dépend du poste horosaisonnier) |

## Couverture tarifaire validée

CU4, MU4, LU, CUd, MUDTd, C4, HTA.

Pour chaque code tarif × poste, le référentiel TURPE 7 fournit le prix unitaire de la composante `variable` (€/MWh) et les forfaits `network_management` / `counting`.

## Usage dans le code

| Service | Rôle |
|---|---|
| `services/turpe.py` | Lookup composantes TURPE pour un (tariff_code, poste, year) |
| `services/invoice_analysis.py` | Contrôle des composantes TURPE facturées vs référentiel — codes d'erreur `TURPE_VERSION_MISSING`, `TURPE_AMOUNT_MISMATCH` |
| `services/power_recommendations.py` | Chiffrage prudent d'une modification de puissance : `delta_eur = delta_kVA × coef_TURPE_kVA_an` |

## Garde-fous appliqués

- **Tolérance** : ± 0,05 EUR/MWh sur la composante variable, ± 0,05 EUR sur les forfaits (cohérent avec [[Modules/Énergie - Facturation]])
- **Version inconnue** : si la période facturée ne couvre pas une version TURPE référencée → flag `TURPE_VERSION_MISSING` → décision `review`
- **Préconisation prudente** : la projection annuelle d'une économie/surcoût utilise les coefficients fixes TURPE (pas les prix BPU variables) pour éviter de sur-promettre

## Liens

- Cadre Hérault Énergies (refacturation acheminement à l'euro hors C1) : [[Modules/Énergie - Facturation]]
- Préconisations puissance (marges 20/12/5 %) : [[Modules/Énergie - Préconisations]]
- Spec source : `saas/specs/07_referentiel_turpe_7.md`
