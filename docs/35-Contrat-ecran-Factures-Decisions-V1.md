# 35 — Contrat d’écran Factures & décisions V1

> Date : 2026-06-24  
> Statut : proposition V1 intégrée au prototype  
> Périmètre : import, contrôle contractuel, imputation comptable, décision et transmission aux finances

## 1. Décision structurante

La matrice comptable appartient au **contrat ou au lot dans une version datée**. Une facture et ses lignes héritent de la version active au moment du traitement. La facture conserve ensuite un instantané de l’imputation appliquée afin qu’une modification future de la matrice ne réécrive jamais l’historique.

La matrice n’est donc pas ressaisie facture par facture. La comptabilité :

- maintient et valide les versions contractuelles ;
- traite les règles manquantes ou ambiguës ;
- corrige exceptionnellement une imputation de facture avec motif ;
- valide l’instantané transmis aux finances.

Le classeur XLSX est un outil d’échange et de travail en masse. La plateforme reste la source de vérité.

## 2. Chaîne fonctionnelle

1. **Importer** un lot fournisseur, y compris une année complète.
2. **Dédoublonner** avec une clé stable et reconnaître nouvelles, connues ou révisées.
3. **Parser** en-tête, périodes, sites/compteurs et lignes de facturation.
4. **Associer** chaque facture au contrat, lot et version applicables.
5. **Contrôler** prix, quantités, taxes, acheminement et cohérences.
6. **Appliquer** la matrice comptable aux lignes parsées.
7. **Résoudre** les règles manquantes, ambiguës ou ventilées.
8. **Décider** conformité/paiement puis produire l’export de transmission.

Une facture connue et close réimportée n’est pas retraitée silencieusement. Elle est classée `inchangée`, `révisée` ou `doublon`, avec un rapport de lot.

## 3. Objets métier

### Version de matrice contractuelle

- contrat, marché et lot ;
- fournisseur ;
- numéro de version ;
- dates d’effet ;
- statut `brouillon`, `à valider`, `active`, `archivée` ;
- auteur, validateur et historique.

### Règle comptable

Une règle relie une composante parsée et un périmètre aux axes comptables :

| Entrée de règle | Sortie comptable |
|---|---|
| Fournisseur, contrat, lot, composante | Service |
| Site, bâtiment, compteur ou famille | Fonction |
| Période ou date d’effet | Nature |
| Poste P1/P2/P3, fourniture, acheminement, taxe | Numéro d’opération |
| Condition ou clé de ventilation | Antenne et pourcentage |

Les axes retenus pour la V1 sont : **service, fonction, nature, numéro d’opération et antenne**. Le marché/lot, le site et la composante restent des axes de justification et de rapprochement.

### Instantané d’imputation de facture

L’instantané contient la version de matrice utilisée, les règles appliquées, les valeurs produites, les corrections manuelles, les motifs et l’identité du validateur. Il est immuable après transmission, sauf réouverture tracée.

## 4. Écrans V1

### F01 — Lot d’import

Affiche les étapes : import, dédoublonnage, parsing, association contractuelle, imputation, décision/export. Pour chaque étape : total, réussites, exceptions et rapport téléchargeable.

### F02 — File Factures & décisions

Colonnes minimales : fournisseur/facture, site, marché, montant, date, état de matrice, état de contrôle, décision et action.

États de matrice :

- `Validée` : instantané comptable validé ;
- `Proposée` : imputation automatique complète à confirmer ;
- `À compléter` : règle ou axe manquant ;
- `À arbitrer` : plusieurs règles possibles ;
- `Non applicable` : document sans écriture attendue.

### F03 — Matrices comptables par contrat

Chaque carte contrat présente version active, couverture automatique, nombre de règles et exceptions. L’éditeur permet le travail en masse par composante et périmètre, sans mélanger les contrats.

### F04 — Imputation d’une facture

La fiche facture présente :

- lignes parsées et montants ;
- contrat et version associés ;
- imputation proposée par ligne ;
- origine de chaque règle ;
- ventilation et contrôle du total à 100 % ;
- correction avec motif ;
- validation comptable.

### F05 — Aperçu de réimport XLSX

Avant toute écriture, l’écran classe les lignes :

- ajout ;
- modification ;
- inchangée ;
- introuvable ;
- conflit de version ;
- erreur bloquante.

La validation crée un **nouveau brouillon de version**. Elle ne modifie jamais directement la version active.

## 5. Aller-retour XLSX

### Colonnes stables minimales

| Colonne | Rôle |
|---|---|
| `contract_id` | Identifiant technique du contrat |
| `contract_version_id` | Version contractuelle visée |
| `matrix_version` | Version lisible de la matrice |
| `rule_id` | Identifiant stable de règle |
| `effective_from` / `effective_to` | Période d’application |
| `supplier`, `market`, `lot` | Contexte lisible |
| `component_code` / `component_label` | Élément de facturation parsé |
| `site_ref` / `meter_ref` | Périmètre éventuel |
| `service`, `function`, `nature` | Axes comptables |
| `operation`, `antenna` | Pilotage et drill-down |
| `allocation_percent` | Ventilation |
| `comment` | Motif ou précision métier |

### Contrôles bloquants

- identifiants techniques présents ;
- version exportée encore compatible ;
- dates d’effet cohérentes ;
- axes obligatoires renseignés ;
- somme des ventilations égale à 100 % ;
- absence de doublon de règle ;
- référentiels service/fonction/nature/opération/antenne valides ;
- aucune suppression implicite d’une règle absente du classeur.

## 6. Gouvernance et droits

| Action | Comptabilité | Responsable marché | Administrateur |
|---|---:|---:|---:|
| Lire matrices et imputations | Oui | Oui | Oui |
| Modifier un brouillon | Oui | Proposition | Oui |
| Importer/exporter XLSX | Oui | Lecture/export | Oui |
| Activer une version | Oui selon droit | Validation métier | Oui |
| Corriger une facture | Oui avec motif | Proposition | Oui |
| Réouvrir après transmission | Droit renforcé | Non | Oui |

## 7. Règles UX

- afficher la règle appliquée et sa provenance, pas seulement le résultat ;
- conserver la facture dans son contexte pendant l’édition ;
- permettre l’édition en masse sans masquer les exceptions ;
- distinguer clairement matrice contractuelle et correction ponctuelle ;
- ne jamais présenter un code simulé comme validé ;
- rendre visibles couverture, version et date d’effet ;
- réserver la couleur rouge aux blocages réels.

## 8. Critères d’acceptation

1. Une facture importée retrouve son contrat et la version de matrice applicable.
2. Une facture déjà close peut être réimportée sans perdre décision ni historique.
3. Chaque ligne comptable est traçable jusqu’à la ligne de facturation et la règle.
4. Une ventilation incomplète ou différente de 100 % bloque la validation.
5. Une modification de matrice ne change pas les factures déjà transmises.
6. Le réimport XLSX présente un différentiel avant création du brouillon.
7. Les règles manquantes sont regroupées pour correction en masse.
8. L’export de transmission utilise uniquement des imputations validées.
9. Les valeurs du prototype restent explicitement simulées jusqu’à validation comptable.

## 9. Ordre de raccordement

1. figer le schéma de version/règle/instantané ;
2. mapper les matrices et exports existants par contrat ;
3. raccorder ENGIE puis EDF et TotalEnergies ;
4. traiter DALKIA séparément par P1/P2/P3 ;
5. implémenter export XLSX ;
6. implémenter réimport avec aperçu des différences ;
7. valider sur un lot réel anonymisé avec la comptabilité.
