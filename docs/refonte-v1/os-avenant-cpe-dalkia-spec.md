# OS / avenants CPE DALKIA - cadrage metier

> Statut : actif, cadrage valide utilisateur du 2026-07-16.
> Route produit : `/refonte-v1/os-avenant`.
> Branche de travail : `staging/factures-import-et-demande-comptable`.

## Objectif

Simplifier la preparation des entrees, sorties et modifications de sites dans le marche CPE DALKIA.
La plateforme doit permettre a la collectivite de formuler un besoin, visualiser immediatement
l'impact financier, collecter les complements DALKIA, produire si besoin un OS EXE1 de prise en
charge rapide, puis regrouper un ou plusieurs OS dans un avenant EXE10.

Le DPGF officiel reste la source contractuelle finale : les dossiers OS/avenant sont un espace de
preparation et ne doivent pas modifier le referentiel DPGF actif tant qu'un nouvel acte signe n'est
pas importe.

## Decisions validees

- Un dossier Po2 represente un futur avenant, pas uniquement un OS.
- Un dossier peut contenir plusieurs lignes : ajout, suppression, modification, remplacement.
- Plusieurs OS signes peuvent etre regroupes dans une fiche de preparation et un avenant unique.
- Les suppressions doivent etre affichees en impact negatif : economie pour la collectivite.
- La date d'effet doit produire un prorata au jour pres.
- Les impacts doivent etre visibles en impact annuel plein, prorata de l'annee de prise d'effet,
  projection par exercice budgetaire, et projection jusqu'a la fin du marche.
- Les documents generes sont telechargeables dans Po2 ; pas de signature integree en v1.

## Sources contractuelles

- DPGF actif importe dans `cpe_dalkia_ref_*` : source principale pour supprimer ou modifier un site
  existant.
- Offre finale DALKIA `01_24BT039_L1_AE_ANNEXES_OFFRE_FINALE.xlsx` : source de controle et de
  comparaison pour les ajouts, notamment :
  - `Annexe 3.1 - P2 - A` : P2 par site et par exercice ; les lignes 8-10 posent les periodes, les colonnes P2.1/P2.2/P2.3/P2.4 et le total ;
  - `Annexe 4 - P3` : P3 par site et par exercice ; les lignes 8-10 posent les periodes, les colonnes P3.1/P3.2/P3.3/P3.4 et le total ;
  - `Annexe 6 - P1 GAZ` : P1 gaz ; les lignes 9-10 exposent les prix unitaires T1/T2, puis les lignes de sites a partir de la zone P1 fixe/P1 variable donnent PCE, tarif, QT, part fixe, variable et total ;
  - `RECAP MARCHE` : recapitulatif financier global.
- `CCAPM.docx` : confirme que les modifications de perimetre avec impact financier sont actees par
  avenant, et que certains prix P1 gaz sont formalises par ordre de service.
- `24BT039L1_AV_AV1_DALKIA_SIGNE_ENTREPRISE_MAIRE_tampon.pdf` : exemple EXE10 signe, utile pour
  calibrer le niveau de detail attendu dans l'avenant.

## Regles de calcul v1

### Suppression de site

Pour une suppression, Po2 lit les montants du site dans le DPGF actif pour l'exercice concerne :
P1 gaz, P1 electricite, P2 et P3. Le delta est negatif.

Si le DPGF contient des montants differents selon les exercices, la projection doit utiliser le
montant de chaque exercice, pas seulement le montant de l'annee de prise d'effet.

### Ajout de site

Pour un ajout, v1 propose un site comparable et pre-remplit P1/P2/P3 depuis le DPGF actif.
L'ecran affiche les composants source disponibles : P1 gaz/electricite, prix unitaire, QT, part
fixe/variable, total, et decomposition P2/P3. La saisie reste modifiable pour ajuster le cas reel
avant validation DALKIA, mais le point de depart ne doit plus etre un zero manuel.

### Prorata et fin de marche

- Prorata au jour pres par exercice civil.
- Fin de marche retenue pour la projection : 12/10/2033.
- Exemple : une date d'effet au 01/09/2026 impacte seulement les jours du 01/09/2026 au 31/12/2026
  pour l'exercice 2026, puis les exercices pleins, puis l'exercice 2033 jusqu'au 12/10/2033.

### Revision de prix

Ne pas recoder une formule parallele dans ce module.
Po2 possede deja un socle backend pour les revisions DALKIA : indices, preuves PDF, observations
factures, coefficient observe P2/P3, et P1 gaz traite separement via prix gaz/OS.

Etape suivante : exposer dans le dossier OS/avenant une option d'affichage "base marche" puis
"estimation revisee" en reutilisant ce moteur, sans confondre valeur d'avenant contractuelle et
controle de facture.

## Workflow cible

1. Brouillon collectivite : type de mouvement, sites, date d'effet, justification.
2. Impact financier Po2 : annuel, prorata, par exercice, fin de marche.
3. Envoi DALKIA : demande de complements techniques et financiers.
4. DALKIA complete : PCE/PDL, tarif, cibles, reserves, montants proposes si ajout.
5. Validation collectivite.
6. Generation OS EXE1 si prise en charge rapide.
7. Regroupement des OS signes dans une fiche de preparation avenant.
8. Generation ou aide a la redaction EXE10.
9. Import du DPGF/avenant officiel, comparaison prevu Po2 vs acte signe.

## Statuts v1

- `draft` : brouillon.
- `sent_to_dalkia` : transmis a DALKIA.
- `dalkia_completed` : DALKIA a complete sa partie.
- `pending_collectivity_validation` : a valider par la collectivite.
- `os_ready` : OS pret a produire/signer.
- `os_signed` : OS signe.
- `in_service` : prise en charge effective.
- `included_in_avenant` : integre dans un avenant.
- `cancelled` : annule.

## Prochaines etapes recommandees

1. Finaliser la projection par exercice budgetaire dans l'API et l'ecran.
2. Ajouter une page detail dossier avec lignes, statut, historique simple et actions.
3. Generer l'OS EXE1.
4. Generer la fiche de preparation avenant.
5. Brancher l'estimation revisee P2/P3 et le traitement P1 gaz sans modifier la base contractuelle.
6. Ajouter un vrai assistant de comparaison pour choisir le site comparable le plus pertinent.
