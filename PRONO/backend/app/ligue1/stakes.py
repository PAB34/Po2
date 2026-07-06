"""
Enjeu réel du match — pas une statistique de forme, mais la SITUATION du
classement : qu'est-ce que cette équipe a encore à jouer (titre, Europe,
maintien) compte tenu des points, du nombre de matchs restants et des autres
équipes ? C'est le facteur que le marché intègre souvent de façon plus
grossière que les stats de forme pures, surtout en fin de saison (matchs
sans enjeu, "dead rubber") ou en différentiel entre les deux équipes d'un
même match.

Méthode : classement reconstruit depuis les résultats Football-Data de la
saison en cours, puis un calcul d'élimination mathématique SIMPLIFIÉ (borne
triviale : points actuels vs points maximum atteignable par l'adversaire le
plus proche de la zone). Ce n'est PAS une preuve combinatoire complète
(qui demanderait de simuler tous les calendriers restants des concurrents),
mais c'est l'estimation standard utilisée dans le journalisme sportif.
Toujours présenté comme une estimation, jamais comme un fait certain avant
qu'il ne soit mathématiquement acquis.
"""
import numpy as np
import pandas as pd

from .config import (
    LIGUE1_EUROPE_ZONE, LIGUE1_RELEGATION_ZONE,
    LIGUE1_LUTTE_GAP_SHARE, LIGUE1_LUTTE_GAP_CAP, LIGUE1_LUTTE_GAP_FLOOR,
    LIGUE1_TRES_TOT_PLAYED_MAX_RATIO, LIGUE1_FIN_DE_SAISON_REMAINING_RATIO,
)

RES_PTS = {"H": (3, 0), "A": (0, 3), "D": (1, 1)}


def _season_sort_key(season):
    s = str(season)
    return int(s) if s.isdigit() else -1


def current_season(hist: pd.DataFrame) -> str:
    """Saison la plus récente présente dans l'historique."""
    seasons = hist["Season"].astype(str).unique()
    if len(seasons) == 0:
        return ""
    return sorted(seasons, key=_season_sort_key)[-1]


def compute_standings(hist: pd.DataFrame, season: str) -> pd.DataFrame:
    """Classement actuel de la saison (matchs déjà joués uniquement)."""
    g = hist[(hist["Season"].astype(str) == str(season)) & hist["FTR"].isin(["H", "D", "A"])]
    rows = {}

    def ensure(t):
        if t not in rows:
            rows[t] = {"team": t, "played": 0, "points": 0, "gf": 0, "ga": 0, "w": 0, "d": 0, "l": 0}

    for _, r in g.iterrows():
        h, a = r["HomeTeam"], r["AwayTeam"]
        ensure(h); ensure(a)
        hg, ag = int(r["FTHG"]), int(r["FTAG"])
        hp, ap = RES_PTS[r["FTR"]]
        rows[h]["played"] += 1; rows[a]["played"] += 1
        rows[h]["points"] += hp; rows[a]["points"] += ap
        rows[h]["gf"] += hg; rows[h]["ga"] += ag
        rows[a]["gf"] += ag; rows[a]["ga"] += hg
        rows[h]["w" if hp == 3 else ("d" if hp == 1 else "l")] += 1
        rows[a]["w" if ap == 3 else ("d" if ap == 1 else "l")] += 1

    if not rows:
        return pd.DataFrame(columns=["team", "rank", "played", "points", "gd", "gf", "ga",
                                     "n_teams", "total_matchdays", "games_remaining", "max_points"])

    df = pd.DataFrame(list(rows.values()))
    df["gd"] = df["gf"] - df["ga"]
    df = df.sort_values(["points", "gd", "gf"], ascending=False).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)

    n_teams = len(df)
    total_matchdays = (n_teams - 1) * 2  # championnat aller-retour standard
    df["n_teams"] = n_teams
    df["total_matchdays"] = total_matchdays
    df["games_remaining"] = (total_matchdays - df["played"]).clip(lower=0)
    df["max_points"] = df["points"] + df["games_remaining"] * 3
    return df


def _lutte_threshold(games_remaining: int) -> float:
    """Seuil 'en lutte', resserré mécaniquement à mesure que la saison avance."""
    points_en_jeu = games_remaining * 3
    dynamic = LIGUE1_LUTTE_GAP_SHARE * points_en_jeu
    return max(LIGUE1_LUTTE_GAP_FLOOR, min(LIGUE1_LUTTE_GAP_CAP, dynamic))


def _season_stage(played: int, total_matchdays: int, games_remaining: int) -> str:
    if total_matchdays <= 0:
        return "coeur"
    if games_remaining == 0:
        return "terminee"
    if played <= round(total_matchdays * LIGUE1_TRES_TOT_PLAYED_MAX_RATIO):
        return "tres_tot"
    if games_remaining <= round(total_matchdays * LIGUE1_FIN_DE_SAISON_REMAINING_RATIO):
        return "fin"
    return "coeur"


def _stage_qualifier(stage: str, level: str, games_remaining: int) -> str:
    """Texte ajouté au libellé pour refléter l'avancement de la saison (hors tres_tot,
    géré séparément car le calcul d'enjeu par zone n'est pas fiable à ce stade)."""
    if stage == "fin" and level == "Fort":
        if games_remaining <= 3:
            return f" — décisif (plus que {games_remaining} match(s))"
        return " — sprint final"
    return ""


def _enjeu_label(flags, rank, n_teams, games_remaining, europe_zone, releg_zone, gaps):
    """Construit un libellé d'enjeu + un niveau (Fort/Moyen/Faible).

    Deux logiques distinctes, dans cet ordre de priorité :
    1. Les statuts CONFIRMÉS (élimination/qualification mathématique) — rares,
       ne se déclenchent quasiment qu'en toute fin de saison.
    2. Le statut "EN LUTTE", basé sur l'écart de points à la zone concernée
       (LIGUE1_LUTTE_GAP_POINTS) — le signal utile dès le milieu de saison.
    """
    if games_remaining == 0:
        # Saison terminée : le classement est définitif, plus de "lutte" possible.
        if rank == 1:
            return "Titre remporté (saison terminée)", "Faible"
        if rank <= europe_zone:
            return "Place européenne obtenue (saison terminée)", "Faible"
        if rank > n_teams - releg_zone:
            return "Relégué (saison terminée)", "Faible"
        return "Saison terminée, sans enjeu", "Faible"

    # --- 1) Statuts mathématiquement confirmés (rares, fin de saison) ---
    if flags["champion_confirme"]:
        return "Titre déjà assuré mathématiquement", "Faible"
    if flags["relegation_confirmee"]:
        return "Déjà relégué mathématiquement", "Faible"
    if flags["europe_confirmee"]:
        return "Place européenne déjà assurée mathématiquement", "Faible"
    if flags["maintien_confirme"]:
        return "Maintien déjà assuré, sans autre enjeu", "Faible"

    # --- 2) "En lutte" par écart de points (signal utile toute la saison) ---
    # Priorité : maintien (urgence la plus concrète) > titre (pour les
    # équipes de tête, avant de retomber sur le générique "zone Europe") >
    # Europe > rien à jouer.
    if flags["en_zone_relegation"]:
        return "Lutte pour le maintien (zone rouge)", "Fort"
    if gaps["releg"] is not None and gaps["releg"] <= 0:
        return "Lutte pour le maintien (zone rouge)", "Fort"
    if gaps["releg"] is not None and 0 < gaps["releg"] <= gaps["threshold"]:
        return "Lutte pour le maintien (menacé)", "Fort"

    if rank <= 4 and gaps["title"] is not None and gaps["title"] <= gaps["threshold"]:
        return "Lutte pour le titre", "Fort"
    if rank == 1:
        return "En tête du championnat", "Moyen"

    if flags["en_zone_europe"]:
        return "Défend sa place européenne", "Moyen"
    if gaps["europe"] is not None and gaps["europe"] <= gaps["threshold"]:
        return "Lutte pour une place européenne", "Moyen"

    return "Sans enjeu direct (ventre mou)", "Faible"


def team_stakes(standings: pd.DataFrame, team: str) -> dict:
    row = standings[standings["team"] == team]
    if not len(row) or standings.empty:
        return {"team": team, "summary": f"{team} — classement indisponible.", "level": "Indéterminé"}

    row = row.iloc[0]
    n = int(row["n_teams"])
    rank = int(row["rank"])
    points = int(row["points"])
    max_points = int(row["max_points"])
    games_remaining = int(row["games_remaining"])
    played = int(row["played"])
    total_matchdays = int(row["total_matchdays"])
    stage = _season_stage(played, total_matchdays, games_remaining)

    leader_points = int(standings.iloc[0]["points"])
    europe_zone = min(LIGUE1_EUROPE_ZONE, n)
    releg_zone = min(LIGUE1_RELEGATION_ZONE, n)

    europe_boundary = standings.iloc[europe_zone - 1]   # dernière place européenne
    europe_outside = standings.iloc[europe_zone] if n > europe_zone else None
    releg_boundary = standings.iloc[n - releg_zone]      # première place hors relégation
    releg_inside = standings.iloc[n - releg_zone]         # première équipe reléguée (même ligne si zone=boundary+1)

    flags = {
        "en_zone_europe": rank <= europe_zone,
        "en_zone_relegation": rank > n - releg_zone,
        # Élimination titre : même avec un sans-faute, n'atteint pas le total actuel du leader.
        "elimine_titre": (rank > 1) and (max_points < leader_points),
        "champion_confirme": (rank == 1) and (points > int(standings.iloc[1]["max_points"])) if n > 1 else False,
        # Élimination Europe : même avec un sans-faute, ne dépasse pas l'équipe juste devant la zone.
        "elimine_europe": (not (rank <= europe_zone)) and (europe_outside is not None) and
                          (max_points < int(europe_boundary["points"])),
        "europe_confirmee": (rank <= europe_zone) and (points > int(europe_outside["max_points"]))
                            if europe_outside is not None else (rank <= europe_zone and games_remaining == 0),
        # Sécurité maintien : même si le concurrent danger gagne tout, ne peut pas nous rattraper.
        "safe_relegation": points > int(releg_inside["max_points"]) if rank <= n - releg_zone else False,
        "relegation_confirmee": (rank > n - releg_zone) and (max_points < int(releg_boundary["points"])),
    }
    flags["maintien_confirme"] = flags["safe_relegation"] and games_remaining > 0 and not flags["en_zone_europe"]

    # Trop tôt dans la saison : le classement n'est pas encore assez "étalé" pour
    # qu'un écart de points en zone basse/haute du tableau veuille dire quoi que ce
    # soit (ex. après 5 matchs, presque toutes les équipes sont à quelques points
    # les unes des autres — ça ne reflète pas une vraie proximité compétitive).
    # On ne classe PAS par zone à ce stade (sauf les statuts mathématiquement
    # confirmés ci-dessus, qui restent des faits valables à tout moment).
    confirmed_any = any([flags["champion_confirme"], flags["relegation_confirmee"],
                         flags["europe_confirmee"], flags["maintien_confirme"]])
    if stage == "tres_tot" and not confirmed_any:
        enjeu_label_full = f"Trop tôt pour évaluer l'enjeu (saison qui débute, {played} match(s) joué(s))"
        summary = (f"{team} — {rank}e place provisoire, {points} pts en {played} matchs. "
                  f"{enjeu_label_full}.")
        return {
            "team": team, "rank": rank, "n_teams": n, "points": points,
            "played": played, "games_remaining": games_remaining,
            "max_points": max_points, "gd": int(row["gd"]),
            "enjeu_label": enjeu_label_full, "level": "Faible", "season_stage": stage,
            "lutte_threshold": None, "flags": flags, "summary": summary,
        }

    threshold = _lutte_threshold(games_remaining) if games_remaining > 0 else 0.0
    # Écarts de points (None si la notion ne s'applique pas à cette équipe).
    gaps = {
        "threshold": threshold,
        # Écart pour sortir de la zone rouge (si en dehors) : points - (points du premier relégable).
        "releg": (points - int(releg_inside["points"])) if rank <= n - releg_zone else None,
        # Écart pour entrer en zone Europe (si en dehors) : points du dernier qualifié - points.
        "europe": (int(europe_boundary["points"]) - points) if rank > europe_zone else None,
        # Écart au leader (si pas déjà leader).
        "title": (leader_points - points) if rank > 1 else None,
    }

    enjeu_label, level = _enjeu_label(flags, rank, n, games_remaining, europe_zone, releg_zone, gaps)
    enjeu_label_full = enjeu_label + _stage_qualifier(stage, level, games_remaining)

    summary = (f"{team} — {rank}e place, {points} pts en {played} matchs "
              f"({games_remaining} restants). {enjeu_label_full}.")

    return {
        "team": team, "rank": rank, "n_teams": n, "points": points,
        "played": played, "games_remaining": games_remaining,
        "max_points": max_points, "gd": int(row["gd"]),
        "enjeu_label": enjeu_label_full, "level": level, "season_stage": stage,
        "lutte_threshold": round(threshold, 1),
        "flags": flags, "summary": summary,
    }


def match_stakes_note(home_stakes: dict, away_stakes: dict) -> str:
    """Note de synthèse si l'enjeu est asymétrique entre les deux équipes."""
    lvl_order = {"Fort": 2, "Moyen": 1, "Faible": 0, "Indéterminé": -1}
    lh = lvl_order.get(home_stakes.get("level"), -1)
    la = lvl_order.get(away_stakes.get("level"), -1)
    if lh < 0 or la < 0 or lh == la:
        return ""
    fort, faible = (home_stakes, away_stakes) if lh > la else (away_stakes, home_stakes)
    return (f"Enjeu asymétrique : {fort['team']} joue gros ({fort['enjeu_label'].lower()}) "
           f"face à {faible['team']}, qui n'a pas la même pression ({faible['enjeu_label'].lower()}).")


def journee_stakes(hist: pd.DataFrame, matches: pd.DataFrame) -> dict:
    season = current_season(hist)
    standings = compute_standings(hist, season)
    teams = pd.unique(pd.concat([matches["HomeTeam"], matches["AwayTeam"]]))
    return {t: team_stakes(standings, t) for t in teams}, standings, season
