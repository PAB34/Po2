# 21 - Cartographie fonctionnelle vers une experience utilisateur reussie

> Date : 2026-06-22
> Objet : transformer toutes les fonctionnalites developpees en parcours coherents et definir la methode de construction du design system.

## 1. Etat reel de la refonte

### Ce qui a commence

- navigation par domaines dans `App.tsx` ;
- shell, topbar, sous-navigation et routes conteneurs ;
- premiers parcours regroupes, notamment `Factures marche` ;
- atelier de cartographie HTML et registre de raccordement ;
- theme sombre et premiers patterns de cartes, badges, tableaux et boutons.

### Ce qui n'a pas encore reellement commence

Le **design system au sens strict** n'est pas construit :

- pas de dossier ou package de composants fondateurs ;
- pas de tokens complets et semantiques pour couleurs, espaces, typographie, rayons, elevations et mouvements ;
- pas de catalogue vivant des composants et de leurs etats ;
- pas de conventions partagees pour les statuts metier ;
- pas de tests visuels, d'accessibilite ou de non-regression ;
- `styles.css` reste monolithique et plusieurs pages recreent leurs propres patterns.

Verdict : **la refonte de navigation a commence ; le design system est seulement esquisse**.

## 2. Pourquoi l'inventaire endpoints ne suffit pas

Un endpoint est une capacite technique, pas une fonctionnalite utilisateur. Un ecran construit directement depuis la liste des endpoints reproduit la structure du backend et produit une interface morcelee.

La cartographie canonique doit suivre cette chaine :

```text
Capacite technique
-> donnee metier et qualite
-> regle/calcul
-> situation utilisateur
-> decision attendue
-> preuve necessaire
-> parcours
-> ecran
-> composant
-> mesure de succes
```

Exemple :

```text
ENEDIS fournit des kWh mensuels
-> rattaches a un PRM et un site, couverture connue
-> normalises par les DJU
-> derive ou trajectoire anormale
-> analyser / corriger / prevoir
-> serie source + DJU + hypothese
-> Fluides > Electricite > Performance
-> courbe, ecart, projection, drill-down
-> decision comprise en moins de 30 secondes
```

## 3. Registre fonctionnel canonique

Chaque fonctionnalite developpee doit avoir une ligne avec les champs suivants :

| Champ | Question |
|---|---|
| ID capacite | Quel identifiant durable permet de la suivre ? |
| Domaine | Patrimoine, Fluides, Marches, Technique, Finance, Administration ? |
| Utilisateur | Qui l'utilise reellement ? |
| Situation | A quel moment de son travail ? |
| Decision | Que doit-il decider, corriger ou transmettre ? |
| Donnees | Quelles sources, quel grain, quelle periode ? |
| Regles | Quels calculs, tolerances ou obligations ? |
| Qualite | Fraicheur, completude, confiance, rattachement ? |
| Preuve | Qu'est-ce qui rend le resultat defendable ? |
| Capacites existantes | Services, endpoints, modeles et pages reutilisables ? |
| Ecran cible | Dans quel parcours la fonctionnalite apparait-elle ? |
| Exposition | Quotidien, direction, expert, administration, cache ? |
| Action refonte | Brancher, refondre, fusionner, completer, cacher, retirer ? |
| Statut validation | Inventorie, service teste, endpoint teste, front valide, metier valide ? |
| KPI de succes | Comment sait-on que l'experience aide vraiment ? |

La source technique reste [[13-Matrice-routes-fonctionnalites-refonte-api]]. La source metier devient ce registre, enrichi depuis [[14-Catalogue-fonctionnalites-commentees-et-reaffectation]] et [[18-Registre-raccordement-frontend]].

## 4. Cartographier par objets et evenements

Les domaines ne suffisent pas : l'experience doit etre construite autour d'objets stables et d'evenements.

### Objets stables

- Site, Batiment, Local ;
- PRM, PCE, compteur eau ;
- contrat, marche, lot, version contractuelle ;
- facture, avoir, engagement, budget ;
- equipement, famille, action de maintenance, action PPT ;
- serie de consommation, DJU, prevision ;
- preuve documentaire, decision, export.

### Evenements

- facture recue ou corrigee ;
- donnee distributeur publiee ou manquante ;
- contrat/avenant prenant effet ;
- derive de consommation detectee ;
- prevision depassant budget ou cible ;
- equipement devenant critique ;
- contrat arrivant a echeance ;
- site ou equipement sans couverture ;
- decision transmise aux finances.

Le cockpit doit surtout afficher les evenements demandant une action, pas une collection de statistiques passives.

## 5. Les parcours de niveau 1

| Parcours | Question utilisateur | Sortie attendue |
|---|---|---|
| Controler une facture | Est-elle payable au regard du contrat ? | decision, justification, export finance |
| Piloter le budget | Ou en sommes-nous et ou allons-nous finir ? | realise, engage, atterrissage, ecart |
| Piloter les consommations | Comment evoluent-elles et que prevoit-on ? | serie, DJU, derive, prevision kWh et euros |
| Programmer le CVC | Que faut-il remplacer et quand ? | criticite et PPT chiffre |
| Verifier la maintenance | Quels sites/equipements ne sont pas couverts ? | matrice de couverture et actions |
| Fiabiliser le patrimoine | Quelles donnees ne sont pas rattachees ? | file de rapprochement et qualite |

Chaque fonctionnalite doit servir au moins un parcours. Sinon elle reste experte, cachee, ou candidate au retrait.

## 6. DJU : capacite transversale

Les DJU ne doivent pas etre enfermes dans une page Energie. Ils fournissent un contexte commun a :

- comparaison temporelle des consommations ;
- normalisation climatique et detection de derive ;
- atterrissage annuel de consommation ;
- CPE DALKIA, cibles et interessement ;
- diagnostic CVC et effet des travaux ;
- explication direction des ecarts physiques et financiers.

Le service DJU doit exposer source, station, periode, couverture, valeur reelle, normale de reference et methode. Les ecrans consommateurs reutilisent la meme definition et signalent les donnees manquantes.

## 7. Atterrissage de consommation et passage aux euros

Il faut separer puis relier deux previsions :

```text
Atterrissage physique = consommation reelle connue
+ consommation restante prevue selon saison, DJU, tendance et perimetre

Atterrissage financier = volumes physiques prevus
x prix contractuels applicables
+ acheminement, taxes, capacite, CEE, termes fixes
+ engagements non lies aux volumes
```

### V1 explicable

Pour chaque PRM/PCE/site :

1. mesurer la couverture ENEDIS/GRDF et choisir la date d'arret ;
2. sommer le reel connu ;
3. calculer une intensite `kWh/DJU` sur une periode de reference comparable ;
4. projeter les DJU restants avec une normale ou un scenario ;
5. distinguer usages thermosensibles et non thermosensibles lorsque les donnees le permettent ;
6. appliquer les prix/version contractuelle correspondant aux periodes projetees ;
7. ajouter les composantes fixes/reglementees sans les multiplier par les kWh ;
8. afficher scenarios bas/central/haut, hypotheses et confiance.

La facture sert a convertir et reconcilier, mais la source prioritaire des volumes reste le distributeur. Les volumes factures servent aussi de controle de couverture et de coherences.

## 8. Architecture d'information cible

```text
Tableau de bord
  Files a traiter
  Trajectoires direction

Patrimoine
  Sites / Batiments / Locaux
  Rattachements et qualite

Fluides & consommations
  Portefeuille
  Electricite ENEDIS
  Gaz GRDF
  Performance & DJU
  Atterrissage consommations
  Donnees distributeurs (expert)

Marches & contrats
  Factures marche
  Budget & atterrissage financier
  DALKIA
  SPIE
  Couverture maintenance

Technique
  Inventaire CVC
  Criticite
  PPT
  F-Gaz / ESP

Administration
  Imports, referentiels, contrats, connecteurs, diagnostics
```

Les liens transversaux restent visibles : depuis un site, aller aux consommations, factures, contrats et equipements ; depuis une facture ou une anomalie, revenir au site et aux preuves.

## 9. Design system oriente decisions

### Fondations

- tokens semantiques : surfaces, textes, bordures, action, succes, vigilance, blocage, information ;
- typographie et densite adaptees aux tableaux metier ;
- grille, espaces, rayons, elevations et breakpoints ;
- icones limitees et coherentes ;
- mouvement discret uniquement pour expliquer un changement d'etat.

### Composants indispensables

- `PageHeader`, filtres globaux et fil d'Ariane ;
- `KpiCard` avec valeur, contexte, tendance, confiance et action ;
- `StatusBadge` fonde sur un dictionnaire metier unique ;
- `WorkQueue` pour les files a traiter ;
- `DecisionPanel` avec preuve, motif et historique ;
- `DataTable` dense avec filtres, colonnes, export et drill-down ;
- `TimeSeriesChart` avec reel, reference, DJU, prevision et annotations ;
- `CoverageMatrix` pour maintenance et qualite ;
- `EvidenceDrawer` pour sources, documents et limites ;
- etats chargement, vide, donnees partielles, erreur et acces refuse.

### Criteres UX

- l'objet, le risque et l'action attendue sont compris en moins de 30 secondes ;
- tout KPI critique permet de remonter a ses lignes sources ;
- aucune couleur n'est la seule porteuse d'information ;
- les hypotheses et limites sont visibles sans jargon inutile ;
- les filtres de periode, patrimoine et perimetre ont le meme comportement partout ;
- les actions destructrices ou engageantes demandent confirmation et conservent une trace.

## 10. Methode de realisation

### Etape 1 - Inventaire consolide

Fusionner les documents 08, 13, 14 et 18 dans un registre exploitable. Detecter doublons, capacites sans ecran, ecrans sans preuve et regles presentes seulement dans React.

### Etape 2 - Story mapping

Pour chaque parcours de niveau 1, ordonner les activites utilisateur et les fonctionnalites necessaires. Definir un parcours nominal, les erreurs et les cas incomplets.

### Etape 3 - Contrats d'ecran

Avant le visuel, documenter pour chaque ecran : utilisateur, question, donnees, actions, preuves, etats, permissions, performance et critere de fini.

### Etape 4 - Prototype avec donnees reelles

Prototyper un parcours vertical avec des cas reels, y compris anomalies et donnees manquantes. ENGIE est le bon premier parcours ; l'atterrissage ENEDIS/DJU est le suivant.

### Etape 5 - Design system minimum

Extraire les composants repetes du premier parcours, documenter leurs variantes et les reutiliser dans le deuxieme. Ne pas construire une bibliotheque abstraite avant les usages reels.

### Etape 6 - Validation metier

Faire tester chaque parcours sur des taches concretes : trouver une facture bloquee, expliquer un ecart, identifier un site non entretenu, lire une prevision. Mesurer erreurs, temps et incomprehensions.

### Etape 7 - Migration et nettoyage

Brancher, rediriger, mesurer puis retirer seulement apres preuve que toutes les capacites utiles sont couvertes.

## 11. Definition de reussite globale

La refonte est reussie lorsque :

- toutes les capacites utiles sont rattachees a un parcours, une decision et une preuve ;
- aucune fonctionnalite critique n'est perdue dans la migration ;
- la direction lit trajectoires, risques et montants sans connaitre les noms techniques du code ;
- les agents metier traitent leurs files sans exporter pour comprendre ;
- l'interface reste coherente quand de nouveaux marches, fluides ou obligations sont ajoutes ;
- le code frontend n'accumule plus de nouvelles pages monolithiques.

## 12. Articulation avec les profils et le developpement

Le registre canonique doit porter un profil principal et les profils secondaires de chaque capacite. Les capacites metier et l'UX progressent en parallele mais se rejoignent dans chaque tranche verticale. Voir [[22-Developpement-deux-pistes-et-profils-utilisateurs]].

## 13. Source de verite operationnelle

La methode de ce document est instanciee dans [[24-Cockpit-canonique-reconstruction-produit-frontend]]. Le cockpit 24 devient le registre a maintenir ; ce document 21 reste la reference methodologique.
