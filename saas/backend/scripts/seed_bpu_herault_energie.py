"""
Import BPU Hérault Énergie 2026 — Lots 1, 2
  EDF   → Lot 2 Éclairage Public   (302 PRMs)
  ENGIE → Lot 1 Bâtiments          (227 PRMs)

Données saisies depuis BPU_2026_Lots_1_2_et_7.xlsx transmis le 2026-05-05.
year=None = prix courants (utilisés par défaut dans le wizard et la facturation).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import SessionLocal
from app.models.billing import BillingBpuLine, BillingConfig

CITY_ID = 1  # Sète

# ── Lot 2 — Éclairage Public (EDF) ───────────────────────────────────────────
# Source : BPU onglet "Lot 2" colonnes Assimilé EP / EP
# (fourniture, capacite, cee, go, total) en €/MWh HTT

BPU_LOT2_EDF: dict[str, list[tuple]] = {
    "CU": [
        ("base",    75.80, 0.49, 9.09, 1.52, 86.90),
    ],
    "LU": [
        ("base",    75.80, 0.49, 9.09, 1.52, 86.90),
    ],
    "CU4": [
        ("hph",   105.58, 0.97, 9.09, 1.52, 117.16),
        ("hch",    74.92, 0.00, 9.09, 1.52,  85.53),
        ("hpe",    48.84, 0.00, 9.09, 1.52,  59.45),
        ("hce",    51.33, 0.00, 9.09, 1.52,  61.94),
    ],
    "MU4": [
        ("hph",   105.58, 0.97, 9.09, 1.52, 117.16),
        ("hch",    74.92, 0.00, 9.09, 1.52,  85.53),
        ("hpe",    48.84, 0.00, 9.09, 1.52,  59.45),
        ("hce",    51.33, 0.00, 9.09, 1.52,  61.94),
    ],
    # MUDT lot 2 : fourniture/capacité non renseignées (cellules noires BPU)
    "MUDT": [
        ("hp",   None,  None,  9.09, 1.52, None),
        ("hc",   None,  None,  9.09, 1.52, None),
    ],
    "C4": [
        ("hph",   106.14, 1.21, 9.09, 1.52, 117.96),
        ("hch",    78.76, 0.00, 9.09, 1.52,  89.37),
        ("hpe",    46.47, 0.00, 9.09, 1.52,  57.08),
        ("hce",    57.10, 0.00, 9.09, 1.52,  67.71),
    ],
    "C2": [
        ("pointe", 147.19, 2.37, 9.09, 1.52, 160.17),
        ("hph",    114.31, 0.26, 9.09, 1.52, 125.18),
        ("hch",     87.18, 0.00, 9.09, 1.52,  97.79),
        ("hpe",     82.56, 0.00, 9.09, 1.52,  93.17),
        ("hce",     64.40, 0.00, 9.09, 1.52,  75.01),
    ],
}

# ── Lot 1 — Bâtiments (ENGIE) ─────────────────────────────────────────────────
# Source : BPU onglet "Lot 1" colonnes Bâtiment

BPU_LOT1_ENGIE: dict[str, list[tuple]] = {
    "CU": [
        ("base",    75.29, 0.52, 10.59, 1.67, 88.07),
    ],
    "LU": [
        ("base",    75.29, 0.52, 10.59, 1.67, 88.07),
    ],
    "CU4": [
        ("hph",   105.91, 1.24, 10.59, 1.67, 119.41),
        ("hch",    78.19, 0.32, 10.59, 1.67,  90.77),
        ("hpe",    51.07, 0.00, 10.59, 1.67,  63.33),
        ("hce",    46.16, 0.00, 10.59, 1.67,  58.42),
    ],
    "MU4": [
        ("hph",   105.91, 1.24, 10.59, 1.67, 119.41),
        ("hch",    78.19, 0.32, 10.59, 1.67,  90.77),
        ("hpe",    51.07, 0.00, 10.59, 1.67,  63.33),
        ("hce",    46.16, 0.00, 10.59, 1.67,  58.42),
    ],
    "MUDT": [
        ("hp",    80.12, 0.68, 10.59, 1.67,  93.06),
        ("hc",    62.96, 0.15, 10.59, 1.67,  75.37),
    ],
    "C4": [
        ("hph",   107.81, 1.32, 10.59, 1.67, 121.39),
        ("hch",    77.39, 0.00, 10.59, 1.67,  89.65),
        ("hpe",    49.33, 0.00, 10.59, 1.67,  61.59),
        ("hce",    51.39, 0.00, 10.59, 1.67,  63.65),
    ],
    "C2": [
        ("pointe", 109.46, 1.26, 10.59, 1.67, 122.98),
        ("hph",    109.46, 1.26, 10.59, 1.67, 122.98),
        ("hch",     75.62, 0.00, 10.59, 1.67,  87.88),
        ("hpe",     51.18, 0.00, 10.59, 1.67,  63.44),
        ("hce",     45.35, 0.00, 10.59, 1.67,  57.61),
    ],
}


def seed(db, supplier: str, lot: str, bpu: dict) -> None:
    cfg = db.query(BillingConfig).filter_by(city_id=CITY_ID, supplier=supplier).first()
    if not cfg:
        cfg = BillingConfig(city_id=CITY_ID, supplier=supplier, tariff_code=None, lot=lot, has_hphc=True)
        db.add(cfg)
        db.flush()
        print(f"  Config créée  id={cfg.id}")
    else:
        cfg.lot = lot
        print(f"  Config trouvée id={cfg.id} → lot mis à jour : {lot}")

    # Remplacement idempotent (year=None = prix courants)
    deleted = db.query(BillingBpuLine).filter_by(config_id=cfg.id, year=None).delete()
    if deleted:
        print(f"  {deleted} ligne(s) existante(s) supprimées")

    lines = []
    for tariff_code, rows in bpu.items():
        for (poste, pu_f, pu_c, pu_cee, pu_go, pu_total) in rows:
            lines.append(BillingBpuLine(
                config_id=cfg.id,
                year=None,
                tariff_code=tariff_code,
                poste=poste,
                pu_fourniture=pu_f,
                pu_capacite=pu_c,
                pu_cee=pu_cee,
                pu_go=pu_go,
                pu_total=pu_total,
            ))
    db.add_all(lines)
    db.commit()
    print(f"  {len(lines)} lignes BPU insérées")


def main() -> None:
    db = SessionLocal()
    try:
        print("\n=== Seed BPU Hérault Énergie 2026 ===\n")

        print("ELECTRICITE DE FRANCE → Lot 2 Éclairage Public")
        seed(db, "ELECTRICITE DE FRANCE", "lot2", BPU_LOT2_EDF)

        print("\nENGIE → Lot 1 Bâtiments")
        seed(db, "ENGIE", "lot1", BPU_LOT1_ENGIE)

        print("\n✓ Terminé")
    finally:
        db.close()


if __name__ == "__main__":
    main()
