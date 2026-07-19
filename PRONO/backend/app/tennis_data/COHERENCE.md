# Module de cohérence des picks tennis (v1)

Qualifie la relation logique entre picks d'un même match (et d'un ticket). Le module
**ne recalcule jamais** les probabilités des sous-modèles : il pose des drapeaux.

## Source des corrélations

Corrélations **empiriques** calculées sur l'historique de matchs terminés
(`app.tennis_calibration.HistoricalCalibration.records`, **41 434 matchs** : ATP 27 411,
WTA 14 023). L'a priori tennis sert uniquement à choisir *quelles* paires calculer, jamais
à fixer une valeur en dur.

6 marchés « match » (le favori = le mieux classé au ranking) :
`over_22_5`, `three_sets`, `tiebreak`, `favorite_2_0`, `favorite_2_1`, `favorite_cover_2_5`.

Hors v1 (échantillons trop minces / jointure incertaine) : props joueur (aces, doubles
fautes, breaks) × marché. Signalés « hors matrice v1 », jamais flaggés à tort.

## Métrique et seuils

- **phi** (corrélation de deux binaires) par paire, par circuit (ALL/ATP/WTA) et par
  *bin de force du favori* (seuils de proba 0.60/0.70/0.80/0.90).
- Un *pick* est un couple `(marché, côté)`. Passer au côté opposé (ex. Under = NON over_22_5)
  **inverse le signe** du phi.
- Classement du phi signé du couple de picks :
  - `|phi| < 0.10` → **quasi indépendant**
  - `0.20 ≤ |phi| < 0.35` → relation **modérée** (flaggée)
  - `|phi| ≥ 0.35` → relation **forte** (flag prioritaire)
  - phi signé **> 0** entre les deux picks joués → **redondance** (combiné mal payé / refusé)
  - phi signé **< 0** → **tension** (les picks se contredisent)
- **`MIN_SAMPLE = 200`** : sous ce seuil pour une paire, relation `non_evaluee` — jamais de
  drapeau silencieusement faux.

Justification des seuils : sur binaires le phi est atténué vs une corrélation continue ;
0.20 marque déjà une co-occurrence nette, 0.35 une dépendance forte. Avec n en milliers ces
valeurs sont très significatives. Tout est ajustable en tête de `tennis_coherence.py`.

## Probabilité jointe corrigée (`check_ticket`)

Pour une paire **intra-match**, on estime la vraie proba jointe par la **fréquence jointe
historique conditionnée au bin de force du favori** (les cases de la table 2×2 déduites des
marges du bin et de `p_ab`). Choix v1 vs copule gaussienne :

- **Retenu** : fréquence historique du bin. Aucune hypothèse de structure de dépendance,
  directement lisible, suffisant pour l'usage « ce combiné se contredit / est redondant ».
- **Écarté en v1** : copule gaussienne. Elle n'est justifiée que si l'on veut la proba jointe
  **spécifique aux probas exactes du match** (ex. cet Under=59 %, ce 3-sets=36 %) plutôt qu'aux
  marges historiques du bin. Report en v2 si besoin de ce raffinement.

La sortie précise `note: "marges du bin, pas les probas exactes du match"` pour rester honnête.
Les paires **inter-matchs** sont traitées comme **indépendantes** (matchs distincts) et comptées
à part.

## Sorties

- `coherence_flags(picks, circuit)` → drapeaux tension/redondance d'un match (ajouté à
  l'export match sous `coherence_flags`).
- `check_ticket(selections)` → `selections = [{match_id, market, side, circuit?, bin?}]` :
  paires intra-match (relation + proba jointe), paires inter-matchs (indépendantes), picks
  non évalués (hors matrice ou n < seuil).

## Corrélations principales (ALL, n=41 434)

| Paire | phi |
|---|---|
| over_22_5 × three_sets | **+0.825** (→ Under × 3 sets = −0.825) |
| favorite_2_0 × favorite_cover_2_5 | +0.755 |
| favorite_2_1 × three_sets | +0.685 |
| favorite_2_0 × three_sets | −0.648 |
| favorite_2_0 × over_22_5 | −0.563 |
| over_22_5 × tiebreak | +0.412 |
| favorite_cover_2_5 × over_22_5 | −0.312 |
| favorite_cover_2_5 × three_sets | −0.296 |
| three_sets × tiebreak | +0.189 |

## Régénérer la matrice

```bash
python -m app.tennis_coherence --summary          # recalcule + écrit coherence_matrix.json + tableau
python -m app.tennis_coherence --min-sample 300   # seuil personnalisé
```
La config `coherence_matrix.json` est **versionnée** (commitée) et rechargée au runtime.
