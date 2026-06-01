# Formules, indices et demandes de travaux P3

tags: #CPE #DALKIA #facturation #indices #preuves #P3 #BPU #workflow

## Decision produit

L'entree `/cpe` > `Referentiel finance` > `Indices` doit devenir :

> **Formules et indices**

Cette entree centralise :

1. les formules contractuelles applicables ;
2. les valeurs de base et les indices periodiques ;
3. les coefficients observes dans les exports XLSX DALKIA ;
4. les pieces PDF justificatives ;
5. le statut de verification de chaque valeur ;
6. les conflits entre valeur declaree par DALKIA et valeur officielle verifiee.

L'objectif n'est pas de considerer silencieusement une valeur extraite d'une facture comme officielle.
Le PDF sert de preuve contradictoire : il explique le calcul DALKIA et permet de verifier que Po2
retombe sur le meme coefficient. La promotion au statut `official_verified` reste une action explicite.

## Familles de formules a centraliser

### P1 gaz

Le controle P1 comprend plusieurs niveaux :

```text
P1 chauffage = QT x Pugaz
```

Le prix `Pugaz` depend de la formule contractuelle par typologie tarifaire (`T1`, `T2`, `T3`, `T4`)
et des composantes applicables : `PEG`, `TVD`, `CEE`, `TICGN`, ainsi que leurs valeurs de reference.

Pour la periode couverte par l'OS n°3, le prix gaz fixe doit rester trace comme une version contractuelle
particuliere. Les acomptes P1 sont controles separement : trois acomptes de `1/4 P10`, puis decompte
definitif.

### P2

La meme formule de revision s'applique aux postes P2, sous reserve des regles de facturation propres
a certains postes :

```text
P2 = P20 x (0,15 + 0,70 x ICHT-IME / ICHT-IME0 + 0,15 x FSD2 / FSD20)
```

Valeurs de base connues :

| Indice | Valeur base |
|---|---:|
| ICHT-IME0 | 141,4 |
| FSD20 | 169,8 |

Cas particuliers a conserver dans le moteur :

- `P2.4` : facture annuellement apres validation de l'atteinte des objectifs energetiques ; montant
  ramene a 50% si les objectifs ne sont pas atteints ;
- `Sensibilisation energetique` : facture trimestriellement comme les autres postes P2 ;
- taux horaires BPU : revises selon la formule P2.

### P3

La formule confirmee apres mise au point OUV11 est utilisee pour `P3.1` a `P3.4` :

```text
P3 = P30 x (0,15 + 0,30 x ICHT-IME / ICHT-IME0 + 0,55 x BT40 / BT400)
```

Valeurs de base connues :

| Indice | Valeur base |
|---|---:|
| ICHT-IME0 | 141,4 |
| BT400 | 128,4 |

Cas complementaires :

- quatre acomptes trimestriels de `1/4 P30 revise` ;
- equipements BPU : revises selon la formule P3 ;
- coefficients de transparence materiels et sous-traitance : fixes pendant la duree du marche.

### Autres calculs a conserver dans le catalogue

Ces calculs ne sont pas tous des revisions de prix, mais ils doivent etre visibles dans le meme
catalogue pour comprendre une facture et tracer la regle appliquee :

| Famille | Calcul ou regle |
|---|---|
| Interessement energetique | `NB`, `N'B`, `NC`, DJU, `Pu`, penalite ou interessement |
| P2.4 | Facturation a 100% ou 50% selon validation des objectifs |
| APE P3.4 | Montant global et forfaitaire ; suivi separe du programme de travaux |
| BPU hors forfait | Prix unitaire, taux horaire, coefficient materiel ou sous-traitance, justificatif |
| Compte P3 | Redevances creditees, depenses debitees, engagements reserves, solde |

## Limite de la migration 0030

La migration `0030_add_cpe_invoice_evidences.py` a livre un premier workflow utile :

- stockage du PDF DALKIA ;
- extraction du coefficient et des indices declares ;
- liaison avec `cpe_revision_indices` ;
- statut `declared_to_verify`.

Mais `cpe_invoice_evidences.invoice_id` est obligatoire. Cette contrainte impose de televerser un PDF
depuis une facture archivee. Elle ne convient pas au centre `Formules et indices`, car une meme preuve
peut justifier une valeur commune a plusieurs factures.

Ne pas modifier retroactivement la migration `0030` si elle est deja deployee.

## Migration additive a prevoir

Creer une migration suivante, par exemple `0031_generalize_cpe_revision_evidences.py` :

1. rendre `invoice_id` optionnel dans `cpe_invoice_evidences` ;
2. ajouter `evidence_kind` : `invoice_pdf`, `official_publication`, `contract_document`, `os`, `manual_note` ;
3. ajouter les metadonnees `market`, `contract_code`, `year`, `quarter`, `effective_date` ;
4. ajouter une table de liaison plusieurs-a-plusieurs entre preuves et factures ;
5. conserver la liaison entre un indice et sa preuve principale ;
6. historiser les changements de statut : `declared_to_verify`, `official_verified`, `rejected`, `superseded` ;
7. permettre plusieurs preuves pour une meme valeur sans ecraser silencieusement une preuve officielle.

## Parcours cible dans Formules et indices

### Vue 1 - Formules contractuelles

Afficher une fiche par famille : `P1`, `P2`, `P3`, `BPU`, `P2.4`, `Interessement`.

Chaque fiche montre :

- formule lisible ;
- version et date d'effet ;
- contrat et lot ;
- indices requis ;
- valeurs de base ;
- source contractuelle ;
- cas particuliers ;
- statut de verification.

### Vue 2 - Indices et preuves

Afficher les valeurs par annee et trimestre :

- valeur declaree DALKIA ;
- valeur officielle verifiee ;
- ecart eventuel ;
- source ;
- PDF ou publication rattachee ;
- date d'effet ;
- statut.

### Vue 3 - Nouveaux coefficients detectes

Lors de l'import XLSX :

1. calculer `coefficient observe = prix revise / prix de base` ;
2. comparer avec les coefficients deja connus ;
3. creer une alerte si le coefficient est nouveau ou contradictoire ;
4. proposer directement l'import PDF depuis cette alerte ;
5. extraire la date, le coefficient et les indices declares ;
6. afficher un apercu avant enregistrement ;
7. conserver les valeurs comme `declarees DALKIA - a verifier` ;
8. recalculer les factures affectees apres validation explicite.

Message cible :

> Nouveau coefficient DALKIA detecte pour P2 2026 T2. Importer une facture PDF justificative pour
> extraire les indices declares, puis verifier ces valeurs aupres d'une source officielle.

Le bouton `Importer PDF` peut rester visible dans le detail d'une facture comme raccourci, mais le
parcours principal et la liste des preuves appartiennent a `Formules et indices`.

## Prochain chantier Travaux P3 / BPU

L'entree `/cpe` devra egalement recevoir un module principal `Travaux P3` avec :

1. parser versionne des feuilles `Annexe 7 - B.P.U - D.Q.E` Lot 1 et Lot 2 ;
2. catalogue BPU consultable : 128 prestations standards, 7 taux horaires, 3 coefficients materiels,
   3 coefficients sous-traitance et 4 equipements de transition ;
3. registre des demandes DALKIA ;
4. qualification obligatoire : `P3.1-P3.3`, `P3.4`, `BPU hors forfait`, `urgence securite` ;
5. controle automatique code BPU, quantite, prix, revision, coefficient, justificatif et budget ;
6. espace fournisseur cloisonne ;
7. alerte controleur, decision historisee, email et bon pour accord ;
8. suivi realisation, reception et rapprochement avec la facture ;
9. compte P3 : acomptes, engagements reserves, travaux realises et solde.

## Ordre recommande

1. Refaire `Formules et indices` et generaliser les preuves PDF.
2. Ajouter le catalogue des formules versionnees.
3. Brancher les alertes XLSX vers l'import PDF centralise.
4. Recalculer automatiquement les factures affectees.
5. Developper ensuite le referentiel BPU P3 puis le workflow de demandes de travaux.

