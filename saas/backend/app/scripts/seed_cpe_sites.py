"""Seed des sites CPE DALKIA avec les cibles NB contractuelles.

Source : Annexe 5.1 (gaz) et Annexe 5.2 (électricité) de l'Acte d'Engagement
offre finale DALKIA — Lot 1 Bâtiments communaux Ville de Sète.
Complété par OS N°3 (Ordre de Service n°3, 15 janvier 2026) pour le tarif GRDF
et le PCE (identifiant compteur) de chaque site.

DJU de référence : 1 426 DJU (base 18°C, station Montpellier, 1981-2010).

Usage :
    python -m app.scripts.seed_cpe_sites
    python -m app.scripts.seed_cpe_sites --city-id 1
    python -m app.scripts.seed_cpe_sites --dry-run
"""
from __future__ import annotations

import argparse

# fmt: off
# Données extraites de l'Annexe 5.1 et 5.2 de l'Acte d'Engagement DALKIA
# + OS N°3 (tarif et PCE)
# Colonnes : (code_site, nom_site, categorie, nb_mwh_pci, ecs_ref_m3_an,
#              q_ecs_mwh_pci_per_m3, cible_elec_mwh, tarif, pce, notes)
# tarif : T1 | T2 | T3 | None (pas de contrat gaz propre)
# pce   : identifiant PCE GRDF | None

CPE_SITES_DATA: list[tuple] = [
    # ── ENS — Enseignement ────────────────────────────────────────────────────
    # ENS 01 : même PCE que ENS 02 (sous-comptage), NB=0
    ("VDS-ENS 01",   "Maternelle AGNÈS VARDA",                            "ENS",  0.0,   0.0,  None,  15.8, None, "24349204040145", "Sous-comptage ENS 02"),
    ("VDS-ENS 02",   "Élémentaire FERDINAND BUISSON + Rest. scol.",        "ENS",133.1,  42.9,  None,  33.5, "T2", "24349204040145", None),
    ("VDS-ENS 03",   "Maternelle CONDORCET",                              "ENS", 32.8,  10.6,  None,  14.2, "T2", "24352821935922", None),
    ("VDS-ENS 04",   "Maternelle EUGÉNIE COTTON",                         "ENS", 59.3,  19.1,  None,  13.3, "T2", "24330535343508", None),
    ("VDS-ENS 05.01","Maternelle GASTON BABY",                            "ENS", 29.2,   9.4,  None,  10.2, "T2", "24349927579988", None),
    ("VDS-ENS 05.02","Maternelle GASTON BABY — Apt. syndicat",            "ENS",  0.0,   0.0,  None,   0.3, "T2", "24348480333464", None),
    ("VDS-ENS 05.03","Maternelle GASTON BABY — Centre médico-scolaire",   "ENS", 15.4,   5.0,  None,   1.0, "T2", "24348769769030", None),
    ("VDS-ENS 05.04","Maternelle GASTON BABY — GAÏA 34",                  "ENS",  6.2,   2.0,  None,   2.6, "T2", "24310564387702", None),
    ("VDS-ENS 05.05","Maternelle GASTON BABY — Restaurant scolaire",      "ENS", 39.8,  12.8,  None,  14.4, "T2", None,             "PCE non renseigné dans OS N°3"),
    ("VDS-ENS 06",   "Maternelle HÉLÈNE BOUCHER",                         "ENS", 33.1,  10.7,  None,   9.1, "T2", "2453545574182",  "PCE à vérifier (13 chiffres)"),
    ("VDS-ENS 07",   "Maternelle LOUIS BLANC",                            "ENS", 25.1,   8.1,  None,   6.7, "T2", "24331982621909", None),
    ("VDS-ENS 08",   "Maternelle LOUIS PASTEUR",                          "ENS", 66.5,  21.4,  None,  14.9, "T2", "24363386335390", None),
    ("VDS-ENS 09",   "Maternelle LOUISE MICHEL",                          "ENS", 25.5,   8.2,  None,  25.6, "T1", "24347901579996", None),
    ("VDS-ENS 10",   "Élémentaire ARAGO / Maternelle MICHELET",           "ENS",128.5,  41.4,  None,  53.0, "T1", "24338639640741", None),
    ("VDS-ENS 11",   "Élémentaire GEORGES BRASSENS",                      "ENS", 58.1,  18.7,  None,  19.8, "T2", "24347612144312", None),
    ("VDS-ENS 12.01","Élémentaire JEAN MACÉ",                             "ENS", 67.8,  21.8,  None,  23.9, "T2", "GI109761",       None),
    ("VDS-ENS 12.02","Élémentaire JEAN MACÉ — Restaurant scolaire",       "ENS",  2.8,   0.9,  None,   7.4, None, "24325180784928", "Tarif=0 dans OS N°3 — sous-comptage ENS 12.01"),
    ("VDS-ENS 12.03","Bureaux SLIM (Jean Macé)",                          "ENS",  2.5,   0.8,  None,  43.8, "T2", "24325904373902", None),
    ("VDS-ENS 13",   "Élémentaire LA RENAISSANCE + Rest. scol.",           "ENS",133.5,  47.6,   1.0,  35.9, "T1", "24306367441991", None),
    ("VDS-ENS 14.01","Élémentaire LAKANAL",                               "ENS", 70.1,  25.7,  None,  14.4, "T2", "24385093901043", None),
    ("VDS-ENS 14.02","Élémentaire LAKANAL — RASED",                       "ENS", 14.7,   4.7,  None,   0.0, "T2", "2439088266433",  "PCE à vérifier (13 chiffres)"),
    ("VDS-ENS 15",   "Élémentaire PAUL BERT + Rest. scol.",                "ENS", 69.1,  30.8,   3.3,  18.2, "T2", "24363965206507", None),
    ("VDS-ENS 16",   "Groupe scolaire ANATOLE FRANCE",                    "ENS", 33.4,  10.8,  None,  26.0, "T2", "24347177990906", None),
    ("VDS-ENS 17.01","GS Élémentaire PAUL LANGEVIN (NORD)",               "ENS", 25.4,  13.0,  None,   0.0, "T2", "24338205386922", None),
    ("VDS-ENS 17.02","GS Maternelle PAUL LANGEVIN + Rest. scol.",         "ENS", 57.9,  20.5,  None,  13.8, "T2", "24338494822531", None),
    ("VDS-ENS 17.03","GS Élémentaire PAUL LANGEVIN (SUD)",                "ENS", 27.3,  10.3,  None,  14.4, "T2", "24311432522777", None),
    ("VDS-ENS 17.04","GS Restaurant scol. PAUL LANGEVIN",                 "ENS", 34.2,  12.8,   0.9,  17.3, "T2", "24397539636589", None),
    ("VDS-ENS 17.05","GS Accueil loisirs périscolaires LANGEVIN",         "ENS", 20.2,   6.5,  None,  23.0, "T2", "24338494822531", "Même PCE que ENS 17.02"),
    ("VDS-ENS 18",   "C.F.A. NICOLAS ALBANO",                             "ENS",125.8,  50.1,   2.7, 206.9, "T2", "GI091908",       None),
    ("VDS-ENS 19",   "Centre de loisirs LE VALLON",                       "ENS", 34.2,  13.5,  None,  10.0, "T2", "24329088165528", None),
    # ── SPORT — Équipements sportifs ──────────────────────────────────────────
    ("VDS-SPORT 01",    "Complexe sportif ALFRED NAKACHE",                 "SPORT", 90.4, 36.6, None, 109.4, "T2", "GI137295",       None),
    ("VDS-SPORT 02.01", "LE BARROU — Halle MAURICE AUGUSTE VIE",          "SPORT", 20.3,  6.5, None,  15.1, "T2", "2439421128087",  "PCE à vérifier (13 chiffres)"),
    # SPORT 02.02 et 02.03 absents de OS N°3 (potentiellement résiliés — avenant 1)
    ("VDS-SPORT 02.02", "LE BARROU — Halle LOUIS MARTY",                  "SPORT",129.7, 41.8, None,  79.7, None, None,             "Absent OS N°3 — vérifier avenant 1"),
    ("VDS-SPORT 02.03", "LE BARROU — TENNIS CLUB",                        "SPORT",  0.0,  0.0, None,   0.0, None, None,             "Absent OS N°3 — vérifier avenant 1"),
    ("VDS-SPORT 02.04", "LE BARROU — SPORTS ÉMERGENTS",                   "SPORT", 96.4, 30.8, None,  41.2, "T2", "24354848034385", None),
    ("VDS-SPORT 03",    "Gymnase du LIDO",                                 "SPORT",110.1, 35.2, None,  89.0, "T2", "24300723411312", None),
    ("VDS-SPORT 04",    "Gymnase PAUL DI STEFANO",                        "SPORT", 89.3, 29.7, None,  54.6, "T2", "24357308187746", None),
    ("VDS-SPORT 05",    "Gymnase VINCENT FERRARI",                        "SPORT", 19.8,  6.9, None,  44.6, "T2", "24350651168903", None),
    # ── BAM — Bâtiments administratifs et techniques ──────────────────────────
    ("VDS-BAM 01",  "ARCHIVES MUNICIPALES (médiathèque)",                 "BAM",  0.0,  0.0, None,  8.6, None, None,             "Pas de gaz (OS N°3)"),
    ("VDS-BAM 02",  "Ateliers EMOP, Voirie, Peinture, Plomberie, etc.",   "BAM", 70.9,  0.0, None,  0.0, "T2", "24356295163172", None),
    ("VDS-BAM 03",  "Ateliers MÉCANIQUE",                                 "BAM", 79.6,  0.0, None,  0.0, "T2", "24310274782446", None),
    ("VDS-BAM 04",  "Ateliers ÉLECTRICITÉ",                               "BAM", 62.3,  0.0, None,  0.0, "T2", "24355282138581", None),
    ("VDS-BAM 05",  "Atelier GARAGE",                                     "BAM",  0.0,  0.0, None,237.3, None, "24355282138581", "Sous-comptage BAM 04"),
    ("VDS-BAM 06",  "Ateliers MENUISERIE",                                "BAM",  0.0,  0.0, None,  0.0, None, "24355282138581", "Sous-comptage BAM 04"),
    ("VDS-BAM 07",  "Atelier SERRURERIE",                                 "BAM",  0.0,  0.0, None,  0.0, None, "24355282138581", "Sous-comptage BAM 04"),
    ("VDS-BAM 08",  "CTM LOUIS CATANZANO",                                "BAM", 11.6,  0.0, None,  None, "T2", "24354992702958", None),
    # BAM 09 : T3 dans OS N°3 mais PRIX affiché = 74.17 (T2) → anomalie contractuelle
    ("VDS-BAM 09",  "Complexe funéraire RAYMOND FÉLICES (crématorium)",   "BAM", 32.8,  0.0, None,  None, "T3", "GI091897",       "ANOMALIE OS N°3 : tarif=T3 mais prix=74.17 (T2) — à vérifier DALKIA"),
    ("VDS-BAM 10",  "CSU — PÔLE SÉCURITÉ",                               "BAM",  0.0,  0.0, None,  None, None, None,             "Absent OS N°3"),
    ("VDS-BAM 11",  "Direction des SPORTS",                               "BAM",  0.0,  0.0, None,  None, None, None,             "Absent OS N°3"),
    ("VDS-BAM 12",  "HÔTEL DE VILLE",                                     "BAM",  0.7,  0.0, None,  None, "T1", "24359189519161", None),
    ("VDS-BAM 13",  "LES HALLES",                                         "BAM",  0.0,  0.0, None,  None, None, None,             "Absent OS N°3"),
    ("VDS-BAM 14",  "POLICE MUNICIPALE et CSU",                           "BAM",  0.0,  0.0, None,  None, None, "24355282138581", "Sous-comptage BAM 04"),
    ("VDS-BAM 15",  "Salle polyvalente GEORGES BRASSENS",                 "BAM",  0.0,  0.0, None,  None, None, None,             "Absent OS N°3"),
    ("VDS-BAM 16",  "SERRES MUNICIPALES",                                 "BAM", 51.4, 91.0, None,  None, "T2", "GI091909",       None),
    # ── CULT — Culture ────────────────────────────────────────────────────────
    ("VDS-CULT 01", "École des BEAUX-ARTS",                               "CULT", 54.3,  0.0, None,  None, None, None,             "Absent OS N°3"),
    # CULT 02.01/02/03 et CULT 05 : nouveaux sites identifiés dans OS N°3
    ("VDS-CULT 02.01", "Ex conservatoire JEAN MOULIN",                    "CULT",  0.0,  0.0, None,  None, "T2", "24310130064611", "Nouveau OS N°3 — NB à compléter depuis Annexe 5.1 CCAS"),
    ("VDS-CULT 02.02", "Ex conservatoire JEAN MOULIN — Logement n°13",    "CULT",  0.0,  0.0, None,  None, "T2", "24331693186390", "Nouveau OS N°3 — NB à compléter"),
    ("VDS-CULT 02.03", "Ex conservatoire JEAN MOULIN — Logement n°15",    "CULT",  0.0,  0.0, None,  None, "T2", "24331259032936", "Nouveau OS N°3 — NB à compléter"),
    ("VDS-CULT 05",    "Musée PAUL VALERY",                               "CULT",  0.0,  0.0, None,  None, "T2", "24370766943113", "Nouveau OS N°3 — NB à compléter"),
    # ── CCAS — Centre Communal d'Action Sociale ───────────────────────────────
    ("CCAS 01",  "EMACF FRANCOISE DOLTO",                    "CCAS", 0.0,  0.0, None, None, "T2", "24350361643410", "NB à compléter"),
    ("CCAS 04",  "Résidence autonomie LE THONNAIRE",          "CCAS", 0.0,  0.0, None, None, "T3", "GI091902",       "NB à compléter"),
    ("CCAS 05",  "Structure Multi Accueil CHÂTEAU VERT",      "CCAS", 0.0,  0.0, None, None, "T2", "24327206834125", "NB à compléter"),
    ("CCAS 07",  "Structure Multi Accueil QUARTIER HAUT",     "CCAS", 0.0,  0.0, None, None, "T2", "24362807464172", "NB à compléter"),
    ("CCAS 08",  "Structure Multi Accueil VICTOR HUGO",       "CCAS", 0.0,  0.0, None, None, "T2", "24347901530753", "NB à compléter"),
    ("CCAS 09",  "Structure Multi Accueil LACAN",             "CCAS", 0.0,  0.0, None, None, None, "24367293715978", "Tarif=0 OS N°3 — pas de gaz"),
]
# fmt: on


def seed(city_id: int | None = None, dry_run: bool = False) -> None:
    from app.core.db import SessionLocal
    from app.services.cpe import create_site, get_site_by_code, update_site
    from app.schemas.cpe import CpeSiteCreate, CpeSiteUpdate

    db = SessionLocal()
    try:
        created = 0
        updated = 0
        skipped = 0
        for row in CPE_SITES_DATA:
            code, nom, cat, nb, ecs, qecs, elec, tarif, pce, notes = row
            existing = get_site_by_code(db, code)

            if existing:
                # Mettre à jour tarif et pce si non renseignés
                needs_update = (
                    existing.tarif != tarif or
                    existing.pce != pce or
                    (notes and existing.notes != notes)
                )
                if needs_update:
                    if dry_run:
                        print(f"[DRY-RUN] Mettrait à jour : {code} tarif={tarif} pce={pce}")
                        updated += 1
                    else:
                        update_site(db, existing, CpeSiteUpdate(
                            tarif=tarif,
                            pce=pce,
                            notes=notes if notes else existing.notes,
                        ))
                        updated += 1
                        print(f"  ↺ {code} — tarif={tarif} pce={pce}")
                else:
                    skipped += 1
                continue

            if dry_run:
                print(f"[DRY-RUN] Créerait : {code} — {nom} (NB={nb} MWhPCI, tarif={tarif})")
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
                    tarif=tarif,
                    pce=pce,
                    dju_reference=1426.0,
                    actif=True,
                    notes=notes,
                ),
            )
            created += 1
            print(f"  ✓ {code} — {nom}")

        print(f"\nTerminé : {created} créés, {updated} mis à jour, {skipped} inchangés.")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed des sites CPE DALKIA")
    parser.add_argument("--city-id", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    seed(city_id=args.city_id, dry_run=args.dry_run)
