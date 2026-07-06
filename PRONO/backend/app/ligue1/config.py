"""
Configuration — moteur Ligue 1 (probabilités, dynamiques, blessés, actu).

Le moteur de probabilités s'appuie sur la donnée la plus fiable disponible
gratuitement : les cotes des bookmakers les plus « sharp ».

Hiérarchie de fiabilité (validée par log loss sur l'historique 2021-2026) :
  1. Pinnacle (PS*)  — le bookmaker de référence, le plus précis ;
  2. Bet365  (B365*) — repli ;
  3. Moyenne marché (Avg*) — repli de dernier recours.
Dévigottage proportionnel (retrait de marge). Léger, sans scipy.

Rappel d'honnêteté : ces probabilités sont les meilleures estimations gratuites
possibles, mais elles reflètent le marché. Elles guident la lecture des matchs ;
elles ne donnent aucun avantage sur les bookmakers.
"""
import os

# Dossier de données/caches (volume monté en conteneur).
DATA_DIR = os.environ.get("PRONO_DATA_DIR",
                          os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data")))
os.makedirs(DATA_DIR, exist_ok=True)

# Données (gratuites)
LEAGUE_CODE = "F1"
FOOTBALL_DATA_BASE = "https://www.football-data.co.uk/mmz4281"
FOOTBALL_DATA_FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"
SEASON_START_YEARS = list(range(2016, 2027))
RAW_CACHE = os.path.join(DATA_DIR, "raw.pkl")   # cache historique
RAW_CACHE_TTL_HOURS = 24

# Hiérarchie des sources de cotes pour estimer la probabilité (1 = priorité max).
ODDS_SOURCES = [
    ("Pinnacle", {"H": "PSH", "D": "PSD", "A": "PSA"}),
    ("Bet365",   {"H": "B365H", "D": "B365D", "A": "B365A"}),
    ("Moyenne",  {"H": "AvgH", "D": "AvgD", "A": "AvgA"}),
]

# Niveaux de confiance, basés sur la probabilité du résultat le plus probable.
# Décrit la chance de gagner, pas un avantage.
CONF_FORT = 0.60
CONF_MOYEN = 0.45
DRAW_MAX_FOR_FORT = 0.30

# ------------------------------------------------------------------
# Enjeu réel (classement) — zones européennes / relégation.
# ⚠ Ces tailles de zone dépendent des règles UEFA de la saison (coefficient
# pays) et peuvent varier d'une année à l'autre. Valeurs par défaut Ligue 1
# (18 équipes depuis 2023-24) : ~5 places européennes (C1+C3+C4 combinées,
# approximatif), 3 places de relégation (2 directes + 1 barrage).
# À ajuster en début de saison si la réglementation change.
LIGUE1_EUROPE_ZONE = 5
LIGUE1_RELEGATION_ZONE = 3

# ------------------------------------------------------------------
# Seuil "en lutte" — DYNAMIQUE, pas une valeur fixe.
# ------------------------------------------------------------------
# Un écart de 8 points ne représente pas la même urgence en septembre (30
# matchs restants, 90 points encore en jeu) qu'à 3 journées de la fin (9
# points en jeu). Le seuil doit donc se resserrer mécaniquement à mesure que
# la saison avance, pour rester cohérent avec la réalité sportive.
#
# Formule : threshold = clamp(SHARE * points_encore_en_jeu, FLOOR, CAP)
#   - SHARE  : part des points restants encore en jeu en dessous de laquelle
#              on considère l'écart comme "rattrapable" (0.35 ≈ l'équipe
#              peut combler l'écart sans gagner la quasi-totalité de ses
#              matchs restants).
#   - CAP    : plafond, ≈ 2-3 victoires d'écart (le repère classique "encore
#              jouable"). Gouverne tant qu'il reste beaucoup de matchs.
#   - FLOOR  : plancher en toute fin de saison, pour ne pas exclure à tort
#              un petit écart réel (1-3 points) lors des derniers matchs.
LIGUE1_LUTTE_GAP_SHARE = 0.35
LIGUE1_LUTTE_GAP_CAP = 8
LIGUE1_LUTTE_GAP_FLOOR = 3

# En dessous de ce nombre de matchs joués (sur l'ensemble de la saison), on
# nuance les libellés "en lutte" comme prématurés (échantillon trop petit
# pour que le classement soit significatif).
LIGUE1_TRES_TOT_PLAYED_MAX_RATIO = 0.18   # ≈ 6 matchs sur 34
# En dessous de ce nombre de matchs restants, on accentue l'urgence du
# libellé ("décisif", "sprint final").
LIGUE1_FIN_DE_SAISON_REMAINING_RATIO = 0.25  # ≈ les 8 derniers matchs sur 34

# ------------------------------------------------------------------
# Trêve internationale / hivernale — détectée depuis nos propres dates de
# calendrier (cf. calendar_context.py), aucune source externe nécessaire.
# ------------------------------------------------------------------
# Écart (en jours) entre 2 journées au-delà duquel on considère que ce n'est
# plus le rythme hebdomadaire normal (3-7 jours) mais une vraie coupure.
BREAK_GAP_THRESHOLD_DAYS = 9
# Mois où tombent les fenêtres internationales FIFA pendant une saison de
# Ligue 1 (août à mai) : septembre, octobre, novembre, mars. Juin existe
# aussi mais tombe hors saison. Stable d'une année sur l'autre.
FIFA_WINDOW_MONTHS = {9, 10, 11, 3}

# Regroupement en « journée » : nouveau bloc si l'écart entre 2 matchs dépasse N jours.
JOURNEE_GAP_DAYS = 4

# ------------------------------------------------------------------
# Actualité (gratuite, sans clé API) — Google News RSS en français.
# ------------------------------------------------------------------
NEWS_MAX_ITEMS = 5        # nb de titres remontés par équipe
NEWS_MAX_AGE_DAYS = 30    # on ignore les articles plus vieux que N jours

# Nom court Football-Data -> requête de recherche d'actualité optimisée.
# (Clubs de Ligue 1 2025-26 ; complétez à chaque montée/descente.)
NEWS_QUERIES = {
    "Paris SG":   'PSG "Paris Saint-Germain" Ligue 1',
    "Marseille":  '"Olympique de Marseille" OM Ligue 1',
    "Lyon":       '"Olympique Lyonnais" OL Ligue 1',
    "Monaco":     '"AS Monaco" Ligue 1',
    "Lille":      '"LOSC Lille" Ligue 1',
    "Nice":       '"OGC Nice" Ligue 1',
    "Lens":       '"RC Lens" Ligue 1',
    "Rennes":     '"Stade Rennais" Rennes Ligue 1',
    "Strasbourg": '"RC Strasbourg" Ligue 1',
    "Brest":      '"Stade Brestois" Brest Ligue 1',
    "Nantes":     '"FC Nantes" Ligue 1',
    "Toulouse":   '"Toulouse FC" TFC Ligue 1',
    "Auxerre":    '"AJ Auxerre" Ligue 1',
    "Le Havre":   '"Le Havre AC" HAC Ligue 1',
    "Angers":     '"Angers SCO" Ligue 1',
    "Metz":       '"FC Metz" Ligue 1',
    "Lorient":    '"FC Lorient" Ligue 1',
    "Paris FC":   '"Paris FC" Ligue 1',
}

# ------------------------------------------------------------------
# Blessés — Transfermarkt (gratuit, scraping). Vue détaillée = dates de retour.
# ------------------------------------------------------------------
TM_INJURIES_URL = "https://www.transfermarkt.fr/ligue-1/verletztespieler/wettbewerb/FR1/plus/1"
TM_CACHE_FILE = os.path.join(DATA_DIR, "injuries_cache.json")
TM_CACHE_HOURS = 12   # ne re-télécharge pas plus d'une fois toutes les 12 h

# Surveillance anti-cassure du scraping (alertes journalisées).
TM_LOG_FILE = os.path.join(DATA_DIR, "injuries.log")   # journal des récupérations + alertes
TM_MIN_EXPECTED_ROWS = 5           # en dessous = suspect (Ligue 1 a toujours des blessés)
TM_DROP_ALERT_RATIO = 0.4          # alerte si < 40 % du dernier relevé sain

# Nom Transfermarkt (mot-clé) -> nom court Football-Data.
TM_CLUB_MAP = {
    "Paris Saint-Germain": "Paris SG", "Paris FC": "Paris FC",
    "Marseille": "Marseille", "Lyon": "Lyon", "Monaco": "Monaco",
    "Lille": "Lille", "Nice": "Nice", "Lens": "Lens", "Rennes": "Rennes",
    "Strasbourg": "Strasbourg", "Brest": "Brest", "Nantes": "Nantes",
    "Toulouse": "Toulouse", "Auxerre": "Auxerre", "Le Havre": "Le Havre",
    "Angers": "Angers", "Metz": "Metz", "Lorient": "Lorient",
}
