# PRONO - Spec pivot value betting booste

Statut : cadrage actif
Derniere mise a jour : 2026-07-02

## 1. Objectif

Faire evoluer PRONO d'une application privee de lecture Ligue 1 vers un moteur de simulation et de validation statistique pour selections a value positive et tickets boostes.

Le pivot ne doit pas transformer immediatement l'interface en conseil de pari. Tant que les backtests walk-forward ne prouvent pas la robustesse du modele, l'application reste en mode recherche, simulation et audit.

## 2. Decision de transition

Le principe historique de PRONO reste valable pour l'ecran actuel : les probabilites 1/N/2 affichees dans `/api/ligue1/journee` sont les probabilites de marche sans marge, calculees depuis les cotes Football-Data.

Le nouveau cahier des charges autorise un moteur de probabilites modele, mais uniquement dans un espace separe : backtest, simulation, comparaison marche vs modele, detection de value theorique, tickets boostes experimentaux.

La production ne doit jamais presenter ces sorties comme un gain attendu garanti. Aucun ROI positif ne doit etre promis.

## 3. Existant backend utile

### Deja en place

- `app/main.py` : FastAPI, CORS, healthcheck, inclusion auth + routes Ligue 1.
- `app/auth.py` : JWT Bearer, compte prive unique, changement de mot de passe.
- `app/db.py` : SQLite minimal pour l'utilisateur, pas de stockage metier.
- `app/routes_ligue1.py` : endpoints proteges `/api/ligue1/*`.
- `app/ligue1/data.py` : chargement Football-Data historique + fixtures.
- `app/ligue1/probabilities.py` : cotes 1/N/2 vers probabilites sans marge par methode proportionnelle, source prioritaire Pinnacle > Bet365 > Moyenne.
- `app/ligue1/dynamics.py` : forme recente depuis les resultats historiques.
- `app/ligue1/stakes.py` : classement, enjeux, zones Europe/maintien.
- `app/ligue1/derby.py` : rivalites statiques.
- `app/ligue1/calendar_context.py` : detection de treve via ecarts calendrier.
- `app/ligue1/context_level.py` : niveau de lecture transparent, sans impact sur les probabilites.
- `app/ligue1/injuries_tm.py` : blessures Transfermarkt, cache et alertes.
- `app/ligue1/news.py` : Google News RSS equipe + ligue.
- `app/ligue1/service.py` : assemblage du payload journee.

### Reutilisable pour le cahier

- Devigottage proportionnel des cotes : base de `market_no_vig`.
- Historique Football-Data : resultats, cotes historiques de cloture et quelques colonnes bookmaker selon disponibilite.
- Classement et dynamique : signaux contextuels possibles pour exploration, a utiliser avec horodatage strict pour eviter les fuites temporelles.
- Auth et deploiement : suffisants pour exposer plus tard des endpoints prives.

## 4. Manques backend

### Donnees

- Pas de table metier pour snapshots de cotes.
- Pas d'historique intra-match ou pre-match horodate par instant de decision.
- Pas de stockage des tickets, selections, backtests ou resultats simules.
- Pas de connecteur actuellement identifie pour over 0.5, over 1.5, double chance, equipe marque, tennis, boost bookmaker ou regles de settlement.
- Pas de source xG, compositions, fatigue calendrier europeen ou meteo.

### Moteur statistique

- Pas de modele personnel calibre.
- Pas de lambda buts / matrice de scores.
- Pas de probabilites jointes pour selections du meme match.
- Pas de calcul EV selection, EV ticket, CLV ou exposition evenement.
- Pas de calibration par tranches, Brier score ou log loss dedies au modele.
- Pas de walk-forward backtest.
- Pas de simulation Monte Carlo.
- Pas de tests unitaires PRONO versionnes.

## 5. Architecture cible progressive

Ne pas refondre tout le backend. Ajouter un sous-domaine applicatif isole sous `app/value/` ou `app/ligue1/value/` selon le perimetre retenu.

Phase 1 - noyau mathematique pur :

- `odds.py` : conversion cote vers probabilite implicite, retrait de marge.
- `ev.py` : fair odds, EV selection, EV ticket booste, probabilite rentable.
- `clv.py` : closing line value.
- `blocks.py` : bloc evenement, probabilite jointe, detection correlation.
- `tickets.py` : construction et evaluation de tickets a partir de blocs.
- tests unitaires sur les exemples du cahier.

Phase 2 - backtest minimal 1/N/2 Ligue 1 :

- utiliser l'historique Football-Data disponible ;
- definir une heure theorique de decision quand la donnee le permet ;
- refuser ou alerter si la donnee est une cote de cloture utilisee comme cote de selection ;
- mesurer log loss, Brier, calibration, ROI simule, CLV si cote de cloture separee disponible.

Phase 3 - collecte de snapshots :

- table `odds_snapshots` ou fichier parquet/csv versionne hors runtime selon contrainte de deploiement ;
- champs minimum : sport, competition, event_id, match, market, selection, bookmaker, odds, captured_at, kickoff, source ;
- job de collecte periodique si une source gratuite fiable existe ;
- politique anti-fuite : aucune donnee posterieure a `decision_at` dans un backtest.

Phase 4 - modeles par marche :

- football : matrice de scores pour deduire 1/N/2, over, double chance, equipe marque et combinaisons du meme match ;
- tennis : vainqueur match seulement en premiere version ;
- calibration walk-forward du poids modele vs marche si un modele personnel existe.

Phase 5 - endpoints prives :

- `GET /api/value/health` ;
- `POST /api/value/backtests` ;
- `GET /api/value/backtests/{id}` ;
- `GET /api/value/backtests/{id}/metrics` ;
- `GET /api/value/backtests/{id}/tickets` ;
- `POST /api/value/simulations/boosted-tickets`.

## 6. Tests minimums a creer

- cote 1.25 -> probabilite implicite 0.80 ;
- cotes 1.25 / 4.20 -> overround environ 1.0381 ;
- retrait de marge -> 0.7706 / 0.2294 ;
- EV selection : `0.88 * 1.16 - 1 = 0.0208` ;
- CLV : `1.25 / 1.18 - 1 = 0.0593` ;
- ticket booste : `15 * 1.16 = 17.40` ;
- probabilite minimale rentable : `1 / 17.40 = 0.0575` ;
- meme match : interdire le produit naif de jambes correlees quand une probabilite jointe n'est pas fournie ;
- anti-fuite temporelle : une donnee posterieure a `decision_at` doit faire echouer ou alerter le backtest.

## 7. Proposition front

Le front ne vient qu'apres la validation du noyau et d'un backtest minimal. Il reste en vanilla JS, sans build.

### Navigation cible

- Onglet `Matchs` : conserve l'ecran actuel, probabilites de marche et contexte.
- Onglet `Backtests` : liste des runs, statut, periode, sport, marche, ROI, CLV, log loss, Brier, drawdown.
- Onglet `Selections` : tableau des selections detectees en simulation : marche, cote, proba marche, proba modele, proba finale, EV, resultat.
- Onglet `Tickets boostes` : tickets simules, blocs, cote brute, boost, cote boostee, probabilite corrigee, EV, exposition evenement, risk score.
- Onglet `Calibration` : tranches de probabilite, proba moyenne estimee, taux reel, ecart.
- Onglet `Donnees` : sources disponibles, profondeur historique, fraicheur des snapshots, alertes anti-fuite.

### Principes UX

- Toujours distinguer `marche`, `modele`, `final/calibre` et `resultat reel`.
- Afficher un badge `Simulation` tant que le modele n'est pas valide.
- Afficher les limites de donnee quand CLV ou walk-forward complet sont impossibles.
- Ne jamais afficher "pari sur" ou "gain garanti".
- Privilegier des tableaux denses, filtres, exports CSV et details de ticket.

## 8. Questions a trancher

1. Le perimetre initial reste-t-il Ligue 1 uniquement ?
2. Le premier marche backteste est-il 1/N/2 ou over 1.5 ?
3. Dispose-t-on d'une source gratuite fiable pour snapshots de cotes ?
4. Le boost simule est-il fixe ou depend-il du nombre de selections ?
5. Quelle taille de session cible : 10 tickets comme dans le cahier ?
6. Quelle mise fictive standard pour les backtests ?
7. Accepte-t-on d'utiliser les cotes Football-Data historiques comme proxy de cloture uniquement pour mesurer, jamais pour choisir ?

## 9. Prochaine tranche recommandee

Creer le noyau mathematique pur et ses tests, sans endpoint et sans front :

- odds conversion + devig ;
- EV selection ;
- CLV ;
- EV ticket booste ;
- blocs correles ;
- garde-fou anti-produit-naif.

Cette tranche est faible risque : elle ne touche pas a l'app existante, ne change pas les probabilites affichees et pose la base testable du cahier.

## 10. Etat implementation

Tranche 1 amorcee le 2026-07-02 :

- `app/value/odds.py` : conversion cote, retrait de marge proportionnel ;
- `app/value/ev.py` : fair odds, EV selection, cote boostee, probabilite rentable, EV ticket ;
- `app/value/clv.py` : closing line value ;
- `app/value/blocks.py` : blocs evenement et garde-fou correlations meme match ;
- `app/value/tickets.py` : evaluation de tickets boostes ;
- `tests/test_value_math.py` : tests unitaires sur les exemples du cahier.

Cette implementation reste sans endpoint et sans impact sur `/api/ligue1/journee`.

Tranche 2 amorcee le 2026-07-02 :

- `app/value/metrics.py` : log loss, Brier score multiclasses, calibration par tranches ;
- `app/value/backtest.py` : backtest minimal marche 1/N/2 avec warning explicite quand les cotes ne sont qu'un proxy de cloture ;
- garde `TemporalLeakageError` si une donnee horodatee est posterieure a `decision_at` ;
- `tests/test_value_backtest.py` : tests de metriques, mode closing proxy et anti-fuite temporelle ;
- `app/value/ligue1_market.py` : adaptateur vers l'historique Football-Data et les sources Pinnacle/Bet365/Moyenne existantes ;
- `tests/test_value_ligue1_market.py` : tests de couverture source et backtest via historique synthetique ;
- `app/value/boost.py` : grille de boost configurable par nombre de selections, type Winamax ;
- `tests/test_value_boost.py` : tests du boost par nombre de selections et limite 10 selections.

Limite volontaire : cette tranche ne valide pas encore une strategie value betting. Elle mesure une baseline marche et pose les garde-fous temporels avant collecte de snapshots.



## 11. Arbitrages utilisateur 2026-07-02

Parametres confirmes :

- perimetre initial : Ligue 1 + tennis ;
- premier marche backteste : football 1/N/2 et tennis vainqueur match (`h2h`) ;
- objectif data : gratuite autant que possible ;
- taille de session : 10 tickets ;
- mise fictive standard : 50 EUR ;
- boost : depend du nombre de selections selon un modele type Winamax ;
- usage Football-Data closing/proxy : accepte pour avancer, tant que les limites sont explicites.

Clarification importante : l'app actuelle ne recupere pas directement les cotes chez les bookmakers. Elle consomme Football-Data, qui compile des cotes de bookmakers et de marche. Pour des decisions pre-match et de la CLV, il faut collecter nos propres snapshots horodates ou utiliser une API qui expose `last_update`/`captured_at`.

## 12. Strategie acquisition data gratuite

### Football Ligue 1

Priorite 1 : conserver Football-Data pour historique, resultats, cotes d'ouverture/pre-cloture/cloture quand disponibles. C'est gratuit et deja integre, mais ce n'est pas un flux continu de snapshots decisionnels.

Priorite 2 : collecter nos propres snapshots des fixtures Football-Data. Les fixtures sont mises a disposition avant match, mais a faible frequence. Cela donne une premiere serie temporelle gratuite si on planifie des relevés periodiques cote app.

Priorite 3 : The Odds API plan gratuit pour odds recentes Ligue 1 + tennis, si une cle gratuite est creee. Le plan gratuit donne 500 credits/mois et pas d'historical odds. Il peut donc servir a collecter nos propres snapshots a partir d'aujourd'hui, pas a backfiller l'historique.

### Tennis

Piste 1 : Tennis-Data, site reseau de Football-Data, annonce des donnees tennis gratuites avec resultats et cotes. A verifier par integration fichier avant de construire le modele.

Piste 2 : The Odds API gratuit pour odds recentes tennis (`h2h`) si le quota suffit. Meme contrainte : pas d'historique gratuit, donc snapshots a collecter nous-memes.

### Donnees a stocker

Table ou fichier `odds_snapshots` :

- `sport` : `football` / `tennis` ;
- `competition` : `ligue1`, `atp`, `wta`, tournoi ;
- `event_id` stable si disponible ;
- `home_or_player_1`, `away_or_player_2` ;
- `market` : `1x2` ou `h2h` ;
- `selection` ;
- `bookmaker` ;
- `odd` ;
- `captured_at` ;
- `last_update` source si disponible ;
- `commence_time` / `kickoff` ;
- `source` ;
- `raw_payload_hash` optionnel pour audit.

Regle : un backtest value reel doit utiliser uniquement des snapshots dont `captured_at <= decision_at < commence_time`.

## 13. Boost type Winamax

Implementation amorcee : `app/value/boost.py`.

Le boost est une grille par nombre de selections, limitee a 10 selections pour coller a la session cible. Le bareme actuel est volontairement configurable : les promotions Winamax peuvent changer, et le bareme officiel courant devra etre confirme par capture/regle source avant usage en resultat final.

Tant que ce bareme n'est pas confirme, les backtests doivent afficher `boost_model = winamax_like_configurable` et non `Winamax officiel`.


## 14. Tranche snapshots horodates

Implementation amorcee le 2026-07-02 :

- `app/value/snapshots.py` : modele `OddsSnapshot`, hash stable du payload brut, stockage SQLite `odds_snapshots` avec unicite source/evenement/marche/selection/bookmaker/captured_at ;
- `app/value/collectors.py` : normalisation de lignes Football-Data vers snapshots 1/N/2 et normalisation The Odds API v4 vers snapshots football 1x2 ou tennis h2h ;
- `tests/test_value_snapshots.py` : tests de stockage, deduplication et normalisation des deux familles de source.

Cette tranche ne fait aucun appel reseau. Elle prepare l'ingestion gratuite :

1. Football-Data fixtures/historique deja accessible par l'app ;
2. The Odds API plan gratuit si une cle est ajoutee ;
3. Tennis-Data a verifier ensuite comme source gratuite tennis historique.

La prochaine etape backend est un endpoint/job prive de collecte qui ecrit ces snapshots dans le volume `PRONO_DATA_DIR`, puis un backtest qui choisit un snapshot avant match (`captured_at <= decision_at`) et mesure ensuite la CLV sur le dernier snapshot disponible avant coup d'envoi.

## 15. Routes privees de collecte

Implementation amorcee le 2026-07-02 :

- `app/value/service.py` : service de collecte Football-Data vers `odds_snapshots.db` dans `PRONO_DATA_DIR` ;
- `app/routes_value.py` : routes protegees par JWT ;
- `GET /api/value/health` : statut du store snapshots, nombre total, repartition par source ;
- `POST /api/value/collect/football-data` : collecte les fixtures Football-Data courantes et insere les cotes disponibles ;
- `tests/test_value_service.py` : insertion, deduplication et stats sur donnees synthetiques.

Ces routes restent privees et ne produisent aucun conseil de pari. Elles servent uniquement a accumuler la donnee horodatee necessaire aux futurs backtests CLV/value.

## 16. Rapport CLV depuis snapshots

Implementation amorcee le 2026-07-02 :

- `app/value/clv_report.py` : construit une CLV par `event_id` / `market` / `selection` / `bookmaker` ;
- snapshot de decision : dernier snapshot `captured_at <= decision_at` ;
- snapshot de cloture : dernier snapshot disponible avant `commence_time`, prioritairement apres `decision_at` ;
- `GET /api/value/clv?decision_at=...&event_id=...&market=...` : endpoint prive de rapport ;
- `tests/test_value_clv_report.py` : tests du choix des snapshots et du filtrage store.

Limite : la CLV devient fiable uniquement quand le store contient plusieurs snapshots horodates pour un meme evenement. Sur une seule collecte, le rapport peut etre vide ou peu informatif.

## 17. Collecte The Odds API

Implementation amorcee le 2026-07-02 :

- `app/value/odds_api.py` : client The Odds API v4 en standard library, sans dependance nouvelle ;
- variable requise : `PRONO_ODDS_API_KEY` ;
- `app/value/service.py` : `collect_the_odds_api_snapshots(...)` normalise le payload vers `odds_snapshots` ;
- `POST /api/value/collect/odds-api?sport_key=...&sport=...&competition=...` : route privee de collecte ;
- parametres optionnels : `regions`, `markets`, `bookmakers` ;
- `tests/test_value_odds_api.py` : tests de construction URL, erreur sans cle et collecte sur payload simule.

Usage cible gratuit : collecter des snapshots courants Ligue 1 et tennis a partir de maintenant. Le plan gratuit ne backfill pas l'historique. La collecte doit donc tourner regulierement pour construire notre propre profondeur temporelle.

Exemples de sports keys a verifier via `/v4/sports` avant usage : `soccer_france_ligue_one` pour Ligue 1 si actif, et les cles tennis ATP/WTA du tournoi en cours.

## 18. Backtest moteur tickets boostes

Implementation amorcee le 2026-07-02 :

- `app/value/ticket_backtest.py` : selections favorites 1/N/2 depuis probabilites marche sans marge, construction chronologique de tickets boostes, profit, ROI, hit rate, drawdown ;
- `GET /api/value/backtests/ligue1/boosted-tickets` : endpoint prive de rapport ;
- parametres : `selections_per_ticket` (1-10), `stake` (defaut 50 EUR), `max_tickets`, `min_odd`, `max_odd` ;
- `tests/test_value_ticket_backtest.py` : tests selection favorite, filtres de cote, profit, ROI, drawdown ;
- `tests/test_value_backtest_service.py` : test du service avec historique synthetique.

Priorite corrigee : ce backtest moteur doit etre execute et interprete avant de developper un front riche ou de tirer des conclusions. Il utilise actuellement `p_final = p_market_no_vig` et les cotes Football-Data comme proxy historique. Il valide la mecanique EV/tickets/boost, pas encore une strategie rentable.
