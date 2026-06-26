# 33 - Dernières questions utilisateur avant les contrats d'écran

> Date : 2026-06-24  
> Objectif : isoler uniquement ce que Pascal doit encore décider. Tout ce qui relève de l'audit, de l'UX détaillée, des API, du prototype ou de la recette est affecté à Codex.  
> Statut : **6/6 réponses consolidées** dans le contrat d'écran Fluides, document 34.

## Réponse courte : que te reste-t-il réellement à faire ?

1. Répondre aux **six questions Fluides** ci-dessous. Tu peux écrire simplement `Proposition validée` lorsque ma recommandation te convient.
2. Fournir les pièces SPIE plus tard, lorsque ce marché entrera réellement dans le chantier : CCTP, CCAP, acte d'engagement, DPGF, avenants/ordres de service, sites et équipements.
3. Relire les conclusions de la future revalidation DALKIA P1/P2/P3. Tu n'as pas à reconstruire les matrices toi-même.

C'est tout. Tu n'as pas à définir les endpoints, les composants React, les états d'erreur, les clés techniques ou les scénarios de test.

---

## QF01 — Porte d'entrée du domaine Fluides

**Question :** lorsque tu ouvres `Fluides`, quelle vue doit apparaître en premier ?

**Proposition Codex :** une vue portefeuille de tous les sites, avec consommation électricité/gaz, évolution, couverture des données, principales dérives et atterrissage annuel. Un clic ouvre le site, puis le compteur PRM/PCE si nécessaire.

**Pourquoi :** cela respecte le principe global → détail et permet de repérer immédiatement les sites qui nécessitent une analyse.

**Ta réponse :**  une vue portefeuille de tous les sites, avec consommation électricité/gaz/eau, évolution, couverture des données, principales dérives et atterrissage annuel. Un clic ouvre le site, puis le compteur PRM/PCE/Compteur eau si nécessaire. C'est probablement la page qui sera le plus vue car elle suscite beaucoup de curiosité. C'est donc une page qui doit vraiment être percutante. ici on ne traite bien entendu uniquement des consommations, données obtenues depuis les distributeurs directement.


---

## QF02 — Comparaison affichée par défaut

**Question :** quelle comparaison doit être visible immédiatement pour juger une consommation ?

**Proposition Codex :** afficher par défaut l'année en cours contre N-1 corrigée des DJU lorsque le fluide dépend du chauffage. L'utilisateur peut ensuite afficher N-1 brute, N-2, N-3 et une référence moyenne trois ans.

**Pourquoi :** une comparaison brute peut faire croire à une amélioration ou une dérive simplement causée par la météo.

**Ta réponse :**  afficher par défaut l'année en cours contre N-1 corrigée des DJU lorsque le fluide dépend du chauffage (elec+gaz)/climatisation elec)/eau . L'utilisateur peut ensuite afficher N-1 brute, N-2, N-3 et une référence moyenne trois ans. L'idéal serait en plus un peu comme on a déjà fait dans l'état de base, c'est à dire des comparaison saisonnière hiver et été. 


---

## QF03 — Granularité temporelle

**Question :** quel niveau de détail doit être privilégié ?

**Proposition Codex :** vue mensuelle pour le pilotage du portefeuille et l'atterrissage ; vue journalière pour analyser une dérive ; courbes horaires ou demi-horaires ENEDIS seulement dans le détail expert d'un compteur.

**Pourquoi :** les courbes très fines sont utiles au diagnostic, mais trop chargées pour piloter 100 sites.

**Ta réponse :**  Il faut savoir qu'on distingue les consommations journalières et les courbes de charges horaires. Une lecture des dérives de courbes de charges est également intéressantes


---

## QF04 — Présentation de l'atterrissage

**Question :** souhaites-tu un seul chiffre prévisionnel ou plusieurs scénarios ?

**Proposition Codex :** afficher un scénario central comme chiffre principal, accompagné d'une fourchette basse/haute. La formule doit montrer séparément : réalisé distributeur, consommation restante estimée, DJU futurs, prix contractuels, parts fixes et parts variables.

**Pourquoi :** le chiffre central reste lisible pour la Direction, tandis que la fourchette rend l'incertitude honnête.

**Ta réponse :**  Proposition validée


---

## QF05 — Modification manuelle d'une prévision

**Question :** un utilisateur Fluides peut-il corriger une hypothèse automatique lorsqu'il connaît un événement futur : fermeture, travaux, changement d'usage ou nouvel équipement ?

**Proposition Codex :** oui. Le profil Fluides peut créer un scénario corrigé avec motif, période, impact et pièce éventuelle. La prévision automatique reste conservée et la Direction voit clairement l'écart entre automatique et corrigé.

**Pourquoi :** une prévision purement statistique ignore les événements métier déjà connus. L'historique empêche néanmoins les corrections invisibles.

**Ta réponse :**  Proposition validée, hyper pertinent


---

## QF06 — Place de l'eau dans la première interface

**Question :** l'entrée Eau doit-elle être visible dès la première refonte alors que les données ne sont pas encore raccordées ?

**Proposition Codex :** conserver `Fluides` comme domaine général, mais ne pas afficher une page Eau vide dans la navigation principale. Prévoir son emplacement dans l'architecture et l'activer dès qu'un export ou un connecteur réel est disponible.

**Pourquoi :** l'architecture reste prête sans donner l'impression qu'une fonctionnalité vide est opérationnelle.

**Ta réponse :**  Non afficher dans la navigation l'eau et avec indication à construire (quelque chose du genre)


---

## Ce que Codex prend désormais en charge sans nouvelle question

- revalider séparément les contrôles DALKIA P1, P2 et P3 ;
- produire les contrats d'écran Facturation, Cockpit, Sites 360° et Fluides ;
- inventorier les API, calculs et données déjà disponibles ;
- signaler précisément les endpoints réellement manquants ;
- étendre le prototype à toutes les pages principales ;
- transformer le prototype validé en tokens et composants React ;
- prévoir chargement, absence de données, erreur, permission et données périmées ;
- constituer un premier jeu de recette à partir des fichiers réels déjà présents dans le dépôt ;
- te demander uniquement les exemples qui manqueraient réellement ;
- définir et exécuter la stratégie de migration progressive du frontend.

## Éléments non bloquants pour commencer la refonte

- le corpus SPIE : il bloque le module SPIE, pas Facturation/Cockpit/Sites/Fluides ;
- l'eau : elle reste prévue dans l'architecture mais n'empêche pas les écrans électricité/gaz ;
- le portail tiers DALKIA : reporté en phase 2 ;
- l'intégration CIRIL : explicitement hors V1.

## Après tes réponses

Les six réponses ont été traitées. Le **contrat d'écran Fluides** et son prototype détaillé sont livrés ; aucune nouvelle réponse générale n'est attendue.
