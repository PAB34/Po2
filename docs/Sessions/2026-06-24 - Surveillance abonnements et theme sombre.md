# Session — Surveillance des abonnements et thème sombre

> Date : 2026-06-24

## Objectif

Compléter le parcours Fluides avec une surveillance du calibrage des abonnements et adapter le prototype au thème système de l’utilisateur.

## Réalisé

- ajout du bloc `Abonnements à recalibrer` dans le prototype Fluides ;
- distinction distributeur/mesure et fournisseur/contrat ;
- méthode électricité basée sur les courbes ENEDIS 30 minutes et la puissance souscrite EDF/ENGIE ;
- méthode gaz basée sur GRDF, CAR, profils et contrat TotalEnergies ;
- méthode eau prévue selon la granularité réelle de télérelève ou d’index ;
- ajout des modes `Automatique`, `Sombre` et `Clair`, avec persistance locale ;
- mise à jour du contrat d’écran, du backlog, de l’index et du journal d’état.

## Vérifications

- chargement du prototype et exécution du JavaScript constatés ;
- thème automatique résolu en sombre lorsque le navigateur expose la préférence Windows sombre ;
- bascule manuelle du thème constatée ;
- serveur local disponible sur `http://127.0.0.1:8765/`.

## Suite

Le raccordement réel demandera un moteur de recommandation versionné, des paramètres contractuels historisés et une règle de confiance liée à la couverture des courbes de charge ou relevés.


## Complément — drill-down explicable

Le prototype inclut désormais une fiche de calcul par abonnement. Elle montre le lien entre contrat, mesure et recommandation, ainsi que la couverture, la fraîcheur, les étapes du calcul et l’action humaine attendue. Les cas électricité, gaz et eau utilisent des méthodes distinctes.
