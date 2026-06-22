# 2026-06-22 - Factures gaz TotalEnergies (contrôle v1)

> IA : Claude (Opus 4.8)
> Branche : `feat/gas-invoices`

## Demande

Implémenter le contrôle des factures gaz TotalEnergies (fichier
`saas/energie/TOTAL ENERGY/FACTURES.xlsx`) à l'image d'ENGIE/EDF. D'abord parser
le fichier pour maîtriser les données, puis proposer et implémenter l'intégration.

## Parsing — données maîtrisées

Fichier = 1 feuille, **58 factures × 68 colonnes**, 1 ligne = 1 facture, Commune de Sète.
- 53 FACTURE + 5 AVOIR (TTC négatif), **10 PCE / 10 sites**, janv–fév 2026, tarif T2, classes B0/B1/B2I.
- Cohérence parfaite : `PRIX CONSO × kWh = MONTANT CONSO` (écart < 0,01 €), `Σ 12 composantes = TOTAL HORS TVA`,
  `HT + TVA = TTC`, `m³ × coeff = kWh`. Portefeuille : 22 717 € HT / 27 261 € TTC / 257 418 kWh.

## Arbitrages utilisateur

- Architecture = **module gaz dédié** (le gaz n'entre pas dans le modèle élec PRM/segments).
- Périmètre v1 = **contrôle structure** (cohérence/TVA/conversion) ; v2 = contrôle prix.

## Livré (v1)

Backend :
- `GasInvoice` (table `gas_invoices`, migration `0057`) ;
- `services/gas_invoice.py` : parser xlsx (mapping 68 colonnes, décimales FR, dates, avoirs),
  moteur de contrôle de cohérence (prix×kWh, Σ=HT, HT+TVA=TTC, conversion m³→kWh, TVA 20/5,5 %),
  import (upsert + force_update), portefeuille, décision, recompute ;
- l'import **alimente `gas_pces`** -> la boîte de rapprochement (PO2-PAT-003) rattache les PCE aux bâtiments ;
- endpoints `/api/gas/invoices/*`.

Frontend :
- section TotalEnergies (gaz) dans **Factures marché › Hérault Énergie › TotalEnergies** (remplace le placeholder) :
  import xlsx, cartes portefeuille, tableau par site/PCE (rattaché ?), table factures avec contrôle + décision.

## Validation (staging, copie réelle de la prod)

- `compileall` + parsing/contrôle du vrai fichier en local : 58 lignes, toutes cohérentes (0 anomalie).
- Build front OK, migration 0057 appliquée.
- Import réel sur staging : 58 factures, HT 22 717 € / TTC 27 261 € / 257 418 kWh, **10 gas_pces créés**.
- Boîte de rapprochement : 10 PCE collectés, 8 avec candidat (ex. École des Beaux Arts -> bâtiment, score 100).
- HTTP + auth OK (401 sans token).

## v2 livré — contrôle prix fourniture (2026-06-22)

Source de vérité confirmée par l'utilisateur : `extraction_tarifs_BPU_herault.xlsx`
(extraction canonique élec + gaz). Section Lot 7 / TOTALENERGIES / 2026 = fourniture 35,23 ·
CEE 3,89 · CEE précarité 3,06 · CPB 0,41 · GO 16,25 (€ HT/MWh) — identique au seed.

- Table éditable `gas_bpu_prices` (migration `0058`, seed BPU lot 7 2026 T1-T4), endpoints
  `GET/PATCH /api/gas/invoices/bpu`.
- Moteur étendu : contrôle prix fourniture vs BPU (+ CPB), basé sur l'**année de facturation**
  (date comptable) avec repli sur le BPU le plus récent. Les PCE à prix révisable PEG sont
  signalés « à contrôler » (pas une erreur).
- Frontend : la référence BPU s'affiche dans la section TotalEnergies ; les écarts prix
  remontent dans la colonne contrôle.
- Validé staging contre le vrai fichier : **49 conformes / 9 à prix révisable** (56,88 ≠ 35,23).

## v3 (partie 1) livré — export fiche liaison finance (2026-06-22)

- `GET /api/gas/invoices/export` génère un XLSX (feuille Factures détaillée + Synthèse par site
  avec TOTAL) et horodate la transmission (`finance_exported_at`). Bouton dans la section TotalEnergies.
- Validé staging : XLSX 2 feuilles, 58 factures, total 22 717 € HT / 257 418 kWh.

## v3 (partie 2) livré — contrôle cohérence acheminement (2026-06-22)

Pas de barème ATRD/ATRT GRDF dans le repo (dossier GRDF = API ADICT only) → contrôle de
cohérence sans donnée externe : le taux ATRD variable (€/MWh) doit être stable par tarif.
Sur le vrai fichier : taux T2 = **12,08 €/MWh** (dispersion 12,06–12,10, σ=0,01) → référence
= médiane par tarif, écart > 1 €/MWh signalé. Aucun faux positif sur le lot actuel ; prêt à
détecter les anomalies futures. Implémenté dans `compute_control` (achem_ref calculé sur tout le lot).

## v3 (partie 3) — référentiel ATRD/ATRT en miroir de TURPE (2026-06-22)

Constat utilisateur : ATRD/ATRT = le « TURPE du gaz » (tarif réseau réglementé CRE,
passthrough). Mise en place d'un référentiel éditable `gas_network_tariffs`
(migration `0059`) sur le modèle du module TURPE / du BPU gaz : par année et option
(T1-T4), terme variable ATRD (€/MWh) + abonnement annuel, daté et sourcé CRE.

- Contrôle acheminement passé de « cohérence (médiane observée) » à **référence absolue**
  quand le barème est renseigné (capte une dérive uniforme qu'une médiane ne verrait pas),
  avec repli cohérence sinon.
- Seed : terme variable ATRD T2 2026 = 12,08 €/MWh (dérivé des factures, **à confirmer
  barème CRE ATRD**). T1/T3/T4 et termes fixes à compléter via `PATCH /api/gas/invoices/network-tariff`.
- Endpoints `GET/PATCH /api/gas/invoices/network-tariff` ; barème affiché dans la section TotalEnergies.

Note : les termes fixes ATRD/ATRT dépendent de la capacité du PCE (variables d'un PCE à
l'autre) → restent en cohérence ; seul le terme variable est référencé par option.

## v3 (partie 4) — barème CRE ATRD 7 complet (2026-06-22)

Grille ATRD 7 GRDF au 1er juillet 2025 (valable jusqu'au 30/06/2026) récupérée et seedée
(migration `0060`), recoupée contre les factures (T2 = 12,08 €/MWh confirmé) :

| Option | Abonnement €/an | Terme variable €/MWh |
|---|---|---|
| T1 | 54,72 | 44,94 |
| T2 | 186,12 | 12,08 |
| T3 | 1 301,40 | 8,69 |
| T4 | 21 705,72 | 1,18 |

Source : CRE délibération 2025-122. Contrôle terme variable ATRD désormais absolu sur T1-T4.
Abonnement annuel stocké (186,12/12 = 15,51 €/mois = terme fixe ATRD facturé sur mois plein).

## v3 (partie 5) — contrôle terme fixe ATRD proraté (2026-06-22)

Règle de prorata GRDF identifiée sur les factures : terme fixe ATRD = abonnement/12 par
mois plein, proraté par jours sur les mois partiels (ex. 15,51 × 18/28 = 9,97 pour 18 j de
février ; 186,12/12 = 15,51 sur mois plein). Implémenté `_prorated_atrd_fixe` + contrôle
absolu vs abonnement CRE (tolérance 0,20 €). Aucun faux positif sur le lot réel.
Contrôle acheminement ATRD désormais complet : terme variable + terme fixe.

## v3 (partie 6) — contrôle taxes (accise/TICGN daté + CTA) (2026-06-22)

- Accise gaz (ex-TICGN) modélisée **par date d'effet** (table `gas_tax_rates`, migration `0061`) :
  15,43 €/MWh au 1er août 2025 → 16,39 €/MWh au 1er février 2026 (confirmé contre factures +
  sources publiques). Contrôle = montant TICGN / kWh vs taux de la période de conso (tol 0,25).
- CTA = 24,76 % du terme fixe ATRD (observé stable) → contrôle CTA = coeff × ATRD fixe (tol 0,20).
- Endpoints `GET/PATCH /api/gas/invoices/tax-rates`. Aucun faux positif sur le lot réel.

Couverture contrôle gaz : cohérence + fourniture (BPU) + acheminement ATRD (variable+fixe) + taxes.

## v3 (partie 7) — révisable PEG référencé ; ATRT/CEE = données externes (2026-06-22)

Analyse des 3 derniers points :
- **Fourniture révisable PEG** : les 9 factures sont toutes à 56,88 €/MWh (conso déc. 2025).
  Table éditable `gas_supply_revisable_prices` (migration `0062`, par mois), endpoints
  `GET / PUT /api/gas/invoices/revisable`. Les 9 factures deviennent **conformes** (58/58 valides).
  Les mois suivants se renseignent au fil de l'eau (valeur = indice PEGAS, donnée marché).
- **ATRT (transport)** : `ATRT fixe / CAR` ≈ 0,671 €/MWh-CAR mais varie par PCE/zone → un contrôle
  de cohérence par médiane génère des **faux positifs** (testé). Non retenu : contrôle absolu
  nécessite le barème transport GRDF (flux externe).
- **CEE classique** : prix de marché variable par période (déc. 2025 ≈ 2,9 ; 2026 ≈ 8,1) →
  cohérence = faux positifs. Non retenu : nécessite les CEE définitifs fournisseur (révisés mars).

Conclusion : le contrôle gaz est complet sur tout ce qui est réglementé/contractuel
(fourniture ferme + révisable, acheminement ATRD variable+fixe, accise, CTA, TVA, cohérence).
ATRT et CEE restent volontairement non contrôlés faute de donnée de référence externe.

## Bilan — contrôle gaz TotalEnergies bouclé

Nécessite de charger les **barèmes de référence** :
1. **BPU gaz lot 7 TotalEnergies** (prix conso par classe + abonnement) -> contrôle `PRIX CONSO GAZ`.
2. **Barème ATRD/ATRT GRDF** (terme fixe/variable par tarif T) -> contrôle acheminement.
3. **Taux TICGN/accise** (€/MWh) + CTA -> contrôle taxes.
Puis : export fiche liaison finance (comme ENGIE/DALKIA) et suivi mensuel conso facturée vs relevés GRDF.
