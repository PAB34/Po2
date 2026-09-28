"""Catalogue des ponts thermiques types de la NF EN ISO 14683, tableau C.2 (D158).

Le fichier est une transcription : il est lu tel quel, jamais recalculé. Un pont du relevé y renvoie par son
code (`C1`, `IW3`…) ; celui que le catalogue ne couvre pas est « à modéliser » (NF EN ISO 10211).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

FICHIER = Path(__file__).resolve().parents[1] / "data" / "thermique_ponts_iso14683.json"

# Un pont absent du catalogue : il reste compté, mais sa valeur ψ est à calculer à part.
A_MODELISER = "a_modeliser"


@lru_cache(maxsize=1)
def catalogue() -> dict[str, Any]:
    return json.loads(FICHIER.read_text(encoding="utf-8"))


def codes() -> set[str]:
    return {pont["code"] for pont in catalogue()["ponts"]}


def reference_valide(valeur: str) -> bool:
    return valeur == A_MODELISER or valeur in codes()
