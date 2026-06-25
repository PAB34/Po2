# 34 - Contrat d'écran Fluides V1

> Date : 2026-06-24  
> Statut : décisions utilisateur consolidées ; contrat UX prêt à prototyper, raccordement backend partiel.  
> Source métier : document 33, carte BPMN V1 et audit du code existant.

## 1. Finalité

L'écran `Fluides` doit permettre de répondre rapidement à quatre questions :

1. Comment évoluent les consommations réelles du patrimoine ?
2. Quels sites ou compteurs dérivent et pourquoi ?
3. Où devrait se situer la consommation en fin d'année ?
4. Quel impact financier peut être estimé à partir des prix contractuels ?

La consommation physique affichée provient des distributeurs : ENEDIS pour l'électricité, GRDF pour le gaz et, à terme, le distributeur d'eau. Les factures ne remplacent jamais les volumes distributeurs ; elles servent à contrôler et valoriser les consommations.

## 2. Décisions utilisateur intégrées

- porte d'entrée : portefeuille de tous les sites ;
- fluides visibles : électricité, gaz et eau ;
- eau visible avec un badge `À construire`, sans simuler de données ;
- comparaison principale : année en cours contre N-1 corrigée du climat lorsque pertinent ;
- comparaisons secondaires : N-1 brute, N-2, N-3 et moyenne trois ans ;
- lectures saisonnières : hiver et été ;
- niveaux temporels : mensuel, journalier, puis courbe de charge 30 minutes ou horaire ;
- atterrissage : scénario central accompagné d'une fourchette basse/haute ;
- scénario corrigé manuellement possible, avec motif et historique ;
- navigation : portefeuille → site → compteur PRM/PCE/compteur d'eau.

## 3. Règles climatiques

La correction climatique doit être appliquée uniquement lorsqu'elle possède un sens physique :

| Usage | Indicateur | Règle |
|---|---|---|
| Chauffage gaz ou électrique | DJU chauffage | Comparer les consommations liées au chauffage à climat équivalent. |
| Climatisation électrique | DJU froid / besoin de froid | Comparer la saison chaude et les besoins de refroidissement. |
| Électricité non thermosensible | Aucune correction par défaut | Montrer la consommation brute et la saisonnalité. |
| Eau | Aucune correction DJU | Comparer brut, saisons et événements connus ; météo/pluviométrie seulement comme contexte futur. |

Une valeur corrigée doit toujours permettre d'afficher la valeur brute, la station météo, la période, les DJU employés et la formule.

## 4. Architecture des écrans

### F01 — Portefeuille Fluides

Route cible : `/fluides`.

C'est la page d'entrée la plus visuelle du domaine. Elle agrège les sites sans noyer l'utilisateur dans le détail compteur.

Sections dans l'ordre :

1. en-tête, période, périmètre et fraîcheur ;
2. sélecteur `Tous · Électricité · Gaz · Eau — À construire` ;
3. KPI physiques, évolution corrigée, couverture et atterrissage ;
4. courbe principale consommation réelle / référence / prévision ;
5. bascule hiver / été et explication climatique ;
6. dérives prioritaires, y compris dérives de courbe de charge ;
7. classement des sites ;
8. qualité et rattachements manquants.

### F02 — Détail d'un site

Route cible : `/sites/:siteId?onglet=fluides`.

Le site présente :

- consommations mensuelles par fluide ;
- évolution brute et corrigée ;
- compteurs rattachés et couverture ;
- atterrissage physique et financier du site ;
- événements expliquant une rupture ;
- accès au détail de chaque compteur.

### F03 — Détail compteur

Routes cibles : `/fluides/electricite/:prm`, `/fluides/gaz/:pce` puis eau.

Niveaux :

- synthèse et identité ;
- consommation journalière ;
- courbe de charge 30 minutes/horaire ;
- profils semaine/week-end ;
- hiver/été et performance climatique ;
- puissance maximale et puissance souscrite pour l'électricité ;
- diagnostic de qualité et historique de collecte.

### F04 — Atterrissage et scénarios

Route cible : `/fluides/atterrissage` ou panneau latéral depuis le portefeuille.

Le calcul expose :

`réalisé distributeur + consommation restante estimée = atterrissage physique`

Puis :

`atterrissage physique × prix variables + parts fixes prévues = atterrissage financier`

La page distingue scénario central, bas et haut. Une correction métier crée une nouvelle version et ne remplace jamais silencieusement le calcul automatique.

## 5. Contenu de la page portefeuille

### En-tête

- titre `Fluides & consommations` ;
- exercice et période d'observation ;
- filtres patrimoine, usage, antenne et qualité ;
- date de dernière donnée ENEDIS et GRDF ;
- action `Exporter la synthèse`.

### KPI

| KPI | Valeur | Accès détail |
|---|---|---|
| Consommation observée | kWh/MWh et m³ selon le filtre | Ventilation par fluide et site. |
| Évolution | % vs N-1 corrigée ou brute | Méthode, référence et saison. |
| Atterrissage physique | scénario central et fourchette | Formule et hypothèses. |
| Atterrissage financier | euros et écart au budget | Prix contractuels utilisés. |
| Couverture | compteurs et jours couverts | Non rattachés, absents, périmés. |
| Dérives | nombre et impact estimé | File priorisée. |

### Courbe principale

- série réelle année courante ;
- N-1 brute en pointillé ;
- N-1 corrigée du climat si applicable ;
- prévision centrale prolongée jusqu'à décembre ;
- bande basse/haute ;
- annotations : fermeture, travaux, changement d'usage, panne, nouvel équipement ;
- choix mensuel ou journalier selon le niveau.

### Dérives de courbe de charge

Le diagnostic expert recherche notamment :

- talon nocturne anormal ;
- consommation les week-ends ou périodes de fermeture ;
- pointe inhabituelle ;
- plateau permanent ;
- rupture durable par rapport au profil habituel ;
- dépassement ou mauvais calibrage de puissance ;
- trous de données ou courbe de charge inactive.

Chaque dérive affiche la période, le site, le compteur, l'impact, le niveau de confiance et le lien vers la courbe concernée.

### Classement des sites

Colonnes : site, usages, électricité, gaz, eau, évolution corrigée, atterrissage, couverture, dérives et action.

Le classement par défaut privilégie l'impact, pas seulement la consommation absolue.

## 6. États obligatoires

| État | Comportement |
|---|---|
| Chargement | Squelettes conservant la structure de la page. |
| Aucune donnée | Expliquer la source absente et proposer l'action adaptée. |
| Donnée partielle | Afficher la valeur avec couverture, période et confiance. |
| Donnée périmée | Bandeau daté ; ne pas présenter l'atterrissage comme actuel. |
| Compteur non rattaché | Conserver la donnée et proposer le rapprochement patrimoine. |
| Erreur source | Afficher la dernière donnée fiable et l'erreur de collecte séparément. |
| Permission insuffisante | Lecture limitée sans masquer l'existence du domaine. |
| Eau non raccordée | Carte pédagogique `À construire` : données attendues, bénéfices et dépendances. |
| Prévision impossible | Expliquer l'hypothèse ou la source manquante ; aucun chiffre inventé. |

## 7. Surveillance et calibrage des abonnements

Le domaine Fluides comporte une file `Abonnements à recalibrer`. Elle rapproche les mesures distributeurs des paramètres contractuels actifs et produit une recommandation explicable, jamais une modification automatique du contrat.

### Électricité — ENEDIS et fournisseurs EDF/ENGIE

ENEDIS fournit la mesure ; EDF, ENGIE ou un autre titulaire porte le contrat de fourniture. Le calcul utilise les courbes de charge au pas 30 minutes, les puissances maximales, la saisonnalité, le segment tarifaire et la puissance souscrite.

La recommandation distingue :

- sous-dimensionnement avec risque de dépassement ;
- puissance cohérente ;
- sur-souscription avec économie potentielle ;
- données insuffisantes ou courbe inactive.

Le moteur doit comparer le maximum observé, les percentiles élevés, les profils hiver/été et une marge de sécurité adaptée au segment. Il expose la puissance actuelle, la puissance cible, le risque, le gain estimé et les mois de données exploités.

### Gaz — GRDF et TotalEnergies

Le gaz ne doit pas copier artificiellement la méthode électrique. Le calibrage utilise les consommations GRDF disponibles, le profil hiver, la CAR, le tarif d'acheminement, les capacités ou paramètres contractuels applicables et les composantes fixes du contrat TotalEnergies.

Une recommandation n'est affichée que si les données permettent réellement de comparer le profil observé au contrat. Le P1 DALKIA reste analysé dans le domaine Marchés/CPE, même lorsque la consommation GRDF sert de référence contradictoire.

### Eau

Le calibrage sera activé lorsque la source réelle sera disponible. Selon le distributeur et le contrat, il pourra analyser le diamètre du compteur, l'abonnement, les débits de pointe, le talon permanent, la télérelève et les volumes. Sans télérelève, l'interface affiche une confiance réduite et ne simule pas une courbe de charge.

### Tableau de surveillance

Colonnes minimales : périmètre, distributeur, fournisseur, site/compteur, abonnement actuel, mesure de référence, recommandation, risque, économie potentielle, confiance et action.

Actions : ouvrir le compteur, lire le calcul, créer une tâche, préparer une demande au fournisseur et classer `maintenir` avec justification. Toute évolution contractuelle reste une décision humaine tracée.

### Fiche de calcul d’un abonnement

Le clic sur une recommandation ouvre une fiche latérale sans perdre le portefeuille. Elle contient obligatoirement :

- le diagnostic synthétique et son impact annuel ;
- le paramètre contractuel actuel, la mesure de référence et la cible proposée ;
- la courbe ou le profil réellement utilisé, avec source, fraîcheur et couverture ;
- les étapes du calcul : pointe, percentile, marge, palier et valorisation ;
- le contrat actif, son fournisseur et le risque identifié ;
- les actions humaines `maintenir`, `instruire` ou `préparer la demande fournisseur`.

Pour l’eau ou toute donnée trop pauvre, la même fiche explique pourquoi le calcul est impossible et quelles données sont nécessaires. Elle n’affiche ni cible ni économie fictive.

## 8. Profils et actions

| Action | Fluides | Direction | Technique/CVC | Administrateur |
|---|---:|---:|---:|---:|
| Lire portefeuille et détail | Oui | Oui | Oui | Oui |
| Créer scénario corrigé | Oui | Non | Proposition/commentaire | Oui |
| Valider une hypothèse budgétaire | Proposition | Oui | Non | Oui |
| Gérer sources et collectes | Consultation | Consultation | Consultation | Oui |
| Corriger un rattachement | Proposition | Non | Proposition | Oui / Patrimoine |

Toute correction de scénario contient auteur, date, motif, période, valeur avant/après et pièce éventuelle.

## 9. Raccordement aux capacités existantes

### Déjà disponible ou largement exploitable

| Besoin écran | API/capacité existante | État |
|---|---|---|
| Portefeuille électrique et PRM | `GET /api/energie` | Développé, interface actuelle fragmentée. |
| Audit couverture et fraîcheur ENEDIS | `GET /api/energie/data-ranges`, `GET /api/energie/data-audit` | Développé. |
| DJU mensuels | `GET /api/energie/dju/monthly` | Développé. |
| Détail PRM | `GET /api/energie/{prm_id}` | Développé. |
| Consommation journalière | `GET /api/energie/{prm_id}/daily-consumption` | Développé. |
| Courbe de charge | `GET /api/energie/{prm_id}/load-curve` | Développé, pas 30 minutes. |
| Profils, puissance et calibrage électrique | `annual-profile`, `max-power`, `preconisation` | Développé ; à intégrer dans la file multi-fluides. |
| Performance hiver/été | `dju-performance`, `dju-seasonal` | Développé ; méthode à fiabiliser selon usage. |
| Référentiel PCE GRDF | `GET /api/grdf/pces` | Développé. |
| Consommations gaz mensuelles | `GET /api/grdf/conso/monthly` | Développé. |
| État de collecte GRDF | `GET /api/grdf/conso/status` | Développé. |
| Rapprochement GRDF / P1 DALKIA | `GET /api/grdf/rapprochement-p1/{year}` | Développé, hors portefeuille distributeur principal. |

### À construire ou consolider

- endpoint portefeuille multi-fluides agrégé par site et période ;
- agrégation mensuelle/journalière GRDF par site ;
- moteur de détection des dérives de courbe de charge ;
- moteur d'atterrissage physique central/bas/haut ;
- conversion financière par versions de prix et parts fixes/variables ;
- scénarios manuels versionnés et journalisés ;
- événements métier annotant les séries ;
- eau : référentiel compteurs, import/API, séries, couverture et rapprochement ;
- contrat de données commun pour les graphiques temporels.

Les consommations DALKIA issues de ses exports restent dans le domaine Marchés/CPE. Elles peuvent servir de comparaison contractuelle, mais ne remplacent pas les données distributeurs du portefeuille Fluides.

## 10. Critères d'acceptation UX

1. Un utilisateur identifie en moins de 30 secondes les trois sites qui dérivent le plus.
2. Il distingue sans ambiguïté consommation brute, corrigée et prévisionnelle.
3. Il peut passer du patrimoine au site puis au compteur sans perdre ses filtres.
4. Toute valeur affiche source, période, couverture et fraîcheur.
5. Une courbe de charge permet de repérer nuits, week-ends et ruptures.
6. L'atterrissage expose formule, hypothèses et fourchette.
7. Une correction manuelle reste distincte du calcul automatique.
8. La page Eau est visible comme chantier futur, sans fausses données.
9. Une recommandation d’abonnement affiche mesure, contrat, marge, économie, risque et confiance.
10. Aucun volume issu d'une facture n'est présenté comme une mesure distributeur.
11. Les données non rattachées ou incomplètes ne disparaissent jamais.

## 11. Ordre de réalisation recommandé

1. prototyper F01 Portefeuille Fluides avec données simulées réalistes ;
2. réutiliser le détail PRM existant pour F03 électricité ;
3. créer le détail PCE gaz sur le même contrat temporel ;
4. construire l'endpoint portefeuille unifié ;
5. développer l'atterrissage physique puis financier ;
6. ajouter scénarios et annotations métier ;
7. préparer Eau avec le badge `À construire` jusqu'à obtention d'une source réelle.
