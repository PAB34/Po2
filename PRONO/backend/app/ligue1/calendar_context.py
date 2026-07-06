"""
Trêve internationale / hivernale — détectée depuis NOS PROPRES données de
calendrier, sans source externe : un écart anormal entre deux journées de
Ligue 1 trahit presque toujours une coupure (trêve FIFA ou trêve hivernale
française). Aucune fiche joueur par joueur (convocation en sélection,
décalage horaire) n'est faite ici — c'est hors de portée gratuite — mais le
simple fait de signaler "ce week-end suit une coupure de X jours" est déjà
un contexte réel et vérifiable, à 100% gratuit et sans entretien.

Méthode : on mesure l'écart entre la dernière date jouée et la première
date de la prochaine journée. Un écart "normal" en Ligue 1 est de 3 à 7
jours (rythme hebdomadaire, parfois resserré en semaine). Au-delà, on
distingue :
  - trêve FIFA (sept/oct/nov/mars : fenêtres internationales standard
    pendant la saison) ;
  - trêve hivernale (coupure de fin d'année, spécifique au football
    français) ;
  - pause prolongée générique si la cause ne correspond à aucun des deux
    cas ci-dessus (on ne prétend pas connaître la raison).
"""
import pandas as pd

from .config import BREAK_GAP_THRESHOLD_DAYS, FIFA_WINDOW_MONTHS

WINTER_MONTHS = {12, 1}


def detect_break(hist: pd.DataFrame, season: str, upcoming_start) -> dict:
    """Renvoie un dict décrivant la coupure avant `upcoming_start`, ou
    {'detected': False} si l'écart est normal (ou en tout début de saison)."""
    upcoming_start = pd.Timestamp(upcoming_start).normalize()
    g = hist[(hist["Season"].astype(str) == str(season)) & hist["FTR"].isin(["H", "D", "A"])]
    if g.empty:
        return {"detected": False}

    prev_dates = g[g["Kickoff"].dt.normalize() < upcoming_start]["Kickoff"]
    if prev_dates.empty:
        return {"detected": False}  # tout début de saison : rien à comparer

    prev_date = prev_dates.max().normalize()
    gap_days = (upcoming_start - prev_date).days

    if gap_days < BREAK_GAP_THRESHOLD_DAYS:
        return {"detected": False, "gap_days": gap_days}

    spans_winter = prev_date.month in WINTER_MONTHS or upcoming_start.month in WINTER_MONTHS
    spans_fifa_window = prev_date.month in FIFA_WINDOW_MONTHS or upcoming_start.month in FIFA_WINDOW_MONTHS

    if spans_winter and gap_days >= 14:
        label = "Reprise après la trêve hivernale"
        note = (f"{gap_days} jours sans match : la Ligue 1 a observé sa coupure de fin "
               f"d'année. Les équipes peuvent manquer de rythme à la reprise.")
        kind = "hivernale"
    elif spans_fifa_window:
        label = "Reprise après une trêve internationale"
        note = (f"{gap_days} jours sans match : trêve internationale (sélections). "
               f"Joueurs convoqués potentiellement fatigués ou décalés au retour.")
        kind = "internationale"
    else:
        label = "Reprise après une pause prolongée"
        note = f"{gap_days} jours sans match avant cette journée (raison non déterminée)."
        kind = "inconnue"

    return {"detected": True, "gap_days": gap_days, "kind": kind, "label": label, "note": note}
