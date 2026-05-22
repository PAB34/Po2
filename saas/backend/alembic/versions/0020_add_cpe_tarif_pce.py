"""Add tarif and pce to cpe_sites, tarif to cpe_prix_gaz.

OS N°3 (Ordre de Service n°3) — prix molécule gaz fixé sur 5 ans (2026-2030)
avec 3 typologies tarifaires : T1 (puissance souscrite ≥ 450 kWh/h),
T2 (intermédiaire), T3 (grande consommation).

Revision: 0020
Revises: 0019_add_cpe_tables
Create Date: 2026-05-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019_add_cpe_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- cpe_sites : tarif (T1/T2/T3) et PCE (identifiant compteur GRDF) ------
    op.add_column("cpe_sites", sa.Column("tarif", sa.String(5), nullable=True))
    op.add_column("cpe_sites", sa.Column("pce", sa.String(50), nullable=True))

    # -- cpe_prix_gaz : ajout tarif + mise à jour de la contrainte unique ------
    op.add_column("cpe_prix_gaz", sa.Column("tarif", sa.String(5), nullable=True))

    # Supprime l'ancienne contrainte unique (annee seul)
    op.drop_constraint("uq_cpe_prix_gaz_annee", "cpe_prix_gaz", type_="unique")

    # Nouvelle contrainte unique (annee, tarif) — un prix par type de tarif et par exercice
    op.create_unique_constraint(
        "uq_cpe_prix_gaz_annee_tarif",
        "cpe_prix_gaz",
        ["annee", "tarif"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_cpe_prix_gaz_annee_tarif", "cpe_prix_gaz", type_="unique")
    op.create_unique_constraint("uq_cpe_prix_gaz_annee", "cpe_prix_gaz", ["annee"])
    op.drop_column("cpe_prix_gaz", "tarif")
    op.drop_column("cpe_sites", "pce")
    op.drop_column("cpe_sites", "tarif")
