# Pilotage financier et controle global des factures DALKIA

tags: #CPE #DALKIA #facturation #controle #reporting #budget

## Besoin metier

La vue `Factures` ne doit pas etre seulement une archive. Pour la personne chargee du suivi
financier du marche, elle doit fournir une lecture annuelle du realise et permettre de distinguer :

- les montants P1, P2, P3 et hors familles ;
- les factures par mois sur l'exercice courant du 01/01 au 31/12 ;
- les types de facture DALKIA `AC`, `AJ`, `DE`, `EC`, `RE` ;
- les contrats actifs CPE Ville et les contrats hors perimetre ;
- les montants annuels de reference deja saisis dans le referentiel.

Le controle des factures doit disposer de sa propre entree afin de ne pas melanger le pilotage
financier, les archives et la file des anomalies.

## Increment livre

### Factures : suivi financier annuel

- contrats hors perimetre CPE Ville exclus par defaut ;
- exercice courant affiche explicitement du 01/01 au 31/12 ;
- indicateurs : total facture, nombre de factures, moyenne par facture, references contractuelles
  disponibles ;
- graphique mensuel empile P1 / P2 / P3 / autres et nombre de factures ;
- graphique de repartition par statut ;
- graphique des montants par type de facture `AC`, `AJ`, `DE`, `EC`, `RE` ;
- top 10 des postes factures ;
- archive filtrable conservee pour les exports XLSX et les justificatifs PDF.

### Controle factures : audit portefeuille

- nouvelle entree `Controle factures` ;
- action unique `Lancer le controle global` sur les contrats actifs CPE Ville ;
- recalcul backend de toutes les factures du perimetre ;
- indicateurs : factures analysees, conformes, avec ecarts, bloquees, montant total controle ;
- graphique qualite du portefeuille ;
- graphique des anomalies par famille de controle ;
- file de traitement priorisee par facture.

## Limite connue et prochaine marche

Le rapprochement realise / prevu n'est complet que si les references contractuelles sont saisies.
Il faut parser et versionner les enveloppes DPGF des annexes du lot 1 et du lot 2 pour alimenter :

1. budget annuel par famille `P1`, `P2`, `P3` ;
2. budget par poste et par site lorsque l'annexe le permet ;
3. acomptes attendus, definitifs, ajustements et regularisations ;
4. ecart realise / prevu et taux de consommation budgetaire ;
5. suivi du compte P3 : acomptes, engagements reserves, travaux realises et solde.

Cette etape est complementaire du chantier `Travaux P3 / BPU`.

## Increment calendrier et transmission finances

Les quatre dates de l'export DALKIA sont exploitees :

| Colonne DALKIA | Usage Po2 |
|---|---|
| `DATE D'ÉDITION` | date d'emission DALKIA et delai apres fin de periode |
| `DATE D'ÉCHÉANCE DE LA FACTURE` | priorisation comptable avant echeance |
| `DÉBUT PÉRIODE DE FACTURATION` | debut du rattachement contractuel |
| `FIN PÉRIODE DE FACTURATION` | fin du rattachement contractuel et exercice de suivi |

Decision de perimetre :

- Po2 ne suit pas le paiement comptable ;
- Po2 suit l'emission de la fiche de liaison vers le service finance ;
- l'horodatage `finance_exported_at` est renseigne automatiquement au telechargement XLSX depuis
  `Controle factures`.

Evolution UX :

- `Factures` devient une vue analytique en lecture seule ;
- ajout KPI transmission, echeances depassees, echeances proches et echeances absentes ;
- ajout graphique mensuel montants edites / montants a echeance ;
- ajout des dates et badges d'echeance dans l'archive ;
- les actions decision, PDF et export XLSX sont deplacees dans `Controle factures`.

Controle ajoute :

- `invoice_timeline` verifie dates manquantes, periode inversee et echeance anterieure a l'edition.
