# Referentiel TURPE 7 - controle facture et impact abonnement

Date : 2026-05-06

## Objectif

Ajouter un referentiel TURPE exploitable par le module Energie pour :

- selectionner automatiquement le bareme applicable selon la periode de facture ;
- recalculer les composantes principales d'acheminement ;
- comparer les lignes ENGIE facturees avec le montant attendu ;
- chiffrer prudemment l'impact annuel d'une modification de puissance sur la part fixe TURPE.

## Source chargee en V1

Source tarifaire :

- Enedis, brochure tarifaire TURPE 7 HTA/BT, tarifs en vigueur au 1er aout 2025 ;
- decision CRE TURPE 7 HTA-BT n 2025-78 du 13 mars 2025 ;
- modification CRE n 2026-33 du 4 fevrier 2026, sans changement des coefficients de facture generiques utilises ici.

Periode chargee :

| Code | Validite |
| --- | --- |
| `TURPE_7_HTA_BT_2025_08` | 2025-08-01 au 2026-07-31 |

La prochaine mise a jour attendue est le 2026-08-01. Si une facture depasse la periode chargee,
le controle passe en alerte `TURPE_VERSION_MISSING` au lieu de produire un faux calcul.

## Composantes controlees

Le moteur controle les composantes principales presentes dans les factures ENGIE :

- `network_management` : composante annuelle de gestion, proratee au nombre de jours ;
- `network_counting` : composante annuelle de comptage, proratee au nombre de jours ;
- `network_withdrawal` : part fixe de soutirage, proratee au nombre de jours ;
- `network_variable` : part variable de soutirage, controlee au prix unitaire EUR/kWh et au montant.

Tolerance :

- ligne TURPE : 0,05 EUR HT ;
- total acheminement PRM/FIC : 0,10 EUR HT ;
- prix unitaire : 0,00005 EUR/kWh.

## Couverture tarifaire

Le referentiel contient les coefficients generiques HTA-BT suivants :

- BT <= 36 kVA : CU4, MU4, LU, CU derogatoire, MUDT derogatoire ;
- BT > 36 kVA : CU, LU ;
- HTA : CU/LU avec pointe fixe ou pointe mobile.

La V1 calcule automatiquement la part fixe multi-postes BT > 36 kVA et HTA uniquement si la facture
contient le detail des puissances souscrites par poste. A defaut, le controle reste partiel.

## Effet sur la preconisation abonnement

Quand le PRM est en BT <= 36 kVA et que la formule d'acheminement est reconnue, la preconisation
affiche maintenant un ordre de grandeur annuel limite a :

`delta kVA x coefficient fixe TURPE`

Ce montant n'inclut pas la fourniture, les taxes, les depassements, ni un changement de repartition
horosaisonniere. Il doit rester presente comme un ordre de grandeur prudent.
