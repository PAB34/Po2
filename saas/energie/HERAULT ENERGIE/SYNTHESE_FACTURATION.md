# Synthese facturation - Marche energie Herault Energie

Objectif de ce fichier : servir de reference rapide pour les controles de factures dans Po2, sans devoir relire les pieces contractuelles completes a chaque evolution.

Sources principales :
- `2024-FCS-03_CCTP-C_LOTS 1 A 6.pdf`
- `2024-FCS-03_CCAP_LOTS 1 A 6.pdf`
- `2024-FCS-03_CCTP-C_LOTS 7 A 8.pdf`
- `2024-FCS-03_CCAP-C_LOTS 7 ET 8.pdf`
- `Formules de facturation.docx`

## 1. Frequence de facturation attendue

### Electricite - lots 1 a 6

Regle cible :
- facturation mensuelle pour l'ensemble des PDL ;
- a defaut, facturation bimestrielle ou semestrielle selon les possibilites fournisseur/compteur ;
- cas particulier mentionne : certains PDL C5 non encore munis d'un compteur Linky/AMM ou non aptes a communiquer.

Lecture operationnelle pour Po2 :
- un PDL Linky ou facture au pas mensuel doit normalement presenter une couverture mensuelle continue ;
- un PDL hors Linky peut presenter un cycle bimestriel ;
- une facturation estimee est possible, mais doit etre regularisee au minimum semestriellement a partir d'index releves ;
- au moins deux factures sur consommation reelle doivent etre etablies par an pour les PDL factures au pas bimestriel hors Linky.

Pieces reperees :
- CCTP-C lots 1 a 6, article 6-1 : etablissement de la facturation.
- CCAP lots 1 a 6, article 8 : facturation mensuelle, a defaut bimestrielle ou semestrielle.

### Gaz - lots 7 a 8

Regle cible :
- factures mensuelles pour l'ensemble des PDL, sauf demande contraire des membres ;
- PDL teleleves ou Gazpar : consommation reelle ;
- PDL a releve semestrielle hors Gazpar/teleleve : facturation mensuelle possible sur reel ou estime ;
- au moins deux factures sur consommation reelle doivent etre etablies par an.

Lecture operationnelle pour Po2 :
- le suivi attendu est mensuel ;
- une absence de facture sur un mois doit etre signalee plus fortement qu'en electricite, sauf demande contraire connue ;
- les estimations doivent etre surveillees pour verifier la regularisation sur index releve.

Pieces reperees :
- CCTP-C lots 7 a 8, article 6-1 : etablissement de la facturation.
- CCAP-C lots 7 et 8, article 8 : factures mensuelles sauf demande contraire des membres.

## 2. Delais de transmission et retard

Regle commune relevee :
- premieres factures apres bascule : avant le dernier jour du mois M+2 suivant le premier mois de fourniture ;
- factures suivantes : avant le dernier jour du mois M+1 suivant le dernier mois de la periode de facturation conforme a la frequence convenue.

Lecture operationnelle pour Po2 :
- si une facture couvre janvier, elle devrait etre recue avant fin fevrier dans le cycle normal ;
- si une periode bimestrielle couvre janvier-fevrier, elle devrait etre recue avant fin mars ;
- les retards doivent etre suivis par facture et aussi par PDL lorsque la facture est groupee.

Pieces reperees :
- CCAP lots 1 a 6, penalite pour retard de facturation.
- CCAP-C lots 7 et 8, penalite pour retard de facturation.

## 3. Donnees numeriques attendues

Le titulaire doit mettre a disposition un flux de donnees de consommation et de facturation :
- prioritairement en temps continu, c'est-a-dire a chaque edition de facture ;
- a defaut au pas mensuel ;
- avec les factures PDF vectorielles ;
- avec les donnees de consommation ayant servi a la facturation ;
- si disponible, avec les points d'index.

Le flux doit etre scrupuleusement identique a la facture.

Lecture operationnelle pour Po2 :
- les donnees XLSX/flux doivent pouvoir etre rapprochees des factures PDF ;
- toute difference entre piece comptable et flux numerique est une anomalie contractuelle ;
- les graphiques de suivi peuvent s'appuyer sur le flux XLSX, mais les ecarts doivent rester tracables jusqu'a la facture.

Pieces reperees :
- CCTP-C lots 1 a 6, article 8-4.
- CCTP-C lots 7 a 8, article 8-4.

## 4. Informations minimales attendues par ligne PDL

Les pieces demandent un detail par PDL, independamment des regroupements de factures.

Champs importants pour Po2 :
- nom ou numero du regroupement de facture ;
- nom du PDL ;
- adresse du PDL ;
- code postal ;
- numero de facture ;
- type de facture : facture, annulation, avoir, regularisation ;
- date de facture ;
- date de debut et date de fin de periode de consommation ;
- nature de la consommation : relevee ou estimee ;
- consommation de la periode ;
- composantes de fourniture ;
- composantes d'acheminement ;
- taxes et contributions ;
- prestations distributeur ;
- total HT, TVA, TTC.

Lecture operationnelle pour Po2 :
- les controles doivent rester au niveau PDL/site, meme si la facture est regroupee ;
- les graphiques mensuels doivent pouvoir compter :
  - le nombre de factures/bordereaux ;
  - le nombre de PDL/sites factures ;
  - les consommations facturees ;
  - les consommations relevees ENEDIS/GRD ;
  - les mois ou une facture est estimee.

## 5. Pre-controle et correction des factures

Le titulaire doit controler la fiabilite des donnees avant edition.

Les pieces mentionnent :
- obligation de resultat sur la qualite des factures emises ;
- processus de correction et de validation ;
- traitement des erreurs signalees par un membre ;
- possibilite de mise en statut suspendue en cas de demande d'information sur une facture supposee erronee.

Lecture operationnelle pour Po2 :
- une facture avec anomalie significative doit rester en statut "a verifier" ou "refusee" jusqu'a justification ;
- le rapport fournisseur doit faciliter une demande d'explication claire ;
- les anomalies doivent separer :
  - erreur de prix BPU ;
  - erreur TURPE/acheminement ;
  - ecart consommation facturee vs relevee ;
  - trou ou chevauchement de periode ;
  - facture estimee non regularisee ;
  - incoherence entre flux numerique et facture.

## 6. Penalites utiles au controle

Penalite pour facture non conforme :
- penalite possible a compter du 15e jour apres rejet ou non-conformite renouvelee ;
- montant repere : 15 EUR par jour calendaire et par facture non conforme.

Penalite pour retard de facturation :
- montant repere : 10 EUR par jour calendaire de retard et par facture non transmise ;
- une facture groupee est comptabilisee autant de fois que de PDL presents dans la facture groupee.

Penalite pour non-correspondance facture / donnees numeriques :
- montant repere : 20 EUR par jour calendaire et par facture non conforme.

Penalite pour retard ou non-transmission des flux mensuels :
- penalites specifiques mentionnees sur les fichiers mensuels et les flux de consommation/facturation.

Lecture operationnelle pour Po2 :
- le suivi des trous de facturation doit compter les PDL concernes, pas seulement les bordereaux ;
- le rapport fournisseur doit pouvoir isoler les factures/PDL en retard ou incomplets.

## 7. Recommandations Po2 pour le graphique factures

Sur la page `/energie/factures`, le graphique de tete devrait afficher, pour l'annee courante :

1. Consommation facturee ENGIE par mois.
2. Consommation relevee ENEDIS par mois.
3. Nombre de factures/bordereaux par mois.
4. Nombre de PDL/sites factures par mois.
5. Nombre de PDL/sites avec donnees ENEDIS disponibles.
6. Signal "mois incomplet" lorsque :
   - ENEDIS presente de la consommation mais aucune facture ENGIE ;
   - le nombre de PDL factures chute fortement par rapport aux mois voisins ;
   - une periode attendue est absente ;
   - une facture estimee n'a pas de regularisation semestrielle connue.

Priorite de developpement :
- court terme : afficher `invoice_count` deja disponible dans l'API mensuelle ;
- moyen terme : ajouter `site_count`/`prm_billed_count` par mois ;
- moyen terme : ajouter une alerte "trou potentiel" basee sur les periodes couvertes par PRM ;
- long terme : stocker la frequence attendue par PRM ou par segment pour distinguer mensuel, bimestriel et semestriel.

## 8. Regles de controle a formaliser dans le code

Frequence attendue :
- electricite Linky/C2-C4 : mensuel par defaut ;
- electricite C5 Linky/AMM : mensuel par defaut ;
- electricite C5 non communicant : bimestriel ou semestriel possible ;
- gaz : mensuel par defaut, sauf demande contraire.

Delai attendu :
- facture suivante attendue avant fin M+1 apres la fin de periode ;
- premiere facture apres bascule attendue avant fin M+2.

Couverture attendue :
- pas de trou non justifie entre deux periodes d'un meme PRM ;
- pas de chevauchement non justifie ;
- premiere et derniere facture : prorata attendu sur les termes fixes.

Qualite de la consommation :
- distinguer consommation relevee et estimee ;
- verifier au moins deux factures reelles par an pour les cycles non teleleves ;
- verifier regularisation semestrielle des estimations.

