"""Seed des sites CPE DALKIA avec les cibles NB contractuelles.

Source : Annexe 5.1 (gaz) et Annexe 5.2 (électricité) de l'Acte d'Engagement
offre finale DALKIA — Lot 1 Bâtiments communaux Ville de Sète.
DJU de référence : 1 426 DJU (base 18°C, station Montpellier, 1981-2010, oct→mai).

Usage :
    python -m app.scripts.seed_cpe_sites
    python -m app.scripts.seed_cpe_sites --city-id 1
    python -m app.scripts.seed_cpe_sites --dry-run
"""
from __future__ import annotations

import argparse
import sys

# fmt: off
# Données extraites de l'Annexe 5.1 et 5.2 de l'Acte d'Engagement DALKIA
# (code_site, nom_site, categorie, nb_mwh_pci, ecs_ref_m3_an, q_ecs_mwh_pci_per_m3, cible_elec_mwh)
# q_ecs = None si non défini dans le bordereau (à compléter ultérieurement)
CPE_SITES_DATA: list[tuple] = [
    # ── ENS — Enseignement ────────────────────────────────────────────────────
    ("VDS-ENS 01",   "Maternelle AGNÈS VARDA",                            "ENS",  0.0,   0.0,  None,  15.8),
    ("VDS-ENS 02",   "Élémentaire FERDINAND BUISSON + Rest. scol.",        "ENS",133.1,  42.9,  None,  33.5),
    ("VDS-ENS 03",   "Maternelle CONDORCET",                              "ENS", 32.8,  10.6,  None,  14.2),
    ("VDS-ENS 04",   "Maternelle EUGÉNIE COTTON",                         "ENS", 59.3,  19.1,  None,  13.3),
    ("VDS-ENS 05.01","Maternelle GASTON BABY",                            "ENS", 29.2,   9.4,  None,  10.2),
    ("VDS-ENS 05.02","Maternelle GASTON BABY — Apt. syndicat",            "ENS",  0.0,   0.0,  None,   0.3),
    ("VDS-ENS 05.03","Maternelle GASTON BABY — Centre médico-scolaire",   "ENS", 15.4,   5.0,  None,   1.0),
    ("VDS-ENS 05.04","Maternelle GASTON BABY — GAÏA 34",                  "ENS",  6.2,   2.0,  None,   2.6),
    ("VDS-ENS 05.05","Maternelle GASTON BABY — Restaurant scolaire",      "ENS", 39.8,  12.8,  None,  14.4),
    ("VDS-ENS 06",   "Maternelle HÉLÈNE BOUCHER",                         "ENS", 33.1,  10.7,  None,   9.1),
    ("VDS-ENS 07",   "Maternelle LOUIS BLANC",                            "ENS", 25.1,   8.1,  None,   6.7),
    ("VDS-ENS 08",   "Maternelle LOUIS PASTEUR",                          "ENS", 66.5,  21.4,  None,  14.9),
    ("VDS-ENS 09",   "Maternelle LOUISE MICHEL",                          "ENS", 25.5,   8.2,  None,  25.6),
    ("VDS-ENS 10",   "Élémentaire ARAGO / Maternelle MICHELET",           "ENS",128.5,  41.4,  None,  53.0),
    ("VDS-ENS 11",   "Élémentaire GEORGES BRASSENS",                      "ENS", 58.1,  18.7,  None,  19.8),
    ("VDS-ENS 12.01","Élémentaire JEAN MACÉ",                             "ENS", 67.8,  21.8,  None,  23.9),
    ("VDS-ENS 12.02","Élémentaire JEAN MACÉ — Restaurant scolaire",       "ENS",  2.8,   0.9,  None,   7.4),
    ("VDS-ENS 12.03","Bureaux SLIM (Jean Macé)",                          "ENS",  2.5,   0.8,  None,  43.8),
    ("VDS-ENS 13",   "Élémentaire LA RENAISSANCE + Rest. scol.",           "ENS",133.5,  47.6,   1.0,  35.9),
    ("VDS-ENS 14.01","Élémentaire LAKANAL",                               "ENS", 70.1,  25.7,  None,  14.4),
    ("VDS-ENS 14.02","Élémentaire LAKANAL — RASED",                       "ENS", 14.7,   4.7,  None,   0.0),
    ("VDS-ENS 15",   "Élémentaire PAUL BERT + Rest. scol.",                "ENS", 69.1,  30.8,   3.3,  18.2),
    ("VDS-ENS 16",   "Groupe scolaire ANATOLE FRANCE",                    "ENS", 33.4,  10.8,  None,  26.0),
    ("VDS-ENS 17.01","GS Élémentaire PAUL LANGEVIN (NORD)",               "ENS", 25.4,  13.0,  None,   0.0),
    ("VDS-ENS 17.02","GS Maternelle PAUL LANGEVIN + Rest. scol.",         "ENS", 57.9,  20.5,  None,  13.8),
    ("VDS-ENS 17.03","GS Élémentaire PAUL LANGEVIN (SUD)",                "ENS", 27.3,  10.3,  None,  14.4),
    ("VDS-ENS 17.04","GS Restaurant scol. PAUL LANGEVIN",                 "ENS", 34.2,  12.8,   0.9,  17.3),
    ("VDS-ENS 17.05","GS Accueil loisirs périscolaires LANGEVIN",         "ENS", 20.2,   6.5,  None,  23.0),
    ("VDS-ENS 18",   "C.F.A. NICOLAS ALBANO",                             "ENS",125.8,  50.1,   2.7, 206.9),
    ("VDS-ENS 19",   "Centre de loisirs LE VALLON",                       "ENS", 34.2,  13.5,  None,  10.0),
    # ── SPORT — Équipements sportifs ──────────────────────────────────────────
    ("VDS-SPORT 01",    "Complexe sportif ALFRED NAKACHE",                 "SPORT", 90.4, 36.6, None, 109.4),
    ("VDS-SPORT 02.01", "LE BARROU — Halle MAURICE AUGUSTE VIE",          "SPORT", 20.3,  6.5, None,  15.1),
    ("VDS-SPORT 02.02", "LE BARROU — Halle LOUIS MARTY",                  "SPORT",129.7, 41.8, None,  79.7),
    ("VDS-SPORT 02.03", "LE BARROU — TENNIS CLUB",                        "SPORT",  0.0,  0.0, None,   0.0),
    ("VDS-SPORT 02.04", "LE BARROU — SPORTS ÉMERGENTS",                   "SPORT", 96.4, 30.8, None,  41.2),
    ("VDS-SPORT 03",    "Gymnase du LIDO",                                 "SPORT",110.1, 35.2, None,  89.0),
    ("VDS-SPORT 04",    "Gymnase PAUL DI STEFANO",                        "SPORT", 89.3, 29.7, None,  54.6),
    ("VDS-SPORT 05",    "Gymnase VINCENT FERRARI",                        "SPORT", 19.8,  6.9, None,  44.6),
    # ── BAM — Bâtiments administratifs et techniques ──────────────────────────
    ("VDS-BAM 01",  "ARCHIVES MUNICIPALES (médiathèque)",                 "BAM",  0.0,  0.0, None,  8.6),
    ("VDS-BAM 02",  "Ateliers EMOP, Voirie, Peinture, Plomberie, etc.",   "BAM", 70.9,  0.0, None,  0.0),
    ("VDS-BAM 03",  "Ateliers MÉCANIQUE",                                 "BAM", 79.6,  0.0, None,  0.0),
    ("VDS-BAM 04",  "Ateliers ÉLECTRICITÉ",                               "BAM", 62.3,  0.0, None,  0.0),
    ("VDS-BAM 05",  "Atelier GARAGE",                                     "BAM",  0.0,  0.0, None,237.3),
    ("VDS-BAM 06",  "Ateliers MENUISERIE",                                "BAM",  0.0,  0.0, None,  0.0),
    ("VDS-BAM 07",  "Atelier SERRURERIE",                                 "BAM",  0.0,  0.0, None,  0.0),
    ("VDS-BAM 08",  "CTM LOUIS CATANZANO",                                "BAM", 11.6,  0.0, None,  None),
    ("VDS-BAM 09",  "Complexe funéraire RAYMOND FÉLICES (crématorium)",   "BAM", 32.8,  0.0, None,  None),
    ("VDS-BAM 10",  "CSU — PÔLE SÉCURITÉ",                               "BAM",  0.0,  0.0, None,  None),
    ("VDS-BAM 11",  "Direction des SPORTS",                               "BAM",  0.0,  0.0, None,  None),
    ("VDS-BAM 12",  "HÔTEL DE VILLE",                                     "BAM",  0.7,  0.0, None,  None),
    ("VDS-BAM 13",  "LES HALLES",                                         "BAM",  0.0,  0.0, None,  None),
    ("VDS-BAM 14",  "POLICE MUNICIPALE et CSU",                           "BAM",  0.0,  0.0, None,  None),
    ("VDS-BAM 15",  "Salle polyvalente GEORGES BRASSENS",                 "BAM",  0.0,  0.0, None,  None),
    ("VDS-BAM 16",  "SERRES MUNICIPALES",                                 "BAM", 51.4, 91.0, None,  None),
    # ── CULT — Culture ────────────────────────────────────────────────────────
    ("VDS-CULT 01", "École des BEAUX-ARTS",                               "CULT", 54.3,  0.0, None,  None),
]
# fmt: on


def seed(city_id: int | None = None, dry_run: bool = False) -> None:
    from app.core.db import SessionLocal
    from app.services.cpe import create_site, get_site_by_code
    from app.schemas.cpe import CpeSiteCreate

    db = SessionLocal()
    try:
        created = 0
        skipped = 0
        for row in CPE_SITES_DATA:
            code, nom, cat, nb, ecs, qecs, elec = row
            existing = get_site_by_code(db, code)
            if existing:
                skipped += 1
                continue
            if dry_run:
                print(f"[DRY-RUN] Créerait : {code} — {nom} (NB={nb} MWhPCI)")
                created += 1
                continue
            create_site(
                db,
                CpeSiteCreate(
                    city_id=city_id,
                    code_site=code,
                    nom_site=nom,
                    categorie=cat,
                    nb_mwh_pci=nb,
                    ecs_ref_m3_an=ecs,
                    q_ecs_mwh_pci_per_m3=qecs,
                    cible_elec_mwh=elec,
                    dju_reference=1426.0,
                    actif=True,
                    notes=None,
                ),
            )
            created += 1
            print(f"  ✓ {code} — {nom}")

        print(f"\nTerminé : {created} créés, {skipped} déjà existants.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed des sites CPE DALKIA")
    parser.add_argument("--city-id", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    seed(city_id=args.city_id, dry_run=args.dry_run)
