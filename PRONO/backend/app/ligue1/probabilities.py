"""
Moteur de probabilités = cotes sharp dévigottées (méthode proportionnelle).

Pour chaque match, on prend la source la plus fiable disponible
(Pinnacle > Bet365 > Moyenne) et on convertit les cotes 1/N/2 en probabilités
en retirant la marge du bookmaker (normalisation proportionnelle des
probabilités implicites). Pas de dépendance lourde (scipy retiré).
"""
import numpy as np
import pandas as pd

from .config import ODDS_SOURCES, CONF_FORT, CONF_MOYEN, DRAW_MAX_FOR_FORT

OUTCOMES = ["H", "D", "A"]


def _devig(odds):
    """3 cotes décimales -> (probas normalisées, marge bookmaker)."""
    odds = np.asarray(odds, dtype=float)
    if np.any(~np.isfinite(odds)) or np.any(odds <= 1.0):
        return None, np.nan
    inv = 1.0 / odds
    s = inv.sum()
    return inv / s, float(s - 1.0)


def _pick_source(row):
    for name, cols in ODDS_SOURCES:
        if all(c in row.index for c in cols.values()):
            p, margin = _devig([row.get(cols["H"]), row.get(cols["D"]), row.get(cols["A"])])
            if p is not None:
                return name, p, margin
    return None, None, np.nan


def _confidence(p_pick, p_draw):
    if not np.isfinite(p_pick):
        return "Indéterminé"
    if p_pick >= CONF_FORT and (not np.isfinite(p_draw) or p_draw <= DRAW_MAX_FOR_FORT):
        return "Fort"
    if p_pick >= CONF_MOYEN:
        return "Moyen"
    return "Faible"


def compute_probabilities(matches: pd.DataFrame) -> pd.DataFrame:
    out = matches.copy().reset_index(drop=True)
    rec = []
    for _, r in out.iterrows():
        src, p, margin = _pick_source(r)
        if p is None:
            rec.append(dict(P_home=np.nan, P_draw=np.nan, P_away=np.nan, source="aucune",
                            book_margin=np.nan, pick_outcome="", pick="",
                            pick_proba=np.nan, confidence="Indéterminé"))
            continue
        i = int(np.argmax(p))
        outcome = OUTCOMES[i]
        label = r["HomeTeam"] if outcome == "H" else (r["AwayTeam"] if outcome == "A" else "Nul")
        rec.append(dict(P_home=p[0], P_draw=p[1], P_away=p[2], source=src, book_margin=margin,
                        pick_outcome=outcome, pick=label, pick_proba=p[i],
                        confidence=_confidence(p[i], p[1])))
    return pd.concat([out, pd.DataFrame(rec)], axis=1)
