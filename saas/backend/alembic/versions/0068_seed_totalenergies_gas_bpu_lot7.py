"""seed TotalEnergies gas BPU lot 7 in normalized BPU tables

Revision ID: 0068
Revises: 0067
Create Date: 2026-07-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None


_SUPPLIER = "TOTALENERGIES"
_YEAR = 2026
_LOT = 7
_FILENAME = "BPU_2026_Lots_1_2_et_7.xlsx"
_PROFILES = {
    "T1": "Moins de 6 000 kWh/an",
    "T2": "Entre 6 000 et 300 000 kWh/an",
    "T3": "Entre 300 000 et 5 000 000 kWh/an",
    "T4": "Plus de 5 000 000 kWh/an",
}
_COMPONENTS = (
    ("fourniture", "PU fourniture ferme", 35.23),
    ("cee", "PU CEE classique", 3.89),
    ("cee_precarite", "PU CEE precarite", 3.06),
    ("cpb", "PU CPB", 0.41),
    ("go", "PU GO", 16.25),
)
_NOTES = "CEE provisoires janv.-fevr. 2026 ; revision/regularisation des mars 2026."


def _delete_existing(conn) -> None:
    doc_ids = [
        row[0]
        for row in conn.execute(
            sa.text(
                """
                SELECT id FROM bpu_documents
                WHERE supplier = :supplier
                  AND valid_year = :year
                  AND lot_number = :lot
                  AND market_subsequent IS NULL
                  AND amendment_number IS NULL
                """
            ),
            {"supplier": _SUPPLIER, "year": _YEAR, "lot": _LOT},
        ).fetchall()
    ]
    if not doc_ids:
        return
    params = {"doc_ids": doc_ids}
    doc_ids_param = sa.bindparam("doc_ids", expanding=True)
    conn.execute(
        sa.text(
            """
            DELETE FROM bpu_price_components
            WHERE period_id IN (
                SELECT p.id
                FROM bpu_time_periods p
                JOIN bpu_segments s ON s.id = p.segment_id
                WHERE s.document_id IN :doc_ids
            )
            """
        ).bindparams(doc_ids_param),
        params,
    )
    conn.execute(
        sa.text(
            "DELETE FROM bpu_time_periods WHERE segment_id IN (SELECT id FROM bpu_segments WHERE document_id IN :doc_ids)"
        ).bindparams(doc_ids_param),
        params,
    )
    conn.execute(sa.text("DELETE FROM bpu_fixed_charges WHERE document_id IN :doc_ids").bindparams(doc_ids_param), params)
    conn.execute(sa.text("DELETE FROM bpu_segments WHERE document_id IN :doc_ids").bindparams(doc_ids_param), params)
    conn.execute(sa.text("DELETE FROM bpu_documents WHERE id IN :doc_ids").bindparams(doc_ids_param), params)


def upgrade() -> None:
    conn = op.get_bind()
    _delete_existing(conn)

    document_id = conn.execute(
        sa.text(
            """
            INSERT INTO bpu_documents (
                supplier, valid_year, market_subsequent, lot_number, amendment_number,
                amendment_label, pdf_filename, pdf_relative_path, extraction_status,
                extraction_method, extraction_confidence, extraction_notes
            ) VALUES (
                :supplier, :year, NULL, :lot, NULL,
                'BPU Herault Energie Lot 7 gaz', :filename,
                'HERAULT ENERGIE/HISTORIQUE BPU/extraction_tarifs_BPU_herault.xlsx',
                'manual', 'manual_seed_gas_lot7', 1.0, :notes
            )
            RETURNING id
            """
        ),
        {"supplier": _SUPPLIER, "year": _YEAR, "lot": _LOT, "filename": _FILENAME, "notes": _NOTES},
    ).scalar_one()

    for profile, label in _PROFILES.items():
        segment_id = conn.execute(
            sa.text(
                """
                INSERT INTO bpu_segments (
                    document_id, segment_type, segment_code, segment_label, usage_label, notes
                ) VALUES (:document_id, 'usage', :profile, :label, 'Gaz', :notes)
                RETURNING id
                """
            ),
            {"document_id": document_id, "profile": profile, "label": label, "notes": _NOTES},
        ).scalar_one()
        period_id = conn.execute(
            sa.text(
                """
                INSERT INTO bpu_time_periods (segment_id, period_code, period_label)
                VALUES (:segment_id, 'BASE', 'Profil gaz annuel')
                RETURNING id
                """
            ),
            {"segment_id": segment_id},
        ).scalar_one()
        for component_type, component_label, value in _COMPONENTS:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO bpu_price_components (
                        period_id, component_type, component_label, price_value, price_unit,
                        price_value_eur_per_mwh, is_negative, notes
                    ) VALUES (
                        :period_id, :component_type, :component_label, :value, 'EUR HT/MWh',
                        :value, false, :notes
                    )
                    """
                ),
                {
                    "period_id": period_id,
                    "component_type": component_type,
                    "component_label": component_label,
                    "value": value,
                    "notes": _NOTES,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()
    _delete_existing(conn)
