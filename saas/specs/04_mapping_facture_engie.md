# Mapping facture ENGIE - Facture unique multisite electricite

Source analysee : `saas/energie/ENGIE/FAC54210765114459130000078112.pdf`

Date d'analyse : 2026-05-06

## 1. Conclusion courte

La facture ENGIE fournie est exploitable sans OCR : le PDF contient du texte extractible.

La structure est suffisamment reguliere pour construire un parseur fiable en premiere version, a condition de ne pas se limiter a la page de synthese. Le coeur de l'exploitation doit etre la combinaison :

- enveloppe facture, page 1 ;
- index multi-sites, page 3 ;
- fiches info conso, pages 4 a 17 ;
- lignes detaillees de facture ;
- releves/index et puissances, lorsque presents.

Le champ `Regroupement : MUSEES` est une information metier structurante. Il correspond a une typologie de batiments ou a un perimetre de facturation groupe. Il doit etre stocke et rendu filtrable, au meme titre que le fournisseur, le marche, le lot et les PRM.

## 2. Structure du document

### 2.1 Page 1 - Enveloppe facture

La premiere page porte les donnees globales opposables de la facture.

Champs presents dans l'exemple :

- fournisseur : ENGIE ;
- type : Facture Unique Multi-Site electricite ;
- numero facture : `130000078112` ;
- date facture : `6 mars 2026` ;
- date de prelevement / echeance : `07 avril 2026` ;
- mode de paiement : `PRELEVEMENT AUTOMATIQUE` ;
- reference client globale : `400 000 229 002` ;
- titulaire : `MAIRIE DE SETE` ;
- SIREN/SIRET contractant : `213403017 00014` ;
- reference du marche : `2024-FCS-03` ;
- regroupement : `MUSEES` ;
- donnees Chorus :
  - numero EJ : `FLUIDES MUSEES` ;
  - collectivite / libelle : `SETE` ;
  - code service executant : `RFE` ;
- montant TTC a payer : `13 432,55 EUR` ;
- consommation totale : `52,458 MWh`.

Totaux globaux visibles :

- fourniture electricite : `5 882,36 EUR` ;
- terme variable fourniture : `5 190,01 EUR` ;
- electricite origine renouvelable : `87,58 EUR` ;
- obligation capacite : `49,27 EUR` ;
- contribution CEE : `555,50 EUR` ;
- acheminement : `3 671,41 EUR` ;
- total hors toutes taxes : `9 553,77 EUR` ;
- total taxes : `1 640,02 EUR` ;
- total electricite hors TVA : `11 193,79 EUR` ;
- TVA 20 % : `2 238,76 EUR`.

Regle de controle : les montants de la page 1 font foi. Les totaux par PRM/FIC peuvent presenter des ecarts d'arrondi au centime.

### 2.2 Page 2 - Informations fournisseur et lexique

Cette page contient surtout :

- contacts ENGIE ;
- informations de paiement ;
- mentions legales ;
- lexique.

Elle n'est pas prioritaire pour le controle facture. Elle peut etre ignoree en V1, sauf si l'on veut enrichir une fiche fournisseur.

### 2.3 Page 3 - Index multi-sites

La page 3 liste les points de livraison inclus dans la facture unique multisite.

Colonnes utiles :

- PRM/PDL ;
- numero de compteur ;
- periode globale de consommation ;
- nom du site ;
- adresse du point de livraison ;
- option tarifaire ;
- segment ;
- consommation kWh ;
- fourniture HT ;
- acheminement HT ;
- services et prestations techniques ;
- taxes et contributions ;
- TVA 5,5 % ;
- TVA 20 % ;
- total TTC ;
- page de la FIC.

Sites detectes dans l'exemple :

| PRM | Site | Segment | Option | Periode synthese | Conso kWh | Total TTC |
| --- | --- | --- | --- | --- | ---: | ---: |
| 24327496216403 | SALLE DE LA MACARONADE | C5 | BT <= 36 kVA, 4 plages | 01/01/2026 - 10/02/2026 | 3 | 11,76 |
| 24342112704012 | MUSEE DE LA MER | C5 | BT <= 36 kVA, 4 plages | 01/01/2026 - 19/02/2026 | 0 | 31,40 |
| 24368017304978 | CHAPELLE DU QUARTIER HAUT | C5 | BT <= 36 kVA, 4 plages | 01/01/2026 - 01/03/2026 | 3 370 | 940,38 |
| 30002431058705 | MIAM | C4 | BT > 36 kVA, 4 plages | 01/01/2026 - 06/02/2026 | 21 723 | 5 499,97 |
| 30002431566185 | ESPACE GEORGES BRASSENS | C4 | BT > 36 kVA, 5 plages | 01/01/2026 - 06/02/2026 | 13 028 | 3 272,28 |
| 50008213870861 | MUSEE DE LA MER | C4 | BT > 36 kVA, 4 plages | 01/01/2026 - 06/02/2026 | 14 334 | 3 676,75 |

Attention : le nom de site n'est pas unique. `MUSEE DE LA MER` correspond ici a deux PRM distincts, l'un en C5 et l'autre en C4. La clef fonctionnelle ne doit donc jamais etre le nom du site seul.

Attention egalement : dans ce PDF, la colonne `Page de la FIC` ne doit pas etre utilisee comme pointeur technique fiable. Le parseur doit retrouver les fiches par les marqueurs `Fiche info conso`, `PDL/PRM` et periode, pas par le numero de page annonce dans le tableau.

### 2.4 Pages 4 a 17 - Fiches info conso

Chaque fiche info conso porte le detail par PRM et par sous-periode. Un meme PRM peut avoir plusieurs fiches sur une meme facture.

Champs d'entete d'une fiche :

- numero facture ;
- date facture ;
- numero de FIC ;
- site ;
- regroupement ;
- periode de consommation ;
- reference client locale ;
- titulaire ;
- date d'echeance du contrat ;
- offre ;
- acheminement / option tarifaire ;
- segment ;
- PDL/PRM ;
- designation du site ;
- adresse de livraison ;
- type de compteur ;
- numero de compteur, lorsqu'il est present ;
- puissance souscrite ;
- puissance atteinte, surtout sur C4.

Fiches detectees :

| Page PDF | FIC | PRM | Site | Segment | Periode |
| ---: | --- | --- | --- | --- | --- |
| 4 | 120009783694 | 24327496216403 | SALLE DE LA MACARONADE | C5 | 01/01/2026 - 10/01/2026 |
| 5 | 650000498672 | 24327496216403 | SALLE DE LA MACARONADE | C5 | 11/01/2026 - 10/02/2026 |
| 6 | 640000420875 | 24342112704012 | MUSEE DE LA MER | C5 | 20/01/2026 - 19/02/2026 |
| 7 | 820006337384 | 24342112704012 | MUSEE DE LA MER | C5 | 01/01/2026 - 19/01/2026 |
| 8-9 | 740000493457 | 24368017304978 | CHAPELLE DU QUARTIER HAUT | C5 | 01/01/2026 - 01/02/2026 |
| 10 | 770000453100 | 24368017304978 | CHAPELLE DU QUARTIER HAUT | C5 | 02/02/2026 - 01/03/2026 |
| 11 | 640000420073 | 30002431058705 | MIAM | C4 | 07/01/2026 - 06/02/2026 |
| 12 | 690000453825 | 30002431058705 | MIAM | C4 | 01/01/2026 - 06/01/2026 |
| 13-14 | 640000420062 | 30002431566185 | ESPACE GEORGES BRASSENS | C4 | 07/01/2026 - 06/02/2026 |
| 15 | 690000453814 | 30002431566185 | ESPACE GEORGES BRASSENS | C4 | 01/01/2026 - 06/01/2026 |
| 16 | 640000420093 | 50008213870861 | MUSEE DE LA MER | C4 | 07/01/2026 - 06/02/2026 |
| 17 | 690000453845 | 50008213870861 | MUSEE DE LA MER | C4 | 01/01/2026 - 06/01/2026 |

## 3. Lignes detaillees a exploiter

Les blocs de detail suivent une structure assez stable :

- famille de facturation ;
- libelle ;
- periode ;
- quantite ;
- prix unitaire HT ;
- montant HT ;
- taux de TVA.

Familles detectees :

- `Electricite` ;
- `Acheminement electricite` ;
- `Vos services et autres prestations` ;
- `Taxes et Contributions` ;
- `TVA`.

Exemples de lignes de fourniture :

- Consommation HP Saison Haute ;
- Consommation HC Saison Haute ;
- Consommation Pointe ;
- Electricite d'origine renouvelable ;
- Certificats d'economie d'energie ;
- Obligation Capacite HP Saison Haute ;
- Obligation Capacite HC Saison Haute ;
- Obligation Capacite Pointe.

Exemples de lignes d'acheminement :

- Composante de comptage ;
- Composante de soutirage ;
- Composante de gestion ;
- Consommation HP Saison Haute ;
- Consommation HC Saison Haute ;
- Consommation HP Saison Basse ;
- Consommation HC Saison Basse ;
- Consommation Pointe.

Exemples de lignes taxes :

- Contribution tarifaire d'acheminement ;
- Contribution service public electricite.

Point important pour le rapprochement BPU : les prix de fourniture sont exprimes sur la facture en EUR/kWh. Le BPU peut etre exprime en EUR/MWh. Le controle doit donc comparer `prix_facture_kwh` avec `prix_bpu_mwh / 1000`.

Exemple :

- facture : `0,10591 EUR/kWh` ;
- BPU equivalent : `105,91 EUR/MWh`.

## 4. Releves, index et puissances

Les fiches contiennent un bloc `Consommation d'energie`.

Champs a extraire :

- poste horosaisonnier ;
- numero compteur ;
- date ancienne releve ;
- ancien index ;
- date nouvelle releve ;
- nouvel index ;
- type de releve : `R`, `E`, `A` ;
- difference ;
- energie kWh ;
- puissance souscrite ;
- puissance atteinte.

Codes detectes :

- `Base` ;
- `HPSH` : heures pleines saison haute ;
- `HCSH` : heures creuses saison haute ;
- `HPSB` : heures pleines saison basse ;
- `HCSB` : heures creuses saison basse ;
- `Pointe`, sur les contrats 5 plages.

Exemple C4 :

- puissance souscrite HPSH : `50 kVA` ;
- puissance atteinte HPSH : `42 kVA`.

Ce bloc est tres important pour la future fonction de calibrage, car il permet de relier la facture a la puissance souscrite et a la puissance reellement atteinte par poste horosaisonnier.

## 5. Donnees a stocker

### 5.1 Niveau import

Table existante a conserver : `energy_invoice_imports`.

Elle sert a tracer :

- fichier importe ;
- hash ;
- utilisateur ;
- ville ;
- statut d'analyse ;
- fournisseur detecte.

### 5.2 Niveau facture

Nouvelle table cible proposee : `energy_invoices`.

Champs :

- `id` ;
- `city_id` ;
- `import_id` ;
- `supplier` ;
- `invoice_type` ;
- `invoice_number` ;
- `invoice_date` ;
- `payment_due_date` ;
- `payment_method` ;
- `global_customer_reference` ;
- `contract_holder` ;
- `contract_siret` ;
- `market_reference` ;
- `regroupement` ;
- `chorus_ej` ;
- `chorus_service_code` ;
- `chorus_label` ;
- `total_consumption_mwh` ;
- `total_ht` ;
- `total_taxes` ;
- `total_vat` ;
- `total_ttc` ;
- `currency` ;
- `raw_extracted_text_hash`.

### 5.3 Niveau PRM / site facture

Nouvelle table cible proposee : `energy_invoice_sites`.

Champs :

- `id` ;
- `invoice_id` ;
- `prm_id` ;
- `site_name` ;
- `delivery_address` ;
- `meter_number` ;
- `meter_type` ;
- `local_customer_reference` ;
- `segment` ;
- `tariff_option_label` ;
- `usage_type` : courte / longue utilisation si detectee ;
- `regroupement` ;
- `summary_period_start` ;
- `summary_period_end` ;
- `summary_consumption_kwh` ;
- `summary_supply_ht` ;
- `summary_network_ht` ;
- `summary_services_ht` ;
- `summary_taxes` ;
- `summary_vat_5_5` ;
- `summary_vat_20` ;
- `summary_total_ttc`.

### 5.4 Niveau FIC / periode

Nouvelle table cible proposee : `energy_invoice_periods`.

Champs :

- `id` ;
- `invoice_site_id` ;
- `fic_number` ;
- `period_start` ;
- `period_end` ;
- `pdf_page_start` ;
- `pdf_page_end` ;
- `supply_ht` ;
- `network_ht` ;
- `services_ht` ;
- `taxes_ht` ;
- `total_ht` ;
- `total_vat` ;
- `total_ttc` ;
- `subscribed_power_kva` ;
- `max_reached_power_kva`.

### 5.5 Niveau ligne facture

Nouvelle table cible proposee : `energy_invoice_lines`.

Champs :

- `id` ;
- `invoice_period_id` ;
- `family` ;
- `label` ;
- `normalized_code` ;
- `period_start` ;
- `period_end` ;
- `quantity` ;
- `quantity_unit` ;
- `unit_price_ht` ;
- `unit_price_unit` ;
- `amount_ht` ;
- `vat_rate` ;
- `raw_line`.

Codes normalises proposes :

- `SUPPLY_HPSH` ;
- `SUPPLY_HCSH` ;
- `SUPPLY_HPSB` ;
- `SUPPLY_HCSB` ;
- `SUPPLY_POINTE` ;
- `GREEN_ENERGY` ;
- `CEE` ;
- `CAPACITY_HPSH` ;
- `CAPACITY_HCSH` ;
- `CAPACITY_POINTE` ;
- `TURPE_COUNTING` ;
- `TURPE_WITHDRAWAL_FIXED` ;
- `TURPE_MANAGEMENT` ;
- `TURPE_HPSH` ;
- `TURPE_HCSH` ;
- `TURPE_HPSB` ;
- `TURPE_HCSB` ;
- `TURPE_POINTE` ;
- `CTA` ;
- `CSPE`.

### 5.6 Niveau releves et puissances

Nouvelle table cible proposee : `energy_invoice_meter_reads`.

Champs :

- `id` ;
- `invoice_period_id` ;
- `period_code` ;
- `meter_number` ;
- `previous_read_date` ;
- `previous_index` ;
- `current_read_date` ;
- `current_index` ;
- `reading_type` ;
- `difference` ;
- `energy_kwh` ;
- `subscribed_power_kva` ;
- `reached_power_kva`.

## 6. Controles a produire

### 6.1 Controles de coherence facture

- facture deja importee : fournisseur + numero facture + hash ;
- montant TTC page 1 coherent avec somme index multi-sites ;
- consommation totale page 1 coherente avec somme PRM ;
- somme des FIC coherente avec la ligne PRM ;
- periode facturee sans trou ni chevauchement pour un meme PRM ;
- PRM connu dans le module Energie ;
- regroupement reconnu ;
- donnees Chorus presentes.

### 6.2 Controles BPU

- ligne de fourniture variable par poste horosaisonnier ;
- ligne electricite origine renouvelable ;
- ligne CEE ;
- ligne obligation capacite ;
- unites converties correctement entre EUR/MWh et EUR/kWh ;
- ecart prix facture / prix BPU ;
- ecart montant calcule / montant facture ;
- tolerance d'arrondi configurable.

### 6.3 Controles acheminement et taxes

En V1, controler d'abord :

- presence des familles ;
- totaux par famille ;
- coherence arithmetique ligne par ligne ;
- coherences des quantites kWh.

En V2, ajouter le recalcul fin TURPE et taxes selon les regles en vigueur.

### 6.4 Controle calibrage

La facture apporte des donnees directement utiles :

- puissance souscrite par PRM ;
- puissance atteinte par poste, surtout C4 ;
- segment C4/C5 ;
- option courte/longue utilisation ;
- saison/poste.

Ces donnees peuvent alimenter le module `Calibrage`, mais la preconisation ne doit pas etre declaree comme economie certaine sans simulation TURPE et verification de depassement.

## 7. Strategie de parseur proposee

### 7.1 V1 pragmatique

1. Extraire le texte avec `pypdf` cote backend.
2. Identifier le fournisseur par contenu : `ENGIE`, `Facture Unique Multi-Site`.
3. Parser la page 1 avec expressions regulieres.
4. Parser toutes les pages contenant `Fiche info conso`.
5. Grouper les pages qui partagent le meme numero FIC.
6. Parser les entetes FIC.
7. Parser les blocs `Detail de votre facture`.
8. Parser les blocs `Consommation d'energie`.
9. Generer un JSON normalise.
10. Stocker ce JSON en base et afficher le resultat dans l'interface d'import.

### 7.2 Points de vigilance

- Les libelles peuvent etre sur plusieurs lignes.
- Les nombres francais contiennent des espaces milliers et des virgules decimales.
- Une meme FIC peut tenir sur plusieurs pages.
- Une facture peut contenir plusieurs PRM pour le meme nom de site.
- La page d'index est utile mais ne doit pas etre la seule source de verite.
- La page 1 fait foi pour le total TTC.
- Les montants par PDL/FIC sont parfois indicatifs.
- Les colonnes extraites du PDF peuvent etre dans un ordre visuel imparfait.

## 8. Proposition d'implementation

### Etape 1 - Parseur ENGIE PDF

Ajouter un service backend :

- `app/services/invoice_parsers/base.py` ;
- `app/services/invoice_parsers/engie_pdf.py`.

Ajouter une dependance backend :

- `pypdf`.

Sortie attendue :

- supplier ;
- invoice ;
- sites ;
- periods ;
- lines ;
- meter_reads ;
- parser_warnings.

### Etape 2 - Tables metier facture

Ajouter les migrations et modeles :

- `EnergyInvoice` ;
- `EnergyInvoiceSite` ;
- `EnergyInvoicePeriod` ;
- `EnergyInvoiceLine` ;
- `EnergyInvoiceMeterRead` ;
- `EnergyInvoiceControl`.

### Etape 3 - Analyse automatique apres import

Au moment de l'import :

- stocker le fichier ;
- detecter le fournisseur ;
- parser le contenu ;
- enregistrer les donnees normalisees ;
- afficher un statut `analyse OK`, `analyse partielle`, ou `analyse en erreur`.

### Etape 4 - Interface utilisateur

Dans `/energie/factures` :

- afficher les factures importees ;
- afficher le regroupement ;
- afficher le montant TTC ;
- afficher le nombre de PRM ;
- afficher les alertes ;
- ouvrir une vue detaillee de facture ;
- permettre de valider/refuser plus tard.

### Etape 5 - Controle BPU

Une fois le parseur stabilise :

- rapprocher chaque ligne normalisee avec le BPU ;
- afficher les ecarts ;
- produire un statut de controle par facture, par PRM et par ligne.

## 9. Decision produit

Le champ `Regroupement` doit devenir une dimension fonctionnelle de l'energie.

Proposition :

- stocker `regroupement` au niveau facture ;
- recopier `regroupement` au niveau PRM facture pour faciliter les filtres ;
- permettre un filtre UI par regroupement ;
- utiliser ce champ pour preparer la validation Chorus et les circuits internes par typologie de batiments.

Dans l'exemple, `MUSEES` permet de comprendre que la facture regroupe plusieurs batiments culturels : SALLE DE LA MACARONADE, MUSEE DE LA MER, CHAPELLE DU QUARTIER HAUT, MIAM, ESPACE GEORGES BRASSENS.

