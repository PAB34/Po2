"""add address columns to locals

Le fichier d'inventaire patrimonial porte une adresse ET une parcelle sur CHAQUE ligne,
y compris les lignes de type LOCAL. Or l'import ne conservait que le nom, le niveau et
le statut d'occupation : l'adresse etait perdue, et la parcelle finissait en texte libre
dans le champ `commentaire` ('Parcelle: ...').

Consequence pour l'aller-retour ASTECH : un CODE_BIEN qui designe un local se voyait
attribuer l'adresse du batiment parent, alors que le fichier source connaissait sa
propre adresse (une entree ou un numero de voirie peut differer de celui du batiment).

Ces colonnes reprennent le sous-ensemble utile de `buildings`, afin que l'heritage
puisse preferer l'adresse propre du local quand elle existe, et retomber sur celle du
batiment porteur sinon.

Revision ID: 0074
Revises: 0073
Create Date: 2026-08-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0074"
down_revision = "0073"
branch_labels = None
depends_on = None


_COLUMNS = (
    ("adresse_reconstituee", sa.String(length=255)),
    ("code_postal", sa.String(length=10)),
    ("nom_commune", sa.String(length=255)),
    ("latitude", sa.Float()),
    ("longitude", sa.Float()),
    ("dgfip_reference_norm", sa.String(length=32)),
)


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column("locals", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("locals", name)
