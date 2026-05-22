# Export finances DALKIA - analyse du 22/05/2026

tags: #CPE #DALKIA #facturation #P1 #P2 #P3 #import

> Source analysee : `saas/energie/DALKIA/FACTURES/export_finances-20260522_0154.csv`
> Role dans Po2 : source de lignes financieres DALKIA avant controle contradictoire des factures CPE.

---

## Ce que contient le fichier

L'export n'est pas une facture PDF et n'est pas non plus un fichier de releves mensuels. C'est un export de lignes financieres de l'espace client DALKIA.

Il contient notamment :
- identifiant de contrat DALKIA ;
- numero et type de facture ;
- type de marche, marche et poste facture ;
- periode de facturation ;
- montant HT ;
- prix de base et prix ou forfait revise ;
- site ou detail de prestation ;
- consommation, unite et index de releve quand DALKIA les expose.

Cette granularite est tres utile : une facture peut etre decomposee par site et par poste `P1`, `P2`, `P3`, mais elle impose de conserver la ligne de detail et pas seulement un total facture.

---

## Chiffres constates dans l'export

| Mesure | Valeur |
|--------|--------|
| Lignes | 6 821 |
| Factures distinctes | 526 |
| Contrats distincts | 8 |
| Lieux / details distincts | 287 |
| Lignes avec consommation | 163 |
| Lignes avec index de releve | 163 |
| Lignes avec prix ou forfait revise | 6 139 |
| Lignes avec prix de base | 4 721 |

### Repartition par marche

| Marche | Lignes | Factures | Montant HT |
|--------|--------|----------|------------|
| P1 | 2 296 | 213 | 1 065 574,49 EUR |
| P2 | 2 741 | 163 | 853 689,85 EUR |
| P3 | 1 313 | 99 | 438 415,93 EUR |
| R2 | 336 | 42 | 116 354,73 EUR |
| R1 | 126 | 42 | 36 904,89 EUR |
| Autres | 9 | 9 | 196 440,74 EUR |

Conclusion immediate : l'export ne doit pas etre importe sans filtre dans le registre CPE. Il contient bien les postes `P1/P2/P3`, mais aussi des lignes hors controle CPE cible (`R1`, `R2`, `Autres`).

---

## Contrats trouves

| Code contrat | Libelle principal | Lignes | Periode observee |
|--------------|-------------------|--------|------------------|
| `C00025811F` | SETE - BATIMENTS COMMUNAUX LOT 1 | 4 770 | 20/07/2022 au 31/12/2025 |
| `C00190116O` | SETE - BATIMENTS COMMUNAUX LOT 1 | 1 237 | 01/01/2025 au 31/03/2026 |
| `C00025812G` / `C00190155J` | BATIMENTS COMMUNAUX LOT 2 | 194 | Lot 2 |
| autres codes | Thalassothermie, piscine, sous-stations | 620 | Hors Lot 1 CPE |

Le meilleur candidat pour le CPE Lot 1 recent est `C00190116O` dans cet export :
- ses lignes visibles sur les periodes 2025 T4 et 2026 T1 portent des codes sites du referentiel actuel, par exemple `VDS-ENS 16`, `VDS-BAM 16`, `CCAS 08` ;
- 1 223 de ses 1 237 lignes contiennent un code site `VDS-*` ou `CCAS` ;
- 69 codes sites distincts sont detectes.

> Point a faire confirmer dans le controle metier : le code contrat DALKIA `C00190116O` doit etre rattache explicitement au marche CPE `24 BT 039` dans Po2 avant ingestion definitive.

### Ecart avec le referentiel CPE actuel

La comparaison avec les codes actuellement seedees dans `seed_cpe_sites.py` remonte :

| Situation | Codes |
|-----------|-------|
| Presents dans l'export, absents du seed | `CCAS 02`, `CCAS 03`, `CCAS 06`, `CCAS 10`, `VDS-CULT 03`, `VDS-CULT 04`, `VDS-CULT 06` |
| Presents dans le seed, absents de cet export | `CCAS 09`, `VDS-CULT 01`, `VDS-ENS 12.02` |

Ce n'est pas forcement une erreur de facture : cela peut venir du perimetre effectif apres OS/avenant, d'un site non facture sur la periode ou d'un referentiel encore incomplet. En revanche, l'import definitif doit remonter ces ecarts comme une file de reconciliation, pas les corriger silencieusement.

---

## Ce que le fichier permet de controler

### P1 - Fourniture gaz

L'export permet deja :
- reperer les lignes d'acompte, de decompte, d'ajustement et de refacturation ;
- distinguer les postes gaz principaux et les accessoires exposes dans le poste facture (`P1`, `ABT`, `CTA`, `TERME FIXE`, `STOCKAGE`, `LOCATION`, `CPB`, prestations ponctuelles) ;
- conserver les prix de base et prix revises exposes par DALKIA ;
- rattacher une grande partie des lignes recentes a un site CPE via le code `VDS-*` / `CCAS`.

Limite constatee au 22/05/2026 :
- pour le contrat recent `C00190116O`, les lignes visibles ne portent pas encore de consommation ; elles representent surtout acomptes, forfaits et refacturations ;
- le rapprochement avec GRDF ne peut donc pas etre fait avec cet export seul sur 2026 T1 ;
- le controle des volumes P1 devra utiliser GRDF puis etre recroise avec le decompte definitif DALKIA quand les quantites seront publiees.

### P2 - Exploitation et maintenance

L'export fournit les lignes P2 et les montants par periode. Il est adapte pour :
- controler la presence des acomptes attendus ;
- suivre les sous-postes exposes (`P2`, `P2-11`, `P2-12`, `P2-2`, `P2-4`, etc.) ;
- preparer le controle des formules de revision avec les indices contractuels.

Il ne prouve pas a lui seul la realisation des prestations ni les livrables attendus : ces preuves devront etre rattachees au controle P2.

### P3 - Garantie totale

L'export fournit les lignes P3 et les montants, avec une forte presence de `P3.4` dans le contrat recent.

Il peut alimenter :
- le suivi de facturation P3 ;
- le suivi du compte P3 et des travaux programmes ;
- la comparaison entre facturation, programme de travaux et pieces d'execution.

---

## Decisions d'integration Po2

### Tranche livree

Po2 expose maintenant :
- un **preview d'export finances DALKIA** depuis le cockpit `/cpe` ;
- un **import persiste** filtre sur le contrat CPE recent `C00190116O` et les marches `P1/P2/P3`.

Le preview permet :
- analyse du CSV sans persistance ;
- synthese des marches, contrats, factures et montants ;
- detection des codes sites CPE dans le detail de prestation ;
- signalement des lignes hors `P1/P2/P3` et des limites de donnees.

Endpoint : `POST /api/cpe/finances/preview`.

L'import persiste cree :
- un lot d'import deduplique par hash ;
- une facture DALKIA reconstituee depuis les lignes d'export ;
- les lignes DALKIA de detail conservees avec montant, poste, prix exposes, consommation/index si presents ;
- un statut de rapprochement initial vers le site CPE : `auto_matched`, `site_unknown` ou `site_code_missing`.

Endpoints :
- `GET/POST /api/cpe/finances/imports` ;
- `GET /api/cpe/finances/imports/{id}` ;
- `GET /api/cpe/finances/imports/{id}/lines`.

Dans `/cpe`, le lot selectionne ouvre deja le premier controle P1 : types de factures, acomptes `AC`, decomptes `DE`, postes accessoires P1 et niveau de preparation au rapprochement GRDF via les sites ayant un PCE.

### Modele cible recommande

L'ingestion definitive devra separer :

1. **Lot d'import** : fichier, hash, date, utilisateur et alertes.
2. **Facture DALKIA** : numero, type de facture, contrat, periode, destinataire, montant consolide.
3. **Ligne DALKIA** : marche, poste facture, service vendu, site brut, code site detecte, montant, prix de base, prix revise, consommation, index.
4. **Controle CPE** : poste `P1/P2/P3`, statut, ecarts, preuves, avoir ou penalite attendue.

Ne pas remplacer les factures PDF par cet export : le CSV sert de table de controle et de rapprochement, les justificatifs restent necessaires.

---

## Prochain ordre de developpement

1. Qualifier manuellement les codes inconnus et les lignes sans code site dans la file de reconciliation.
2. Construire le controle `P1` contradictoire :
   - rapprocher les volumes avec GRDF ;
   - verifier les prix gaz et les accessoires ;
   - qualifier les acomptes et le decompte definitif.
3. Ajouter ensuite les controles `P2` et `P3` avec calendrier contractuel, indices et preuves.
