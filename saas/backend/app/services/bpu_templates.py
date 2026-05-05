from typing import TypedDict


class BpuLineTemplate(TypedDict):
    tariff_code: str
    poste: str
    pu_fourniture: float | None
    pu_capacite: float | None
    pu_cee: float | None
    pu_go: float | None
    pu_total: float | None
    observation: str | None


# BPU Herault Energie 2026.
# Lot 7 Gaz is intentionally not mapped here yet: it will need a dedicated
# GRDF/gas billing grid because its components differ from the electricity BPU.
BPU_TEMPLATES_BY_LOT: dict[str, list[BpuLineTemplate]] = {
    "lot1": [
        {"tariff_code": "CU", "poste": "base", "pu_fourniture": 75.29, "pu_capacite": 0.52, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 88.07, "observation": None},
        {"tariff_code": "LU", "poste": "base", "pu_fourniture": 75.29, "pu_capacite": 0.52, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 88.07, "observation": None},
        {"tariff_code": "CU4", "poste": "hph", "pu_fourniture": 105.91, "pu_capacite": 1.24, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 119.41, "observation": None},
        {"tariff_code": "CU4", "poste": "hch", "pu_fourniture": 78.19, "pu_capacite": 0.32, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 90.77, "observation": None},
        {"tariff_code": "CU4", "poste": "hpe", "pu_fourniture": 51.07, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 63.33, "observation": None},
        {"tariff_code": "CU4", "poste": "hce", "pu_fourniture": 46.16, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 58.42, "observation": None},
        {"tariff_code": "MU4", "poste": "hph", "pu_fourniture": 105.91, "pu_capacite": 1.24, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 119.41, "observation": None},
        {"tariff_code": "MU4", "poste": "hch", "pu_fourniture": 78.19, "pu_capacite": 0.32, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 90.77, "observation": None},
        {"tariff_code": "MU4", "poste": "hpe", "pu_fourniture": 51.07, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 63.33, "observation": None},
        {"tariff_code": "MU4", "poste": "hce", "pu_fourniture": 46.16, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 58.42, "observation": None},
        {"tariff_code": "MUDT", "poste": "hp", "pu_fourniture": 80.12, "pu_capacite": 0.68, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 93.06, "observation": None},
        {"tariff_code": "MUDT", "poste": "hc", "pu_fourniture": 62.96, "pu_capacite": 0.15, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 75.37, "observation": None},
        {"tariff_code": "C4", "poste": "hph", "pu_fourniture": 107.81, "pu_capacite": 1.32, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 121.39, "observation": None},
        {"tariff_code": "C4", "poste": "hch", "pu_fourniture": 77.39, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 89.65, "observation": None},
        {"tariff_code": "C4", "poste": "hpe", "pu_fourniture": 49.33, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 61.59, "observation": None},
        {"tariff_code": "C4", "poste": "hce", "pu_fourniture": 51.39, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 63.65, "observation": None},
        {"tariff_code": "C2", "poste": "pointe", "pu_fourniture": 109.46, "pu_capacite": 1.26, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 122.98, "observation": None},
        {"tariff_code": "C2", "poste": "hph", "pu_fourniture": 109.46, "pu_capacite": 1.26, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 122.98, "observation": None},
        {"tariff_code": "C2", "poste": "hch", "pu_fourniture": 75.62, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 87.88, "observation": None},
        {"tariff_code": "C2", "poste": "hpe", "pu_fourniture": 51.18, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 63.44, "observation": None},
        {"tariff_code": "C2", "poste": "hce", "pu_fourniture": 45.35, "pu_capacite": 0.0, "pu_cee": 10.59, "pu_go": 1.67, "pu_total": 57.61, "observation": None},
    ],
    "lot2": [
        {"tariff_code": "CU", "poste": "base", "pu_fourniture": 75.80, "pu_capacite": 0.49, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 86.90, "observation": None},
        {"tariff_code": "LU", "poste": "base", "pu_fourniture": 75.80, "pu_capacite": 0.49, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 86.90, "observation": None},
        {"tariff_code": "CU4", "poste": "hph", "pu_fourniture": 105.58, "pu_capacite": 0.97, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 117.16, "observation": None},
        {"tariff_code": "CU4", "poste": "hch", "pu_fourniture": 74.92, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 85.53, "observation": None},
        {"tariff_code": "CU4", "poste": "hpe", "pu_fourniture": 48.84, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 59.45, "observation": None},
        {"tariff_code": "CU4", "poste": "hce", "pu_fourniture": 51.33, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 61.94, "observation": None},
        {"tariff_code": "MU4", "poste": "hph", "pu_fourniture": 105.58, "pu_capacite": 0.97, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 117.16, "observation": None},
        {"tariff_code": "MU4", "poste": "hch", "pu_fourniture": 74.92, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 85.53, "observation": None},
        {"tariff_code": "MU4", "poste": "hpe", "pu_fourniture": 48.84, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 59.45, "observation": None},
        {"tariff_code": "MU4", "poste": "hce", "pu_fourniture": 51.33, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 61.94, "observation": None},
        {"tariff_code": "MUDT", "poste": "hp", "pu_fourniture": None, "pu_capacite": None, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": None, "observation": "Prix fourniture/capacite non renseigne dans le BPU source."},
        {"tariff_code": "MUDT", "poste": "hc", "pu_fourniture": None, "pu_capacite": None, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": None, "observation": "Prix fourniture/capacite non renseigne dans le BPU source."},
        {"tariff_code": "C4", "poste": "hph", "pu_fourniture": 106.14, "pu_capacite": 1.21, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 117.96, "observation": None},
        {"tariff_code": "C4", "poste": "hch", "pu_fourniture": 78.76, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 89.37, "observation": None},
        {"tariff_code": "C4", "poste": "hpe", "pu_fourniture": 46.47, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 57.08, "observation": None},
        {"tariff_code": "C4", "poste": "hce", "pu_fourniture": 57.10, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 67.71, "observation": None},
        {"tariff_code": "C2", "poste": "pointe", "pu_fourniture": 147.19, "pu_capacite": 2.37, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 160.17, "observation": None},
        {"tariff_code": "C2", "poste": "hph", "pu_fourniture": 114.31, "pu_capacite": 0.26, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 125.18, "observation": None},
        {"tariff_code": "C2", "poste": "hch", "pu_fourniture": 87.18, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 97.79, "observation": None},
        {"tariff_code": "C2", "poste": "hpe", "pu_fourniture": 82.56, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 93.17, "observation": None},
        {"tariff_code": "C2", "poste": "hce", "pu_fourniture": 64.40, "pu_capacite": 0.0, "pu_cee": 9.09, "pu_go": 1.52, "pu_total": 75.01, "observation": None},
    ],
}


def get_bpu_template(lot: str | None) -> list[BpuLineTemplate]:
    if not lot:
        return []
    return BPU_TEMPLATES_BY_LOT.get(lot, [])
