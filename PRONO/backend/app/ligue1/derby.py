"""
Derby / rivalité — contexte de match qui ne se lit pas dans les stats brutes.

Un derby se joue différemment d'un match neutre : intensité plus forte, plus
de cartons, scores souvent plus serrés, motivation indépendante du
classement. Le marché le sait globalement (la cote en tient compte dans
l'absolu), mais c'est une information utile à AFFICHER pour comprendre une
cote ou un nombre de buts/cartons qui semblerait sinon "anormal".

Table statique, pas de scraping — donc fiable et sans entretien, à mettre à
jour seulement si de nouveaux clubs montent en Ligue 1.
"""

# Paires (triées alphabétiquement) -> nom usuel de la rivalité.
# Limité aux clubs réguliers/actuels de Ligue 1 ; harmless si l'un des deux
# n'est pas en L1 cette saison (le derby restera simplement inactif).
DERBY_PAIRS = {
    tuple(sorted(("Paris SG", "Marseille"))): "Le Classique",
    tuple(sorted(("Lille", "Lens"))): "Derby du Nord",
    tuple(sorted(("Nantes", "Rennes"))): "Derby Breton",
    tuple(sorted(("Monaco", "Nice"))): "Derby de la Côte d'Azur",
    tuple(sorted(("Marseille", "Nice"))): "Derby Méditerranéen",
    tuple(sorted(("Paris SG", "Paris FC"))): "Derby Parisien",
    tuple(sorted(("Brest", "Lorient"))): "Derby Breton (Finistère/Morbihan)",
    tuple(sorted(("Rennes", "Lorient"))): "Derby Breton",
    tuple(sorted(("Lyon", "Saint Etienne"))): "Derby Rhône-Alpes",
    tuple(sorted(("Lyon", "St Etienne"))): "Derby Rhône-Alpes",
    tuple(sorted(("Metz", "Nancy"))): "Derby Lorrain",
    tuple(sorted(("Toulouse", "Bordeaux"))): "Derby du Sud-Ouest",
    tuple(sorted(("Montpellier", "Nimes"))): "Derby du Languedoc",
    tuple(sorted(("Nantes", "Bordeaux"))): "Derby de l'Atlantique",
}


def derby_name(team_a: str, team_b: str):
    """Renvoie le nom de la rivalité si c'est un derby connu, sinon None."""
    return DERBY_PAIRS.get(tuple(sorted((team_a, team_b))))


def is_derby(team_a: str, team_b: str) -> bool:
    return derby_name(team_a, team_b) is not None
