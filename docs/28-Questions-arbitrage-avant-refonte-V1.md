# 28 - Questions et arbitrages avant la refonte V1

> Date : 2026-06-24  
> Statut : registre de décisions à relire avec l'utilisateur avant et pendant la refonte.

## Comment lire ce registre

- 🔴 `◆` **Structurant** : décision nécessaire avant de figer le workflow, le modèle de données ou les droits.
- 🟠 `◇` **Conception** : choix à traiter pendant les ateliers UX ; il ne bloque pas le démarrage du socle.
- 🟢 `✓` **Validé** : réponse enregistrée dans la fiche du cadre concerné dans l'atelier.

La carte V1 porte les mêmes identifiants `A01` à `A26`. Le filtre **Arbitrages** permet de n'afficher que ces cadres. Les réponses saisies dans les fiches sont sauvegardées localement et incluses dans l'export JSON.

## Là où ton temps a le plus de valeur

Tu ne dois pas passer du temps à choisir des composants React, des couleurs de boutons ou une architecture technique. Ton apport est décisif sur huit sujets :

1. les profils réels, leurs responsabilités et leurs premières décisions quotidiennes ;
2. la définition du pivot `site / bâtiment` et la manière dont tu navigues dans le patrimoine ;
3. le cycle de vie d'une facture : nouvelle, contrôlée, décidée, réclamée, traitée, réouverte ;
4. les règles de déduplication des imports et de conservation de l'historique ;
5. les sources et dimensions de la matrice budgétaire et comptable ;
6. la définition métier d'un site couvert, non couvert ou couvert de manière ambiguë ;
7. les hypothèses d'atterrissage des consommations et des dépenses ;
8. les règles de criticité CVC et d'arbitrage du programme de travaux.

## Registre consolidé des décisions

Ce tableau est désormais la **source de vérité durable**. Les réponses originales sont conservées intégralement en annexe. `Validé` signifie que la règle peut être utilisée pour concevoir la V1 ; `À compléter` signifie que le cadrage est utile mais qu'une précision reste nécessaire avant de figer le workflow concerné.

### Décisions normalisées

| ID | Priorité | Statut | Décision produit consolidée | Dernier point à fermer |
|---|---|---|---|---|
| A01 | ◆ Structurant | ✅ Validé | Profils cibles : Direction, Fluides, Technique/CVC, Finances, Patrimoine et Administrateur général. Un utilisateur peut cumuler les rôles. Un accès tiers DALKIA est envisagé pour déposer les devis P3. | Confirmer si « Maintenance » constitue un rôle autonome ou une vue du profil Technique/CVC, et si le portail tiers DALKIA appartient bien à la V1. |
| A02 | ◆ Structurant | ✅ Validé | Le site est la porte d'entrée opérationnelle ; le bâtiment est l'objet physique ; le local est le niveau fin. La navigation conserve explicitement cette hiérarchie. | — |
| A03 | ◆ Structurant | ✅ Validé | La lecture est largement ouverte au lancement. Les modifications et validations sont contrôlées. L'utilisateur demande un rôle à l'inscription, mais celui-ci ne devient actif qu'après validation par l'Administrateur général. | Définir les données sensibles et les modifications qui pourront être déléguées sans passer systématiquement par l'Administrateur général. |
| A04 | ◆ Structurant | ✅ Validé | Clé facture : fournisseur, type de document, numéro et marché/lot ; période et montant servent de garde-fous. Le destinataire facturé doit aussi être enregistré et contrôlé. | — |
| A05 | ◆ Structurant | ✅ Validé | Le cycle doit distinguer : importée, contrôlée, anomalie à expliquer, décision métier, transmise aux finances, validée ou rejetée dans CIRIL, traitée et éventuellement réouverte avec motif. | Confirmer l'étape exacte qui classe définitivement une facture comme traitée et les rôles autorisés à la réouvrir. |
| A06 | ◆ Structurant | ✅ Validé | Le profil Fluides gère les contacts des marchés Hérault Énergie, DALKIA P1 et eau. Les contacts sont versionnés par marché/lot avec principal et escalade. | Attribuer explicitement la gestion des contacts DALKIA P2/P3 et SPIE, probablement au profil Technique/CVC. |
| A07 | ◆ Structurant | ✅ Validé | La V1 génère le destinataire, l'objet et le brouillon ; l'utilisateur relit puis envoie depuis sa messagerie habituelle. Aucun envoi direct n'est requis en V1. | — |
| A08 | ◆ Structurant | ✅ Validé | Le budget initial est immuable et versionné séparément des décisions modificatives et du prévisionnel courant. | — |
| A09 | ◆ Structurant | ✅ Validé | CIRIL est la source de l'exécution comptable ; les exports fournisseurs XLSX alimentent le contrôle métier ; les PDF restent les pièces reçues par les comptables. | Obtenir un export CIRIL représentatif et identifier les clés de rapprochement : exercice, opération, engagement, tiers, pièce, facture et mandat. |
| A10 | ◆ Structurant | ✅ Validé | La couverture est calculée aux niveaux site, bâtiment, local et famille d'équipement, avec dates d'effet, exceptions, ambiguïtés et chevauchements explicites. | — |
| A11 | ◆ Structurant | 🟠 À compléter | SPIE comporte un lot. Son périmètre s'appuie sur la liste des bâtiments et l'inventaire CVC ; le rattachement contractuel se fait au bâtiment selon le même principe que DALKIA. | — |
| A12 | ◆ Structurant | ✅ Validé | L'atterrissage est explicable par fluide et par site, compare N-1, N-2 et N-3 corrigés des DJU, pondère les données récentes et expose toutes ses hypothèses. | — |
| A13 | ◇ Conception | ✅ Validé | Le réalisé est valorisé aux prix facturés ; le reste à consommer utilise les prix contractuels versionnés ; un scénario prudent reste optionnel. | — |
| A14 | ◇ Conception | ✅ Validé | L'intégration de l'eau est différée tant que l'accès distributeur n'est pas disponible. L'architecture Fluides doit néanmoins rester extensible à l'eau. | — |
| A15 | ◇ Conception | ✅ Validé | La criticité CVC repose sur un score transparent, des pondérations éditables et une justification visible ; aucune note opaque. | — |
| A16 | ◇ Conception | ✅ Validé | Le PPT couvre cinq ans. La sécurité et le réglementaire priment ; plusieurs scénarios sont produits selon l'enveloppe budgétaire. | — |
| A17 | ◇ Conception | 🟠 À compléter | DALKIA P1 relève du profil Fluides ; P2 et P3 du profil Technique/CVC. L'export `export_maintenance_20260624.csv` constitue la première source à analyser pour P2. | Définir la matrice des contrôles, tolérances et preuves P1/P2/P3 après analyse des fichiers et pièces contractuelles. |
| A18 | ◇ Conception | ✅ Validé | Le design sera sobre, dense mais lisible et orienté décision. Les composants seront éprouvés sur les vrais tableaux avant généralisation. | — |
| A19 | ◇ Conception | ✅ Validé | Les files de travail dans l'application sont prioritaires. Le digest est configurable ; l'urgence est réservée aux échéances critiques ; pas d'e-mail par défaut. | — |
| A20 | ◇ Conception | ✅ Validé provisoire | Aucun document ni décision n'est écrasé ; provenance, versions et version active sont explicites. La durée légale de conservation sera confirmée ultérieurement. | Vérification juridique ultérieure, sans bloquer la conception V1. |
| A21 | ◇ Conception | ✅ Validé | Trois premières familles d'exports : contrôle des factures, budget/atterrissage et patrimoine technique/PPT. Chaque chiffre conserve sa source. | — |
| A22 | ◇ Conception | ✅ Validé | Les prototypes doivent être testés avec des représentants réels des profils avant généralisation. | Identifier au minimum : un directeur, la comptable Hérault Énergie/DALKIA, la comptable EDF/éclairage public, le référent Fluides, le référent Technique/CVC et le référent Patrimoine. |
| A23 | ◇ Conception | ✅ Validé | La réclamation est factuelle et courte : référence, période, écart, règle, preuve, correction demandée et délai de réponse. | — |
| A24 | ◇ Conception | ✅ Validé | Le cockpit Direction couvre quatre décisions : budget par opération et matrice comptable, consommations et dérives, état technique du patrimoine, besoins N+1 et trajectoire PPT. Chaque vue permet le drill-down jusqu'au bâtiment, compteur ou écriture utile. | — |
| A25 | ◇ Conception | ✅ Validé | Chaque donnée affiche source, dernière mise à jour, période couverte et confiance. Proposition : fiable si couverture ≥ 95 % et fraîcheur conforme ; dégradée entre 70 et 95 % ou avec un cycle de retard ; inutilisable sous 70 %, sans rattachement ou sans source. | Valider ou adapter ces seuils par type de donnée. |
| A26 | ◆ Structurant | ✅ Validé | La matrice cible doit relier exercice, service, fonction, nature, numéro d'opération, marché/lot, fournisseur, site/bâtiment, fluide, engagement, facture et mandat. | Terminer l'analyse du fichier comptable DALKIA, l'étendre aux autres marchés et confronter ces dimensions à un export CIRIL réel. |

### Synthèse de clôture

- **24 décisions validées**, dont A20 à titre provisoire ;
- **2 décisions à compléter** : A11 pour le corpus SPIE et A17 pour la revalidation des matrices DALKIA P1/P2/P3 ;
- A26 devient un arbitrage **structurant**, car la matrice comptable conditionne directement le cockpit Direction, le suivi financier et les atterrissages.
## Décisions structurantes — à traiter en premier

| ID       | Sujet                     | Question à trancher                                                                                                                            | Proposition de départ                                                                                                                | Cadre dans la V1                                             |
| -------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------ |
| 🔴 ◆ A01 | Profils et accueils       | Quels profils ont réellement besoin d'un accueil distinct, et quelles sont les trois décisions prioritaires de chacun ?                        | Direction, Fluides/énergie, Maintenance, Technique/CVC, Finances, Patrimoine ; un même utilisateur peut cumuler des rôles.           | `V1 Cockpits` · Accueil personnalisé par profil              |
| 🔴 ◆ A02 | Pivot patrimonial         | Le pivot opérationnel est-il le site, le bâtiment, ou une hiérarchie site > bâtiment > local ? Quelles règles de nommage et de regroupement ?  | Site comme porte d'entrée, bâtiment comme objet physique, local comme niveau fin ; navigation explicite entre les trois.             | `V1 Site 360°` · En-tête Site 360°                           |
| 🔴 ◆ A03 | Droits                    | Qui peut consulter, modifier, décider, réouvrir, administrer les référentiels et exporter, selon quel périmètre ?                              | RBAC par rôle + périmètre ville/service ; toute décision ou réouverture est nominative et auditée.                                   | `V1 Fondations` · Permissions par rôle et périmètre          |
| 🔴 ◆ A04 | Identité facture          | Quelle clé rend une facture unique chez EDF, ENGIE, TotalEnergies et les autres fournisseurs, y compris les avoirs et factures corrigées ?     | Fournisseur + type de document + numéro + marché/lot ; période et montant comme garde-fous, jamais comme unique identité.            | `V1 Historique factures` · Calculer la clé stable de facture |
| 🔴 ◆ A05 | Facture traitée           | À quel événement une facture devient-elle « traitée » ? Qui peut la réouvrir et pour quels motifs ?                                            | Traitée après décision horodatée et attribuée ; réouverture réservée aux rôles autorisés avec motif obligatoire.                     | `V1 Historique factures` · Facture déjà traitée ?            |
| 🔴 ◆ A06 | Contacts marchés          | Qui crée et maintient les contacts entreprise par marché/lot ? Faut-il un contact principal et une escalade ?                                  | Contact principal + escalade, dates de validité, contrôle des données manquantes à l'activation du marché.                           | `V1 Réclamations` · Identifier contact principal et escalade |
| 🔴 ◆ A07 | Envoi des réclamations    | Confirme-t-on pour la V1 l'ouverture de la messagerie/copie/.eml, ou exige-t-on l'envoi direct depuis la plateforme ?                          | V1 : brouillon relu puis envoyé depuis la messagerie habituelle ; envoi direct seulement après validation d'un besoin mesuré.        | `V1 Réclamations` · Quel mode d'envoi ?                      |
| 🔴 ◆ A08 | Budget de référence       | Quelle source fait foi pour le budget initial, les décisions modificatives et les versions du prévisionnel ?                                   | Import budgétaire versionné ; budget initial immuable, décisions modificatives et prévision courante séparées.                       | `Budget` · Définir budget initial et révisions               |
| 🔴 ◆ A09 | Exécution financière      | Quelles sources fournissent engagements, services faits, factures et mandats, à quelle fréquence et avec quels identifiants de rapprochement ? | Imports séparés et datés, rapprochés par exercice, marché, tiers, imputation et pièce ; niveau de fraîcheur visible.                 | `Budget` · Importer réalisé / engagements                    |
| 🔴 ◆ A10 | Couverture maintenance    | Quelle règle permet de déclarer un site couvert, partiellement couvert, ambigu, en chevauchement ou non couvert ?                              | Couverture calculée au niveau site + bâtiment + famille d'équipement, avec dates d'effet et exceptions explicites.                   | `Maintenance` · Calculer couverture par site                 |
| 🔴 ◆ A11 | Marché SPIE               | Quels documents, lots, familles d'équipements, sites et périodes composent exactement le périmètre SPIE ?                                      | Même modèle de rattachement versionné que DALKIA, sans supposer qu'un contrat couvre automatiquement tout un site.                   | `Maintenance` · Importer contrat SPIE                        |
| 🔴 ◆ A12 | Atterrissage consommation | Quelle méthode de référence utiliser pour l'atterrissage kWh : tendance, DJU, historique comparable, effet calendrier, changements d'usage ?   | Méthode explicable par fluide et site, comparaison N-1 corrigée DJU, données récentes pondérées, hypothèses visibles et modifiables. | `Fluides` · Calculer atterrissage annuel kWh                 |
| 🔴 ◆ A26 | Matrice comptable       | Quelles dimensions doivent être communes au budget, aux engagements, factures, mandats et atterrissages ?    | Exercice, service, fonction, nature, opération, marché/lot, fournisseur, site/bâtiment et fluide, avec tables de correspondance versionnées. | `Budget` · Matrice comptable et règles de nature          |

## Choix de conception — à travailler pendant la refonte

| ID       | Sujet                   | Question à travailler                                                                                        | Proposition de départ                                                                                                                        | Cadre dans la V1                                          |
| -------- | ----------------------- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| 🟠 ◇ A13 | Conversion en euros     | Quel prix utiliser pour convertir l'atterrissage kWh en euros lorsque les tarifs changent en cours d'année ? | Réalisé aux prix facturés + reste à consommer aux prix contractuels versionnés, avec scénario prudent optionnel.                             | `Fluides` · Convertir kWh en euros                        |
| 🟠 ◇ A14 | Eau                     | Quel distributeur, quel format et quels compteurs d'eau seront prioritaires ?                                | Préparer le modèle Fluides dès maintenant ; lancer l'intégration seulement après obtention d'un export réel représentatif.                   | `Fluides` · Intégrer eau et compteurs                     |
| 🟠 ◇ A15 | Criticité CVC           | Quels poids donner à vétusté, panne, inconfort, conformité, énergie, coût et absence de redondance ?         | Score transparent, pondérations éditables et justification visible ; jamais de note opaque.                                                  | `CVC/PPT` · Calculer criticité multi-critères             |
| 🟠 ◇ A16 | Programme de travaux    | Quel horizon, quels plafonds annuels et quelles règles d'arbitrage du PPT ?                                  | Horizon 5 ans, urgence réglementaire/sécurité prioritaire, scénarios selon enveloppe budgétaire.                                             | `CVC/PPT` · Construire PPT pluriannuel                    |
| 🟠 ◇ A17 | Contrôle DALKIA         | Quels écarts, tolérances et preuves déclenchent une anomalie P1/P2/P3 ?                                      | Matrice de contrôles versionnée, seuils visibles et drill-down jusqu'au contrat, indice et calcul.                                           | `DALKIA` · Contrôler P1/P2/P3                             |
| 🟠 ◇ A18 | Direction visuelle      | Quelles interfaces de référence expriment le niveau de modernité et de densité souhaité ?                    | Design sobre, dense mais lisible, orienté décisions ; prototype sur les vrais tableaux avant de généraliser.                                 | `V1 Fondations` · Design system et composants métier      |
| 🟠 ◇ A19 | Notifications           | Quelles alertes doivent être immédiates, quotidiennes, hebdomadaires ou seulement visibles dans une file ?   | Pas d'e-mail par défaut ; files de travail dans l'application, digest configurable, urgence réservée aux échéances critiques.                | `V1 Fondations` · Files de travail et notifications       |
| 🟠 ◇ A20 | Documents et preuves    | Combien de temps conserver contrats, factures, imports, décisions et pièces ? Quelles versions font foi ?    | Conservation sans écrasement, métadonnées de provenance et version active explicite ; durée alignée avec les obligations de la collectivité. | `V1 Fondations` · Documents, preuves et versionnement     |
| 🟠 ◇ A21 | Rapports et exports     | Quels rapports récurrents attendent la direction, les finances et les responsables métier ?                  | Commencer par trois exports : contrôle factures, budget/atterrissage, patrimoine technique/PPT ; chaque chiffre conserve sa source.          | `V1 Fondations` · Rapports et exports direction/finance   |
| 🟠 ◇ A22 | Tests utilisateurs      | Quelles personnes réelles représenteront chaque profil et quels critères feront dire « c'est réussi » ?      | Un représentant minimum par profil, scénarios chronométrés, compréhension sans aide et taux de réussite suivis.                              | `V1 Fondations` · Tester les parcours avec chaque profil  |
| 🟠 ◇ A23 | Réclamation fournisseur | Quel ton, quelles informations obligatoires, quelles pièces et quelle demande attendue dans le brouillon ?   | Modèle factuel et court : référence, période, écart, règle, preuve, correction demandée, délai de réponse.                                   | `V1 Réclamations` · Générer objet et corps de réclamation |
| 🟠 ◇ A24 | Cockpit direction       | Quels indicateurs déclenchent réellement une décision de direction, et à quelle maille ?                     | Budget, réalisé, atterrissage, écarts majeurs, risques contractuels, sites non couverts et travaux critiques ; drill-down obligatoire.       | `V1 Cockpits` · Budget, réalisé et risques de dépassement |
| 🟠 ◇ A25 | Qualité des données     | Quels seuils de fraîcheur et de couverture rendent une donnée fiable, dégradée ou inutilisable ?             | Afficher source, dernière mise à jour, période couverte et niveau de confiance ; ne jamais masquer une donnée incomplète.                    | `V1 Site 360°` · Qualité et fraîcheur de chaque source    |

## Séquence d'ateliers proposée

1. **90 min — personnes et gouvernance** : A01, A02, A03, A22.
2. **90 min — factures, marchés et finances** : A04 à A09, A23, A26.
3. **90 min — fluides, maintenance et technique** : A10 à A17, A25.
4. **60 min — expérience cible** : A18 à A21, A24.

Il n'est pas nécessaire de tout trancher avant de coder. Le démarrage raisonnable est : valider ou cadrer les treize arbitrages structurants, prototyper le cockpit et le dossier facture, tester avec de vraies données, puis fermer progressivement les choix de conception.


## Annexe — réponses utilisateur brutes

> Cette annexe conserve les formulations originales saisies le 24 juin 2026. Elles ne sont pas corrigées ni raccourcies.

### A01

Les réponses ci-dessous sont le fruit de mon retour d'expérience au sein de la collectivité, je peux malheureusement passer à côté d'éléments pertinents que tu dois être capable d'identifier et me proposer.

- Direction : Lui sa principale préoccupation et le suivi et la tenue de son budget opérationnel. Pour suivre sa comptabilité il doit avoir une vision sur toutes ses numéros d'opérations comptables à l'aide de représentation graphique très percutante et simple. Il doit pouvoir aussi avoir un tableau dynamique lui permettant d'avoir une vision général puis d'aller au plus prévis selon le niveau de précision qu'il souhaite. Un premier travail avec le service comptabilité a été mené avec la création d'une matrice comptable "C:\Users\pa.borja\Documents\Po2\saas\energie\DALKIA\COMPTABILITE\analyse_codification_dalkia_enrichie_par_code_contrat (1).xlsx" mais non terminé et puis il reste tous les autre smarchés facturés à travailler. C'est véritablement LA prochaine grosse action transversal que je dois mener. 

Il doit également avoir une vision sur les consommations d'énergies d'un manière globales de la même maniere avec des représentation graphique ultra pertinente et simple. Il doit également pouvoir aller sur une granulométrie plus fine directement au bâtiment ou compteur si besoin et visualiser l'historique.

Un point important que j'ai zappé c'est qu'il doit bien evidemment être capable d'avoir une vision sur l'état actuel du patrimoine d'un point de vue technique idéalement avec des chiffres estimatifs intégré à un plan de travaux pour intégrer cela dans une demande budgétaire pour l'année N+1 mais également avoir un planning de travaux pour les années à venir (je ne maitrise pas assez cela)

La direction doit pouvoir identifier les budgets pour chacun des éléments de la matrice comptable (point à éclaircir : sur quel niveau de détail va le budget ex: uniquement numero opération ou plus bas ?)

- Fluides/énergie 
Alors la personne dédiée à cette mission doit pouvoir identifier rapidement et de manière quotidienne les consommations et les dérives. Ici Elle doit pouvoir visualiser un historique de consommations, comparer, et potentiellement comprendre d'où peut provenir le problème. Pareil elle doit avoir des représentations graphiques de tous les fluides en marchés, mais ici sa source de données doit être les distributeurs d'électricité et de gaz (ENEDIS, GRDF SUEZ (je crois que c'est SUEZ je ne maitrise pas encore le marché). Mais ici une des grosses missions est également le suivi du marché de DALKIA d'un point de vue énergétique, vis à vis des cibles, suivre les avenants et OS de services qui peuvent impacter le marché, avoir une projection/atterrissage vis à vis des consommations saisonnières en cours.
- Maintenance
Avoir un vision global de tout

- Technique/CVC
Lui sa mission c'est principalement de suivre le marché de maintenance d'un point de vue technique et financier. Dès qu'il y a un problème technique les agents de la collectivité le contact pour faire un prédiagnostic et solliciter l'entreprisre de maintenace pour du P3 généralement. La plateforme doit lui permettre de vérifier que les demandes de devis P3 que lui soumet via la plateforme le titulaire du marché (DALKIA) sont conforme au BPU.
Mais également il peut arriver que des agents l'appelle pour lui demander où en est la maintenance (P2) du site mais qu'il s'aperçoive que le site n'est pas en marché. Il doit alors être capable d'éditer un ordre de service à faire valider par la direction intégrant les équipements et l'impact budgétaire. Ainsi la plateforme devrait pouvoir de proposer un formulaire d'édition d'ordre de service au service maintenance, une fois validé émission au directeur. Le tiers titulaire DALKIA doit pouvoir déposer ses demandes de devis P3 sur la plateforme, une notification est envoyé pour contrôle/validation même si la plateforme doit déjà contrôle la conformité conformément au BPU du marché.

Lui doit pouvoir affiner le plan pluri annuel de travaux c'est lui en collaboration avec l'entreprise de maintenance, notamment à l'issu des réunions annuels, qui doit pouvoir fournir une base de données des équipements CVC à jour.

- Finances
Alors gros sujet, la comptable de la ville reçois via un outil de comptabilité interne nommé CIRIL des notifications comme quoi des factures sont en attentes de validation. Elles proviennent des marché de hérault énergie pour lequel nous avons un BPU pour le paiement des factures relatives aux consommations électricité et gaz des batiments (ENEDIS et total énergie), la une autre comptable elle s'occupe des factures de EDF car rattaché au service voirie pour l'éclairage publique. La première comptable s'occupe aussi des factures du marché de DALKIA. L'inconvénient c'est que ces factures sont sous format PDF quand elles les recoivent. L'idée c'est que j'importe au format xlsx ces factures dans la plateforme pour que laplateforme puisse les contrôler selon les pièces marchés. UNe fois contrôler elles doivent remettre une fichier de liason au service finance qui va valider la facture. Mais la facture peut aussi ne pas être validé par la plateforme auquel cas la comptable doit pouvoir emettre un mail au réfèrent du marché pour avoir des explications ou un rectificatif. Il faut donc pourvoir identifie rle référent de chacun des marchés côté tiers facturant. Les comptables doivent également pouvoir faire le suivi de la facturation un peu à l'image de ce qu'on a identifié au niveau de la direction.

- Patrimoine
On doit pouvoir maitriser le patrimoine dont est on est propriétaire et locataire de la ville. Chacune des ces entités sont soumis ou non à un devoir d'entretien de notre part en terme de maintenance. Tout comme leur état de vétusteté.

- un même utilisateur peut cumuler des rôles.

### A02

Site comme porte d'entrée, bâtiment comme objet physique, local comme niveau fin ; navigation explicite entre les trois.

### A03

Toute demande de modification doit passer par moi "Administrateur général". la lecture peut se faire par tout le monde. D'ailleurs toute personne enregistré sur le site aura accès dans un premier temps à tous les services. Par la suite selon le rôle de la personne uniquement à ses fonctionnalités désignés. A l'inscription la personne doit pouvoir identifier son rôle, lui donnant alors accès à l'espace qui lui est concerné

### A04

Fournisseur + type de document + numéro + marché/lot ; période et montant comme garde-fous, jamais comme unique identité. Attention le destinataire des factures est hyper important

### A05

Vu dans A01

### A06

La responsable des Fluides/énergie doit pouvoir gérer les contrats de hérault énergie, DALKIA uniquement P1 et de l'eau.

### A07

On doit pouvoir proposer l'édition d'un brouillon relu puis envoyé depuis la messagerie habituelle

### A08

Import budgétaire versionné ; budget initial immuable, décisions modificatives et prévision courante séparées.

### A09

Comprendre depuis ce qui a été écrit en A01

### A10

Couverture calculée au niveau site + bâtiment + local + famille d'équipement, avec dates d'effet et exceptions explicites.

### A11

Nous disposons d'une liste de bâtiments, d'un inventaire technique CVC. Il n'existe qu'un LOT. Le rattachement se fait à l'image de ce qu'on fait pour l'inventaire DALKIA, au bâtiment.

### A12

Méthode explicable par fluide et site, comparaison N-1 N-2 N-3 corrigée DJU, données récentes pondérées, hypothèses visibles et modifiables.

### A13

Réalisé aux prix facturés + reste à consommer aux prix contractuels versionnés, avec scénario prudent optionnel.

### A14

Ne rien prévoir pour l'instant, j'ai des problèmes d'accès à leur plateforme

### A15

Score transparent, pondérations éditables et justification visible ; jamais de note opaque.

### A16

Horizon 5 ans, urgence réglementaire/sécurité prioritaire, scénarios selon enveloppe budgétaire.

### A17

Pour DALKIA le P1 se contrôle via le rôle fluide, le P2 doit se faire via le rôle Technicien/CVC actuellement aucun travail de parsing du fichier xlsx n'a été réalisé mais le fichier se trouve dans "C:\Users\pa.borja\Documents\Po2\saas\energie\DALKIA\MAINTENANCE\export_maintenance_20260624.csv" pour commencer le travail, le P3 aussi via le rôle Technicien/CVC

### A18

Design sobre, dense mais lisible, orienté décisions ; prototype sur les vrais tableaux avant de généraliser.

### A19

Pas d'e-mail par défaut ; files de travail dans l'application, digest configurable, urgence réservée aux échéances critiques.

### A20

Conservation sans écrasement, métadonnées de provenance et version active explicite ; durée alignée avec les obligations de la collectivité. Sujet à peut être revoir plustard

### A21

Commencer par trois exports : contrôle factures, budget/atterrissage, patrimoine technique/PPT ; chaque chiffre conserve sa source.

### A22

_Aucune réponse saisie._

### A23

Modèle factuel et court : référence, période, écart, règle, preuve, correction demandée, délai de réponse.

### A24

_Aucune réponse saisie._

### A25

_Aucune réponse saisie._

### A26

_Aucune réponse saisie._
