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
| `PERIOD_INVALID` | Periode facturee finissant avant son debut | Facture incoherente. |
| `VAT_TOTAL_MISMATCH` | Total HT + TVA different du TTC | Ecart de totalisation fiscale. |
| `VAT_RECALC_MISMATCH` | TVA recalculee depuis les lignes differente de la TVA facturee | Ecart de TVA. |
| `HT_TOTAL_MISMATCH` | Somme des familles HT differente du total HT | Ecart de totalisation HT. |
| `INVOICE_VAT_TOTAL_MISMATCH` | TVA globale differente de la somme des FIC | Ecart de TVA globale. |
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
| `TAX_TOTALS_MISSING` | Totaux HT/TVA/TTC incomplets | Controle taxes incomplet. |
| `PERIOD_MISSING` | Periode facturee incomplete | Controle de continuite incomplet. |
| `LINE_PERIOD_OUTSIDE_SITE_PERIOD` | Ligne facturee hors periode FIC | A verifier avant validation. |
| `PERIOD_GAP` | Trou de facturation entre deux factures importees | A verifier avant validation. |
| `PERIOD_OVERLAP` | Chevauchement avec une facture deja importee | Risque de double facturation. |
| `CONSUMPTION_REFERENCE_MISSING` | Consommation facturee ou periode absente | Controle ENEDIS incomplet. |
| `CONSUMPTION_LOAD_CURVE_MISMATCH` | Consommation facturee differente de la courbe de charge | Ecart ENEDIS a verifier. |
| `ENEDIS_CONSUMPTION_MISSING` | Donnees ENEDIS absentes sur la periode | Controle ENEDIS incomplet. |
| `ENEDIS_CONSUMPTION_PARTIAL` | Donnees ENEDIS partielles | Controle ENEDIS incomplet. |
| `LOAD_CURVE_CONSUMPTION_PARTIAL` | Courbe de charge partielle pour la consommation | Controle fin incomplet, repli possible sur conso journaliere. |
| `POWER_REFERENCE_MISSING` | Donnees de puissance ou periode absentes | Controle puissance incomplet. |
| `SUBSCRIBED_POWER_MISSING` | Puissance souscrite absente de la facture | Controle puissance incomplet. |
| `SUBSCRIBED_POWER_CONTRACT_MISMATCH` | Puissance facture differente du contrat ENEDIS | Ecart de puissance a verifier. |
| `POWER_OVERRUN` | Puissance atteinte superieure a la puissance souscrite | Depassement a verifier. |
| `POWER_OVERRUN_BILLED` | Depassement de puissance facture | Depassement a verifier. |
| `POWER_LOAD_CURVE_MISMATCH` | Puissance atteinte differente du pic courbe de charge | Ecart ENEDIS a verifier. |
| `POWER_LOAD_CURVE_OVERRUN` | Pic courbe de charge superieur a la puissance souscrite | Risque de depassement. |
| `POWER_ENEDIS_MISMATCH` | Puissance atteinte differente du max power ENEDIS | Ecart ENEDIS a verifier. |
| `POWER_ENEDIS_OVERRUN` | Max power ENEDIS superieur a la puissance souscrite | Risque de depassement. |
| `ENEDIS_POWER_MISSING` | Courbe de charge et max power absents | Controle puissance incomplet. |
| `LOAD_CURVE_POWER_PARTIAL` | Courbe de charge partielle pour la puissance | Controle fin incomplet, repli possible sur max power. |

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
- controle HT/TVA/TTC par FIC et au global.
- controle des periodes et detection de trous/chevauchements entre factures importees.
- comparaison de la consommation facturee avec la courbe de charge ENEDIS lorsqu'elle couvre la periode, sinon repli sur la consommation journaliere.
- controle puissance facture vs contrat ENEDIS, puissance atteinte vs courbe de charge, puis repli sur `enedis_max_power.csv` si la courbe de charge est absente ou partielle.

Precision BPU :

- la grille contractuelle est lue comme le couple `Tension d'alimentation` + `Poste horosaisonnier TURPE` du fichier BPU Herault Energie 2026 ;
- les factures C5 en `BT <= 36 kVA SDT CU4 / MU4` peuvent exposer une ligne residuelle `Base` : elle est rapprochee de `CU/base` lorsque le BPU ne contient pas `CU4/base` ou `MU4/base` ;
- les libelles facture `Pointe` en C4 sont rapproches de la ligne BPU `C4/hph`, conforme a la grille Lot 1 et Lot 2 ;
- les libelles saisonniers incoherents avec une formule a un seul poste (`CU`, `LU`, `EP`) sont rapproches de leur poste `base` ;
- les libelles `hph/hpe/hch/hce` sur `MUDT` sont rapproches de `hp/hc`.

## 5. Points volontairement gardes pour V2

Ces controles sont importants mais pas encore implementes en V1 :

- controle reglementaire detaille des taxes autres que TVA ;
- cas TURPE specifiques hors composantes principales (regroupement HTA, alimentations de secours, energie reactive HTA, autoconsommation collective) ;
- comparaison fine avec courbes ENEDIS par poste horosaisonnier ;
- workflow formel validation/refus ;
- generation d'un motif de refus Chorus ;
- gestion des factures gaz GRDF / lot 7.
