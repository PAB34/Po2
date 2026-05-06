# Preconisation abonnement - V1 prudente

Date : 2026-05-06

## Objectif

Transformer l'indicateur `Calibrage` en aide a la decision sans surpromesse financiere.

La V1 produit :

- une puissance cible ;
- trois scenarios : prudent, equilibre, agressif ;
- un niveau de confiance ;
- une justification lisible ;
- une priorisation portefeuille.

Elle produit maintenant un ordre de grandeur annuel quand la part fixe TURPE est calculable.

## Garde-fou budgetaire

L'economie en euros reste limitee a la part fixe TURPE tant que le calcul complet des composantes
d'acheminement, des depassements et des taxes n'est pas audite.

Sources TURPE chargees ou a maintenir :

- decisions CRE TURPE 7 HTA-BT ;
- documents/baremes Enedis en vigueur ;
- composantes observees sur factures controlees.

## Regle technique V1

Donnees utilisees :

- puissance souscrite actuelle ;
- historique de puissance maximale ENEDIS ;
- pic maximal observe ;
- profondeur de l'historique ;
- segment et tarif de distribution.

Scenarios :

| Scenario | Marge appliquee au pic observe |
| --- | ---: |
| prudent | 20 % |
| equilibre | 12 % |
| agressif | 5 % |

La puissance cible est arrondie au kVA superieur.

## Statuts d'action

| Action | Signification |
| --- | --- |
| `increase` | Hausse conseillee : risque de depassement ou sous-dimensionnement. |
| `decrease` | Baisse possible : puissance actuelle nettement superieure au pic observe. |
| `maintain` | Maintien : marge acceptable. |
| `insufficient_data` | Donnees insuffisantes pour recommander. |

## Niveau de confiance

| Confiance | Condition indicative |
| --- | --- |
| `high` | au moins 10 mois et 240 jours de puissance max exploitable |
| `medium` | au moins 3 mois et 60 jours |
| `low` | historique present mais trop court |
| `insufficient` | puissance souscrite ou historique absent |

## Limites V1

- chiffrage economique limite a la part fixe TURPE pour les tarifs BT <= 36 kVA reconnus ;
- pas de cout de modification ;
- pas de distinction eclairage public a 0,1 kVA ;
- pas encore de prise en compte fine des depassements par poste horosaisonnier.

## Evolution V2

Migrer le referentiel code vers une table administrable `turpe_tariff_terms` avec :

- periode de validite ;
- domaine de tension ;
- formule tarifaire d'acheminement ;
- composante de gestion ;
- composante de comptage ;
- composante de soutirage ;
- depassements ;
- coefficients horosaisonniers.

Le chiffrage annuel pourra alors afficher :

- cout actuel estime ;
- cout cible estime ;
- economie potentielle ;
- risque de depassement ;
- hypotheses utilisees.
