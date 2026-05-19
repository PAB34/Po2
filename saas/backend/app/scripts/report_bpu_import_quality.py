"""Report BPU import quality from database contents.

Usage, inside the backend container:
    python -m app.scripts.report_bpu_import_quality
    python -m app.scripts.report_bpu_import_quality --min-components 20
"""
from __future__ import annotations

import argparse

from sqlalchemy import func

from app.core.db import SessionLocal
from app.models.bpu import BpuDocument, BpuPriceComponent, BpuSegment, BpuTimePeriod


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapport qualite import BPU.")
    parser.add_argument(
        "--min-components",
        type=int,
        default=20,
        help="Seuil de prix unitaires par document attendu pour le statut OK metier.",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        status_rows = (
            session.query(BpuDocument.extraction_status, func.count(BpuDocument.id))
            .group_by(BpuDocument.extraction_status)
            .order_by(BpuDocument.extraction_status)
            .all()
        )

        total_docs = session.query(func.count(BpuDocument.id)).scalar() or 0
        total_segments = session.query(func.count(BpuSegment.id)).scalar() or 0
        total_periods = session.query(func.count(BpuTimePeriod.id)).scalar() or 0
        total_components = session.query(func.count(BpuPriceComponent.id)).scalar() or 0

        per_doc = (
            session.query(
                BpuDocument.id,
                BpuDocument.supplier,
                BpuDocument.valid_year,
                BpuDocument.lot_number,
                BpuDocument.market_subsequent,
                BpuDocument.amendment_number,
                BpuDocument.extraction_status,
                BpuDocument.extraction_method,
                BpuDocument.extraction_confidence,
                BpuDocument.pdf_filename,
                func.count(BpuPriceComponent.id).label("components_count"),
            )
            .outerjoin(BpuSegment, BpuSegment.document_id == BpuDocument.id)
            .outerjoin(BpuTimePeriod, BpuTimePeriod.segment_id == BpuSegment.id)
            .outerjoin(BpuPriceComponent, BpuPriceComponent.period_id == BpuTimePeriod.id)
            .group_by(BpuDocument.id)
            .order_by(
                BpuDocument.valid_year.desc(),
                BpuDocument.supplier.asc(),
                BpuDocument.lot_number.asc(),
                BpuDocument.pdf_filename.asc(),
            )
            .all()
        )

    print("\n=== QUALITE IMPORT BPU ===")
    print(f"Documents       : {total_docs}")
    print(f"Segments        : {total_segments}")
    print(f"Postes          : {total_periods}")
    print(f"Prix unitaires  : {total_components}")
    print()

    print("Par statut :")
    for status, count in status_rows:
        print(f"  {status:<12} {count}")
    print()

    print("Par document :")
    weak_docs = 0
    for row in per_doc:
        quality = "OK" if row.components_count >= args.min_components else "A_REVOIR"
        if quality != "OK":
            weak_docs += 1
        confidence = float(row.extraction_confidence or 0)
        ms = f"MS{row.market_subsequent}" if row.market_subsequent else "MS?"
        amendment = f" av{row.amendment_number}" if row.amendment_number else ""
        print(
            f"  [{quality:<8}] {row.valid_year} {row.supplier:<5} lot {row.lot_number} "
            f"{ms}{amendment:<5} "
            f"{row.components_count:>3} prix "
            f"conf={confidence:.2f} method={row.extraction_method or '-':<18} "
            f"{row.pdf_filename}"
        )

    print()
    print(f"Documents sous seuil ({args.min_components} prix) : {weak_docs}/{total_docs}")
    return 0 if weak_docs == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
