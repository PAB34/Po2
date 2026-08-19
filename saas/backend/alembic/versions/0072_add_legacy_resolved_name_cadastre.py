"""add resolved name and cadastre columns to patrimoine_legacy_assets

Quand un bien ASTECH est rattache a un batiment Po2, il doit reprendre TOUT ce que Po2
sait : le nom, l'adresse et la reference cadastrale. La 0071 ne couvrait que l'adresse.

Contrainte constatee en prod (2026-08-19) : les batiments Po2 ne stockent PAS l'adresse
decoupee (numero_voirie, nom_voie, section, numero_plan sont NULL sur les 183 lignes).
Tout est agrege dans `adresse_reconstituee` ('208 AV DU MARECHAL JUIN') et
`dgfip_reference_norm` ('34301000AK0149' = INSEE + prefixe + section + plan). Les valeurs
heritees sont donc reconstituees par analyse de ces deux chaines, dont le format est
regulier, puis stockees decoupees ici — c'est sous cette forme que le reexport devra les
ecrire dans NORUE, LIBELVOIE et REFCAD.

Revision ID: 0072
Revises: 0071
Create Date: 2026-08-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0072"
down_revision = "0071"
branch_labels = None
depends_on = None


_COLUMNS = (
    # Nom retenu (decision Q11 : le nom Po2/IGN gagne et sera reecrit dans ASTECH).
    ("resolved_name", sa.String(length=255)),
    ("resolved_section", sa.String(length=10)),
    ("resolved_numero_plan", sa.String(length=10)),
    # Reference telle qu'attendue par ASTECH : section + numero de plan sur 3 chiffres.
    ("resolved_refcad", sa.String(length=20)),
)


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column("patrimoine_legacy_assets", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("patrimoine_legacy_assets", name)
