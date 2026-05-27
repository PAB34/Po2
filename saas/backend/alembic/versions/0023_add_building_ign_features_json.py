"""add building ign features json

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-26 14:00:00.000000

Permet de stocker plusieurs batiments IGN BDTOPO rattaches a un meme
batiment patrimoine. Necessaire pour les ensembles batis qui s'etalent
sur plusieurs polygones IGN (annexes, batiments en L, complexes scolaires
avec preau+cour+batiment principal...).

Le 1er feature reste 'principal' (stocke dans ign_id / ign_name / ign_label /
ign_attributes_json pour retrocompat). Le tableau complet est stocke en
JSON dans ign_features_json.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("buildings", sa.Column("ign_features_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("buildings", "ign_features_json")
