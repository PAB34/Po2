"""Import the Herault Energie gas Lot 7 BPU into normalized BPU tables.

Usage from the backend container:

    python -m app.scripts.import_bpu_gas_lot7 \
        --xlsx "/workspace/saas/energie/HERAULT ENERGIE/BPU_2026_Lots_1_2_et_7.xlsx"
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.core.db import SessionLocal
from app.models.bpu import (
    BpuDocument,
    BpuPriceComponent,
    BpuSegment,
    BpuTimePeriod,
    COMPONENT_CEE,
    COMPONENT_CEE_PRECARITE,
    COMPONENT_CPB,
    COMPONENT_FOURNITURE,
    COMPONENT_GO,
    EXTRACTION_MANUAL,
    SEGMENT_TYPE_USAGE,
)


DEFAULT_XLSX = Path("/workspace/saas/energie/HERAULT ENERGIE/BPU_2026_Lots_1_2_et_7.xlsx")
LOT7_SHEET = "Lot 7 - Gaz"
SUPPLIER = "TOTALENERGIES"


@dataclass(frozen=True)
class GasLot7Profile:
    year: int
    profile: str
    consumption_level: str
    fourniture: float
    cee_classique: float
    cee_precarite: float
    cpb: float
    go: float
    observation: str | None


def _clean_header(value: object) -> str:
    return " ".join(str(value).replace("\n", " ").split()).lower()


def _column(frame: pd.DataFrame, label_start: str) -> str:
    for column in frame.columns:
        if _clean_header(column).startswith(label_start):
            return str(column)
    raise ValueError(f"Colonne lot 7 introuvable: {label_start}")


def _profile_text(value: object) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        raise ValueError("Valeur de profil gaz vide dans le BPU lot 7.")
    return text


def parse_gas_lot7_frame(frame: pd.DataFrame) -> list[GasLot7Profile]:
    """Parse gas profile rows from the real Lot 7 workbook layout."""
    year_col = _column(frame, "période")
    profile_col = _column(frame, "profil gaz")
    level_col = _column(frame, "niveau de consommation")
    fourniture_col = _column(frame, "pu fourniture")
    cee_col = _column(frame, "pu cee classique")
    cee_precarite_col = _column(frame, "pu cee précarité")
    cpb_col = _column(frame, "pu cpb")
    go_col = _column(frame, "pu go")
    observation_col = _column(frame, "observation")

    profiles: list[GasLot7Profile] = []
    for _, row in frame.iterrows():
        if pd.isna(row.get(profile_col)):
            continue
        observation = None if pd.isna(row.get(observation_col)) else str(row[observation_col]).strip()
        profiles.append(
            GasLot7Profile(
                year=int(row[year_col]),
                profile=_profile_text(row[profile_col]).upper(),
                consumption_level=_profile_text(row[level_col]),
                fourniture=float(row[fourniture_col]),
                cee_classique=float(row[cee_col]),
                cee_precarite=float(row[cee_precarite_col]),
                cpb=float(row[cpb_col]),
                go=float(row[go_col]),
                observation=observation or None,
            )
        )

    if not profiles:
        raise ValueError("Aucun profil gaz exploitable trouve dans le BPU lot 7.")
    return profiles


def import_gas_lot7(xlsx_path: Path) -> dict[str, int]:
    if not xlsx_path.exists():
        raise FileNotFoundError(f"xlsx introuvable: {xlsx_path}")

    profiles = parse_gas_lot7_frame(pd.read_excel(xlsx_path, sheet_name=LOT7_SHEET))
    valid_years = {profile.year for profile in profiles}
    if len(valid_years) != 1:
        raise ValueError(f"Le BPU lot 7 doit porter une seule annee: {sorted(valid_years)}")
    year = valid_years.pop()

    with SessionLocal() as session:
        document = (
            session.query(BpuDocument)
            .filter(
                BpuDocument.supplier == SUPPLIER,
                BpuDocument.valid_year == year,
                BpuDocument.lot_number == 7,
                BpuDocument.market_subsequent.is_(None),
                BpuDocument.amendment_number.is_(None),
            )
            .one_or_none()
        )
        if document is not None:
            session.delete(document)
            session.flush()

        observations = sorted({profile.observation for profile in profiles if profile.observation})
        document = BpuDocument(
            supplier=SUPPLIER,
            valid_year=year,
            lot_number=7,
            amendment_label="BPU Herault Energie Lot 7 gaz",
            pdf_filename=xlsx_path.name,
            pdf_relative_path="HERAULT ENERGIE/BPU_2026_Lots_1_2_et_7.xlsx",
            extraction_status=EXTRACTION_MANUAL,
            extraction_method="xlsx_lot7",
            extraction_confidence=1.0,
            extraction_notes=" | ".join(observations) or None,
        )
        session.add(document)
        session.flush()

        components_count = 0
        for profile in profiles:
            segment = BpuSegment(
                document_id=document.id,
                segment_type=SEGMENT_TYPE_USAGE,
                segment_code=profile.profile,
                segment_label=profile.consumption_level,
                usage_label="Gaz",
                notes=profile.observation,
            )
            session.add(segment)
            session.flush()

            period = BpuTimePeriod(
                segment_id=segment.id,
                period_code="BASE",
                period_label="Profil gaz annuel",
            )
            session.add(period)
            session.flush()

            components = (
                (COMPONENT_FOURNITURE, "PU fourniture ferme", profile.fourniture),
                (COMPONENT_CEE, "PU CEE classique", profile.cee_classique),
                (COMPONENT_CEE_PRECARITE, "PU CEE precarite", profile.cee_precarite),
                (COMPONENT_CPB, "PU CPB", profile.cpb),
                (COMPONENT_GO, "PU GO", profile.go),
            )
            for component_type, label, value in components:
                session.add(
                    BpuPriceComponent(
                        period_id=period.id,
                        component_type=component_type,
                        component_label=label,
                        price_value=value,
                        price_unit="EUR HT/MWh",
                        price_value_eur_per_mwh=value,
                        is_negative=value < 0,
                        notes=profile.observation,
                    )
                )
                components_count += 1

        session.commit()

    return {
        "documents": 1,
        "segments": len(profiles),
        "periods": len(profiles),
        "components": components_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import BPU gaz Herault Energie Lot 7")
    parser.add_argument("--xlsx", default=str(DEFAULT_XLSX), help=f"Chemin du BPU xlsx (defaut: {DEFAULT_XLSX})")
    args = parser.parse_args()

    counters = import_gas_lot7(Path(args.xlsx))
    for key, value in counters.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
