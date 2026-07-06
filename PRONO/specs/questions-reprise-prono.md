# Questions de cadrage - reprise PRONO

Objectif de ce fichier : clarifier ce qui doit etre stabilise, teste et priorise avant de continuer a ajouter des fonctionnalites.

Tu peux repondre directement sous chaque question, en remplacant `Reponse :`.

## 1. Objectif court terme

1. Quel est ton objectif prioritaire pour les 1 a 2 prochaines sessions ?

Reponse : Pourvoir me rassurer sur les données réellement récupérable automatiquement et ce que je dois faire en manuel. Pouvoir lancer des test directement depuis le front et voir les résultats.

2. Tu preferes d'abord :
- stabiliser ce qui existe ;
- rendre le test reel plus simple pour toi ;
- brancher de vraies donnees bookmakers ;
- ameliorer le moteur sportif ;
- preparer une premiere interface ;
- autre chose ?

Reponse :- rendre le test reel plus simple pour toi ;- preparer une premiere interface ;

3. A partir de quel moment tu consideres que PRONO est "testable reellement" ?

Reponse : Lorsque j'aurais pu tester via le front des simulations sur des données reels et ajuster le modèle pour correspondre à ce que je veux

## 2. Donnees sportives Ligue 1

4. Acceptes-tu que l'app fonctionne en mode degrade avec des donnees historiques quand aucune journee future Ligue 1 n'est disponible ?

Reponse : bien sur

5. Quand le reseau est indisponible, veux-tu que PRONO utilise le dernier cache disponible meme s'il est vieux ?

Reponse : oui

6. Souhaites-tu que je cree un script de diagnostic simple qui te dise : historique OK, journees futures OK/KO, cache OK/KO, scenarios OK/KO ?

Reponse : oui si ca te semble pertinent

## 3. Donnees bookmakers

7. Dans l'immediat, veux-tu rester sur un import CSV manuel de cotes, ou brancher une API bookmaker gratuite/quasi gratuite ?

Reponse : Il me semblait qu'on récupéré de manière gratuite ces côtes sans souscription API nul part, mais s'il faut le faire je le ferai mais décrit moi ce que je dois faire. As-tu exploré ce que faisait "C:\Users\pa.borja\Documents\Po2\saas\pronostics" ?

8. Les cotes doivent-elles venir de Winamax specifiquement, ou n'importe quel bookmaker suffit pour commencer ? N'importe quel bookmaker pour commencer

Reponse : n'importe quel bookmaker

9. As-tu deja un format CSV cible que tu veux utiliser, ou dois-je imposer un format simple ?

Reponse : pas du tout et pas envie de le faire en manuel

10. Es-tu pret a fournir une cle API The Odds API / autre service si on choisit cette option ?

Reponse : oui si besoin décris moi comment y parvenir

## 4. Regle odds-blind

11. Confirme-tu la regle suivante : le moteur sportif/scenario ne doit jamais utiliser les cotes, bookmakers, EV, CLV, boost ou prix comme features ?

Reponse : Oui

12. La couche betting/value peut-elle utiliser les scenarios sportifs pour comparer ensuite aux cotes et generer des opportunites ?

Reponse : oui

## 5. Tickets et candidats

13. Aujourd'hui, les "ticket families" sont des candidats de recherche, pas encore des tickets jouables. Est-ce le bon niveau pour l'instant ?

Reponse :

14. Quelles familles veux-tu prioriser ?
- safe ;
- buts ;
- fun simple ;
- boostes ;
- combis prudentes ;
- autre ?

Reponse : Toutes

15. Veux-tu que le systeme affiche surtout peu de tickets tres filtres, ou beaucoup d'idees a auditer ?

Reponse : beaucoup d'idees a auditer

## 6. Backtests et validation

16. Quel est le critere minimum pour dire qu'un signal sportif est prometteur ?

Reponse : Point à calibrer ensemble

17. Sur quelle periode veux-tu backtester en priorite ?

Reponse : sur au minimum deux saisons

18. Veux-tu d'abord valider les scenarios sportifs sans aucune cote, puis seulement ensuite tester la value betting ?

Reponse : non

## 7. Ce que tu veux faire toi-meme

19. Quelles actions veux-tu pouvoir faire toi-meme facilement ?
- lancer les tests ;
- lancer l'API ;
- importer un CSV de cotes ;
- consulter les scenarios ;
- consulter les tickets candidats ;
- lancer un backtest ;
- autre ?

Reponse :lancer les tests consulter les scenarios ;
- consulter les tickets candidats ;
- lancer un backtest ;

20. Prefere-tu des commandes PowerShell pretes a copier, ou un script unique qui orchestre tout ?

Reponse : le faire dpeuis le front directement

21. Veux-tu que je documente un mode "test utilisateur" ultra court, en 5 minutes ?

Reponse : non

## 8. Ce que tu attends de Codex

22. Souhaites-tu que je priorise les corrections techniques avant toute nouvelle fonctionnalite ?

Reponse : oui

23. Souhaites-tu que je maintienne une fiche d'etat claire : fonctionne parfaitement, partiellement, non pret, attendu cote utilisateur ?

Reponse : oui

24. Quand tu dis "go", veux-tu que je continue automatiquement selon le plan priorise, ou que je redonne toujours l'etat + prochaine etape avant d'agir ?

Reponse :toujours l'etat + prochaine etape avant d'agir

## 9. Interface

25. Confirme-tu qu'on ne fait pas de front tout de suite ?

Reponse : non

26. Si on prepare plus tard une interface, quelle premiere vue serait la plus utile ?
- tableau des scenarios ;
- import CSV de cotes ;
- couverture bookmakers ;
- tickets candidats ;
- backtests ;
- autre ?

Reponse :ableau des scenarios ;
- import CSV de cotes ;
- couverture bookmakers ;
- tickets candidats ;
- backtests ;

## 10. Priorite proposee par Codex

Ma recommandation actuelle :

1. Corriger la robustesse du chargement des donnees Ligue 1 avec fallback cache.
2. Ajouter un script de smoke test pour que tu puisses verifier le flux reel facilement.
3. Ajouter une courte documentation "comment tester PRONO maintenant".
4. Faire un test reel avec CSV de cotes ou API bookmaker.
5. Ensuite seulement, ajouter post-match review, UI ou nouvelles familles de tickets.

27. Es-tu d'accord avec cette priorite ?

Reponse : oui

28. Si non, quelle priorite veux-tu imposer ?

Reponse : front après avoir suivi tes recommandations
