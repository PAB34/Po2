# 22 - Developpement a deux pistes et profils utilisateurs

> Date : 2026-06-22
> Decision proposee : poursuivre les capacites metier et construire l'experience utilisateur en parallele, avec une synchronisation obligatoire par tranches verticales.

## 1. Recommandation

Il ne faut ni arreter le developpement fonctionnel pour refaire tout le front, ni continuer a empiler les moteurs en reportant l'experience a plus tard.

Le modele recommande est un **developpement a deux pistes synchronisees** :

```text
Piste A - Capacites metier
modeles, imports, moteurs de calcul, controles, donnees, qualite, tests

Piste B - Experience produit
profils, parcours, architecture d'information, contrats d'ecran, design system, validation utilisateur

Point de rencontre obligatoire
tranche verticale utilisable et demonstrable avec donnees reelles
```

Les pistes avancent en parallele, mais aucune ne peut declarer une fonctionnalite terminee seule.

## 2. Pourquoi ce modele convient a Po2

- beaucoup de moteurs utiles existent deja ; les figer pendant une longue refonte serait une perte de rythme ;
- les besoins metier continuent d'etre decouverts en manipulant les contrats, factures et donnees reelles ;
- l'interface actuelle montre les limites de l'accumulation sans cadre commun ;
- une refonte concue sans les cas reels risquerait d'etre elegante mais inapte aux dossiers complexes ;
- le futur SaaS doit accueillir plusieurs profils alors que l'usage actuel est encore mono-utilisateur.

## 3. Regle d'entree de toute nouvelle fonctionnalite

Avant de coder, une fiche courte doit preciser :

1. le profil utilisateur principal ;
2. la situation de travail ;
3. la decision ou action attendue ;
4. les donnees, leur grain et leur qualite ;
5. la regle ou le calcul ;
6. la preuve a afficher ;
7. le parcours et l'ecran cible ;
8. les etats nominal, vide, incomplet, erreur et interdit ;
9. le composant reutilisable eventuel ;
10. le critere de validation metier.

Une capacite backend peut etre livree avant son ecran final, mais elle doit deja etre rattachee au registre canonique de [[21-Cartographie-fonctionnelle-vers-experience-utilisateur]].

## 4. Definition de termine partagee

Une tranche est terminee lorsque :

- moteur et regles testes ;
- source, fraicheur, qualite et limites visibles ;
- parcours utilisable par le profil cible ;
- preuves et drill-down disponibles ;
- etats de chargement, vide, incomplet et erreur traites ;
- permissions respectees ;
- design system reutilise ou enrichi proprement ;
- validation sur un cas reel ;
- documentation et cartographie mises a jour ;
- ancienne interface conservee/redirigee tant que la couverture n'est pas prouvee.

## 5. Profils utilisateurs proposes

Les profils decrivent des besoins et des vues par defaut. Ils ne doivent pas devenir immediatement des roles rigides : une meme personne peut cumuler plusieurs profils.

### P1 - Pilote maintenance & energie

**Profil principal actuel**, correspondant a l'usage de PAB34.

- supervise patrimoine, fluides, marches, maintenance, CVC, factures et travaux ;
- traite les anomalies et rapprochements ;
- controle ou prepare les decisions ;
- construit budget et atterrissages ;
- maintient certains referentiels.

Accueil : cockpit transversal avec files a traiter, trajectoires, couverture de maintenance et risques techniques.

Niveau : dense, operationnel, avec acces aux preuves et fonctions expertes contextuelles.

### P2 - Analyste energie

- suit ENEDIS, GRDF, eau, DJU et qualite des donnees ;
- analyse consommations, puissances, derives et previsions ;
- rapproche volumes distributeurs et factures ;
- produit l'atterrissage physique puis financier energie.

Accueil : couverture distributeurs, anomalies, consommations vs DJU, prevision annuelle, compteurs non rattaches.

Niveau : analytique ; graphiques temporels, hypotheses et exports.

### P3 - Responsable maintenance et patrimoine technique

- connait les equipements et leur etat ;
- verifie les perimetres DALKIA/SPIE et la couverture des sites ;
- suit obligations, interventions, contrats et echeances ;
- priorise le plan pluriannuel de travaux.

Accueil : sites non entretenus, equipements critiques, contrats a echeance, actions F-Gaz/ESP, besoin PPT.

Niveau : portefeuille puis drill-down Site -> Batiment -> Local -> Equipement.

### P4 - Controleur de gestion / finances

- suit budget initial, revisions, engagements, factures, mandats et atterrissage ;
- verifie la ventilation selon la matrice comptable ;
- consulte les decisions et justificatifs ;
- exporte ou integre les fiches de liaison.

Accueil : budget/realise/atterrissage, factures en attente, ecarts par nature/service/marche, transmissions.

Niveau : financier, sans imposer le detail technique sauf lorsqu'il explique un ecart.

### P5 - Direction / decideur

- arbitre les risques, budgets, travaux et litiges significatifs ;
- demande une explication fiable sans traiter les donnees ;
- compare trajectoire, cible et atterrissage.

Accueil : cinq preuves direction, tendances, risques prioritaires, decisions attendues.

Niveau : synthetique et principalement lecture seule, avec drill-down narratif vers les preuves.

### P6 - Gestionnaire patrimoine / referent de site

- consulte et corrige les informations d'un perimetre patrimonial ;
- confirme occupation, equipements, compteurs et responsables ;
- signale une anomalie, un changement d'usage ou un besoin d'intervention.

Accueil : ses sites, demandes a confirmer, donnees manquantes et actions ouvertes.

Niveau : simple, contextualise, eventuellement limite a certains sites.

### P7 - Administrateur fonctionnel

- gere utilisateurs, villes, imports, connecteurs, referentiels et diagnostics ;
- corrige les mappings et surveille les traitements ;
- ne porte pas les decisions metier a la place des profils operationnels.

Accueil : qualite des donnees, imports, connecteurs, erreurs et configurations.

Niveau : expert, separe des parcours quotidiens.

### P8 - Prestataire externe - futur

- DALKIA, SPIE ou autre titulaire ;
- depose facture, devis ou justificatif ;
- repond a une demande ;
- consulte uniquement son perimetre et la decision partageable.

Ce profil doit rester futur tant que cloisonnement, securite, workflow contradictoire et gouvernance documentaire ne sont pas cadres.

## 6. Profils, droits et personnalisation

Il faut distinguer trois notions :

| Notion | Role |
|---|---|
| Profil d'usage | determine accueil, raccourcis, vocabulaire et densite |
| Permission | autorise lire, modifier, decider, exporter, administrer |
| Perimetre | limite aux villes, services, marches ou sites concernes |

Un utilisateur peut cumuler P1 + P2 + P3, tout en ayant la permission de preparer une decision sans etre l'approbateur final.

A court terme, avec un utilisateur principal : conserver tous les acces, mais permettre de previsualiser les vues Direction, Energie, Maintenance et Finance. Cela prepare le multi-utilisateur sans ralentir l'usage actuel.

## 7. Navigation commune, accueils differents

Les profils ne doivent pas produire huit applications distinctes. La navigation reste commune :

```text
Tableau de bord
Patrimoine
Fluides & consommations
Marches & contrats
Technique
Administration
```

Ce qui varie :

- l'accueil et les KPI prioritaires ;
- l'ordre des files a traiter ;
- les actions disponibles ;
- la densite et les panneaux experts ;
- le perimetre de donnees.

Les objets et ecrans restent partageables par URL afin qu'un responsable energie puisse envoyer une facture ou un site precis a la finance ou a la direction.

## 8. Organisation des chantiers

### Flux continu

- **Discovery UX** : toujours un parcours d'avance ; profils, story map, contrat d'ecran et prototype.
- **Delivery metier** : implemente la tranche courante, backend et frontend utile.
- **Consolidation** : une capacite reservee a la dette, aux composants communs et a la migration.

Repartition indicative dans la phase actuelle :

- 60 % tranches metier prioritaires ;
- 25 % experience/design system au contact de ces tranches ;
- 15 % consolidation, tests et suppression prudente de dette.

Ce ratio est un garde-fou, pas une comptabilite rigide.

### Rythme recommande

1. choisir une tranche direction P0 ;
2. produire son contrat d'ecran et ses cas reels ;
3. developper moteur et experience ensemble ;
4. demonstrer aux profils concernes ;
5. enrichir le design system avec les composants prouves ;
6. mettre a jour le registre de couverture ;
7. ne lancer la tranche suivante qu'avec les ecarts critiques classes.

## 9. Tranches verticales recommandees

1. **Socle factures de fourniture** : dossier commun marche/version -> perimetre -> controle -> decision -> ventilation -> export, avec moteurs propres a chaque fournisseur.
2. **ENGIE electricite batiments** : factures/avoirs -> PRM -> BPU/TURPE/ENEDIS -> decision -> export.
3. **EDF electricite** : eclairage public et autres perimetres EDF -> points de livraison -> BPU/TURPE/ENEDIS -> decision -> export, sans supposer que les regles ENGIE sont identiques.
4. **TotalEnergies gaz** : facture -> PCE -> BPU/PEG -> ATRD/ATRT -> taxes/CEE -> GRDF -> decision -> export.
5. **ENEDIS + GRDF + DJU** : historique distributeurs -> comparaison -> derive -> atterrissage kWh -> conversion en euros par fournisseur et periode contractuelle.
6. **DALKIA** : contrat/version -> P1/P2/P3 -> controle -> atterrissage -> decision.
7. **Couverture maintenance** : contrat DALKIA/SPIE -> patrimoine/equipements -> sites non couverts.
8. **CVC/PPT** : inventaire -> criticite -> action -> cout -> arbitrage annuel.
9. **Budget global** : budget -> engage -> facture -> mandate -> atterrissage multi-marches et multi-fournisseurs.

Chaque tranche enrichit le meme shell et le meme design system.

## 10. Garde-fous contre les deux derives

### Derive « fonctionnalites d'abord »

- aucune nouvelle capacite sans profil, decision et ecran cible ;
- pas de nouveau monolithe React ou service sans frontiere ;
- toute valeur calculee doit exposer source et preuve.

### Derive « design d'abord »

- aucun composant abstrait sans au moins deux usages identifies, sauf fondation evidente ;
- prototypes testes avec donnees reelles, longues valeurs et erreurs ;
- ne pas bloquer un moteur critique en attendant une perfection visuelle globale.

## 11. Decision proposee

Continuer le developpement fonctionnel, oui, mais en changeant la definition de progression :

```text
Une fonctionnalite n'est plus seulement du code qui sait faire.
C'est une capacite rattachee a un profil, une decision, une preuve et un parcours cible.
```

Le prochain pas recommande est de definir le contrat d'ecran du socle de fourniture pour ENGIE, EDF et TotalEnergies, puis de traiter une tranche fournisseur complete. La tranche ENEDIS/GRDF/DJU vient relier les volumes physiques aux memes fournisseurs et aux atterrissages.
