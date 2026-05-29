"""seed initial DALKIA CPE contract references

Revision ID: 0029
Revises: 0028
Create Date: 2026-05-29
"""
from __future__ import annotations

from alembic import op


revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO cpe_contract_references (
            city_id,
            contract_code,
            contract_label,
            reference_kind,
            year,
            market,
            billed_item,
            annual_amount_ht,
            expected_amount_ht,
            installment_count,
            expected_period_months,
            included_billed_items,
            formula,
            tolerance_pct,
            tolerance_eur,
            active,
            notes
        )
        SELECT
            cities.id,
            'C00190116O',
            'SETE (34) - BATIMENTS COMMUNAUX LOT 1',
            'p1_gaz_acompte',
            2026,
            'P1',
            'P1_GAZ_LOT1',
            341293.06,
            NULL,
            4,
            '3,6,9',
            '["P1","ABT","CTA","CPB","LOCATION","STOCKAGE","TERME FIXE"]',
            'Acompte P1 gaz = 1/4 du P1 annuel DPGF revise',
            0.01,
            100.0,
            true,
            'Reference initiale issue de la DPGF LOT 1 2026 ; editable depuis le module CPE.'
        FROM cities
        WHERE code_commune = '34301'
           OR upper(nom_commune) IN ('SETE', 'SÈTE')
        ORDER BY cities.id
        LIMIT 1
        ON CONFLICT ON CONSTRAINT uq_cpe_contract_reference_key DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM cpe_contract_references
        WHERE contract_code = 'C00190116O'
          AND reference_kind = 'p1_gaz_acompte'
          AND year = 2026
          AND market = 'P1'
          AND billed_item = 'P1_GAZ_LOT1'
          AND notes = 'Reference initiale issue de la DPGF LOT 1 2026 ; editable depuis le module CPE.'
        """
    )
