# Audit football-data.org -> modele pronostics CDM 2026

Date audit: 2026-06-08

Source unique analysee: football-data.org API v4.

## Synthese courte

L'integration actuelle du backend PatrimoineAuCarre utilise deja football-data.org, mais uniquement pour synchroniser les scores reels des matchs termines.

Le modele Excel peut etre partiellement alimente par football-data.org:

- tres bon pour: calendrier, equipes, identifiants API, scores, statuts, resultats, historique de matchs par equipe, buts/passes/minutes agregees par joueur si les joueurs sont presents dans la base API.
- possible mais incertain selon competition/tier: coach, squad, staff, lineups, events, scorers/assists de competition.
- non couvert par football-data.org: etat medical fiable, fatigue qualitative, forme club detaillee hors competitions couvertes, xG/xA, notes moyennes, selection officielle garantie, tactique fine du selectionneur, climat/voyage/public, cotes de bookmakers.

Point local important: `FOOTBALL_DATA_TOKEN` n'est pas configure dans `saas/.env` sur ce poste. On peut donc coder le collecteur, mais pas confirmer par appel reel local sans token.

## Donnees deja recuperees par notre code

| Donnee | Endpoint | Statut actuel | Destination actuelle |
|---|---|---:|---|
| Matchs WC groupe | `/v4/competitions/WC/matches?stage=GROUP_STAGE&season=2026` | Deja appele | Service `sync_scores` |
| Statut match | meme endpoint | Deja recupere | Filtre `FINISHED` / `AWARDED` |
| Score final | `score.fullTime.home/away` | Deja recupere | `PronosticsMatch.real_score1/2` |
| Equipes API home/away | `homeTeam`, `awayTeam` | Deja recupere | Matching avec nos equipes locales |
| Verrouillage match | derive du score final | Deja exploite | `PronosticsMatch.locked=True` |

## Donnees recuperables mais non encore exploitees

| Champ modele | Recuperable football-data.org ? | Endpoint principal | Champ API attendu | Statut dans notre app |
|---|---:|---|---|---|
| `team_api_id` | Oui | `/v4/competitions/WC/teams?season=2026` | `teams[].id` | Non stocke |
| Nom officiel equipe | Oui | `/v4/competitions/WC/teams` ou `/v4/teams/{id}` | `name`, `shortName`, `tla` | Non stocke |
| Zone / pays equipe | Oui | idem | `area.name`, `area.code`, `area.flag` | Non stocke |
| Blason equipe | Oui | idem | `crest` | Non stocke |
| Federation/site/venue historique | Oui mais faible valeur modele | `/v4/teams/{id}` | `address`, `website`, `venue`, `founded` | Non stocke |
| Competition en cours | Oui | `/v4/teams/{id}` | `runningCompetitions[]` | Non stocke |
| Coach nom | Oui, si renseigne | `/v4/teams/{id}` | `coach.name` | Non stocke |
| Coach nationalite | Oui, si renseigne | `/v4/teams/{id}` | `coach.nationality` | Non stocke |
| Coach contrat debut/fin | Oui, si renseigne | `/v4/teams/{id}` | `coach.contract.start/until` | Non stocke |
| Staff | Oui, si renseigne | `/v4/teams/{id}` | `staff[]` | Non stocke |
| Squad joueurs | Oui, si renseigne | `/v4/teams/{id}` ou teams competition | `squad[]` | Non stocke |
| Joueur nom | Oui | `/v4/teams/{id}` / `/v4/persons/{id}` | `name`, `firstName`, `lastName` | Non stocke |
| Joueur poste | Oui | idem | `position` | Non stocke |
| Joueur date naissance | Oui | idem | `dateOfBirth` | Non stocke |
| Joueur nationalite | Oui | idem | `nationality` | Non stocke |
| Joueur numero | Oui si renseigne | idem | `shirtNumber` | Non stocke |
| Joueur club courant | Oui via personne | `/v4/persons/{id}` | `currentTeam` | Non stocke |
| Contrat club joueur | Oui si renseigne | `/v4/persons/{id}` | `currentTeam.contract` | Non stocke |
| Market value | Oui si renseigne/tier | `/v4/teams/{id}` | `marketValue`, `squad[].marketValue` | Non stocke |
| Matchs recents equipe | Oui | `/v4/teams/{id}/matches?status=FINISHED&limit=100` | `matches[]` + `resultSet` | Non stocke |
| W/D/L recents equipe | Oui, a calculer ou via `resultSet` | `/v4/teams/{id}/matches` | `resultSet.wins/draws/losses` | Non stocke |
| Buts pour / contre recents | Oui, a calculer | `/v4/teams/{id}/matches` | `score.fullTime` | Non stocke |
| Clean sheets recents | Oui, a calculer | `/v4/teams/{id}/matches` | `score.fullTime` | Non stocke |
| Forme collective | Oui, derivee | `/v4/teams/{id}/matches` | resultats + buts | Non stocke |
| Proba match base resultats | Oui, derivee | `/v4/teams/{id}/matches` | resultats historiques | Non stocke |
| Matchs joueur recents | Oui, si joueur connu | `/v4/persons/{id}/matches` | `matches[]`, `aggregations` | Non stocke |
| Minutes recentes joueur | Oui, si disponible/tier | `/v4/persons/{id}/matches` | `aggregations.minutesPlayed` | Non stocke |
| Titularisations joueur | Oui | `/v4/persons/{id}/matches` | `aggregations.startingXI`, filtre `lineup=STARTING` | Non stocke |
| Banc / entrees / sorties | Oui | `/v4/persons/{id}/matches` | `lineup=BENCH`, `e=SUB_IN`, `e=SUB_OUT` | Non stocke |
| Buts joueur recents | Oui | `/v4/persons/{id}/matches` | `aggregations.goals`, filtre `e=GOAL` | Non stocke |
| Passes joueur recentes | Oui | `/v4/persons/{id}/matches` | `aggregations.assists`, filtre `e=ASSIST` | Non stocke |
| Cartons joueur | Oui | `/v4/persons/{id}/matches` | `yellowCards`, `redCards` | Non stocke |
| Top scorers competition | Oui | `/v4/competitions/WC/scorers?season=2026` | `scorers[]` | Non stocke |
| Arbitres | Oui | `/v4/matches/{id}` ou matches | `referees[]` | Non stocke |
| Head-to-head | Oui | `/v4/matches/{id}/head2head` | historique H2H | Non stocke |

## Donnees du modele non recuperables ou non fiables via football-data.org seul

| Champ modele | Statut football-data.org | Pourquoi |
|---|---|---|
| Classement FIFA officiel actuel | Non garanti | Notre app le maintient en dur; football-data.org n'est pas une API FIFA rankings. |
| Points FIFA | Non disponible | Pas expose dans les ressources documentees. |
| Elo | Non disponible | Pas expose. |
| xG / xA | Non disponible | football-data.org expose buts/assists, pas expected goals. |
| Note moyenne joueur | Non disponible | football-data.org ne documente pas de rating moyen joueur. |
| Blessure actuelle | Non disponible | Pas d'endpoint injury documente. |
| Risque blessure | Non disponible directement | Peut seulement etre approxime par absences/minutes faibles, pas fiable. |
| Fatigue qualitative | Non disponible directement | Peut etre derivee grossierement des minutes/repetition matchs, pas comme donnee brute. |
| Confiance joueur | Non disponible | Variable subjective. |
| Impact absence | Non disponible | A noter manuellement ou a modeliser. |
| Titulaire probable futur | Non disponible fiable | Les lineups sont des donnees match, pas une prediction avant match. |
| Groupe officiel garanti | Incertain | `squad[]` peut exister, mais football-data.org precise que les listes peuvent etre vides/null selon disponibilite/tier. |
| Etat de forme club exhaustif | Partiel | Seulement competitions couvertes et accessibles par token/tier. |
| Selectionneur qualite tactique | Non disponible | Coach nom/contrat possible; note tactique a calculer/manuelle. |
| Grinta pays hote / pays voisin | Non disponible | A conserver comme parametre modele interne. |
| Diaspora / public | Non disponible | A conserver comme hypothese interne. |
| Adaptation climat | Non disponible | A calculer hors API ou manuellement. |
| Fatigue voyage | Non disponible | A calculer par localisation, pas fourni. |
| Cotes bookmakers | Non disponible | football-data.org ne documente pas d'odds. |
| Possession, tirs, tirs cadres, corners | Non disponible dans les ressources documentees | Pas expose comme stats match detaillees dans la doc analysee. |

## Impact par onglet du classeur

### 02_Equipes

Alimentation directe possible:
- equipe, zone, pays/code, blason, API id, coach si renseigne.

Alimentation derivee possible:
- forme collective, attaque/defense empirique, clean sheets, buts pour/contre, profondeur approximative via taille squad/marketValue.

Alimentation non API:
- FIFA rank/points, Elo, contexte Amerique, diaspora, climat, voyage, grinta.

### 03_Joueurs_Retenus

Alimentation directe possible:
- joueur, poste, nationalite, date naissance, numero, club courant, contrat, marketValue si renseigne.

Alimentation derivee possible:
- minutes index, buts recents, passes recentes, titularisations, remplacements, cartons.

Alimentation non API:
- blessure, fatigue ressentie, confiance, impact absence, remplacant niveau fiable, notes moyennes, xG/xA.

### 04_Synthese_Joueurs

Alimentation derivee possible:
- score forme effectif a partir des aggregations joueur.

Non API:
- dependance star qualitative, risque absence star fiable, profondeur qualitative.

### 05_Matchs / 06_Diagnostic_Match / 07_Modele_Probable

Alimentation directe possible:
- date, status, stade/venue, groupe/stage, score final, arbitres, equipes API.

Alimentation derivee possible:
- lambdas empiriques, proba issue approximative, potentiel match ferme/ouvert, risque surprise.

Non API:
- probabilites officielles, xG, cotes, meteo, contexte public reel.

## Ce qu'il faut coder pour etre exhaustif avec football-data.org

1. Ajouter un service `football_data_client.py` dedie.
2. Ajouter une table/cache `pronostics_team_sources`:
   - local_team_name
   - football_data_team_id
   - official_name
   - area_code
   - coach fields
   - squad_last_updated
   - raw payload JSON
3. Ajouter une table/cache `pronostics_player_sources`:
   - football_data_person_id
   - team_id
   - name
   - position
   - currentTeam
   - marketValue
   - raw payload JSON
4. Ajouter un job de collecte:
   - competition teams
   - team detail for each team
   - team recent matches
   - person recent matches for squad players
   - competition scorers
5. Ajouter un export Excel/CSV vers le modele:
   - onglet `08_Sources`
   - alimentation `02_Equipes`
   - alimentation `03_Joueurs_Retenus`
   - alimentation `04_Synthese_Joueurs`

## Limite decisive

football-data.org peut nourrir une base factuelle propre, mais ne suffit pas seul a remplir un modele expert complet. Les donnees qualitatives les plus importantes avant tournoi restent a saisir ou calculer hors API:

- blessures,
- liste officielle definitive si football-data.org renvoie squad vide,
- etat de forme fin subjectif,
- tactique/selectionneur,
- contexte local/public/climat,
- statut titulaire probable.
