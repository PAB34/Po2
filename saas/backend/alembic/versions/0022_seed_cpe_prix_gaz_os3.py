"""Data migration : prix gaz OS N°3 (prix fixe 5 ans 2026-2030).

Insère les prix unitaires T1/T2/T3 en €/MWhPCI pour les exercices 2026 à 2030.
Source : Ordre de Service n°3, signé le 15 janvier 2026, marché 24BT039.

Conversion PCS → PCI : ratio 1.1068 (GRDF zone Languedoc-Roussillon)
  T1 : 107.03 €/MWhPCS × 1.1068 = 118.5000 €/MWhPCI
  T2 :  74.17 €/MWhPCS × 1.1068 =  82.1313 €/MWhPCI
  T3 :  70.78 €/MWhPCS × 1.1068 =  78.3775 €/MWhPCI

Revision: 0022
Revises: 0021 (add_building_meter_links)
Create Date: 2026-05-22

Note : initialement créée comme 0021, renumérotée en 0022 après collision
avec 0021_add_building_meter_links (commit Codespaces parallèle qui prenait
le même numéro). Comme la migration est idempotente (ON CONFLICT DO NOTHING
sur (annee, tarif)), re-jouer si elle avait déjà tourné en base sous le
nom 0021 ne crée pas de doublons.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

PCS_PCI_RATIO = 1.1068

OS3_PRIX_PCS = {"T1": 107.03, "T2": 74.17, "T3": 70.78}

OS3_PRIX = {
    tarif: round(pcs * PCS_PCI_RATIO, 4)
    for tarif, pcs in OS3_PRIX_PCS.items()
}
# T1 → 118.5000, T2 → 82.1313, T3 → 78.3775

ANNEES = list(range(2026, 2031))  # 2026 à 2030 inclus


def upgrade() -> None:
    conn = op.get_bind()
    for annee in ANNEES:
        for tarif, pu_pci in OS3_PRIX.items():
            pcs = OS3_PRIX_PCS[tarif]
            notes = (
                f"OS N°3 (15/01/2026) — prix fixe 5 ans. "
                f"PCS={pcs:.2f} €/MWhPCS × {PCS_PCI_RATIO} = {pu_pci:.4f} €/MWhPCI"
            )
            conn.execute(
                sa.text(
                    """
                    INSERT INTO cpe_prix_gaz (annee, tarif, pu_eur_mwh_pci, source, notes,
                                              created_at, updated_at)
                    VALUES (:annee, :tarif, :pu, 'os3_fixe', :notes, now(), now())
                    ON CONFLICT (annee, tarif) DO NOTHING
                    """
                ),
                {"annee": annee, "tarif": tarif, "pu": pu_pci, "notes": notes},
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM cpe_prix_gaz WHERE source = 'os3_fixe' AND annee BETWEEN 2026 AND 2030"
        )
    )
