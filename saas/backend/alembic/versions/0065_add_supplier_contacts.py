"""add supplier_contacts (réclamations factures)

Revision ID: 0065
Revises: 0064
Create Date: 2026-06-29

Un contact éditable par (ville, fournisseur) pour pré-remplir les brouillons de
réclamation depuis la page Factures & décisions.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("supplier", sa.String(length=80), nullable=False),
        sa.Column("contact_name", sa.String(length=160), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("role", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "supplier", name="uq_supplier_contact_city_supplier"),
    )
    op.create_index("ix_supplier_contacts_city_id", "supplier_contacts", ["city_id"])
    op.create_index("ix_supplier_contacts_supplier", "supplier_contacts", ["supplier"])


def downgrade() -> None:
    op.drop_table("supplier_contacts")
