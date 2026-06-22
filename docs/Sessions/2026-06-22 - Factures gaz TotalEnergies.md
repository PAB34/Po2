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

## Reste à faire — v2 (contrôle prix)

Nécessite de charger les **barèmes de référence** :
1. **BPU gaz lot 7 TotalEnergies** (prix conso par classe + abonnement) -> contrôle `PRIX CONSO GAZ`.
2. **Barème ATRD/ATRT GRDF** (terme fixe/variable par tarif T) -> contrôle acheminement.
3. **Taux TICGN/accise** (€/MWh) + CTA -> contrôle taxes.
Puis : export fiche liaison finance (comme ENGIE/DALKIA) et suivi mensuel conso facturée vs relevés GRDF.
