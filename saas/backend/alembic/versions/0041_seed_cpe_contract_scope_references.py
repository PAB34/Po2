"""seed editable CPE DALKIA contract scope references

Revision ID: 0041_seed_cpe_contract_scope_references
Revises: 0040
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op


revision = "0041_seed_cpe_contract_scope_references"
down_revision = "0040"
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
            active,
            notes
        )
        SELECT
            cities.id,
            data.contract_code,
            data.contract_label,
            'cpe_contract_scope',
            2026,
            'SCOPE',
            data.billed_item,
            true,
            'Perimetre contrat CPE Ville editable ; utilise par les imports, filtres et controles DALKIA.'
        FROM cities
        CROSS JOIN (
            VALUES
                ('C00190116O', 'SETE (34) - BATIMENTS COMMUNAUX LOT 1', 'CPE_VILLE_LOT_1'),
                ('C00190155J', 'SETE (34) - BATIMENTS COMMUNAUX LOT 2', 'CPE_VILLE_LOT_2')
        ) AS data(contract_code, contract_label, billed_item)
        WHERE cities.code_commune = '34301'
           OR upper(cities.nom_commune) IN ('SETE', 'SETE')
        ON CONFLICT ON CONSTRAINT uq_cpe_contract_reference_key DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM cpe_contract_references
        WHERE reference_kind = 'cpe_contract_scope'
          AND year = 2026
          AND market = 'SCOPE'
          AND billed_item IN ('CPE_VILLE_LOT_1', 'CPE_VILLE_LOT_2')
          AND notes = 'Perimetre contrat CPE Ville editable ; utilise par les imports, filtres et controles DALKIA.'
        """
    )
