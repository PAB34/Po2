# PRONO - Integration scenario engine odds-blind

Statut : cadrage actif
Derniere mise a jour : 2026-07-06

## 1. Intention

Integrer la specification de scenarisation de matchs dans PRONO sans casser le
socle value deja construit.

La regle centrale devient :

```text
Donnees sportives -> Scenario odds-blind -> Comparaison aux cotes -> Tickets
```

Le scenario sportif ne doit jamais utiliser les cotes, les bookmakers, la CLV,
les boosts ou l'EV comme features. Ces donnees appartiennent uniquement a la
couche betting deja isolee dans `app/value/`.

## 2. Ce qu'on reprend du document

A reprendre dans PRONO :

- separation stricte prediction sportive / comparaison marche ;
- score de completude des donnees ;
- scenario principal + scenarios alternatifs ;
- marches sportivement coherents ;
- marches a eviter ;
- donnees manquantes bloquantes ou degradantes ;
- revue post-match ulterieure ;
- ticket families plus tard : base safe, buts, periode, joueur, fun.

A ne pas reprendre tout de suite :

- OCR/captures Winamax ;
- tickets joueurs ;
- live conditionnel ;
- API payantes ou non validees ;
- refonte PostgreSQL/Redis/Celery ;
- modele auto-apprenant ;
- pondérations optimisees sans backtest.

## 3. Architecture cible PRONO

```text
PRONO existant
  app/ligue1/*
    data, dynamics, stakes, injuries, news, context_level

Nouvelle couche
  app/value/scenarios.py
    moteur scenario odds-blind pur
    garde anti-cotes
    score de completude
    marches coherents / a eviter

Couche deja en place
  app/value/*
    odds, EV, CLV, snapshots, boosted tickets, backtests
```

Le scenario engine est appele avant toute lecture de cote exploitable pour la
decision betting. Il peut produire des noms de marches (`BTTS`, `Over 1.5`,
`Favori handicap a eviter`) mais il ne lit pas leurs prix.

## 4. MVP developpement

### Phase A - moteur pur

- dataclasses d'entree/sortie ;
- garde-fou anti feature de cote ;
- completude match/equipes/contexte ;
- scenario principal simple ;
- alternatives ;
- marches coherents / marches a eviter ;
- tests unitaires.

### Phase B - endpoint prive

- `POST /api/value/scenarios/football` ;
- entree JSON sportive ;
- sortie ScenarioReport ;
- aucun appel aux cotes.

### Phase C - liaison PRONO Ligue 1

- construire l'entree scenario depuis le payload `/api/ligue1/journee` ;
- stocker plus tard la prediction pour backtest.

### Phase D - comparaison betting

- comparer scenario -> snapshots/cotes ;
- construire tickets par familles uniquement si donnees suffisantes.

## 5. Regles metier MVP

Le moteur MVP reste volontairement simple :

- si les deux equipes ont un profil buts pour et buts contre eleve, signaler
  un scenario ouvert et des marches `Over 1.5` / `BTTS` coherents ;
- si une equipe a un avantage net de forme, signaler une equipe en ascendant ;
- si derby, treve, enjeu fort ou blessures elevees, baisser la confiance et
  ajouter des marches a eviter ;
- si donnees absentes, ne pas inventer : remonter `missing_data` et reduire le
  score de completude.

## 6. Critere d'acceptation phase A

- le moteur refuse une entree contenant `odd`, `odds`, `cote`, `price`,
  `bookmaker`, `ev`, `clv` ;
- un match avec donnees completes produit un scenario principal ;
- un match avec donnees partielles produit une completude degradee ;
- les cotes ne sont jamais necessaires pour generer un scenario ;
- les tests unitaires passent avec la suite value existante.

## 7. Matrice de couverture du document source

Cette section sert de garde-fou : rien du document `spec_application_scenarios_paris_football(5).md` ne doit disparaitre silencieusement. Chaque bloc est classe en `fait`, `partiel`, `differe`, `a auditer` ou `exclu MVP`.

| Bloc source | Couverture PRONO actuelle | Statut | Decision |
|---|---|---:|---|
| Objectif general : donnees -> scenario -> cotes -> tickets | Spec presente + moteur odds-blind MVP | partiel | Continuer via endpoint scenario puis comparaison betting |
| Separation prediction sportive / cotes | Garde anti-cotes dans `scenarios.py` | fait | Regle durable |
| Import automatique donnees gratuites | Football-Data + The Odds API prepare | partiel | Continuer collecte et audit sources |
| Donnees manuelles indisponibles | Non implemente | differe | Creer plus tard imports CSV/forms |
| Audit programme existant | Audit partiel PRONO realise dans conversation | partiel | Formaliser un fichier audit si besoin |
| Base de donnees normalisee | SQLite snapshots odds seulement | partiel | Reporter schema complet scenario/joueurs |
| Fiche match | Front actuel match + futur scenario | partiel | Endpoint scenario avant front |
| Moteur statistique odds-blind | MVP regles simples | partiel | Evoluer vers Poisson/Elo/xG seulement apres donnees |
| Moteur scoring/scenarisation sans cotes | `scenarios.py` MVP | partiel | Ajouter familles de scenarios |
| Comparaison aux cotes | Value layer existante | partiel | Brancher scenario -> odds snapshots |
| Tickets par niveau de risque | Backtest tickets boostes existe, pas familles safe/buts/joueur/fun | partiel | Ajouter ticket families apres scenario MVP |
| Historique predictions pour backtesting | Non implemente | differe | Ajouter stockage predictions/scenarios |
| Score de completude | MVP simple dans `scenarios.py` | partiel | Remplacer par ponderations completes source |
| API-Football / API-Sports | Non integre | a auditer | Verifier free tier/couverture Ligue 1/lineups/stats |
| football-data.org API | Non integre ; Football-Data CSV deja utilise | a auditer | Distinguer football-data.co.uk vs football-data.org |
| Sportmonks | Non integre | a auditer | Probablement hors MVP gratuit |
| OpenLigaDB | Non integre | a auditer | Couverture Ligue 1 probablement insuffisante |
| StatsBomb Open Data | Non integre | a auditer | Utile entrainement, pas live Ligue 1 complet |
| ClubElo / Elo public | Non integre | differe | Bon candidat odds-blind gratuit |
| World Football Elo / FIFA ranking | Non integre | differe | Surtout selections nationales |
| Open-Meteo | Non integre | differe | Necessite base stades/coordonnees |
| Donnees stade internes | Non integre | differe | Creer fichier stades plus tard |
| The Odds API | Client + route collecte | partiel | Ajouter cle et collecte reelle |
| Winamax manuel | Non integre | differe | Prioritaire pour cotes jouables reelles, via CSV manuel d'abord |
| Match exact / competition / date | Disponible partiellement via Football-Data | partiel | Ajouter phase/lieu/statut |
| Phase / enjeu | Enjeu Ligue 1 deja calcule partiellement | partiel | Ajouter phase coupe/neutre plus tard |
| Lieu / stade / altitude | Non implemente | differe | Depend base stades |
| Betting markets 1N2 | Existant | fait | Continuer |
| Qualification | Non implemente | differe | Hors Ligue 1 championnat, utile coupes |
| Over/Under, BTTS | Scenario les nomme, pas odds/backtest dedies | differe | Ajouter apres matrice buts |
| Buts par equipe | Non implemente | differe | Necessite odds/source ou modele score |
| Marches mi-temps/periode | Non implemente | differe | Necessite donnees timing buts |
| Joueurs : buteur/tir cadre/decisif | Non implemente | differe | Bloque sans lineups/stats joueurs fiables |
| Scores exacts / fun | Non implemente | differe | Necessite distribution score |
| Cote + timestamp | Snapshots odds implemente | partiel | Collecte reguliere a lancer |
| Equipes : buts marques/encaisses recents | Disponible partiellement | partiel | Utilise dans scenario MVP |
| xG/xGA | Non implemente | differe | Source gratuite a auditer StatsBomb/autre |
| Tirs/tirs cadres/tirs concedés | Non implemente | differe | API-Football/Sportmonks a auditer |
| Clean sheets / BTTS recents | Non implemente | differe | Calculable depuis historique, a ajouter |
| Buts par periode | Non implemente | differe | Besoin events/minutes |
| Corners/cartons/fautes/arbitre | Non implemente | differe | Source souvent payante, audit requis |
| Compositions probables/officielles | Non implemente | differe | Critique pour tickets joueurs, pas MVP |
| Absents/suspendus | Blessures Transfermarkt existe | partiel | Suspendus non couverts |
| Tireurs penalty/CPA/corners | Non implemente | differe | Saisie manuelle au depart |
| Profils joueurs/temps de jeu | Non implemente | differe | Saisie manuelle/base interne future |
| Jours de repos/fatigue | Partiellement via calendrier possible, non scenario | differe | A integrer scenario |
| Voyage/distance | Non implemente | differe | Besoin stades/geocodage |
| Meteo | Non implemente | differe | Open-Meteo + stades |
| Notes tactiques manuelles | `manual_context` MVP texte libre | partiel | Structurer plus tard |
| Profils joueurs manuels | Non implemente | differe | Futur module saisie |
| Duels cles | Non implemente | differe | Futur scenario avance |
| Raw data store | odds raw hash seulement | partiel | Generaliser API raw payloads |
| Normalization equipes/joueurs/marches | Partiel sur odds snapshots | partiel | Joueurs non couverts |
| Feature engineering style/fatigue/contexte | Tres partiel | partiel | Ajouter par petits incréments backtestes |
| Tables principales document source | Non implemente | differe | Ne pas migrer tout de suite |
| Tables separation modele/marche | Concept applique, stockage incomplet | partiel | Ajouter scenario_predictions plus tard |
| Tables apprentissage/calibration/versioning | Non implemente | differe | Apres stockage predictions/resultats |
| Score completude sportive pondere | MVP non pondere | partiel | Implementer ponderation source apres inventaire donnees |
| Score completude betting pondere | Non implemente | differe | Apres extension marches odds |
| Regles de blocage par sortie | Non implemente | differe | A ajouter avec ticket families |
| Anti-contamination par les cotes | Implemente dans scenarios | fait | Etendre aux futurs modeles |
| Poisson / Dixon-Coles / Monte Carlo / ML | Non implemente | differe | Apres baseline et donnees score/xG |
| Dynamic Team Strength Index | Non implemente | differe | Bonne piste, mais a backtester |
| Regles favori clair / ferme / ouvert / outsider domicile | Partiel : ouvert/ferme/form edge | partiel | Ajouter favori/outsider domicile plus tard |
| Pondérations par marche | Non implemente | differe | Necessite backtest par marche |
| Couche marche : proba implicite/marge/value | Deja dans value layer | fait | Continuer |
| Cote minimale acceptable | `fair_odds` existe | fait | Brancher scenario -> fair odds plus tard |
| Verrouillage prediction sportive | Non stocke | differe | Ajouter snapshot scenario avant cotes |
| Tickets safe/buts/periode/joueur/fun | Non implemente | differe | Ajouter apres scenario + odds markets |
| Workflow J-3 / H-6 / H-1 / H-15 | Non implemente | differe | Future UX/process, pas moteur MVP |
| Backtesting scenario vs reel | Non implemente | differe | Apres stockage scenarios |
| Apprentissage adaptatif/shadow models | Non implemente | differe | Hors MVP jusqu'a volume suffisant |
| Interface match | Front existant sans scenario | partiel | Ajouter apres endpoint scenario |
| Interface saisie manuelle | Non implemente | differe | CSV minimal avant UI |
| Ecran audit sources/quotas | Non implemente | differe | Ajouter apres collecte reguliere |
| Backend PostgreSQL/Redis/Celery | Non retenu | exclu MVP | Rester SQLite/FastAPI tant que PRONO prive |
| Adapter interface commune | Non formalise | differe | Nos collectors jouent ce role partiellement |
| Gouvernance source/timestamp/confidence/raw_reference | Partiel odds snapshots | partiel | Generaliser aux donnees sportives |
| Securite/conformite | Respectee : pas bookmaker login, pas bot pari | fait | Garder mode manuel Winamax |
| Prompt interne generation | Non integre | differe | A utiliser plus tard en template export, pas moteur |
| Post-match reviews | Non implemente | differe | Important apres stockage predictions |
| Features tardives/banc/CPA/penalties/star dependency | Non implemente | differe | A documenter comme backlog scenario avance |
| Branches live conditionnelles | Non implemente | differe | Hors MVP, seulement apres donnees live fiables |

## 8. Oublis ou risques identifies

Les points suivants n'etaient pas assez documentes dans la premiere version de cette spec et doivent rester visibles :

1. **Winamax manuel** : indispensable si l'objectif est de comparer aux cotes reellement jouables. A integrer d'abord par CSV manuel, pas OCR.
2. **Scenario persistence** : il faudra stocker le scenario genere avant lecture des cotes pour prouver l'anti-contamination.
3. **Score de completude betting** : absent pour l'instant ; necessaire avant tickets safe/buts/joueur/fun.
4. **Joueurs/compositions** : tres important pour tickets joueur, mais non disponible gratuitement de facon robuste aujourd'hui.
5. **Meteo/stades** : Open-Meteo est facile techniquement mais demande une base stades fiable.
6. **xG/tirs/big chances** : valeur sportive forte, source gratuite live incertaine. StatsBomb Open Data ne couvre pas tout le live Ligue 1.
7. **Post-match review** : indispensable pour apprendre, mais doit venir apres stockage des predictions.
8. **Modeles Poisson/Elo/DTSI** : interessants, mais doivent tourner en shadow/backtest avant d'influencer les tickets.
9. **Live conditionnel** : tres seduisant, mais hors MVP car donnees live et discipline de validation plus exigeantes.
10. **Architecture lourde** : PostgreSQL/Redis/Celery n'est pas justifiee pour PRONO prive tant qu'un SQLite robuste suffit.

## 9. Backlog d'integration recommande

1. Endpoint prive `POST /api/value/scenarios/football` - fait le 2026-07-06.
2. Adapter PRONO journee -> entree scenario odds-blind - amorce le 2026-07-06 via `GET /api/value/scenarios/ligue1/journee`.
3. Stockage `scenario_predictions` avec timestamp et hash d'entree sportive - amorce le 2026-07-06.
4. Backtest scenario vs reel - amorce le 2026-07-06 via `GET /api/value/backtests/ligue1/scenarios`.
5. Score de completude sportive pondere proche du document source - amorce le 2026-07-06.
6. Score de completude betting pondere - amorce le 2026-07-06 via `GET /api/value/completeness/betting`.
7. Ticket families sans joueurs : safe, buts, fun simple - amorce le 2026-07-06 via `GET /api/value/ticket-families/ligue1`.
8. Import CSV bookmaker manuel - amorce le 2026-07-06 via `POST /api/value/collect/manual-csv`.
9. Rapport couverture odds multi-bookmakers - amorce le 2026-07-06 via `GET /api/value/coverage/odds`.
10. Post-match review.
11. Sources avancees : Open-Meteo + stades, ClubElo, xG/open data, lineups.

## 10. Etat implementation 2026-07-06

Phase B faite :

- `app/routes_value.py` expose `POST /api/value/scenarios/football` derriere l'auth JWT existante ;
- l'endpoint appelle `scenario_from_mapping(...)` et conserve le garde anti-cotes du moteur odds-blind ;
- une entree contenant `odd`, `odds`, `cote`, `price`, `bookmaker`, `ev`, `clv` ou `boost` renvoie une erreur 400 ;
- `tests/test_value_scenarios.py` couvre la declaration de route, un rapport nominal et le refus d'une feature bookmaker.

Phase C amorcee :

- `app/value/ligue1_scenarios.py` adapte le payload `/api/ligue1/journee` vers une entree scenario en liste blanche sportive ;
- l'adaptateur lit les blocs sportifs `home_block` / `away_block`, derby et treve, mais ignore les champs marche deja presents (`p_home`, `p_draw`, `p_away`, `pick`, `pick_proba`, `odds_source`, bookmaker) ;
- `GET /api/value/scenarios/ligue1/journee` retourne les scenarios de la journee sans recopier les probabilites marche ;
- `tests/test_value_ligue1_scenarios.py` verifie l'absence de contamination par les champs marche.

Stockage predictions amorce :

- `app/value/scenario_predictions.py` cree le store SQLite `scenario_predictions` ;
- chaque prediction stocke `predicted_at`, `event_id`, le hash SHA-256 de l'entree sportive canonique, l'entree sportive JSON et le rapport scenario JSON ;
- `POST /api/value/scenarios/ligue1/journee/predictions` persiste explicitement les scenarios de la journee ;
- `tests/test_value_scenario_predictions.py` verifie deduplication, hash sportif stable et absence de contamination marche/bookmaker.

Backtest scenario vs reel amorce :

- `app/value/scenario_backtest.py` rapproche les predictions stockees avec l'historique Football-Data ;
- les metriques restent sportives : `Over 1.5` vs total buts reel, `BTTS` vs les deux equipes marquent, double chance equipe en ascendant vs resultat ;
- `GET /api/value/backtests/ligue1/scenarios` expose le rapport prive ;
- `tests/test_value_scenario_backtest.py` couvre signaux, non-rapprochements, service et route.

Completude sportive ponderee amorcee :

- `app/value/scenarios.py` remplace le comptage uniforme par une ponderation sur 100 ;
- identite match et profil buts pesent plus fort que contexte/enjeux ;
- `ScenarioReport` expose `blocking_missing_data` et `degrading_missing_data` ;
- les marches buts et ascendant ajoutent des avoid markets quand leurs donnees support sont incompletes ;
- `tests/test_value_scenarios.py` couvre identite bloquante, penalite profil buts, penalite forme et exposition API.

Completude betting ponderee amorcee :

- `app/value/betting_completeness.py` score la disponibilite des snapshots odds sans alimenter le moteur sportif ;
- le score tient compte de `decision_at`, snapshots avant decision, marches requis, profondeur de selections, diversite bookmaker, snapshot de cloture et hash brut d'audit ;
- `GET /api/value/completeness/betting` expose le rapport prive par event/marches requis ;
- `tests/test_value_betting_completeness.py` couvre score complet, blocage sans snapshots, marche manquant, degradation bookmaker unique, service et route.

Ticket families sans joueurs amorcees :

- `app/value/ticket_families.py` genere des familles `safe`, `buts` et `fun_simple` depuis les predictions scenario stockees ;
- les familles utilisent la completude sportive et peuvent integrer la readiness betting, mais ne calculent ni cote, ni EV, ni promesse de rentabilite ;
- `GET /api/value/ticket-families/ligue1` expose les candidats de recherche ;
- `tests/test_value_ticket_families.py` couvre generation, filtres de completude, readiness betting, service et route.

Import CSV bookmaker manuel amorce :

- `app/value/manual_odds_csv.py` normalise un CSV bookmaker generique vers `odds_snapshots` ;
- Winamax peut etre fourni comme `default_bookmaker`, mais le pipeline reste multi-bookmaker ;
- `POST /api/value/collect/manual-csv` accepte du texte CSV brut sans dependance `python-multipart` ;
- `tests/test_value_manual_odds_csv.py` couvre normalisation, bookmaker par defaut, lignes invalides, deduplication store et route.

Rapport couverture odds amorce :

- `app/value/odds_coverage.py` agrege `odds_snapshots` par event ;
- le rapport expose sports, competition, participants, marches, selections, bookmakers par marche, premiere/derniere capture et completude betting par event ;
- `GET /api/value/coverage/odds` filtre par event/sport/competition/marches requis ;
- `tests/test_value_odds_coverage.py` couvre aggregation multi-bookmakers, marche manquant, filtres service et route.

Prochaine tranche recommandee : post-match review, avant toute UI.