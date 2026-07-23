# Backtests tennis — que valent les signaux du modèle ?

Trois mesures faites le 2026-07-22 pour répondre à une question simple : parmi tous
les indicateurs affichés par match, lesquels servent réellement à décider ?

Chaque script se relance tel quel et recalcule tout depuis les données brutes.

## 1. `backtest_divergence_elo_forme.py` — Elo et forme contre le classement

```bash
cd PRONO/backend && python backtests/backtest_divergence_elo_forme.py
```

Elo recalculé chronologiquement (K=32) sur `app/tennis_data/tml*`. Compare le
comportement de l'outsider selon que l'Elo et/ou la forme contredisent le classement.

**Résultat (ATP, 20 640 matchs — ticket « prend un set + over 18.5 ») :**

| Groupe | Ticket gagné | Cote juste |
|---|---:|---:|
| Tout concorde | 49,3 % | 2,03 |
| Forme seule contre le favori | 56,0 % | 1,78 |
| Elo seul contre le favori | 60,0 % | 1,67 |
| Elo + forme contre le favori | 61,6 % | 1,62 |

Stable sur trois périodes (+11,6 / +8,7 / +10,6 pt). En WTA, ajouter la forme
**dégrade** le signal (55,6 % → 52,9 %).

## 2. `backtest_elo_vs_marche.py` — le signal survit-il au prix ?

```bash
cd saas/pronostics/Pronos && python <chemin>/backtest_elo_vs_marche.py
```

Utilise `data_cache/td/features_v36.csv` (ATP 2001-2025, cotes réelles dévigottées).
Le test précédent opposait l'Elo au classement ; celui-ci l'oppose **au marché**.

**Résultat (55 049 matchs) :**

| | n | victoires | ROI |
|---|---:|---:|---:|
| Parier l'outsider en général | 42 364 | 30,8 % | −4,9 % |
| Elo d'accord avec le marché | 35 339 | 28,8 % | −5,9 % |
| **Elo contre le marché** | 7 025 | 40,8 % | **−0,0 %** |

**Conclusion majeure** : le signal est réel (+12 pt de victoires) mais le marché le
price presque exactement. Le filtre Elo annule la marge du bookmaker sur le marché
vainqueur, il ne crée pas de profit. Même verdict que `backtest_hangover` : effet
réel, déjà dans le prix.

## 3. `backtest_marches_outsider.py` — quel marché capte le signal ?

```bash
cd saas/pronostics/Pronos && python <chemin>/backtest_marches_outsider.py
```

**Résultat (33 119 matchs) — écart de fréquence divergence vs concordance :**

| Marché | Écart | Cote juste |
|---|---:|---:|
| Outsider gagne le match | +11,7 pt | 2,40 |
| Outsider +3,5 jeux | +10,5 pt | 1,68 |
| Outsider prend ≥ 1 set | +9,5 pt | 1,61 |
| Outsider gagne le set 1 | +8,0 pt | 2,33 |
| Prend un set **et** over 18.5 | +6,9 pt | 1,84 |
| Over 18.5 / 19.5 / 22.5 | +3,3 / +2,9 / +2,5 pt | — |
| Match en 3 sets | +2,3 pt | 2,63 |

**Enseignement** : les marchés de total de jeux ne captent presque rien du signal.
Combiner « prend un set » avec un over fait tomber l'information de +9,5 à +6,9 pt —
l'over est probable mais pas discriminant. Les marchés portant sur le joueur captent
trois à quatre fois plus.

## 4. `backtest_segments_divergence.py` — le ROI nul cache-t-il un segment gagnant ?

```bash
cd saas/pronostics/Pronos && python <chemin>/backtest_segments_divergence.py
```

Le n°2 conclut à un ROI de −0,0 % sur le marché vainqueur. Restait une possibilité :
que cette moyenne soit la somme d'un segment perdant et d'un segment rentable. On
découpe donc les 7 000 paris « Elo contre le marché » par écart Elo, cote de
l'outsider, surface, et par croisement des deux premiers.

**Protocole anti-illusion** — sans lui, ce test ne vaudrait rien : à force de découper,
un segment rentable finit toujours par apparaître.

1. exploration sur **2001-2018**, où l'on regarde tout ;
2. validation sur **2019-2025**, jamais consultée pour choisir les segments ;
3. intervalle de confiance à 95 % sur chaque ROI, et nombre de segments testés affiché.

**Résultat : 26 segments testés, 7 positifs en exploration, 0 confirmé en validation.**

| Segment retenu en exploration | n (validation) | ROI validation | IC 95 % |
|---|---:|---:|---|
| Écart Elo 100-200 pts | 363 | +2,4 % | [−10,3 ; +15,2] |
| Cote outsider 2-3 | 1 633 | +2,8 % | [−2,9 ; +8,5] |
| Écart Elo 100-200 @ cote 2-3 | 314 | +5,2 % | [−7,9 ; +18,4] |
| Surface dure | 1 063 | +1,4 % | [−5,8 ; +8,6] |
| Surface terre | 666 | −3,7 % | [−13,3 ; +5,8] |

Tous les intervalles englobent zéro. **Conclusion** : le −0,0 % global n'est pas une
moyenne trompeuse, c'est un zéro à peu près partout. Le bookmaker price l'Elo dans tous
les segments testés, y compris là où la divergence est la plus violente.

C'est un résultat négatif, et c'est le plus utile de la série : il ferme le marché
vainqueur. L'effort doit porter sur les marchés secondaires — non parce qu'ils sont
prometteurs en soi, mais parce qu'ils sont les seuls dont le prix ne soit pas déjà
mesurable, donc les seuls où le book peut encore avoir tort sans qu'on le sache.

## Limite commune, et pourquoi le journal existe

Les seules cotes archivées portent sur le **vainqueur**. Aucun historique de prix
n'existe pour « prend un set », le handicap jeux ou les totaux. Ces trois backtests
mesurent donc des **fréquences**, pas des gains — sauf le n°2, seul à conclure en ROI.

Un écart de fréquence est une condition nécessaire à une opportunité, jamais une
preuve : le backtest `hangover` montrait un effet net entièrement absorbé par les cotes.

C'est exactement ce trou que comble `app/tennis_journal.py` : en enregistrant le prix
réellement pris sur chaque marché, il rend mesurable ce qu'aucun historique ne permet
de trancher aujourd'hui.
