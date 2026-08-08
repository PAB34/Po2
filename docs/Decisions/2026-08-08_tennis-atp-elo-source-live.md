# ADR — Source live pour l'Elo ATP

- **Date** : 2026-08-08
- **Statut** : accepté
- **Portée** : `PRONO/backend`

## Contexte

La section tennis calcule les probabilités Elo à partir de `joueurs_stats.csv` et de l'historique `tennis_data/tml/`. Le fichier ATP `tml/2026.csv` embarqué provient du dépôt GitHub TennisMyLife, qui est désormais conservé comme référence historique et n'est plus la source live. La source officielle actualisée est `stats.tennismylife.org`, qui publie les CSV annuels.

Conséquence : les Elo ATP deviennent incomplets ou périmés, alors que la WTA conserve une meilleure couverture locale.

## Décision

1. Conserver les fichiers historiques embarqués comme base reproductible et comme repli hors ligne.
2. En production, récupérer le CSV ATP de l'année courante depuis la source officielle TennisMyLife (`https://stats.tennismylife.org/data/{year}.csv`).
3. Mettre ce fichier en cache 24 h dans le volume persistant PRONO et valider son schéma avant remplacement atomique du cache.
4. Recalculer les Elo ATP point-in-time avec la convention déjà utilisée par les backtests du projet : initialisation 1500, K=32, échelle logistique 400, avec un Elo global et un Elo par surface.
5. Injecter ces Elo frais dans `TennisCoach` avant la construction du payload tennis. En cas d'échec réseau ou de fichier invalide, utiliser le dernier cache valide puis, à défaut, les données embarquées.
6. Ne modifier ni le calcul WTA ni l'ancrage marché / les règles de décision.

## Raisons

- Corrige la source de données plutôt que de masquer l'absence d'Elo par le marché.
- Évite de redistribuer les CSV live : ils restent uniquement en cache runtime.
- Préserve un fonctionnement dégradé hors ligne.
- Réutilise la convention Elo déjà testée dans `backtests/` au lieu d'introduire un nouveau modèle.

## Conséquences

- Un accès réseau à TennisMyLife est tenté au maximum toutes les 24 h lors d'un rafraîchissement du payload tennis.
- Les joueurs ATP présents dans l'historique live mais absents de `joueurs_stats.csv` peuvent désormais recevoir un Elo ; leurs autres indicateurs restent prudents/incomplets tant qu'ils ne sont pas présents dans les agrégats locaux.
- Le payload existant et son contrat frontend restent inchangés.
