"""add contract code to cpe accounting nature rules

Revision ID: 0027
Revises: 0026
Create Date: 2026-05-28
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cpe_accounting_nature_rules", sa.Column("contract_code", sa.String(length=80), nullable=True))
    op.create_index(
        "ix_cpe_accounting_nature_rules_contract_code",
        "cpe_accounting_nature_rules",
        ["contract_code"],
        unique=False,
    )
    op.drop_constraint("uq_cpe_accounting_rule_key", "cpe_accounting_nature_rules", type_="unique")
    op.create_unique_constraint(
        "uq_cpe_accounting_rule_contract_key",
        "cpe_accounting_nature_rules",
        ["city_id", "contract_code", "market", "service_sold", "billed_item", "frequency"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_cpe_accounting_rule_contract_key", "cpe_accounting_nature_rules", type_="unique")
    op.create_unique_constraint(
        "uq_cpe_accounting_rule_key",
        "cpe_accounting_nature_rules",
        ["city_id", "market", "service_sold", "billed_item", "frequency"],
    )
    op.drop_index("ix_cpe_accounting_nature_rules_contract_code", table_name="cpe_accounting_nature_rules")
    op.drop_column("cpe_accounting_nature_rules", "contract_code")
