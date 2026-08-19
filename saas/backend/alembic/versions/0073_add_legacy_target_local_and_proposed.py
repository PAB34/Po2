"""add local target and 'propose' status to patrimoine_legacy_assets

Un CODE_BIEN ASTECH designe souvent un LOCAL (logement de fonction, salle, WC publics),
pas le batiment entier. La cible d'un rattachement peut donc etre un batiment OU un
local. Le SITE est explicitement exclu (decision Q15/Q16) : il n'a ni coordonnees ni
cadastre, et le referentiel ASTECH decrit du bati. Les sites restent en revanche dans la
plateforme, ils portent la hierarchie Site > Batiment > Local.

`building_id` est conserve comme **batiment porteur resolu** : pour une cible 'local',
c'est le batiment parent. C'est lui qui alimente l'adresse, le cadastre et la carte —
seuls les batiments portent ces informations (verifie en prod : les 625 locaux n'ont ni
adresse ni position).

Nouveau statut 'propose' : rattache par le moteur, **a confirmer**. 'lie' devient le
statut valide par un humain. Les rattachements automatiques deja en base n'ont jamais
ete confirmes par personne : ils basculent en 'propose'.

Revision ID: 0073
Revises: 0072
Create Date: 2026-08-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patrimoine_legacy_assets",
        sa.Column("local_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "patrimoine_legacy_assets",
        sa.Column("target_type", sa.String(length=20), nullable=False, server_default="building"),
    )
    op.create_foreign_key(
        "fk_legacy_asset_local",
        "patrimoine_legacy_assets",
        "locals",
        ["local_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_patrimoine_legacy_assets_local_id", "patrimoine_legacy_assets", ["local_id"])

    # Les rattachements automatiques n'ont jamais ete valides : ils passent
    # « a confirmer ». Les rattachements manuels restent valides.
    op.execute(
        "UPDATE patrimoine_legacy_assets SET status = 'propose' "
        "WHERE status = 'lie' AND link_origin = 'auto'"
    )


def downgrade() -> None:
    op.execute("UPDATE patrimoine_legacy_assets SET status = 'lie' WHERE status = 'propose'")
    op.drop_index("ix_patrimoine_legacy_assets_local_id", table_name="patrimoine_legacy_assets")
    op.drop_constraint("fk_legacy_asset_local", "patrimoine_legacy_assets", type_="foreignkey")
    op.drop_column("patrimoine_legacy_assets", "target_type")
    op.drop_column("patrimoine_legacy_assets", "local_id")
