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
    conn = op.get_bind()

    # -- cpe_sites : tarif (T1/T2/T3) et PCE (identifiant compteur GRDF) ------
    # ADD COLUMN IF NOT EXISTS — idempotent si migration déjà partiellement appliquée
    conn.execute(sa.text(
        "ALTER TABLE cpe_sites ADD COLUMN IF NOT EXISTS tarif VARCHAR(5)"
    ))
    conn.execute(sa.text(
        "ALTER TABLE cpe_sites ADD COLUMN IF NOT EXISTS pce VARCHAR(50)"
    ))

    # -- cpe_prix_gaz : ajout tarif + mise à jour de la contrainte unique ------
    conn.execute(sa.text(
        "ALTER TABLE cpe_prix_gaz ADD COLUMN IF NOT EXISTS tarif VARCHAR(5)"
    ))

    # Supprime l'ancienne contrainte unique (annee seul) — IF EXISTS pour robustesse
    conn.execute(sa.text(
        "ALTER TABLE cpe_prix_gaz DROP CONSTRAINT IF EXISTS uq_cpe_prix_gaz_annee"
    ))

    # Nouvelle contrainte unique (annee, tarif) — CREATE IF NOT EXISTS via index unique
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_cpe_prix_gaz_annee_tarif "
        "ON cpe_prix_gaz (annee, tarif)"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    # Supprime index/contrainte (créé comme index unique dans upgrade)
    conn.execute(sa.text("DROP INDEX IF EXISTS uq_cpe_prix_gaz_annee_tarif"))
    conn.execute(sa.text(
        "ALTER TABLE cpe_prix_gaz DROP CONSTRAINT IF EXISTS uq_cpe_prix_gaz_annee_tarif"
    ))
    # Restaure contrainte originale
    conn.execute(sa.text(
        "ALTER TABLE cpe_prix_gaz DROP CONSTRAINT IF EXISTS uq_cpe_prix_gaz_annee"
    ))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_cpe_prix_gaz_annee ON cpe_prix_gaz (annee)"
    ))
    conn.execute(sa.text("ALTER TABLE cpe_prix_gaz DROP COLUMN IF EXISTS tarif"))
    conn.execute(sa.text("ALTER TABLE cpe_sites DROP COLUMN IF EXISTS pce"))
    conn.execute(sa.text("ALTER TABLE cpe_sites DROP COLUMN IF EXISTS tarif"))
