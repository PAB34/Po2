"""add resolved address columns to patrimoine_legacy_assets

Quand l'utilisateur pose lui-meme un bien ASTECH sur la carte, on geocode le point a
l'envers et on conserve l'adresse trouvee. Elle est stockee a cote de l'adresse
d'origine (`source_*`), jamais a sa place : le fichier ASTECH doit rester intact tant
que l'utilisateur n'a pas valide, et le reexport a besoin des deux pour tracer
l'ancienne et la nouvelle valeur.

Les champs sont separes (numero / voie / code postal / commune / INSEE) car c'est sous
cette forme qu'ils devront etre reecrits dans les colonnes NORUE, LIBELVOIE, CODPOST,
VILLE et COMMUNE du referentiel d'origine.

Revision ID: 0071
Revises: 0070
Create Date: 2026-08-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None


_COLUMNS = (
    ("resolved_housenumber", sa.String(length=20)),
    ("resolved_street", sa.String(length=255)),
    ("resolved_postcode", sa.String(length=10)),
    ("resolved_city", sa.String(length=120)),
    ("resolved_citycode", sa.String(length=10)),
    ("resolved_label", sa.String(length=255)),
    # 'ign_reverse' (point pose a la main) ou 'building' (herite du batiment Po2).
    ("resolved_source", sa.String(length=20)),
)


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column("patrimoine_legacy_assets", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("patrimoine_legacy_assets", name)
