"""Seed des prix unitaires gaz CPE — OS N°3 (prix fixe 5 ans).

Source : Ordre de Service n°3, signé le 15 janvier 2026.
Marché 24BT039 — Lot 1 Bâtiments communaux + CCAS, Ville de Sète.
Titulaire : DALKIA S.A.

Prix fixés pour la période du 01/01/2026 au 31/12/2030 :
    T1 : 107.03 €HT/MWhPCS (grande puissance souscrite ≥ 450 kW)
    T2 : 74.17 €HT/MWhPCS  (puissance intermédiaire)
    T3 : 70.78 €HT/MWhPCS  (grande consommation annuelle ≥ 5 GWh)

La formule d'intéressement CPE utilise des MWhPCI (pouvoir calorifique inférieur).
Conversion : Pu_PCI = Pu_PCS × PCS_PCI_RATIO (≈ 1.1068 pour gaz naturel Languedoc).

Usage :
    python -m app.scripts.seed_cpe_prix_gaz
    python -m app.scripts.seed_cpe_prix_gaz --dry-run
    python -m app.scripts.seed_cpe_prix_gaz --annees 2026 2027 2028
"""
from __future__ import annotations

import argparse

# Prix OS N°3 en €HT/MWhPCS (source : OS N°3 signé 15/01/2026)
OS3_PRIX_PCS: dict[str, float] = {
    "T1": 107.03,
    "T2": 74.17,
    "T3": 70.78,
}

# Période couverte par le prix fixe OS N°3
OS3_ANNEES = list(range(2026, 2031))  # 2026 à 2030 inclus

# Ratio PCS/PCI pour le gaz naturel distribué à Sète (zone GRDF Languedoc-Roussillon)
# Source : données de qualité du gaz GRDF — affinable via API GRDF ADICT
# Ce coefficient est stable à ±0.5% sur la zone ; l'affiner avec les bulletins GRDF
PCS_PCI_RATIO = 1.1068


def pu_pci(pu_pcs_value: float) -> float:
    """Convertit un prix €/MWhPCS en €/MWhPCI (arrondi à 4 décimales)."""
    return round(pu_pcs_value * PCS_PCI_RATIO, 4)


def seed(annees: list[int] | None = None, dry_run: bool = False) -> None:
    from app.core.db import SessionLocal
    from app.services.cpe import upsert_prix_gaz
    from app.schemas.cpe import CpePrixGazCreate

    cible_annees = annees if annees else OS3_ANNEES
    db = SessionLocal()
    try:
        for annee in cible_annees:
            for tarif, prix_pcs in OS3_PRIX_PCS.items():
                prix_pci = pu_pci(prix_pcs)
                notes_str = (
                    f"OS N°3 (15/01/2026) — prix fixe 5 ans. "
                    f"PCS={prix_pcs:.2f} €/MWhPCS × {PCS_PCI_RATIO} = {prix_pci:.4f} €/MWhPCI"
                )
                if dry_run:
                    print(
                        f"[DRY-RUN] {annee} tarif={tarif} "
                        f"Pu_PCS={prix_pcs:.2f} → Pu_PCI={prix_pci:.4f} €/MWhPCI"
                    )
                    continue

                upsert_prix_gaz(
                    db,
                    CpePrixGazCreate(
                        annee=annee,
                        tarif=tarif,
                        pu_eur_mwh_pci=prix_pci,
                        source="os3_fixe",
                        notes=notes_str,
                    ),
                )
                print(f"  ✓ {annee} {tarif} → {prix_pci:.4f} €/MWhPCI (PCS={prix_pcs:.2f})")

        if not dry_run:
            print(f"\nTerminé : {len(cible_annees) * 3} entrées upsertées (3 tarifs × {len(cible_annees)} ans).")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed des prix gaz OS N°3 (prix fixe 5 ans 2026-2030)"
    )
    parser.add_argument(
        "--annees",
        type=int,
        nargs="+",
        default=None,
        help="Exercices à initialiser (défaut : 2026-2030)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    seed(annees=args.annees, dry_run=args.dry_run)
