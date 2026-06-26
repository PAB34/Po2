# 24 - Cockpit canonique de reconstruction produit et frontend

> Date : 2026-06-22
> Role : source de verite operationnelle pour transformer les capacites developpees en experience utilisateur coherente.
> Ce document ne remplace pas les inventaires techniques detailles ; il les synthetise au niveau ou les decisions produit et UX peuvent etre prises.

## 1. Diagnostic

PatrimoineAuCarre n'est pas un produit realise a 50 %. Il est plutot dans cette situation :

```text
Capacites metier : environ 80 % du coeur envisage developpe
Experience frontend : environ 50 % conforme a l'ambition
Integration produit : insuffisante entre moteurs, workflows, profils et design
```

Il ne faut donc ni recommencer le backend, ni maquiller toutes les pages actuelles. Il faut reconstruire progressivement la couche produit au-dessus des moteurs valides.

## 2. Une seule source de verite, quatre artefacts

A partir de maintenant, la reconstruction frontend repose sur quatre artefacts seulement :

1. **Registre des capacites** : ce que le systeme sait faire et son statut reel.
2. **Workflows metier** : comment un profil accomplit une tache de bout en bout.
3. **Contrats d'ecran** : ce que chaque ecran doit permettre de comprendre et de faire.
4. **Design system** : composants visuels et comportements communs extraits des workflows valides.

Les documents existants deviennent des sources :

- [[13-Matrice-routes-fonctionnalites-refonte-api]] : preuve technique endpoint par endpoint ;
- [[14-Catalogue-fonctionnalites-commentees-et-reaffectation]] : commentaire metier detaille ;
- [[18-Registre-raccordement-frontend]] : premier raccordement aux ecrans ;
- [[21-Cartographie-fonctionnelle-vers-experience-utilisateur]] : methode ;
- [[22-Developpement-deux-pistes-et-profils-utilisateurs]] : profils et organisation ;
- [[23-Seconde-passe-audit-fonctionnel-et-angles-morts]] : controle des oublis.

Le present document devient le cockpit quotidien. On ne doit plus demander a l'utilisateur de relire les 295 endpoints pour savoir quoi construire.

## 3. Statuts communs

### Etat de la capacite

| Statut | Sens |
|---|---|
| Developpe | moteur et donnees existent |
| Partiel | une partie du moteur, des donnees ou des controles manque |
| A construire | besoin valide mais pas de moteur utilisable |
| Futur | conserve dans la vision sans entrer dans les prochains lots |
| Hors produit | ne doit pas etre raccorde |

### Etat de l'experience

| Statut | Sens |
|---|---|
| Operationnelle | workflow utilisable et comprehensible |
| Fragmentee | fonctions presentes mais reparties ou difficiles a enchainer |
| Experte | utilisable seulement avec forte connaissance technique |
| Embryonnaire | ecran ou conteneur existe, experience non aboutie |
| Absente | aucun parcours utilisateur complet |

### Decision de reconstruction

`Conserver`, `Raccorder`, `Refondre`, `Completer`, `Construire`, `Garder expert`, `Mettre en attente`, `Retirer`.

## 4. Registre canonique initial des capacites

Ce registre travaille au niveau **capacite produit**, pas endpoint. Une capacite peut mobiliser plusieurs routes, services et pages.

| ID | Capacite | Profil principal | Etat capacite | Experience actuelle | Ecran cible | Decision |
|---|---|---|---|---|---|---|
| CORE-01 | Authentification, compte, tenant ville | Administrateur | Developpe | Operationnelle simple | Socle / Compte | Conserver puis ajouter permissions |
| PAT-01 | Referentiel Site -> Batiment -> Local | Pilote patrimoine | Developpe | Fragmentee | Patrimoine > Sites et batiments | Refondre |
| PAT-02 | Constitution DGFiP/MAJIC + IGN/OSM + carte | Administrateur / patrimoine | Developpe | Experte | Patrimoine + Administration > Imports | Garder expert, mieux montrer le resultat |
| PAT-03 | Fiche patrimoine transversale | Tous profils metier | Partiel | Fragmentee | Fiche Site/Batiment/Local | Refondre |
| DATA-01 | Rapprochements PRM/PCE/CVC/DALKIA | Pilote | Developpe/partiel | Fragmentee | Patrimoine > Rattachements | Raccorder et unifier |
| DATA-02 | Qualite, couverture, provenance, fraicheur | Pilote / analyste | Partiel | Fragmentee | Cockpit + chaque ecran | Completer transversalement |
| DOC-01 | Documents, preuves et versions contractuelles | Pilote / finances | Partiel | Fragmentee | Marches > Documents et preuves contextuelles | Refondre |
| ELEC-01 | Portefeuille PRM et historique ENEDIS | Analyste energie | Developpe | Fragmentee | Fluides > Electricite | Refondre |
| ELEC-02 | Courbes de charge, profils, puissance max | Analyste energie | Developpe | Experte | Electricite > Analyse | Raccorder |
| ELEC-03 | Preconisations puissance et couts reels | Analyste / direction | Developpe | Partielle | Electricite > Optimisation | Refondre autour de la decision |
| DJU-01 | DJU et performance climatique | Analyste / DALKIA | Developpe/partiel | Fragmentee | Fluides > Performance & DJU | Unifier et fiabiliser |
| GAS-01 | PCE, droits et consommations GRDF | Analyste energie | En cours | Embryonnaire | Fluides > Gaz | Completer |
| FORECAST-01 | Atterrissage consommation kWh | Analyste / direction | A construire sur socles existants | Absente | Fluides > Atterrissage | Construire |
| FORECAST-02 | Conversion des previsions en euros | Analyste / finances | Partiel | Absente | Fluides + Budget | Construire avec prix par periode |
| INV-CORE | Dossier facture multi-fournisseurs | Pilote / finances | Partiel | Fragmentee | Marches > Factures marche | Refondre |
| INV-ENGIE | Factures ENGIE electricite batiments | Pilote | Developpe | Partielle et dense | Factures > ENGIE | Refondre |
| INV-EDF | Factures EDF electricite/eclairage public | Pilote | Developpe/partiel | Partielle | Factures > EDF | Completer et refondre |
| INV-TOTAL | Factures gaz TotalEnergies | Pilote | Developpe | Partielle | Factures > TotalEnergies | Raccorder au dossier commun |
| INV-DEDUPE-01 | Deduplication et mise a jour des factures reimportees | Pilote / admin | Developpe/partiel selon fournisseur | Peu explicite | Factures > Rapport import | Harmoniser la cle et le comportement |
| INV-HISTORY-01 | Cycle nouvelle, traitee, archivee et reouverte | Pilote / finances | Partiel sur decisions existantes | Fragmentee | Factures > A traiter / Historique | Construire les vues et statuts communs |
| INV-IMPORT-AUDIT-01 | Historique des lots et rapport d import | Pilote / admin | Partiel | Technique | Factures > Imports | Unifier cree/ignore/mis a jour/erreur |
| MARKET-CONTACT-01 | Contacts entreprise par marche, lot et periode | Pilote marches | A construire | Absente | Marche > Contacts | Requis avant reclamations assistees |
| CLAIM-01 | Reclamations de facturation et suivi des echanges | Pilote / finances | Partiel via statut de decision | Absente comme parcours | Facture > Reclamation | Construire le suivi et les relances |
| MAIL-DRAFT-01 | Generation destinataire, objet et corps du mail | Pilote | Specifie V1 | Absente | Facture > Reclamation | Recommande avant envoi direct |
| MAIL-SEND-01 | Envoi direct et delivrabilite depuis la plateforme | Administrateur / pilote | Futur | Absente | Service transversal | Arbitrer SMTP/API apres usage du brouillon |
| GAS-CONTROL-DETAIL | Trace de controle gaz par facture | Pilote / finances | Developpe | Operationnelle, a evaluer en usage | TotalEnergies > Fiche de verification | Tester sur cas reels |
| GAS-REF | Referentiels gaz pedagogiques | Pilote / expert energie | Socle de donnees developpe | Absente | Energie > Referentiels gaz | Concevoir en TO-BE sur le modele TURPE |
| GAS-CONTROL-GLOBAL | Synthese portefeuille et drill-down gaz | Pilote / direction | A construire | Absente | Controles gaz > Synthese | Concevoir en TO-BE avant developpement |
| PRICE-01 | BPU historiques et prix contractuels | Expert energie | Developpe | Experte | References depuis facture + Administration | Refondre/Garder expert |
| PRICE-02 | TURPE et tarifs reseau | Analyste / controleur | Developpe | Experte | Facture + Prix reseau | Contextualiser |
| FIN-01 | Matrice comptable energie/CPE | Finances | Developpe | Fragmentee | Finance > Matrice | Unifier et versionner |
| FIN-02 | Budget initial et revisions | Finances / direction | A construire | Absente | Budget > Referentiel | Construire |
| FIN-03 | Engage, commandes, services faits, mandats | Finances | A construire | Absente | Budget > Execution | Construire apres source finance |
| FIN-04 | Atterrissage financier global | Direction / finances | Partiel DALKIA seulement | Absente transversalement | Budget > Atterrissage | Construire |
| CPE-01 | Referentiel DALKIA, actes, DPGF, BPU, versions/diff | Pilote expert | Developpe | Experte | DALKIA > Referentiel | Refondre, resume visible |
| CPE-02 | Factures et controles P1/P2/P3 | Pilote / finances | Developpe | Fragmentee | DALKIA > Controle factures | Refondre |
| CPE-03 | Consommations, DJU, cibles, interessement | Pilote energie | Developpe/partiel | Fragmentee | DALKIA > Performance | Refondre |
| CPE-04 | Indices, formules et preuves | Pilote / finances | Developpe | Experte | DALKIA > Revisions | Raccorder |
| CPE-05 | Devis, BPU, engagements et atterrissage P3 | Pilote maintenance | Developpe/partiel | Fragmentee | DALKIA > Travaux | Refondre et relier au budget/PPT |
| SPIE-01 | Contrat, perimetre et prestations P2 | Pilote maintenance | A construire depuis pieces reelles | Absente | Marches > SPIE | Construire |
| MAINT-01 | Matrice de couverture des contrats | Responsable maintenance | A construire sur patrimoine/CVC | Absente | Marches > Couverture | Construire |
| MAINT-02 | Execution preventive, interventions et preuves | Responsable maintenance | A construire | Absente | Maintenance > Execution | Futur/P1 apres couverture |
| CVC-01 | Inventaire SYPEMI et terrain | Responsable technique | Developpe avec doublon | Fragmentee | Technique > Inventaire CVC | Unifier/refondre |
| CVC-02 | Criticite et sante des equipements | Responsable technique | Partiel | Fragmentee | Technique > Criticite | Completer |
| CVC-03 | Plan pluriannuel de travaux chiffre | Direction / technique | A construire sur socles | Absente | Technique > PPT | Construire |
| REG-01 | F-Gaz, CO2e, echeances, actions | Responsable technique | Developpe | Partielle | Technique > F-Gaz | Raccorder/refondre |
| REG-02 | ESP/DESP | Responsable technique | Developpe/partiel | Partielle | Technique > ESP | Completer |
| OPS-01 | Imports, jobs, backfills et diagnostics | Administrateur | Developpe | Experte | Administration > Operations | Garder expert |
| WF-01 | Files de travail, responsables, echeances, commentaires | Tous operationnels | A construire | Absente | Cockpit + objets | Construire progressivement |
| AUDIT-01 | Journal des corrections et decisions | Direction / admin | Partiel | Fragmentee | Historique transversal | Completer |
| UX-DS-01 | Design system et composants metier | Tous profils | Specifie V1 | Incoherente / partielle | Fondation frontend | Construire avant refonte massive |
| UX-HOME-01 | Accueils et cockpits adaptes aux profils | Tous profils | Specifie V1 | Absente | Accueil > Mon cockpit | Construire par decisions prioritaires |
| UX-SITE-360 | Fiche Site 360 degres transversale | Tous profils metier | Specifie V1 | Fragmentee | Site > Vue 360 degres | Unifier les objets autour du site |
| RBAC-01 | Roles, permissions et perimetres | Administrateur | Specifie V1 sur socle auth | Absente hors tenant ville | Administration > Roles | Construire avant workflows partages |
| SEARCH-01 | Recherche globale multi-objets | Tous profils | Specifie V1 | Absente | Barre de recherche globale | Indexer sites, compteurs, factures, contrats et equipements |
| NOTIF-01 | Alertes, affectations et notifications | Tous operationnels | Specifie V1 | Absente | Cockpit + centre de notifications | Relier aux echeances et anomalies |
| REPORT-01 | Rapports et exports direction/finance | Direction / finances | Specifie V1 sur exports existants | Fragmentee | Rapports | Unifier et planifier les restitutions |
| ACCESS-01 | Accessibilite, responsive et navigation clavier | Tous profils | Specifie V1 | Non auditee | Transversal | Integrer aux criteres de recette |
| UX-MEASURE-01 | Tests utilisateurs et mesure de reussite | Product owner / profils | Specifie V1 | Absente | Transversal | Tester chaque parcours avant livraison |
| WATER-01 | Eau, factures et pluviometrie | Analyste energie | A construire | Absente | Fluides > Eau | Mettre en attente P2 |
| OCC-01 | Occupation et usages | Patrimoine / energie | A construire | Absente | Patrimoine > Usages | Mettre en attente P2 |
| OPERAT-01 | Eco Energie Tertiaire / OPERAT | Direction / energie | A construire | Absente | Conformite | Futur selon echeance |
| BACS-01 | BACS/GTB et ISO 52120 | Responsable technique | Futur | Absente | Technique > BACS | Futur |
| LEASE-01 | Baux et locaux loues | Gestionnaire patrimoine | A construire | Absente | Patrimoine > Baux | Mettre en attente |
| FIELD-01 | Usage terrain/mobile et photos | Technicien/site | A cadrer | Absente | Parcours terrain | Preparer le design, ne pas construire |
| OUT-01 | Pronostics sportifs | Aucun profil Po2 | Developpe hors domaine | Hors produit | Aucun | Retirer de la carte produit |

## 5. Matrice des workflows prioritaires

| Workflow | Profils | Debut | Fin reussie | Priorite UX |
|---|---|---|---|---|
| Controle facture de fourniture | Pilote, finances | facture recue | decision justifiee et exportee | P0 |
| Analyse et atterrissage energie | Analyste, direction | donnees ENEDIS/GRDF | prevision kWh/euros expliquee | P0 |
| Controle et performance DALKIA | Pilote, finances, direction | contrat/version et releves | decision + performance + atterrissage | P0 |
| Couverture maintenance | Responsable maintenance | patrimoine + contrats | sites/equipements non couverts traites | P0 |
| CVC et PPT | Technique, direction | inventaire qualifie | arbitrage annuel chiffre | P0/P1 |
| Budget global | Finances, direction | budget et engagements | atterrissage reconcilie | P0 apres donnees finance |
| Fiabilisation patrimoine | Pilote, admin | objet non rattache | lien valide et historise | transverse |

## 6. Contrat d'ecran obligatoire

Avant de dessiner ou coder un nouvel ecran, remplir [[Templates/Contrat-ecran-UX]]. Un contrat d'ecran contient :

- profils principal et secondaires ;
- question a laquelle l'ecran repond ;
- contexte d'entree et sortie attendue ;
- objets, sources, qualite et periode ;
- actions, decisions et permissions ;
- preuves et drill-down ;
- etats chargement, vide, partiel, erreur, succes ;
- desktop, tablette et besoins terrain ;
- composants du design system ;
- criteres de validation metier et UX.

La maquette visuelle vient apres ce contrat, pas avant.

## 7. Construction du design system

### Lot DS-0 - Fondations

- couleurs semantiques, typographie, espaces, grille, rayons et elevations ;
- densites `direction`, `standard`, `expert` ;
- focus, clavier, contrastes, responsive ;
- dictionnaire des statuts metier.

### Lot DS-1 - Premier workflow facture

Extraire et valider : `PageHeader`, filtres, `KpiCard`, `StatusBadge`, `DataTable`, `ComparisonPanel`, `EvidenceDrawer`, `DecisionPanel`, `AuditTimeline`.

### Lot DS-2 - Workflow temporel ENEDIS/GRDF/DJU

Ajouter : `TimeSeriesChart`, selecteur de periode, comparaison, qualite des donnees, scenarios et hypotheses.

### Lot DS-3 - Maintenance et CVC

Ajouter : `CoverageMatrix`, arborescence patrimoine, criticite, plan d'action et planification pluriannuelle.

Regle : un composant entre dans le design system lorsqu'il est prouve par un workflow reel et reutilisable, pas parce qu'il semble generique.

## 8. Methode de migration sans perdre les 80 % acquis

Pour chaque workflow :

1. selectionner les capacites du registre ;
2. verifier code, donnees reelles et tests ;
3. dessiner le workflow nominal et les exceptions ;
4. remplir les contrats d'ecran ;
5. prototyper avec cas reels et donnees incompletes ;
6. raccorder les moteurs existants sans les reecrire inutilement ;
7. valider avec les profils concernes ;
8. rediriger les anciennes routes ;
9. marquer chaque capacite `couverte par le nouveau front` ;
10. retirer l'ancien uniquement quand la couverture atteint 100 %.

La matrice de couverture devient le garde-fou anti-perte :

```text
Capacite -> workflow -> ecran cible -> composant -> statut validation -> ancienne route retiree ?
```

## 9. Organisation documentaire simplifiee

L'utilisateur ne doit consulter regulierement que :

1. [[Backlog]] pour l'ordre des chantiers ;
2. ce document pour la carte produit et la couverture frontend ;
3. la fiche du workflow en cours ;
4. les contrats d'ecran du workflow ;
5. le module metier concerne pour les regles detaillees.

Les autres audits restent des preuves et archives de travail. Cela evite que la documentation devienne elle-meme un second produit impossible a naviguer.

## 10. Plan d'action immediat

### Semaine/lot 1 - Consolider sans coder de nouvelle page

- valider le registre ci-dessus ;
- choisir le workflow pilote ;
- verifier les cas reels et les donnees disponibles ;
- remplir ses contrats d'ecran ;
- faire un wireframe basse fidelite.

### Lot 2 - Premier parcours refondu

Recommandation : factures de fourniture, car ENGIE, EDF et TotalEnergies permettent de tester un socle commun et trois moteurs differents.

Livrer : file multi-fournisseurs, detail, comparaison attendue/observee, preuves, decision, ventilation et export.

### Lot 3 - Deuxieme parcours

ENEDIS/GRDF/DJU : historique, qualite, comparaison, derive et atterrissage. Il valide les composants temporels et relie les distributeurs aux fournisseurs.

### Lot 4 - Generalisation

DALKIA, couverture maintenance, CVC/PPT puis budget global. Chaque lot reutilise et enrichit le design system.

## 11. Definition du succes

Le frontend cible est reussi lorsque :

- chaque capacite utile du registre appartient a un workflow et un ecran ;
- chaque profil trouve ses priorites depuis son accueil ;
- aucune fonctionnalite developpee n'est perdue ou exposee deux fois sans raison ;
- les moteurs techniques restent complexes mais l'experience explique leurs resultats ;
- sources, qualite, preuves et limites sont visibles ;
- le design est coherent parce que ses composants proviennent de workflows communs ;
- une ancienne page peut etre retiree avec une preuve de couverture, pas au ressenti.

## 12. Atelier visuel

La cartographie des workflows et contrats d'ecran peut etre travaillee dans [[25-Atelier-BPMN-produit-UX]]. Les cadres BPMN portent les IDs du registre canonique afin de relier processus, ecrans et capacites developpees.
