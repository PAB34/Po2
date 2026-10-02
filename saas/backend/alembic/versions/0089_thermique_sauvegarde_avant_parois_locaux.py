"""outil thermique : sauvegarde complète de chaque étude avant le métré par les côtés des locaux (D259)

Les versions ordinaires ne gardent que les pièces (D64). Avant que l'étape Parois passe aux côtés des locaux
(option C, D255), chaque étude reçoit une version qui garde **tout** son contenu (relevé corrigé compris), pour
pouvoir y revenir ou en reprendre une partie.

Revision ID: 0089
Revises: 0088
Create Date: 2026-10-02
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0089"
down_revision = "0088"
branch_labels = None
depends_on = None

MOTIF = "sauvegarde_avant_metre_par_cotes"


def upgrade() -> None:
    connexion = op.get_bind()
    etudes = connexion.execute(sa.text("SELECT id, content_json, local_states_json FROM thermique_etudes")).fetchall()
    for etude_id, contenu_json, etats_json in etudes:
        dernier = connexion.execute(
            sa.text("SELECT MAX(version_number) FROM thermique_etude_versions WHERE etude_id = :e"), {"e": etude_id}
        ).scalar()
        try:
            objets = json.loads(contenu_json or "{}").get("analyse", {}).get("objects", [])
        except ValueError:
            objets = []
        pieces = [objet for objet in objets if isinstance(objet, dict) and objet.get("category") == "piece"]
        connexion.execute(
            sa.text(
                "INSERT INTO thermique_etude_versions "
                "(etude_id, version_number, reason, content_json, pieces_json, local_states_json) "
                "VALUES (:e, :n, :r, :c, :p, :s)"
            ),
            {
                "e": etude_id,
                "n": int(dernier or 0) + 1,
                "r": MOTIF,
                "c": contenu_json,
                "p": json.dumps(pieces, ensure_ascii=False, separators=(",", ":")),
                "s": etats_json or "{}",
            },
        )


def downgrade() -> None:
    op.execute(sa.text(f"DELETE FROM thermique_etude_versions WHERE reason = '{MOTIF}'"))
