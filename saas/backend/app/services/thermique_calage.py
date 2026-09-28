"""Calage d'une planche sur la planche de référence du projet (S2, D173 ; décision Q10 du 2026-09-11).

Chaque planche porte une similitude — rotation, échelle, décalage — qui envoie ses points PDF sur ceux de la
référence. Deux paires de points communs suffisent (croisement d'axes, angle de cage d'escalier, poteau).
Le calcul se fait en nombres complexes : z' = s·z + t, s portant la rotation et l'échelle.

Un calage se fait toujours contre une planche **déjà calée** (ou la référence elle-même) : la chaîne remonte
donc à la référence sans jamais se refermer sur elle-même.
"""
from __future__ import annotations

import json
from typing import Any

from app.models.thermique import ThermiqueSheet

# En deçà, deux points sont trop proches pour fixer une rotation : un clic de travers la fausserait.
ECART_MIN_PT = 20.0


def similitude(sources: list[list[float]], cibles: list[list[float]]) -> dict[str, float]:
    """La similitude qui envoie les deux points `sources` sur les deux points `cibles`."""
    if len(sources) != 2 or len(cibles) != 2:
        raise ValueError("Le calage demande exactement deux paires de points.")
    z1, z2 = (complex(float(x), float(y)) for x, y in sources)
    w1, w2 = (complex(float(x), float(y)) for x, y in cibles)
    if abs(z2 - z1) < ECART_MIN_PT or abs(w2 - w1) < ECART_MIN_PT:
        raise ValueError("Les deux points de calage sont trop proches : écartez-les sur le plan.")
    s = (w2 - w1) / (z2 - z1)
    t = w1 - s * z1
    return {"a": s.real, "b": s.imag, "tx": t.real, "ty": t.imag}


def appliquer(sim: dict[str, float], point: list[float]) -> list[float]:
    z = complex(sim["a"], sim["b"]) * complex(float(point[0]), float(point[1])) + complex(sim["tx"], sim["ty"])
    return [z.real, z.imag]


def composer(apres: dict[str, float], avant: dict[str, float]) -> dict[str, float]:
    """`apres` ∘ `avant` : on applique d'abord `avant`, puis `apres`."""
    s1, t1 = complex(avant["a"], avant["b"]), complex(avant["tx"], avant["ty"])
    s2, t2 = complex(apres["a"], apres["b"]), complex(apres["tx"], apres["ty"])
    s, t = s2 * s1, s2 * t1 + t2
    return {"a": s.real, "b": s.imag, "tx": t.real, "ty": t.imag}


IDENTITE = {"a": 1.0, "b": 0.0, "tx": 0.0, "ty": 0.0}


def charger(sheet: ThermiqueSheet) -> dict[str, Any] | None:
    if not sheet.calage_json:
        return None
    try:
        return json.loads(sheet.calage_json)
    except (TypeError, ValueError):
        return None


def vers_reference(sheet: ThermiqueSheet, reference_id: int | None) -> dict[str, float] | None:
    """La similitude de la planche vers la référence : l'identité pour la référence, sinon son calage."""
    if reference_id is None:
        return None
    if sheet.id == reference_id:
        return dict(IDENTITE)
    calage = charger(sheet)
    if not calage or calage.get("reference_sheet_id") != reference_id:
        return None
    return {cle: float(calage[cle]) for cle in ("a", "b", "tx", "ty")}


def caler(
    sheet: ThermiqueSheet,
    cible: ThermiqueSheet,
    reference_id: int,
    points: list[list[float]],
    points_cible: list[list[float]],
) -> dict[str, Any]:
    """Cale `sheet` sur la référence, par deux points qu'elle partage avec `cible`, elle-même calée."""
    if sheet.id == reference_id:
        raise ValueError("La planche de référence ne se cale pas : ce sont les autres qui se calent sur elle.")
    cible_vers_ref = vers_reference(cible, reference_id)
    if cible_vers_ref is None:
        raise ValueError("Calez d'abord l'autre planche sur la planche de référence du projet.")
    vers_cible = similitude(points, points_cible)
    vers_ref = composer(cible_vers_ref, vers_cible)
    # Contrôle : le rapport d'échelle trouvé doit être celui des échelles déclarées des deux planches.
    ecart_pct = None
    if sheet.scale_denominator and cible.scale_denominator:
        attendu = float(sheet.scale_denominator) / float(cible.scale_denominator)
        trouve = abs(complex(vers_cible["a"], vers_cible["b"]))
        ecart_pct = round((trouve / attendu - 1) * 100, 2)
    return {
        **{cle: round(valeur, 9) for cle, valeur in vers_ref.items()},
        "reference_sheet_id": reference_id,
        "cible_sheet_id": cible.id,
        "points": [[round(float(x), 3), round(float(y), 3)] for x, y in points],
        "points_cible": [[round(float(x), 3), round(float(y), 3)] for x, y in points_cible],
        "ecart_echelle_pct": ecart_pct,
    }
