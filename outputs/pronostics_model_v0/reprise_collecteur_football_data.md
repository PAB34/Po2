# Reprise - Collecteur football-data.org pour modele pronostics CDM 2026

Date: 2026-06-08

Objectif: permettre a une autre IA ou a un prochain thread de reprendre le travail sans contexte oral.

## Contexte produit

Le projet contient une application de pronostics Coupe du Monde 2026 accessible via:

- `https://patrimoineaucarre.com/pronostics`

L'objectif courant n'est pas de modifier l'app publique, mais de construire puis alimenter un modele de pronostic probable dans Excel.

Un classeur v0 existe deja ici:

- `C:/Users/pa.borja/Documents/Po2/outputs/pronostics_model_v0/modele_pronostics_cdm2026_v0.xlsx`

Ce classeur contient notamment:

- `02_Equipes`
- `03_Joueurs_Retenus`
- `04_Synthese_Joueurs`
- `05_Matchs`
- `06_Diagnostic_Match`
- `07_Modele_Probable`
- `08_Sources`

Important: le modele final cherche un score probable, pas un tirage aleatoire/fou. Toute logique `RAND`, `fou`, ou score volontairement spectaculaire est hors sujet pour ce modele.

## Source de donnees retenue

Source unique demandee par l'utilisateur:

- football-data.org API v4

Ne pas utiliser d'autres sources pour cette etape.

La cle API n'est pas presente dans le `saas/.env` local, mais l'utilisateur indique qu'elle est presente sur le VPS.

Dans le code, la configuration est:

- `FOOTBALL_DATA_TOKEN`
- `FOOTBALL_DATA_BASE_URL=https://api.football-data.org/v4`
- `FOOTBALL_DATA_COMPETITION=WC`
- `FOOTBALL_DATA_SEASON=2026`

Le deploiement VPS charge `saas/.env` via `saas/infra/docker-compose.prod.yml`.

## Audit deja realise

Un audit de compatibilite football-data.org -> modele a ete cree ici:

- `C:/Users/pa.borja/Documents/Po2/outputs/pronostics_model_v0/football_data_org_mapping.md`

Synthese de l'audit:

### Deja recupere par l'app actuelle

- matchs WC groupe
- statut match
- scores finaux
- equipes home/away cote API
- verrouillage match apres score reel

### Recuperable mais pas encore exploite avant ce dev

- liste equipes competition
- `team_api_id`
- nom officiel equipe
- zone / pays / code
- blason
- coach si renseigne
- staff si renseigne
- squad si renseignee
- joueurs, postes, nationalites, date naissance
- club courant joueur si expose
- matchs recents equipe
- wins/draws/losses recents
- buts pour / contre recents
- clean sheets
- matchs recents joueur via `persons/{id}/matches`
- minutes, titularisations, buts, assists, cartons joueur via aggregations
- top scorers competition

### Non recuperable ou non fiable via football-data.org seul

- classement FIFA officiel et points FIFA
- Elo
- xG / xA
- note moyenne joueur
- blessures fiables
- confiance joueur
- fatigue qualitative
- titulaire probable futur
- grinta pays hote / pays voisin
- diaspora / public
- adaptation climat
- fatigue voyage
- cotes bookmakers
- meteo

## Developpement realise dans le backend

Un collecteur football-data.org a ete code mais pas encore commit/push.

Fichiers modifies/ajoutes:

- `saas/backend/app/services/football_data.py` nouveau
- `saas/backend/app/api/routes/pronostics.py` modifie
- `saas/backend/app/schemas/pronostics.py` modifie
- `saas/backend/tests/test_pronostics.py` modifie

### Nouveau service

Fichier:

- `saas/backend/app/services/football_data.py`

Fonction principale:

```python
build_pronostics_model_feed(
    include_player_matches: bool = False,
    recent_team_matches_limit: int = 10,
    recent_player_matches_limit: int = 10,
    date_from: date | None = None,
    client: FootballDataClient | None = None,
) -> dict[str, Any]
```

Comportement:

- si `FOOTBALL_DATA_TOKEN` est absent et qu'aucun client de test n'est fourni: retourne un feed `configured=False`.
- recupere les equipes via `/v4/competitions/WC/teams?season=2026`.
- pour chaque equipe, appelle `/v4/teams/{id}`.
- extrait coach, squad, staff, market value si disponible.
- recupere les matchs recents de chaque equipe via `/v4/teams/{id}/matches`.
- calcule une synthese:
  - played count
  - wins/draws/losses si presents dans `resultSet`
  - goals for
  - goals against
  - clean sheets
  - goals per match
- recupere les top scorers via `/v4/competitions/WC/scorers`.
- optionnellement, si `include_player_matches=true`, enrichit chaque joueur via `/v4/persons/{id}/matches`.

Attention: `include_player_matches=true` peut consommer beaucoup d'appels API si les squads sont completes.

### Nouvel endpoint admin

Fichier:

- `saas/backend/app/api/routes/pronostics.py`

Endpoint ajoute:

```text
GET /api/pronostics/admin/model-feed
```

Parametres:

```text
include_player_matches=false
recent_team_matches_limit=10
recent_player_matches_limit=10
```

Exemples apres deploiement:

```text
https://patrimoineaucarre.com/api/pronostics/admin/model-feed
https://patrimoineaucarre.com/api/pronostics/admin/model-feed?include_player_matches=true
```

Endpoint protege par:

- `get_current_user`

Donc il faut etre authentifie comme utilisateur admin/backend classique, pas comme simple joueur pronostics.

### Nouveau schema

Fichier:

- `saas/backend/app/schemas/pronostics.py`

Schema ajoute:

```python
class PronosticsModelFeedRead(BaseModel):
    configured: bool
    source: str
    competition: str
    season: int
    summary: dict[str, Any]
    coverage: dict[str, Any]
    teams: list[dict[str, Any]]
    players: list[dict[str, Any]]
    competition_scorers: list[dict[str, Any]]
    unavailable_fields: dict[str, str]
```

### Tests ajoutes

Fichier:

- `saas/backend/tests/test_pronostics.py`

Ajouts:

- `FakeFootballDataClient`
- `test_model_feed_reports_unconfigured_without_token`
- `test_model_feed_collects_team_coach_squad_and_recent_form`
- `test_model_feed_can_enrich_player_recent_stats`

Ces tests simulent football-data.org sans appel reseau.

## Verification locale realisee

Commande lancee:

```powershell
& 'C:\Users\pa.borja\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m compileall app tests\test_pronostics.py
```

Resultat:

- compilation OK.

Limite:

- `pytest` n'a pas pu etre lance localement car l'environnement disponible n'a pas `pytest`.
- le runtime Python embarque n'a pas non plus `requests` ni `fastapi`, donc pas de test fonctionnel complet local.

## Etat git au moment de la reprise

Fichiers a verifier/stager si on veut poursuivre ce dev:

```text
saas/backend/app/services/football_data.py
saas/backend/app/api/routes/pronostics.py
saas/backend/app/schemas/pronostics.py
saas/backend/tests/test_pronostics.py
outputs/pronostics_model_v0/football_data_org_mapping.md
outputs/pronostics_model_v0/reprise_collecteur_football_data.md
```

Attention: il y a potentiellement d'autres fichiers non suivis ou modifies dans le repo (`outputs/`, `saas/energie/...`). Ne pas les supprimer ni les revert sans accord utilisateur.

## Prochaine etape recommandee

1. Relire le diff.
2. Lancer les tests dans un environnement backend complet si disponible:

```bash
cd saas/backend
pip install -r requirements.txt
pytest tests/test_pronostics.py
```

3. Commit + push les changements backend.
4. Attendre le deploiement GitHub Actions.
5. Tester sur le VPS avec la vraie cle:

```text
https://patrimoineaucarre.com/api/pronostics/admin/model-feed
```

6. Examiner la reponse reelle:

- `configured`
- `summary.teams`
- `summary.players`
- `coverage.competition_teams`
- `coverage.competition_scorers`
- `teams[].squad_available`
- `teams[].coach`
- `teams[].recent_form`
- `players[]`

7. Ne tester `include_player_matches=true` qu'apres avoir vu le nombre de joueurs, pour eviter trop d'appels API:

```text
https://patrimoineaucarre.com/api/pronostics/admin/model-feed?include_player_matches=true
```

8. Selon la reponse reelle, brancher l'export dans le classeur Excel:

- `02_Equipes`: API id, zone, coach, forme equipe, buts pour/contre, clean sheets.
- `03_Joueurs_Retenus`: joueurs, postes, club courant, nationalite, minutes, buts, assists.
- `04_Synthese_Joueurs`: score forme effectif derive.
- `08_Sources`: endpoint, date de releve, statut retrieved/missing.

## Point de vigilance majeur

football-data.org peut renvoyer des champs `null`, des listes vides, ou des donnees limitees selon le tier de token.

Le code doit donc traiter trois statuts differents:

- `retrieved`: donnee effectivement retournee.
- `missing`: endpoint appele mais champ/liste vide.
- `unavailable`: donnee non exposee par football-data.org.

Ne pas considerer une squad vide comme une erreur technique: c'est possiblement une limite de source/tier ou une indisponibilite temporaire.

## Style attendu par l'utilisateur

L'utilisateur veut avancer vite mais garder une trace claire.

Il prefere:

- decisions nettes,
- fichiers concrets,
- explications simples,
- pas de blabla,
- verification reelle des fonctionnalites.

Il faut lui signaler explicitement quand un test n'a pas pu etre realise.

