# Matrice de controles - Factures energie

Date : 2026-05-06

## 1. Statuts de decision

Le controle facture ne doit pas etre binaire trop tot. La V1 retient trois statuts :

- `valid` : aucune erreur bloquante et aucune alerte ;
- `review` : aucune erreur bloquante, mais au moins une alerte metier ;
- `invalid` : au moins une erreur bloquante.

Le statut d'analyse technique reste separe :

- `pending` : fichier importe mais pas encore analyse ;
- `parsed` : analyse terminee sans alerte de parsing ;
- `partial` : analyse terminee avec alerte de parsing ;
- `failed` : analyse impossible.

## 2. Controles bloquants

Une facture est invalide si l'un des controles suivants echoue :

| Code | Controle | Raison |
| --- | --- | --- |
| `SUPPLIER_UNKNOWN` | Fournisseur non reconnu | On ne sait pas appliquer le bon parseur ni le bon BPU. |
| `MISSING_INVOICE_NUMBER` | Numero facture absent | Impossible d'identifier la piece. |
| `MISSING_INVOICE_DATE` | Date facture absente | Impossible de rattacher la facture a une periode. |
| `MISSING_TOTAL_TTC` | Total TTC absent | Impossible de valider le montant opposable. |
| `MISSING_REGROUPEMENT` | Regroupement absent | Impossible de rattacher la facture au perimetre de batiments. |
| `MISSING_MARKET_REFERENCE` | Reference marche absente | Impossible de verifier le cadre contractuel. |
| `MARKET_REFERENCE_MISMATCH` | Reference marche differente de `2024-FCS-03` | Facture potentiellement hors marche. |
| `DUPLICATE_INVOICE_NUMBER` | Numero facture deja importe | Risque de double validation. |
| `NO_SITE_FOUND` | Aucun PRM/FIC detecte | Facture non exploitable. |
| `MISSING_PRM` | PRM absent sur une FIC | Impossible de rattacher la consommation. |
| `UNKNOWN_PRM` | PRM inconnu dans le module Energie | Facture hors perimetre connu ou donnees ENEDIS manquantes. |
| `TOTAL_TTC_MISMATCH` | Somme des FIC incoherente avec le total facture | Ecart arithmetique au-dela de la tolerance. |
| `LINE_AMOUNT_MISMATCH` | Quantite x prix unitaire incoherent | Ligne facturee arithmetiquement fausse. |
| `BPU_PRICE_MISMATCH` | Prix facture different du BPU | Ecart contractuel sur fourniture, capacite, CEE ou GO. |
| `PARSER_FAILED` | Analyse impossible | Le fichier ne peut pas etre controle. |

Tolerance V1 :

- ecart montant : `0,05 EUR` ;
- ecart prix BPU : `0,05 EUR/MWh`.

## 3. Alertes non bloquantes

Une facture passe en `review` si elle ne contient pas d'erreur bloquante mais qu'un controle reste incomplet.

| Code | Controle | Effet |
| --- | --- | --- |
| `MISSING_CHORUS_DATA` | Donnees Chorus incompletes | A verifier avant validation Chorus/refus. |
| `SUPPLIER_CONTRACT_MISMATCH` | Fournisseur ENEDIS different du fournisseur facture | Possible changement de contrat ou erreur de perimetre. |
| `BPU_CONFIG_MISSING` | Configuration BPU fournisseur absente | Facture lisible mais non controlable contractuellement. |
| `BPU_LINES_MISSING` | Configuration fournisseur presente sans lignes BPU | Parametrage incomplet. |
| `BPU_REFERENCE_MISSING` | Poste/tarif absent du BPU | Controle prix incomplet. |
| `BPU_PRICE_MISSING` | Prix BPU non renseigne | Controle prix incomplet. |
| `TURPE_VERSION_MISSING` | Bareme TURPE absent pour la periode | Controle acheminement incomplet. |
| `TURPE_TARIFF_UNKNOWN` | Formule d'acheminement non reconnue | Controle acheminement incomplet. |
| `TURPE_TARIFF_UNSUPPORTED` | Tarif hors referentiel charge | Controle acheminement incomplet. |
| `TURPE_COMPONENT_UNSUPPORTED` | Composante TURPE non traitee | Controle acheminement incomplet. |
| `TURPE_PERIOD_MISSING` | Periode de ligne absente | Controle acheminement incomplet. |
| `TURPE_PERIOD_CROSSES_VERSION` | Ligne a cheval sur deux baremes | Controle acheminement incomplet. |

## 4. Controles ENGIE V1 implementes

La premiere implementation porte sur les PDF ENGIE `Facture Unique Multi-Site electricite`.

Donnees extraites :

- fournisseur ;
- numero facture ;
- date facture ;
- date de prelevement ;
- reference client globale ;
- titulaire ;
- SIRET ;
- reference marche ;
- regroupement ;
- donnees Chorus ;
- total TTC ;
- consommation totale ;
- PRM/FIC ;
- site ;
- adresse ;
- segment ;
- option tarifaire ;
- puissance souscrite ;
- puissance atteinte ;
- lignes de facture ;
- index/releves.

Controles actifs :

- identification documentaire ;
- reference marche ;
- regroupement ;
- doublon par numero facture ;
- PRM connu ;
- fournisseur ENEDIS coherent ;
- somme TTC FIC vs total facture ;
- coherence quantite x prix unitaire ;
- comparaison BPU sur fourniture, capacite, CEE et electricite verte.
- recalcul TURPE 7 HTA-BT pour gestion, comptage, soutirage fixe et soutirage variable lorsque la grille applicable est chargee.

Precision BPU :

- la grille contractuelle est lue comme le couple `Tension d'alimentation` + `Poste horosaisonnier TURPE` du fichier BPU Herault Energie 2026 ;
- les factures C5 en `BT <= 36 kVA SDT CU4 / MU4` peuvent exposer une ligne residuelle `Base` : elle est rapprochee de `CU/base` lorsque le BPU ne contient pas `CU4/base` ou `MU4/base` ;
- les libelles facture `Pointe` en C4 sont rapproches de la ligne BPU `C4/hph`, conforme a la grille Lot 1 et Lot 2 ;
- les libelles saisonniers incoherents avec une formule a un seul poste (`CU`, `LU`, `EP`) sont rapproches de leur poste `base` ;
- les libelles `hph/hpe/hch/hce` sur `MUDT` sont rapproches de `hp/hc`.

## 5. Points volontairement gardes pour V2

Ces controles sont importants mais pas encore implementes en V1 :

- recalcul reglementaire des taxes ;
- cas TURPE specifiques hors composantes principales (regroupement HTA, alimentations de secours, energie reactive HTA, autoconsommation collective) ;
- detection des trous/chevauchements entre factures validees ;
- comparaison fine avec courbes ENEDIS par jour/poste ;
- workflow formel validation/refus ;
- generation d'un motif de refus Chorus ;
- gestion des factures gaz GRDF / lot 7.
