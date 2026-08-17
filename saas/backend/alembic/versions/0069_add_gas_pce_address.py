"""add meter address columns to gas_pces (GRDF situation_compteur)

GRDF ADICT ne restitue aucun « nom de site » (cf. swagger v1.9 : `liste_acces_out`
n'expose que titulaire / code postal). La seule identification géographique
disponible est l'adresse du compteur, renvoyée par
`GET /pce/{id}/donnees_techniques` → `donnees_techniques.situation_compteur`.

Revision ID: 0069
Revises: 0068
Create Date: 2026-08-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


_COLUMNS = (
    ("numero_rue", sa.String(length=20)),
    ("nom_rue", sa.String(length=255)),
    ("complement_adresse", sa.String(length=255)),
    ("commune", sa.String(length=120)),
)


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column("gas_pces", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("gas_pces", name)
