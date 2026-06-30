"""
Niveau de lecture du match — consolide les facteurs de contexte (enjeu fort,
derby, trêve) en UN seul indicateur transparent : Standard / À nuancer /
Volatil.

⚠ Règle absolue : ce module ne fait QUE compter des facteurs déjà calculés
ailleurs (stakes, derby, calendar_context). Il ne pondère rien, n'invente
aucun chiffre, et surtout NE TOUCHE JAMAIS aux probabilités affichées
(P_home/P_draw/P_away, qui restent 100% celles du marché). Il sert
uniquement à dire "ce match a plus de grain de sable que la moyenne",
jamais "voici le bon pari".

Seuls les facteurs jugés réellement "hors normale" comptent (niveau Fort
d'enjeu, pas Moyen — sinon presque tous les matchs de milieu/fin de saison
seraient comptés, ce qui diluerait le signal).
"""

LEVEL_BY_COUNT = {0: "Standard", 1: "Standard", 2: "À nuancer"}
DEFAULT_LEVEL_3PLUS = "Volatil"


def match_context_level(home_team, away_team, home_stakes, away_stakes, derby, break_info):
    factors = []

    if derby:
        factors.append(f"Derby : {derby}")

    if home_stakes and home_stakes.get("level") == "Fort":
        factors.append(f"{home_team} : {home_stakes.get('enjeu_label', '')}")

    if away_stakes and away_stakes.get("level") == "Fort":
        factors.append(f"{away_team} : {away_stakes.get('enjeu_label', '')}")

    if break_info and break_info.get("detected"):
        factors.append(break_info.get("label", "Reprise après une pause"))

    n = len(factors)
    level = LEVEL_BY_COUNT.get(n, DEFAULT_LEVEL_3PLUS)

    return {"level": level, "count": n, "factors": factors}
