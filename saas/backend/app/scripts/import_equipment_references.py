"""
Import du référentiel équipements/matériaux depuis le CSV de durées de vie.

Usage:
    python -m app.scripts.import_equipment_references <csv_path> [--truncate]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.equipment import EquipmentReference


def _parse_float(value: str) -> float | None:
    if not value or not value.strip():
        return None
    try:
        return float(value.strip().replace(",", "."))
    except ValueError:
        return None


def import_equipment_references(csv_path: Path, truncate: bool) -> tuple[int, int, int]:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)

    if not rows:
        raise ValueError("Le fichier CSV est vide.")

    with SessionLocal() as db:
        if truncate:
            db.query(EquipmentReference).delete()
            db.flush()

        existing = {
            er.id_ligne: er
            for er in db.scalars(select(EquipmentReference)).all()
        }

        created_count = 0
        updated_count = 0

        for row in rows:
            id_ligne = int(row["id_ligne"])
            data = {
                "code_niveau_1": row.get("code_niveau_1", "").strip(),
                "libelle_niveau_1": row.get("libelle_niveau_1", "").strip(),
                "code_niveau_2": row.get("code_niveau_2", "").strip(),
                "libelle_niveau_2": row.get("libelle_niveau_2", "").strip(),
                "niveau_3": row.get("niveau_3", "").strip() or None,
                "niveau_4": row.get("niveau_4", "").strip() or None,
                "niveau_5": row.get("niveau_5", "").strip() or None,
                "equipement": row.get("equipement", "").strip(),
                "sypemi_mini_annees": _parse_float(row.get("sypemi_mini_annees", "")),
                "sypemi_reference_annees": _parse_float(row.get("sypemi_reference_annees", "")),
                "sypemi_maxi_annees": _parse_float(row.get("sypemi_maxi_annees", "")),
                "fiche_cee": row.get("fiche_cee", "").strip() or None,
            }

            er = existing.get(id_ligne)
            if er is None:
                db.add(EquipmentReference(id_ligne=id_ligne, **data))
                created_count += 1
            else:
                changed = False
                for key, value in data.items():
                    if getattr(er, key) != value:
                        setattr(er, key, value)
                        changed = True
                if changed:
                    updated_count += 1

        db.commit()

    return len(rows), created_count, updated_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Import référentiel équipements depuis CSV")
    parser.add_argument("csv_path", help="Chemin vers le fichier CSV")
    parser.add_argument("--truncate", action="store_true", help="Vider la table avant import")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"Fichier introuvable: {csv_path}", file=sys.stderr)
        return 1

    try:
        total, created, updated = import_equipment_references(csv_path, args.truncate)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Lignes CSV: {total} | créées: {created} | mises à jour: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
