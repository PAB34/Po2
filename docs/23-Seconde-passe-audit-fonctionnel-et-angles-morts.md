# 23 - Seconde passe d'audit fonctionnel et angles morts

> Date : 2026-06-22
> Methode : comparaison du code reel, des routes, services, modeles, pages React et migrations avec les cadrages 20, 21 et 22.

## 1. Perimetre controle

Photo du depot lors de la passe :

- 19 fichiers de routes et environ 295 declarations d'endpoints ;
- 52 fichiers de services metier/techniques ;
- 21 fichiers de modeles ;
- 60 migrations Alembic, jusqu'aux tarifs reseau gaz ATRD7 ;
- 29 pages React et 11 composants metier partages ;
- inventaires documentaires 08/14/18, puis cadrages 20/21/22.

Cette mesure ne signifie pas que 295 fonctionnalites sont utilisables : certains endpoints sont du CRUD, de l'administration, des variantes techniques ou des capacites sans parcours valide.

## 2. Conclusion generale

Les cinq axes direction restent corrects :

1. controle contractuel des factures ;
2. budget, realise et atterrissage financier ;
3. consommations ENEDIS/GRDF, DJU et atterrissage physique/financier ;
4. etat CVC et plan pluriannuel de travaux ;
5. couverture et pilotage des marches de maintenance.

La passe n'impose pas un sixieme grand domaine. Elle montre plutot :

- quatre fondations transversales insuffisamment visibles ;
- des capacites deja developpees a raccorder explicitement ;
- des extensions metier importantes mais encore non developpees ;
- quelques blocs a garder experts, futurs ou hors produit.

## 3. Fondations transversales a rendre explicites

### F1 - Referentiel patrimonial et geospatial

Capacites existantes : Site -> Batiment -> Local, import DGFiP/MAJIC, IGN/OSM, carte, recherche d'adresse, attachements geographiques, reclassification et informations IGN.

Pourquoi c'est critique : toutes les consommations, factures, contrats, equipements, budgets et actions doivent remonter au meme patrimoine. Ce n'est pas seulement un module d'inventaire ; c'est la cle d'agrégation du produit.

A garantir : identifiants durables, historique des rattachements, heritages Site/Batiment/Local, liens partages et navigation de retour depuis chaque objet.

### F2 - Qualite, rapprochement et provenance des donnees

Capacites existantes : audit ENEDIS, rapprochements PRM/PCE, matching CVC, sites DALKIA, scores de similarite, imports persistants, donnees non rattachees conservees.

Angles morts : vocabulaire de qualite non unifie, provenance et fraicheur pas toujours exposees, absence d'un score transversal de couverture, corrections pas toujours historisees.

A garantir sur chaque KPI : source, date d'arret, couverture, perimetre, confiance et objets exclus.

### F3 - Documents, versions contractuelles et preuves

Capacites existantes : documents BPU, acte/DPGF DALKIA, diffs de versions, indices, justificatifs PDF, factures/avoirs, exports et horodatage de transmission.

Angles morts : pas encore de registre documentaire transversal marche -> version -> date d'effet -> perimetre -> preuve ; historique de decision heterogene ; pieces SPIE absentes.

Cette fondation alimente directement controle facture, budget, maintenance et contradiction fournisseur.

### F4 - Workflow, securite et audit

Capacites existantes : authentification JWT, profil, tenant `city_id`, decisions facture, statuts, imports et jobs.

Angles morts : roles/permissions non modelises finement, journal d'audit transversal absent, notifications/escalades absentes, separation preparateur/approbateur non definie.

A court terme, l'utilisateur unique conserve ses acces ; les contrats d'ecran doivent toutefois preparer profil, permission et perimetre.

## 4. Capacites developpees a ne pas perdre dans la refonte

| Capacite | Etat code constate | Rattachement UX recommande |
|---|---|---|
| Carte et constitution patrimoniale DGFiP/IGN/OSM | developpe | Patrimoine, surtout expert/import, avec resultat visible dans les fiches |
| Reclassification Site/Batiment/Local | developpe | Patrimoine > Qualite et corrections |
| Rapprochement PRM/PCE et file patrimoine | developpe | Patrimoine > Rattachements + alertes dans les parcours consommateurs |
| Audit couverture ENEDIS et diagnostics | developpe | Fluides > Qualite des donnees ; details techniques en Administration |
| Collecte ENEDIS sync/async, jobs et backfill | developpe mais async bloque externement | Administration > Connecteurs, resume de sante dans Fluides |
| Puissance max et preconisations abonnement | developpe | Fluides > Optimisation ; action et economie potentielle |
| Courbes de charge, profils annuels/journaliers | developpe | Fluides > Analyse ; reutiliser pour occupation, derive et dimensionnement |
| Energie reactive et programmation horaire via proxy ENGIE | backend disponible, usage principal non prouve | garder connecteur expert ; reevaluer pour optimisation/occupation |
| Prix reels de puissance et couts | developpe | preconisations et atterrissage financier energie |
| BPU historique, formules, TURPE et CRUD | developpe, avec deux representations a arbitrer | references contextuelles depuis facture ; edition en Administration |
| Imports ENGIE XLSX et EDF CSV | developpe | tranches fournisseurs distinctes dans Factures marche |
| TotalEnergies gaz, BPU et tarif reseau ATRD | developpe/en cours dans le worktree | tranche gaz + liaison GRDF et atterrissage |
| Lots de factures, normalisation, timeline et rapport fournisseur | developpe | dossier de facture commun multi-fournisseurs |
| Matrices comptables energie et CPE | developpe | fondation finance partagee, versionnee et auditable |
| CPE multi-fluides et performance electrique | developpe | DALKIA > Performance, avec DJU/cibles |
| Objectif P2.4, cibles, APE, interessement/penalites | developpe ou partiel | DALKIA > Performance contractuelle, pas dans facture generique |
| DPGF P1, P2/P3, BPU, recap et diff DALKIA | developpe | Referentiel contractuel DALKIA + preuves dans controles |
| Indices, formules et justificatifs PDF | developpe | DALKIA > Revisions et preuves |
| P3 devis et atterrissage | developpe | DALKIA > Travaux/engagements, lien PPT et budget |
| Inventaires SYPEMI et terrain CVC | developpe mais doublon a arbitrer | Technique > Inventaire unifie |
| F-Gaz, CO2e, echeances et ESP/DESP | developpe | Technique > Conformite et plan d'action |
| Rapport de couverture technique | developpe | Technique > Qualite et risques |
| Authentification, compte et tenant | developpe | socle, Administration et futurs profils |

## 5. Angles morts metier importants

### A1 - Execution reelle de la maintenance

La strategie couvre bien les contrats et les sites non couverts, mais pas encore tout le cycle d'exploitation :

```text
plan preventif -> gamme/periodicite -> intervention attendue
-> compte rendu/preuve -> reserve -> delai/SLA -> levee
-> penalite eventuelle -> historique equipement
```

Etat : essentiellement non developpe. A classer P1 apres le referentiel des contrats et la matrice de couverture. Sans ce cycle, Po2 sait qu'un site est contractuellement couvert mais pas necessairement qu'il est effectivement entretenu.

### A2 - Engagements, commandes et mandats comptables

Le controle facture et les exports existent, mais l'atterrissage global exige les engagements juridiques, commandes, services faits, mandats et paiements. Ces donnees ne sont pas encore un flux comptable complet.

Etat : partiel. Il faut definir sources, identifiants de reconciliation et frontiere avec le logiciel financier de la collectivite.

### A3 - Taches, notifications et escalades

Files de travail prevues, mais pas de moteur transversal d'affectation, echeance, relance, commentaire et notification.

Etat : non developpe. Ne pas commencer par une messagerie complexe ; prevoir au minimum responsable, date cible, statut, commentaire et historique sur les objets a traiter.

### A4 - Gouvernance et audit des decisions

Les decisions facture existent, mais la plateforme devra tracer qui a modifie un rattachement, une hypothese, une valeur contractuelle, une prevision ou une decision.

Etat : partiel et heterogene. Besoin transversal avant le multi-utilisateur ou un portail prestataire.

### A5 - Occupation, usages et horaires

Fonctionnalite prevue mais non developpee. Elle enrichit les analyses de courbe de charge, la detection hors presence, les programmations CVC et l'explication des derives.

Etat : P2, sauf si les analyses ENEDIS/DJU montrent que l'absence d'occupation bloque les conclusions.

### A6 - Eau et pluviometrie

L'axe Fluides prevoit l'eau mais aucune chaine complete distributeur/facture/analyse n'existe. A ne pas oublier, sans la placer artificiellement au meme niveau de maturite qu'ENEDIS/GRDF.

Etat : P2, dependant de fichiers et factures reels.

### A7 - Conformite patrimoine : OPERAT, BACS, baux

Ces sujets sont documentes mais repousses : OPERAT et trajectoire Eco Energie Tertiaire, BACS/GTB, locaux loues et baux.

Etat : futurs/P2-P4 selon echeances reglementaires. Maintenir les donnees necessaires dans les fiches patrimoine/CVC pour ne pas fermer la porte.

### A8 - Mesure des gains et scenarios travaux

Le PPT doit a terme relier cout, economie attendue, baisse kWh/CO2, impact reglementaire, priorite et retour sur investissement. Le cadrage actuel parle surtout du cout et de la criticite.

Etat : extension P1 du PPT, apres fiabilisation des inventaires et des consommations de reference.

### A9 - Usage terrain et mobilite

Les inventaires, controles et preuves pourraient etre saisis en visite. Aucun parcours mobile/offline n'est cadre.

Etat : ne pas lancer maintenant, mais inclure responsive, photos/documents et gestes simples dans le design system pour ne pas bloquer une future utilisation terrain.

## 6. Capacites a garder en retrait

| Capacite | Decision |
|---|---|
| Proxy API ENGIE complet | connecteur potentiel/expert tant que l'acces et la valeur ne sont pas prouves ; certaines donnees peuvent etre reutilisees |
| Imports, backfills, diagnostics et CRUD referentiels | Administration ou actions contextuelles, jamais navigation principale par defaut |
| Pronostics sportifs | hors produit PatrimoineAuCarre ; ne pas raccorder au front metier |
| Portail prestataire | futur, apres permissions, audit, documents et workflow contradictoire |

## 7. Correction de la carte produit

Les cinq axes restent au premier plan. Ils reposent sur quatre fondations et conservent plusieurs extensions visibles dans la roadmap :

```text
FONDATIONS
Patrimoine maitre
Qualite / rapprochements / provenance
Documents / contrats / preuves
Workflow / securite / audit

AXES DIRECTION
Factures contractuelles
Budget et atterrissage financier
Consommations / DJU / atterrissage
CVC / PPT
Maintenance et couverture

EXTENSIONS PLANIFIEES
Optimisation puissance et courbes
Execution maintenance
Conformites F-Gaz/ESP puis OPERAT/BACS
Occupation et usages
Eau
Baux
Mesure des gains travaux
```

## 8. Consequences pour le design system

Ajouter aux composants deja proposes :

- `DataQualityBadge` : source, couverture, fraicheur, confiance ;
- `ObjectLink` : lien coherent Site/Batiment/Local/PRM/PCE/Contrat/Equipement ;
- `VersionBadge` et `EffectivePeriod` : version contractuelle et dates d'effet ;
- `AuditTimeline` : imports, corrections, decisions et transmissions ;
- `TaskState` : responsable, echeance, statut et commentaire ;
- `ComparisonPanel` : attendu, observe, ecart, tolerance et preuve ;
- `ScenarioSelector` : bas, central, haut et hypotheses ;
- `EvidenceDrawer` transversal : documents et donnees sources.

Ces composants doivent emerger des tranches verticales et non etre construits tous abstraitement en amont.

## 9. Priorites ajoutees apres la passe

1. Conserver les cinq axes sans les diluer.
2. Traiter patrimoine, qualite/provenance, documents/versions et audit comme fondations obligatoires de chaque tranche.
3. Ajouter l'execution de maintenance a la roadmap apres la couverture contractuelle.
4. Integrer engagements/mandats au cadrage budgetaire avant de promettre un atterrissage finance complet.
5. Raccorder explicitement optimisation puissance/courbes, conformites F-Gaz/ESP et performance DALKIA.
6. Maintenir occupation, eau, OPERAT/BACS, baux et gains travaux comme extensions planifiees, non oubliees.
7. Garder Pronostics hors produit.

## 10. Verdict

La strategie n'avait pas oublie un fournisseur ou un moteur majeur apres la correction EDF/TotalEnergies. Le principal risque etait plus subtil : oublier les fondations de confiance et confondre `couverture contractuelle` avec `maintenance effectivement executee`.

La carte corrigee permet de continuer les fonctionnalites sans perdre l'existant et sans transformer le front en catalogue technique.
