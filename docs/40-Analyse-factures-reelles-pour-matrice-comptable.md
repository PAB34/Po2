# 40 - Analyse des factures réelles pour matrice comptable et contrôle

Date : 2026-06-25  
Objectif : analyser les fichiers factures réels fournis par Pascal avant de figer le workflow `Factures -> contrôle -> matrice comptable -> décision -> export finance`.

Fichiers analysés :

- DALKIA : `saas/energie/DALKIA/FACTURES/export_finances-20260604_0502.xlsx`
- ENGIE : `saas/energie/ENGIE/FACTURES/MesFactures_20260609132103.xlsx`
- EDF : `saas/energie/EDF/20260612_141002814868_EDF160626.csv`
- TotalEnergies : `saas/energie/TOTAL ENERGY/FACTURES.xlsx`

Fichiers complémentaires consultés :

- matrice bêta DALKIA : `saas/energie/DALKIA/COMPTABILITE/analyse_codification_dalkia_enrichie_par_code_contrat (1).xlsx`
- rapports ENGIE déjà présents :
  - `saas/energie/ENGIE/RAPPORTS/audit_filtres_factures_2026.md`
  - `saas/energie/ENGIE/RAPPORTS/rapport_ecarts_tarification_bpu_2026.md`

Exports d'analyse générés :

- `outputs/factures_matrice_analysis/dalkia_matrix_coverage.json`
- `outputs/factures_matrice_analysis/dalkia_coverage_by_poste.csv`
- `outputs/factures_matrice_analysis/dalkia_invoice_risks.csv`
- `outputs/factures_matrice_analysis/engie_summary.json`
- `outputs/factures_matrice_analysis/edf_summary.json`
- `outputs/factures_matrice_analysis/totalenergies_summary.json`

---

## 1. Conclusion courte

Les factures confirment que la matrice comptable ne doit pas être une simple table `fournisseur -> nature`.

Elle doit être structurée au minimum par :

1. fournisseur ;
2. contrat / code contrat / lot ;
3. poste facturé ;
4. service vendu ou composante de facture ;
5. site / compteur quand nécessaire ;
6. période facturée ;
7. statut de règle : cohérent, à valider, à ventiler, à arbitrer, en attente fournisseur.

Le cas DALKIA est le plus déterminant : la matrice bêta couvre déjà la majorité des lignes, mais les lignes non couvertes et les lignes à arbitrer portent des montants significatifs.

---

## 2. DALKIA - export finance

### 2.1 Volumétrie

| Indicateur | Valeur |
|---|---:|
| Lignes finance | 4 941 |
| Factures distinctes | 353 |
| Contrats présents | 4 |
| Montant total HT | 1 226 674,78 € |

Contrats présents dans l'export :

| Code contrat | Lignes |
|---|---:|
| C00025811F | 3 532 |
| C00190116O | 1 237 |
| C00025812G | 148 |
| C00190155J | 24 |

La matrice bêta contient 7 codes contrats, mais cet export finance n'en mobilise que 4.

### 2.2 Croisement avec la matrice bêta DALKIA

| Statut après croisement | Lignes | Montant HT |
|---|---:|---:|
| Cohérent | 4 512 | 765 054,75 € |
| Non couvert par la matrice bêta | 106 | 45 608,47 € |
| À ventiler | 154 | 121 804,71 € |
| À arbitrer comptabilité | 61 | 294 206,85 € |
| En attente DALKIA - fournir n° facture | 108 | 0,00 € |

Lecture :

- 4 835 lignes sur 4 941 trouvent une règle dans la matrice bêta.
- Les 106 lignes non couvertes ne sont pas marginales : 45,6 k€ HT.
- Le plus gros enjeu financier est `P3.4 / WORKS` : 294,2 k€ HT à arbitrer.
- Les lignes `PREST PONC` sont nombreuses mais à 0 € dans cet export ; elles restent importantes car elles matérialisent une demande fournisseur à gérer.

### 2.3 Principaux trous de matrice DALKIA

| Contrat | Poste | Service vendu | Lignes | Factures | Montant HT | Lecture |
|---|---|---|---:|---:|---:|---|
| C00025812G | P2-11 | MAINTENANCE | 24 | 6 | 21 339,24 € | Règle probablement à créer/dupliquer depuis ancien lot 1 |
| C00025812G | P1 | REFACTURATION TICGN | 2 | 1 | 12 838,05 € | Cas gaz/taxe à cadrer |
| C00025812G | P3-11 | MAINTENANCE | 18 | 6 | 11 550,98 € | Règle probablement à créer |
| C00025812G | P1 | CHAUFFAGE | 1 | 1 | -9 505,53 € | Avoir/régularisation à analyser |
| C00025811F | BT41 | CHAUFFAGE | 1 | 1 | -7 265,94 € | Poste absent de la matrice |
| C00025812G | P1 | REFACT PART FIXE ACHEMINEMENT | 2 | 1 | 6 490,59 € | À mapper avec les autres refacturations gaz |
| C00025812G | P2-2 | MAINTENANCE | 18 | 6 | 3 485,24 € | Règle manquante |
| C00025812G | R2 | PART FIXE P2 | 5 | 5 | 3 143,19 € | Poste hors P1/P2/P3 classique |

### 2.4 Factures DALKIA à risque

Le fichier `outputs/factures_matrice_analysis/dalkia_invoice_risks.csv` liste les 353 factures une par une avec :

- numéro de facture ;
- niveau de risque ;
- montant HT ;
- contrats ;
- marchés ;
- périodes ;
- statuts issus du croisement matrice ;
- postes présents.

Synthèse actuelle :

| Risque | Factures |
|---|---:|
| `blocked` | 27 |
| `ok` | 326 |

Le statut `blocked` correspond à au moins un des cas suivants :

- ligne non couverte par la matrice ;
- ligne `P3.4 / WORKS` à arbitrer ;
- ligne en attente DALKIA ;
- mélange qui empêche une validation silencieuse.

### 2.5 Impact direct sur la future matrice

La matrice DALKIA cible doit gérer :

- une règle par `code contrat + poste facturé`, avec normalisation des variantes (`P2.12` vs `P2-12`) ;
- un niveau complémentaire `service vendu`, car certains postes ne suffisent pas ;
- un statut de règle ;
- une action attendue ;
- une alerte/question restante ;
- une validation comptable ;
- la distinction facture / avoir / régularisation ;
- la période facturée, notamment les factures 2026 portant sur des périodes antérieures.

Décision forte proposée : aucune facture DALKIA ne doit être validée automatiquement si elle contient une ligne `NON_COUVERT`, `À arbitrer comptabilité`, `À ventiler` non résolue ou `En attente DALKIA`.

---

## 3. ENGIE - export Mes Factures

### 3.1 Volumétrie

| Indicateur | Valeur |
|---|---:|
| Bordereaux / factures | 185 |
| Lignes site/FIC | 1 267 |
| Montant total TTC | 882 841,41 € |

Répartition par mois de facture :

| Mois | Factures |
|---|---:|
| 2026-03 | 52 |
| 2026-04 | 46 |
| 2026-05 | 46 |
| 2026-06 | 41 |

Répartition par segment :

| Segment | Lignes site |
|---|---:|
| C5 | 931 |
| C4 | 281 |
| C2 | 55 |

### 3.2 Composantes reconnues par le parser existant

Le parseur `app/services/invoice_parsers/engie_xlsx.py` sait déjà reconstruire les lignes :

| Composante | Occurrences |
|---|---:|
| network_variable | 2 632 |
| supply | 2 630 |
| capacity | 1 340 |
| network_management | 1 264 |
| network_counting | 1 264 |
| network_withdrawal | 1 264 |
| network_fixed_total | 1 264 |
| cspe | 1 264 |
| cta | 1 264 |
| cee | 1 050 |
| green_energy | 1 039 |
| network_overrun | 25 |
| network_overrun_quadratic | 10 |

### 3.3 Développements déjà présents

Déjà développé :

- parser ENGIE XLSX multi-feuilles ;
- regroupement par bordereau ;
- reconstitution des lignes facture ;
- contrôles BPU ;
- contrôles TURPE ;
- rapprochement partiel ENEDIS / périodes / puissance ;
- rapports locaux déjà produits sur un export précédent.

Rapports existants :

- l'audit des filtres ENGIE signale que les filtres actuels sont insuffisants sans PRM, site, mois, segment et tarif ;
- le rapport BPU 2026 indique 13 écarts potentiels sur l'ancien export, essentiellement des effets d'arrondi ou petites consommations.

### 3.4 Impact matrice comptable

ENGIE peut être traité via une matrice de composants plutôt stable :

- fourniture électricité ;
- capacité ;
- CEE ;
- garantie origine / électricité verte ;
- acheminement / TURPE ;
- CTA ;
- CSPE / accise ;
- dépassement puissance.

Mais la ventilation analytique doit venir du PRM/site ou du regroupement, pas seulement du poste facturé.

Décision UX : la facture ENGIE doit afficher une trace de contrôle ligne par ligne, puis une proposition d'imputation comptable issue de la matrice active.

---

## 4. EDF - export CSV

### 4.1 Volumétrie

| Indicateur | Valeur |
|---|---:|
| Factures | 81 |
| Lignes site | 489 |
| Montant total TTC | 161 894,44 € |

Répartition par mois :

| Mois | Factures |
|---|---:|
| 2026-01 | 23 |
| 2026-02 | 3 |
| 2026-03 | 24 |
| 2026-04 | 7 |
| 2026-05 | 6 |
| 2026-06 | 18 |

Répartition par segment :

| Segment | Lignes site |
|---|---:|
| C5 | 448 |
| C4 | 31 |
| C2 | 10 |

### 4.2 Composantes reconnues par le parser existant

Le parser `app/services/invoice_parsers/edf_csv.py` produit la même structure que le parser ENGIE.

Composantes principales :

| Composante | Occurrences |
|---|---:|
| supply | 425 |
| cspe | 424 |
| capacity | 420 |
| cee | 419 |
| subscription | 356 |
| cta | 350 |
| network_fixed_total | 347 |
| network_overrun | 37 |

### 4.3 Points de vigilance

Le fichier contient :

- 23 factures négatives ou assimilables à des avoirs/régularisations ;
- 22 factures avec période non renseignée après parsing ;
- des périodes anciennes, dont une facture de juin 2026 portant sur 2024.

Cela confirme que l'historique / réimport / avoirs ne doit pas être traité comme un détail secondaire.

### 4.4 Impact matrice comptable

EDF ressemble à ENGIE dans la structure comptable, mais avec un cas métier probablement différent : éclairage public et/ou postes spécifiques.

La matrice doit donc distinguer :

- fournisseur EDF ;
- lot/marché ;
- site ou code d'imputation ;
- composante de ligne ;
- facture positive vs avoir/régularisation ;
- période facturée.

---

## 5. TotalEnergies - gaz

### 5.1 Volumétrie

| Indicateur | Valeur |
|---|---:|
| Factures/lignes | 58 |
| Factures | 53 |
| Avoirs | 5 |
| Sites nommés | 8 |
| PCE distincts | 10 |
| Tarif acheminement | T2 uniquement |
| Total HT | 22 717,47 € |
| Total TTC | 27 260,98 € |
| Consommation nette | 257 418 kWh |

### 5.2 Cohérence structurelle

Contrôle local réalisé :

- somme des composantes HT = total HT ;
- total HT + TVA = total TTC.

Résultat : aucune anomalie structurelle détectée sur ces deux contrôles.

### 5.3 Décomposition HT

| Composante | Montant |
|---|---:|
| MONTANT CONSO GAZ | 10 187,16 € |
| ABONNEMENT FOURNISSEUR | 33,75 € |
| MONTANT CEE | 1 856,15 € |
| MONTANT CEE PRECARITE | 714,93 € |
| MONTANT CPB | 84,41 € |
| ATRT TERME FIXE | 1 118,66 € |
| ATRD TERME FIXE | 894,04 € |
| ATRD TERME VARIABLE | 3 109,61 € |
| MONTANT AUTRES | 383,82 € |
| MONTANT TICGN / ACCISE SUR GAZ | 4 113,60 € |
| MONTANT CTA | 221,34 € |

### 5.4 Points de vigilance

- 9 lignes ont une consommation ou un montant négatif : à considérer comme avoir/régularisation.
- 10 factures n'ont pas de `NOM SITE` renseigné, même si le PCE est présent.
- Le contrôle réglementaire gaz est déjà plus avancé côté backend que la matrice comptable.

### 5.5 Impact matrice comptable

La matrice gaz doit distinguer :

- PCE/site ;
- composante gaz ;
- facture vs avoir ;
- taxes / acheminement / fourniture ;
- période de consommation.

Le backend possède déjà un service `gas_invoice.py` et un extracteur de lignes synthétiques pour les matrices comptables. Ce fichier est donc prêt pour un raccord V1 assez propre.

---

## 6. Ce qui manque encore

Pas encore analysé faute de fichiers dans cette demande :

- SUEZ ;
- SPIE.

À prévoir :

- SUEZ doit probablement rejoindre `Fluides > Eau`, avec compteur / abonnement / consommation / assainissement / taxes ;
- SPIE ne doit pas être cloné sur DALKIA : il faut probablement un moteur maintenance/P2 plus simple, basé sur périmètre de sites, équipements et prestations.

---

## 7. Recommandations pour la suite

### 7.1 Avant de répondre au fichier de questions 39

Lire cette analyse et surtout les points DALKIA.

Les questions 12 à 17 du document `docs/Archives/39-Questions-avant-raccord-factures-matrices-V1.md` *(archivé)* restent pertinentes, mais il faut y répondre avec ces chiffres en tête :

- `P3.4 / WORKS` = 294,2 k€ HT ;
- `C00190116O / P2 à ventiler` = 118,6 k€ HT ;
- `C00025812G` contient plusieurs postes non couverts ;
- les avoirs/régularisations sont présents chez DALKIA, EDF et TotalEnergies.

### 7.2 Côté développement

Ordre recommandé :

1. importer la matrice DALKIA bêta en version brouillon ;
2. ajouter la normalisation des postes (`P2.12` = `P2-12`, `P3.4` = `P3-4`) ;
3. ajouter le statut de règle dans la matrice ;
4. bloquer ou mettre en revue les factures contenant `NON_COUVERT`, `À ventiler`, `À arbitrer`, `En attente fournisseur` ;
5. raccorder `/refonte-v1/factures` au cycle snapshot réel ;
6. ajouter une vue facture par facture avec détails des lignes non imputables.

### 7.3 Côté UX

La fiche facture doit montrer :

- synthèse facture ;
- source fournisseur ;
- contrat / marché ;
- période ;
- lignes de contrôle ;
- proposition comptable ;
- exceptions ;
- action attendue ;
- statut historique.

Il faut éviter un simple bouton `Valider` sans expliquer ce qui est validé.

