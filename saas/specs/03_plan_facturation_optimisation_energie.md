# Plan de developpement - Facturation energie et optimisation de puissance

## 1. Objectif

Le module Energie doit evoluer vers deux capacites complementaires :

1. produire des preconisations de puissance souscrite et de formule tarifaire d'acheminement, avec une estimation budgetaire prudente ;
2. importer, controler, valider ou refuser les factures d'energie, d'abord depuis des fichiers telecharges dans les espaces clients fournisseurs, puis a terme via une connexion Chorus Pro.

Le module doit rester utilisable depuis un poste d'entreprise sans installation locale. Tous les traitements lourds doivent etre realises cote backend Docker, dans l'application web.

## 2. Principes de conception

### 2.1 La facture devient la preuve financiere

Les donnees ENEDIS permettent de detecter les anomalies techniques et de simuler des scenarios.

La facture, elle, doit devenir la reference financiere opposable :

- prix reel applique ;
- periode facturee ;
- PRM concerne ;
- puissance souscrite ;
- puissance atteinte ;
- depassements ;
- composantes TURPE ;
- fourniture ;
- capacite ;
- CEE ;
- garanties d'origine ;
- taxes ;
- total HTT, TVA, TTC.

Le moteur de controle doit donc toujours relier une facture a ses sources : BPU, donnees ENEDIS, configuration fournisseur/lot, et pieces contractuelles.

### 2.2 Ne pas confondre alerte de calibrage et economie certaine

La colonne actuelle "Calibrage" est un indicateur d'alerte base sur :

- puissance souscrite ;
- puissance maximale observee ;
- ratio pic / puissance souscrite.

Elle ne suffit pas a calculer une economie fiable. Pour estimer un impact financier, il faut prendre en compte le TURPE, la formule tarifaire d'acheminement, les depassements, les puissances par tranche horosaisonniere, et les eventuels couts de modification.

La premiere version doit donc afficher des preconisations avec un niveau de confiance :

- recommande ;
- a confirmer ;
- donnees insuffisantes ;
- risque de depassement.

### 2.3 Le controle facture doit preceder l'automatisation Chorus

Avant de connecter Chorus Pro, il faut stabiliser :

- le modele de donnees facture ;
- le parseur de factures fournisseur ;
- le moteur de controle ;
- le workflow de validation/refus.

La connexion Chorus doit ensuite devenir une source d'import supplementaire, pas une dependance structurante du moteur metier.

## 3. Base contractuelle

Les pieces Herault Energie lots 1 a 6 rendent le module pertinent :

- le CCTP prevoit une optimisation annuelle des couts d'acces au reseau de distribution ;
- cette optimisation porte sur les puissances souscrites et les formules tarifaires d'acheminement ;
- le titulaire doit chiffrer les gains potentiels annuels ;
- les optimisations de puissance doivent etre faites au moins par pas de 0,1 kVA pour l'eclairage public et 1 kVA dans les autres cas ;
- le titulaire doit transmettre des donnees de facturation detaillees par PDL ;
- les factures doivent presenter un niveau de detail permettant leur validation ;
- les couts d'acheminement et prestations distributeur doivent etre refactures a l'euro/l'euro, hors cas C1 directement factures par le GRD.

Consequence produit : le logiciel peut legitimement controler la facture et produire une contre-analyse des optimisations, mais il doit separer "estimation" et "preuve facturee".

## 4. Perimetre fonctionnel cible

### 4.1 Module import factures

Premiere etape : import manuel depuis l'application.

Formats a accepter progressivement :

- PDF simple fournisseur ;
- PDF Factur-X si disponible ;
- XLSX/CSV fournisseur si l'espace client le propose ;
- archive ZIP contenant plusieurs factures ;
- a terme XML ou JSON provenant de Chorus/flux fournisseur.

Fonctions attendues :

- upload multi-fichiers ;
- detection fournisseur ;
- detection numero facture ;
- detection periode ;
- detection PRM ;
- stockage du fichier source ;
- extraction des donnees exploitables ;
- statut d'import : importe, partiellement lu, illisible, doublon.

### 4.2 Module normalisation facture

Chaque facture doit etre transformee en donnees normalisees, meme si le format source varie.

Entites principales :

- facture ;
- ligne facture ;
- composante facture ;
- document source ;
- erreurs d'extraction ;
- resultats de controle.

Composantes minimales a normaliser :

- fourniture energie ;
- capacite ;
- CEE ;
- GO ;
- TURPE / acheminement ;
- depassements de puissance ;
- taxes et contributions ;
- prestations GRD ;
- total HT, HTT, TVA, TTC.

### 4.3 Module controle facture

Le controle doit produire une decision assistee, pas une decision automatique opaque.

Familles de controles :

- identification : fournisseur, SIRET, lot, PRM, ville, periode, numero facture ;
- doublon : meme numero facture, meme fournisseur, meme periode, meme PRM ;
- BPU : prix unitaire facture vs prix BPU courant ;
- consommation : kWh factures vs donnees ENEDIS agregees ;
- periode : dates facturees vs periode attendue ;
- puissance : puissance souscrite, puissance atteinte, depassements ;
- TURPE : presence et coherence des composantes attendues ;
- taxes : presence et taux attendus ;
- totalisation : lignes, sous-totaux, TVA, TTC ;
- pieces justificatives : facture PDF, detail PDL, flux facture.

Chaque controle doit produire :

- statut : conforme, avertissement, anomalie, bloquant, non verifiable ;
- ecart chiffre quand possible ;
- severite ;
- explication lisible ;
- source utilisee ;
- action recommandee.

### 4.4 Workflow validation/refus

Statuts cibles :

- importe ;
- analyse ;
- a verifier ;
- conforme ;
- valide ;
- refuse ;
- contestation envoyee ;
- avoir attendu ;
- corrige.

L'utilisateur doit pouvoir :

- ouvrir une facture ;
- voir les ecarts par PDL ;
- filtrer les anomalies bloquantes ;
- marquer une anomalie comme acceptee ;
- ajouter un commentaire ;
- valider la facture ;
- refuser la facture ;
- generer une note de contestation.

### 4.5 Module preconisation de puissance

Objectif : transformer la colonne "Calibrage" en aide a la decision.

Donnees necessaires :

- puissance souscrite actuelle ;
- puissance maximale atteinte ;
- historique 30 minutes si disponible ;
- max mensuels ;
- segment C2/C4/C5 ;
- tarif de distribution / FTA ;
- consommations par poste horosaisonnier ;
- depassements eventuels ;
- factures deja controlees ;
- couts TURPE observes ou tables tarifaires importees.

Premiere version :

- calculer une puissance cible avec marge de securite ;
- afficher plusieurs scenarios : prudent, equilibre, agressif ;
- signaler le risque de depassement ;
- indiquer le niveau de confiance ;
- ne pas afficher d'economie en euros si les composantes TURPE ne sont pas disponibles.

Version avancee :

- recalculer les composantes TURPE avant/apres ;
- integrer les depassements evites ou crees ;
- estimer l'impact annuel ;
- comparer a l'historique facture ;
- produire une fiche de preconisation exportable.

## 5. Architecture cible

### 5.1 Backend

Nouveaux domaines backend :

- `invoice_imports` : suivi des fichiers importes ;
- `energy_invoices` : entete facture ;
- `energy_invoice_lines` : lignes facture normalisees ;
- `energy_invoice_components` : composantes metier detaillees ;
- `energy_invoice_checks` : resultats de controle ;
- `energy_power_recommendations` : scenarios de puissance ;
- `energy_connector_accounts` : futurs raccordements Chorus/GRDF/portails ;
- `energy_connector_jobs` : executions d'import automatise.

Services :

- `invoice_parser_service` ;
- `invoice_normalization_service` ;
- `invoice_control_service` ;
- `power_recommendation_service` ;
- `chorus_connector_service` plus tard.

### 5.2 Frontend

Nouvelles vues :

- `/energie/factures` : liste des factures importees ;
- `/energie/factures/import` : upload et suivi d'import ;
- `/energie/factures/:id` : detail facture, controles et decision ;
- `/energie/preconisations` : portefeuille des recommandations ;
- `/energie/:prmId/preconisation` : detail d'un PRM.

Ergonomie :

- badges de statut ;
- filtres par fournisseur, lot, periode, PRM, severite ;
- comparaison facture vs attendu ;
- bouton "Valider" ;
- bouton "Refuser / demander correction" ;
- historique des decisions.

## 6. Trajectoire Chorus Pro

### 6.1 Ce que l'on sait

La documentation officielle Chorus Pro indique que :

- Chorus Pro est la plateforme publique de facturation electronique ;
- les raccordements API utilisent un access token via PISTE ;
- les appels API supposent une structure identifiee, un utilisateur gestionnaire, un compte utilisateur technique et des droits API actifs ;
- les formats structures mentionnes dans la documentation incluent notamment Factur-X, XML mixte et XML structure.

Sources a suivre :

- https://aife.economie.gouv.fr/nos-applications/chorus-pro/
- https://aife.economie.gouv.fr/nos-applications/piste/
- https://portail.chorus-pro.gouv.fr/aife_documentation?id=kb_article_view&sysparm_article=KB0011554
- https://portail.chorus-pro.gouv.fr/aife_documentation?id=kb_article_view&sysparm_article=KB0011473

### 6.2 Strategie d'integration

Ne pas commencer par Chorus.

Ordre recommande :

1. import manuel de factures fournisseur ;
2. modele facture robuste ;
3. controle facture ;
4. workflow validation/refus ;
5. raccordement Chorus en mode qualification ;
6. import automatique des factures et pieces jointes ;
7. rapprochement automatique avec factures deja controlees.

### 6.3 Points a confirmer avant developpement Chorus

- droits exacts de la collectivite dans Chorus ;
- capacite a recuperer les factures recues via API avec les habilitations disponibles ;
- format des documents recuperables ;
- presence ou non de donnees structurees exploitables ;
- gestion multi-SIRET / multi-services ;
- contraintes de securite pour les comptes techniques ;
- journalisation obligatoire des imports.

## 7. Plan de realisation

### Phase 0 - Cadrage donnees

Objectif : collecter 10 a 20 factures reelles.

Livrables :

- typologie des factures EDF/ENGIE ;
- champs disponibles ;
- qualite d'extraction PDF ;
- mapping facture vers PRM ;
- liste des controles realistes en MVP.

Decision cle : si les factures PDF sont trop peu structurees, demander en priorite un export XLSX/CSV depuis l'espace client fournisseur.

### Phase 1 - Import manuel et stockage

Objectif : pouvoir importer une facture et la retrouver dans l'application.

Backend :

- table imports ;
- table documents ;
- endpoint upload ;
- stockage fichier ;
- detection doublon ;
- statut d'import.

Frontend :

- page import ;
- liste des imports ;
- messages d'erreur lisibles.

Definition of done :

- un utilisateur importe une facture PDF ;
- le fichier est conserve ;
- la facture apparait dans la liste ;
- les doublons sont detectes.

### Phase 2 - Extraction et normalisation MVP

Objectif : extraire les champs essentiels.

Champs MVP :

- fournisseur ;
- numero facture ;
- date facture ;
- periode ;
- PRM ;
- montant HT/TVA/TTC ;
- consommation totale ;
- puissance souscrite si presente ;
- puissance atteinte si presente ;
- lignes energie si detectables.

Definition of done :

- au moins un format de facture EDF et un format ENGIE sont normalises ;
- les extractions incertaines sont visibles ;
- l'utilisateur peut corriger manuellement un champ mal lu.

### Phase 3 - Controle BPU et coherence simple

Objectif : controler ce qui est deja maitrise.

Controles MVP :

- fournisseur/lot connu ;
- PRM connu ;
- periode plausible ;
- prix BPU applique pour fourniture/capacite/CEE/GO ;
- total ligne coherent ;
- total facture coherent ;
- doublon facture.

Definition of done :

- une facture peut etre classee conforme / a verifier / anomalie ;
- chaque anomalie est expliquee ;
- l'utilisateur peut valider ou refuser.

### Phase 4 - Preconisation puissance v1

Objectif : donner une aide a la decision sans surpromesse financiere.

Fonctions :

- puissance recommandee ;
- scenarios prudent/equilibre/agressif ;
- niveau de confiance ;
- justification ;
- liste des PRM prioritaires ;
- export synthese.

Definition of done :

- la page Energie affiche une action "Voir preconisation" ;
- les PRM sur-souscrits et sous-dimensionnes sont priorises ;
- l'impact budgetaire n'est affiche que si les donnees tarifaires sont suffisantes.

### Phase 5 - Controle TURPE et estimation budgetaire

Objectif : rendre le calcul financier defendable.

Prerequis :

- importer ou maintenir les grilles TURPE applicables ;
- connaitre la FTA ;
- connaitre les depassements ;
- disposer d'un historique facture ou d'une table de calcul fiable.

Fonctions :

- calcul avant/apres puissance ;
- cout annuel estime ;
- economie potentielle ;
- risque de depassement ;
- couts de modification si connus.

Definition of done :

- le logiciel distingue economie estimee et economie constatee ;
- les hypotheses sont affichees ;
- le calcul est auditable.

### Phase 6 - Module Chorus Pro

Objectif : automatiser la recuperation des factures quand le moteur manuel est stable.

Travaux :

- raccordement qualification PISTE/Chorus ;
- compte technique ;
- stockage des secrets ;
- jobs d'import ;
- rapprochement factures Chorus avec factures deja importees ;
- journal d'audit ;
- reprise sur erreur.

Definition of done :

- un job recupere les factures disponibles ;
- les documents sont stockes ;
- les factures passent dans le meme moteur de controle que les imports manuels.

## 8. Risques et garde-fous

### Risques principaux

- factures PDF non structurees ;
- differences fortes entre formats fournisseurs ;
- absence de detail PDL dans certaines factures groupees ;
- donnees TURPE insuffisantes pour une economie fiable ;
- droits Chorus plus limites que prevu ;
- confusion entre facture fournisseur, facture Chorus et donnees GRD.

### Garde-fous

- toujours conserver le document source ;
- toujours tracer la source de chaque controle ;
- permettre la correction manuelle ;
- ne jamais refuser automatiquement une facture ;
- afficher les hypotheses de calcul ;
- separer anomalie bloquante et avertissement ;
- preparer les connecteurs sans rendre l'application dependante d'eux.

## 9. MVP recommande

Le MVP le plus solide est :

1. import manuel PDF/XLSX ;
2. extraction minimale ;
3. correction manuelle des champs ;
4. controle BPU et coherence facture ;
5. workflow valider/refuser ;
6. preconisation puissance qualitative ;
7. estimation budgetaire uniquement quand les donnees sont suffisantes.

Ce MVP cree rapidement de la valeur et prepare correctement Chorus Pro, sans bloquer le produit sur une integration externe complexe.

## 10. Questions a trancher

- Quels formats exacts EDF et ENGIE sont disponibles depuis les espaces clients ?
- Les factures sont-elles par PDL ou groupees ?
- Les exports contiennent-ils les composantes TURPE detaillees ?
- L'utilisateur veut-il controler au niveau facture globale, PDL, ou ligne de composante ?
- Quels seuils d'ecart sont acceptables pour valider une facture ?
- La collectivite dispose-t-elle deja des habilitations Chorus necessaires ?
- Faut-il produire un courrier/mail de contestation standardise ?
