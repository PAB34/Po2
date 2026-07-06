# Cahier de reprise IA — Modèle de value betting boosté

## Contexte

Je dispose déjà d’une application / d’un premier modèle de pronostics orienté football, notamment autour de la Ligue 1.  
Je dispose également de connecteurs API permettant de récupérer des données de matchs et d’autres informations utiles.

L’objectif est de faire évoluer ce projet vers un modèle de **value betting boosté**, centré sur la détection de sélections à espérance positive, puis sur la construction de combinés boostés.

Le développement doit se faire de manière **statistique, testable et progressive**.  
Le front ne doit pas être prioritaire.  
La priorité absolue est de valider le modèle par backtest avant tout test réel.

---

## Objectif général

Construire un moteur capable de :

1. récupérer et historiser les cotes disponibles à différents instants ;
2. convertir les cotes en probabilités implicites ;
3. retirer la marge bookmaker ;
4. comparer la probabilité de marché sans marge avec la probabilité issue du modèle ;
5. calibrer les probabilités ;
6. détecter les sélections à value positive ;
7. construire des tickets combinés boostés ;
8. tenir compte des corrélations, notamment lorsque plusieurs paris concernent le même match ;
9. backtester la stratégie sans fuite d’information ;
10. produire des indicateurs fiables avant tout développement front.

---

## Principe fondamental

La stratégie ne doit pas être formulée comme :

> Je cherche des petites cotes sûres.

Elle doit être formulée comme :

> Je cherche des écarts statistiquement mesurables entre la probabilité réelle estimée, la probabilité implicite du bookmaker, et la cote boostée obtenue en combiné.

La formule centrale est :

```text
EV_ticket = P_ticket_corrigée × cote_boostée - 1
```

Il ne faut jamais utiliser naïvement :

```text
EV_ticket = produit des probabilités individuelles × cote_boostée - 1
```

lorsque certaines sélections sont corrélées.

---

## Règles de développement imposées

L’IA ne doit pas commencer par le front.

L’IA ne doit pas proposer immédiatement une nouvelle architecture backend complète.

L’IA doit d’abord :

1. auditer le projet existant ;
2. comprendre les connecteurs API déjà disponibles ;
3. comprendre le modèle actuel ;
4. identifier les données déjà stockées ;
5. vérifier la qualité et la profondeur historique des données ;
6. poser les questions nécessaires ;
7. proposer un plan de validation statistique ;
8. implémenter ou corriger le noyau mathématique ;
9. lancer les tests ;
10. backtester ;
11. corriger ;
12. retester ;
13. demander validation avant de passer à l’étape suivante.

Le front ne doit venir qu’après validation statistique du modèle.

---

## Questions que l’IA doit poser avant de développer

### Questions sur le projet existant

1. Quel langage et quels frameworks sont utilisés actuellement ?
2. Le modèle Ligue 1 actuel est-il un script, un service, une API ou un module intégré ?
3. Les connecteurs API existants récupèrent-ils :
   - calendrier ;
   - résultats ;
   - statistiques équipes ;
   - xG ;
   - compositions ;
   - blessures ;
   - cotes ;
   - historique des cotes ;
   - résultats de marchés de paris ?
4. Les données sont-elles horodatées précisément ?
5. Les cotes récupérées sont-elles datées par snapshot ?
6. Quelle profondeur historique est disponible ?
7. Les données permettent-elles de reconstituer ce qui était connu à une date donnée ?
8. Les résultats des paris sont-ils déjà normalisés ?
9. Les matchs annulés, reportés, void ou abandonnés sont-ils identifiés ?
10. Le modèle existant produit-il une probabilité ou seulement un pronostic ?

### Questions sur les sports et marchés

1. Quels sports doivent être intégrés en priorité ?
2. Le football Ligue 1 reste-t-il le périmètre initial ?
3. Le tennis doit-il être ajouté dès maintenant ou dans une deuxième phase ?
4. Quels marchés sont disponibles historiquement ?
5. Quels marchés ont suffisamment d’historique pour être backtestés proprement ?
6. Les règles de règlement des marchés sont-elles connues ?
7. Les cotes sont-elles disponibles sur plusieurs bookmakers ou un seul ?

### Questions sur la stratégie

1. Quelle fourchette de cotes individuelles viser ?
2. La fourchette indicative 1,08 à 1,35 est-elle retenue pour le test initial ?
3. Quelle cote cible viser pour les combinés ?
4. Exemple de cible : cote brute entre 12 et 20.
5. Quel boost doit être simulé ?
6. Le boost est-il fixe ou dépend-il du nombre de sélections ?
7. Combien de tickets doivent être simulés par session ?
8. Quelle mise fictive utiliser en backtest ?
9. La stratégie doit-elle chercher :
   - le meilleur EV ;
   - la meilleure CLV ;
   - le meilleur ROI historique ;
   - la meilleure stabilité ;
   - ou un compromis ?
10. Quel niveau de risque maximal est acceptable ?

---

## Marchés à cibler au départ

La liste ci-dessous n’est pas une vérité statistique absolue.  
Elle n’est pas garantie rentable.  
Elle est proposée parce que ces marchés sont généralement plus simples à modéliser, plus lisibles et plus adaptés à un premier backtest.

La rentabilité devra être prouvée par les données.

### Niveau 1 — Priorité de backtest

#### Football

- over 0,5 but ;
- over 1,5 buts ;
- équipe marque au moins 1 but ;
- double chance ;
- draw no bet ;
- vainqueur match, uniquement si le modèle existant est déjà solide sur ce marché.

#### Tennis

- vainqueur du match.

### Niveau 2 — À tester après validation du niveau 1

#### Football

- équipe gagne + over 1,5 ;
- équipe gagne + équipe marque ;
- double chance + over 0,5 ;
- équipe marque + over 1,5 ;
- qualification, seulement si les règles exactes sont bien intégrées.

#### Tennis

- joueur gagne + adversaire gagne un set ;
- joueur gagne 2-0 ;
- over jeux ;
- handicap jeux.

### Niveau 3 — À éviter au départ

- buteur ;
- passeur ;
- cartons ;
- corners ;
- score exact ;
- temps du premier but ;
- marchés exotiques ;
- combinés complexes sans historique fiable.

Raison : ces marchés sont plus difficiles à modéliser, souvent plus volatils, potentiellement moins liquides, et plus exposés à des marges bookmaker élevées.

---

## Conversion des cotes en probabilités

Pour chaque cote décimale :

```text
probabilité_implicite_brute = 1 / cote
```

Exemple :

```text
cote = 1,25
probabilité_implicite_brute = 1 / 1,25 = 0,80 = 80 %
```

Mais cette probabilité contient la marge bookmaker.

---

## Retrait de la marge bookmaker

Pour un marché à deux issues :

```text
q_A = 1 / cote_A
q_B = 1 / cote_B

overround = q_A + q_B

p_A_sans_marge = q_A / overround
p_B_sans_marge = q_B / overround
```

Exemple :

```text
Joueur A : cote 1,25 → q_A = 80,00 %
Joueur B : cote 4,20 → q_B = 23,81 %

overround = 103,81 %

p_A_sans_marge = 80 / 103,81 = 77,06 %
p_B_sans_marge = 23,81 / 103,81 = 22,94 %
```

Conclusion importante :

```text
Une cote à 1,25 ne signifie pas forcément 80 % de chances réelles.
Après retrait de marge, elle peut plutôt correspondre à environ 77 %.
```

---

## Modèle de probabilité corrigé

Il ne faut pas utiliser arbitrairement une formule fixe du type :

```text
p_final = 70 % marché + 30 % modèle
```

Cette formule peut servir à explorer, mais ne doit pas être considérée comme validée.

La recommandation est d’utiliser le marché comme base, puis de mesurer l’apport réel du modèle.

### Méthode recommandée

Partir de :

```text
p_market_no_vig
```

Comparer avec :

```text
p_model
```

Utiliser une correction en logit :

```text
écart_modèle = logit(p_model) - logit(p_market_no_vig)
```

Puis :

```text
p_final = sigmoid(logit(p_market_no_vig) + λ × écart_modèle)
```

Avec :

```text
λ entre 0 et 1
```

Interprétation :

```text
λ = 0     → confiance totale dans le marché
λ = 0,30  → le modèle corrige légèrement le marché
λ = 1     → confiance forte dans le modèle
```

Le paramètre λ doit être appris ou sélectionné par backtest walk-forward.  
Il ne doit pas être choisi à l’intuition.

---

## Calibration des probabilités

Un modèle peut avoir un bon taux de prédiction tout en étant mauvais en probabilité.

L’IA doit donc mesurer :

```text
Brier score
log loss
courbe de calibration
calibration par tranches de probabilité
```

Exemples de tranches :

```text
50 % - 55 %
55 % - 60 %
60 % - 65 %
65 % - 70 %
70 % - 75 %
75 % - 80 %
80 % - 85 %
85 % - 90 %
90 % - 95 %
```

Pour chaque tranche, comparer :

```text
probabilité moyenne estimée
taux de réussite réel
écart de calibration
```

Si le modèle estime 80 % de probabilité mais que les événements ne passent que 72 % du temps, le modèle est trop optimiste.

---

## Détection de value

Pour chaque sélection :

```text
fair_odds = 1 / p_final
```

Puis :

```text
EV_selection = p_final × cote_disponible - 1
```

Une sélection est théoriquement intéressante si :

```text
EV_selection > 0
```

Mais dans un modèle réel, il faut absorber l’erreur du modèle.  
Il est donc recommandé d’exiger un seuil minimal :

```text
EV_selection > +1 % minimum
EV_selection > +2 % ou +3 % de préférence
```

La fourchette de cote 1,08 à 1,35 ne doit pas être considérée comme une preuve de sécurité.  
Elle doit seulement servir de filtre de stabilité pour le POC.

Exemple :

```text
p_final = 0,84
cote = 1,15

EV = 0,84 × 1,15 - 1
EV = -3,4 %
```

Même à cote basse, le pari peut être mauvais.

---

## Football — Modèle recommandé

Pour le football, le modèle doit idéalement produire une matrice de scores probables.

### Étape 1 — Estimation des buts attendus

```text
λ_home = buts attendus équipe domicile
λ_away = buts attendus équipe extérieur
```

Les lambdas doivent intégrer autant que possible :

```text
xG pour
xG contre
domicile / extérieur
forme récente pondérée
force adverse
absences importantes
rotation probable
fatigue calendrier
enjeu du match
météo si marché lié aux buts
```

### Étape 2 — Matrice des scores

Produire une probabilité pour chaque score :

```text
0-0
1-0
0-1
1-1
2-0
2-1
1-2
3-0
...
```

### Étape 3 — Déduction des marchés

À partir de la matrice, calculer :

```text
P(victoire domicile)
P(match nul)
P(victoire extérieur)
P(double chance 1X)
P(double chance X2)
P(over 0,5)
P(over 1,5)
P(équipe domicile marque)
P(équipe extérieur marque)
P(victoire domicile + over 1,5)
P(victoire domicile + équipe domicile marque)
P(double chance + over 0,5)
```

Avantage majeur : les marchés simples et les marchés combinés du même match sont dérivés d’une même base probabiliste.

---

## Tennis — Modèle recommandé

Pour la première version, limiter le tennis au marché :

```text
vainqueur du match
```

Pour intégrer des marchés plus fins, le modèle devra produire :

```text
probabilité de victoire 2-0
probabilité de victoire 2-1
probabilité de défaite 1-2
probabilité de défaite 0-2
probabilité de nombre de jeux
probabilité de handicap jeux
```

Sans cette granularité, il ne faut pas combiner plusieurs marchés du même match de tennis.

---

## Gestion des paris du même match

Il ne faut pas interdire automatiquement plusieurs paris sur le même match.

La règle correcte est :

```text
Plusieurs paris sur le même match sont autorisés uniquement si la probabilité jointe est calculée.
```

Il est interdit de faire :

```text
P(A ∩ B) = P(A) × P(B)
```

lorsque A et B concernent le même match ou sont manifestement corrélés.

Il faut calculer :

```text
P(A ∩ B)
```

directement.

### Exemple football

Paris :

```text
Équipe A gagne
Over 1,5 buts
Équipe A marque
```

Ces événements sont fortement liés.

Le modèle doit calculer :

```text
P(Équipe A gagne ET over 1,5 ET Équipe A marque)
```

via la matrice des scores.

Il doit additionner uniquement les scores compatibles avec tous les paris du bloc.

Exemple :

```text
2-0
2-1
3-0
3-1
3-2
4-0
...
```

### Règle de bloc

Un ticket doit être découpé en blocs.

Un bloc correspond à :

```text
un événement sportif unique
```

Si plusieurs sélections appartiennent au même match, elles forment un seul bloc.

Ensuite :

```text
P_ticket = produit des probabilités des blocs indépendants
```

et non produit naïf de toutes les jambes.

---

## Construction des tickets boostés

Pour chaque ticket :

```text
cote_brute = produit des cotes
cote_boostée = cote_brute × (1 + boost)
P_ticket = produit des probabilités de blocs
EV_ticket = P_ticket × cote_boostée - 1
```

Le ticket est théoriquement jouable si :

```text
EV_ticket > 0
```

Mais pour absorber l’erreur modèle :

```text
EV_ticket > +3 % minimum
EV_ticket > +5 % de préférence
```

La construction du ticket ne doit pas maximiser uniquement la cote.  
Elle doit maximiser un compromis entre :

```text
EV ticket
stabilité
CLV potentielle
corrélation
exposition événement
qualité des données
niveau de confiance
```

---

## Exposition événement

Même si les blocs sont correctement modélisés, il faut contrôler l’exposition entre plusieurs tickets.

Exemple :

```text
10 tickets générés
7 tickets contiennent le même favori tennis
```

L’exposition est :

```text
7 / 10 = 70 %
```

Cela signifie qu’un seul événement peut détruire 70 % de la session.

Indicateur recommandé :

```text
exposition_événement = nombre de tickets impactés par l’événement / nombre total de tickets
```

Lecture indicative :

```text
< 30 %    → concentration acceptable
30-50 %   → concentration moyenne
> 50 %    → concentration forte
```

Une concentration forte n’est pas automatiquement interdite, mais elle doit être justifiée par une EV plus élevée et affichée clairement dans le backtest.

Règle suggérée :

```text
EV minimum normale : +3 %
EV minimum si forte concentration : +7 % à +10 %
```

---

## CLV — Closing Line Value

La CLV mesure si la cote prise était meilleure que la cote de clôture.

```text
CLV = cote_prise / cote_cloture - 1
```

Exemple positif :

```text
cote_prise = 1,25
cote_cloture = 1,18

CLV = 1,25 / 1,18 - 1
CLV = +5,93 %
```

Exemple négatif :

```text
cote_prise = 1,25
cote_cloture = 1,34

CLV = 1,25 / 1,34 - 1
CLV = -6,72 %
```

La CLV doit être utilisée comme critère de validation du modèle, pas seulement comme indicateur secondaire.

Interprétation :

```text
ROI positif + CLV négative = méfiance, possible chance temporaire
ROI négatif + CLV positive sur petit échantillon = modèle potentiellement intéressant
ROI positif + CLV positive = signal fort
ROI négatif + CLV négative = modèle probablement mauvais
```

---

## Backtest — Règle absolue

Le backtest doit simuler le monde réel.

Il ne doit jamais utiliser une information qui n’était pas disponible au moment théorique de la décision.

### Ordre obligatoire d’un backtest

```text
1. Choisir une date/heure de décision
2. Charger uniquement les données disponibles à cette heure
3. Charger uniquement les cotes disponibles à cette heure
4. Calculer les probabilités marché sans marge
5. Calculer les probabilités modèle
6. Calibrer / appliquer le modèle selon les paramètres appris précédemment
7. Détecter les value bets
8. Construire les combinés
9. Appliquer le boost réellement disponible ou simulé
10. Attendre les résultats
11. Mesurer ROI, CLV, drawdown, calibration et stabilité
```

### Interdictions

Le backtest ne doit jamais :

```text
utiliser les cotes de clôture pour choisir le pari
utiliser une composition officielle si elle n’était pas connue à l’heure du pari
utiliser une blessure connue après coup
utiliser des xG produits après le match
utiliser un classement mis à jour après le match
sélectionner les meilleurs tickets a posteriori
optimiser sur la période de test
```

---

## Validation walk-forward

Le modèle doit être évalué en walk-forward.

Principe :

```text
entraîner sur une période passée
tester sur la période suivante
avancer dans le temps
répéter
agréger les résultats
```

Exemple :

```text
Entraînement : août → décembre
Test : janvier

Entraînement : août → janvier
Test : février

Entraînement : août → février
Test : mars
```

Cela permet de limiter le risque de surapprentissage et de fuite temporelle.

---

## Indicateurs à produire

### Niveau sélection simple

Pour chaque sport et marché :

```text
nombre de sélections détectées
cote moyenne
probabilité marché moyenne
probabilité modèle moyenne
probabilité finale moyenne
fair odds moyenne
EV moyenne estimée
taux de réussite réel
ROI réel
CLV moyenne
Brier score
log loss
calibration par tranches
```

### Niveau bloc même match

Pour chaque bloc :

```text
nombre de sélections dans le bloc
probabilité jointe estimée
cote combinée du bloc
EV du bloc
marchés concernés
résultat réel du bloc
```

### Niveau ticket

Pour chaque ticket :

```text
nombre de blocs
nombre total de sélections
cote brute
boost appliqué
cote boostée
probabilité estimée
EV ticket
résultat
profit/loss
CLV moyenne des sélections
exposition événement
risk score
```

### Niveau session de 10 tickets

Pour chaque session :

```text
nombre de tickets
nombre de tickets gagnants
probabilité estimée d’au moins un gagnant
gain/perte total
ROI session
exposition maximale à un événement
perte maximale possible
événements les plus exposants
```

### Niveau global

```text
ROI global
CLV moyenne globale
drawdown maximal
plus longue série de pertes
volatilité des résultats
performance par sport
performance par marché
performance par fourchette de cote
performance par niveau d’EV
performance par niveau de boost
stabilité par période
```

---

## Simulation Monte Carlo

Pour comprendre la variance de la stratégie, l’IA doit prévoir une simulation Monte Carlo.

Objectifs :

```text
simuler la distribution des résultats
estimer le risque de longues séries perdantes
estimer le risque de drawdown
estimer la probabilité de perdre 10, 20, 50 tickets de suite
estimer la robustesse du ROI
```

La simulation doit utiliser les probabilités estimées des tickets ou des blocs, pas uniquement les résultats historiques bruts.

---

## Taille d’échantillon

Pour des tickets à cote 15 à 20, 100 tickets ne suffisent pas pour conclure.

À cote 15 :

```text
seuil de rentabilité sans boost = 1 / 15 = 6,67 %
```

À cote 20 :

```text
seuil de rentabilité sans boost = 1 / 20 = 5 %
```

Sur 100 tickets, quelques tickets gagnants ou perdants peuvent fortement déformer le ROI.

Objectif recommandé avant test réel :

```text
plusieurs milliers de sélections simples
plusieurs centaines à milliers de tickets simulés
validation par période
validation par sport
validation par marché
validation par niveau de cote
```

---

## Score de risque recommandé

L’IA peut construire un score de risque de 0 à 100.

Ce score ne doit pas remplacer l’EV.  
Il sert à qualifier la fragilité du ticket.

Facteurs possibles :

```text
cote individuelle élevée
EV faible
donnée ancienne
forte variation négative de cote
marché peu liquide
composition incertaine
blessure incertaine
modèle mal calibré sur ce marché
faible historique disponible
corrélation forte
exposition élevée à un événement
```

Lecture indicative :

```text
0-30   → risque faible
31-60  → risque moyen
61-100 → risque élevé
```

---

## Critères de validation avant front

Le front ne doit pas être développé tant que les conditions suivantes ne sont pas remplies :

```text
les cotes sont correctement converties en probabilités
la marge est correctement retirée
les probabilités modèle sont calibrées
les probabilités jointes sont calculées pour les paris du même match
les tickets sont évalués par EV corrigée
le backtest walk-forward fonctionne
les métriques principales sont produites
la CLV est suivie
les risques d’exposition sont mesurés
les résultats sont stables sur plusieurs périodes
les tests automatisés passent
```

---

## Tests minimaux attendus

### Test conversion cote

```text
cote = 1,25
probabilité_implicite = 0,80
```

### Test retrait de marge

```text
cote_A = 1,25
cote_B = 4,20

overround = 1/1,25 + 1/4,20
overround ≈ 1,0381

p_A_sans_marge ≈ 0,7706
p_B_sans_marge ≈ 0,2294
```

### Test EV sélection

```text
p_final = 0,88
cote = 1,16

EV = 0,88 × 1,16 - 1
EV = 0,0208
```

### Test CLV

```text
cote_prise = 1,25
cote_cloture = 1,18

CLV = 1,25 / 1,18 - 1
CLV ≈ 0,0593
```

### Test ticket boosté

```text
cote_brute = 15
boost = 16 %

cote_boostée = 15 × 1,16
cote_boostée = 17,40
```

### Test probabilité minimale rentable

```text
cote_boostée = 17,40

p_min = 1 / 17,40
p_min ≈ 5,75 %
```

### Test corrélation même match

L’IA doit vérifier qu’un ticket contenant :

```text
Équipe A gagne
Over 1,5 buts
Équipe A marque
```

n’est pas évalué par :

```text
P(A gagne) × P(over 1,5) × P(A marque)
```

mais par :

```text
P(A gagne ET over 1,5 ET A marque)
```

via la matrice des scores.

### Test anti-fuite temporelle

Le backtest doit échouer ou alerter si une donnée postérieure à l’heure théorique de décision est utilisée.

---

## Ordre de travail demandé à l’IA

L’IA doit respecter cet ordre :

```text
1. Auditer le projet existant
2. Poser les questions de cadrage
3. Identifier les données disponibles et leur profondeur historique
4. Vérifier les horodatages
5. Vérifier les marchés réellement backtestables
6. Valider les règles de règlement des marchés
7. Implémenter / corriger les fonctions mathématiques pures
8. Écrire les tests unitaires
9. Tester la conversion cote → probabilité
10. Tester le retrait de marge
11. Tester l’EV sélection
12. Tester la CLV
13. Tester l’EV ticket boosté
14. Tester les probabilités jointes même match
15. Mettre en place le backtest walk-forward
16. Produire les métriques par sélection, bloc, ticket et session
17. Corriger le modèle selon les résultats
18. Retester
19. Demander validation
20. Préparer seulement ensuite un front minimal
```

---

## Instruction finale à l’IA

Tu dois reprendre le développement de cette application de manière incrémentale.

Ne commence pas par le front.

Ne propose pas immédiatement une refonte backend ou une nouvelle base de données.

Commence par comprendre le code existant, les connecteurs et le modèle actuel.

Pose-moi les questions nécessaires avant de modifier le projet.

Ensuite, concentre-toi sur la validation statistique :

```text
probabilité marché sans marge
probabilité modèle
calibration
EV sélection
probabilité jointe des paris du même match
EV ticket boosté
CLV
exposition événement
backtest walk-forward
Monte Carlo
```

À chaque étape :

```text
explique ce qui a été fait
liste les fichiers modifiés
lance les tests
corrige les erreurs
présente les résultats
demande validation avant de passer à l’étape suivante
```

Le front ne doit être développé qu’après validation du modèle par backtest.

---

## Résumé opérationnel

Le modèle attendu repose sur cinq piliers :

```text
1. Probabilité marché sans marge
2. Modèle personnel calibré
3. Probabilités jointes pour les paris du même match
4. Backtest walk-forward sans fuite d’information
5. EV ticket boosté + CLV + contrôle d’exposition
```

Le modèle ne doit jamais considérer une cote basse comme sûre.

Le modèle doit prouver statistiquement que le boost compense la marge cumulée, le risque de corrélation et l’erreur de probabilité.

Tant que cette preuve n’est pas établie, l’application doit rester en mode simulation / backtest.
