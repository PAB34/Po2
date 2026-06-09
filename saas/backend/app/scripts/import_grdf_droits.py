"""Import du référentiel des droits d'accès GRDF ADICT dans `gas_pces`.

Source : export GRDF « liste_droit_d_acces » (XLSX), une ligne par PCE avec
l'état du droit, le rôle du tiers, les périmètres accordés et le numéro unique
du droit d'accès (id_droit_acces, requis pour la révocation).

Contrairement au fichier de consentement (`modele-donnees.xlsx`), cet export
reflète l'état RÉEL côté GRDF : les droits y sont déjà `Active`, donc la collecte
de consommation peut démarrer sans nouvelle déclaration.

Particularités gérées :
- 2 rôles : `AUTORISE_CONTRAT_FOURNITURE` (périmètres renseignés `Vrai`) et
  `DETENTEUR_CONTRAT_FOURNITURE` (périmètres vides dans l'export → on les laisse
  à False, à confirmer en visio que le détenteur lit quand même conso/contract/tech).
- PCE de formats mixtes (14 chiffres et `GI+6`) : importés tels quels.
- Colonnes lues par sous-chaîne d'en-tête (robuste à l'encodage du fichier).

Usage :
    python -m app.scripts.import_grdf_droits --file "/chemin/liste_droit_d_acces_GRDF (1).xlsx"
    python -m app.scripts.import_grdf_droits --file ... --city-id 1
    python -m app.scripts.import_grdf_droits --file ... --dry-run
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
from typing import Any

import openpyxl


def _truthy(value: Any) -> bool:
    """GRDF exprime les périmètres en 'Vrai'/'Faux' (ou OUI/NON)."""
    if value is None:
        return False
    return str(value).strip().lower() in {"vrai", "oui", "true", "1"}


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    txt = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    return None


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    txt = str(value).strip()
    return txt or None


def _col_index(header: list[str], *needles: str) -> int | None:
    """Index de la première colonne dont l'en-tête contient TOUS les fragments.

    Mode ET : indispensable pour distinguer des colonnes proches, p. ex.
    « Date de début d'accès aux données » (acc + donn) de « Etat du droit
    d'accès » (acc seul) ou « Date de début de consentement ».
    """
    for i, h in enumerate(header):
        low = (h or "").lower()
        if all(n.lower() in low for n in needles):
            return i
    return None


def parse_file(path: str) -> list[dict]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [("" if c is None else str(c)) for c in rows[0]]

    idx = {
        "nom_site": _col_index(header, "Libell", "du site"),
        "etat": _col_index(header, "Etat du droit"),
        "raison_sociale": _col_index(header, "Raison sociale"),
        "id_pce": _col_index(header, "PCE"),
        "courriel": _col_index(header, "email"),
        "code_postal": _col_index(header, "Code postal"),
        "role": _col_index(header, "le du tiers"),
        "date_debut_acces": _col_index(header, "but d", "acc"),  # Date de début d'accès
        "date_fin_acces": _col_index(header, "fin d", "acc"),
        "perim_pub": _col_index(header, "consommation publi"),
        "perim_inf": _col_index(header, "consommation informativ"),
        "perim_contract": _col_index(header, "contractuelles"),
        "perim_tech": _col_index(header, "technique"),
        "id_droit_acces": _col_index(header, "unique du droit"),
    }

    records: list[dict] = []
    for raw in rows[1:]:
        def g(key: str) -> Any:
            i = idx[key]
            return raw[i] if i is not None and i < len(raw) else None

        id_pce = _clean(g("id_pce"))
        if not id_pce:
            continue
        records.append(
            {
                "id_pce": id_pce,
                "nom_site": _clean(g("nom_site")),
                "nom_titulaire": _clean(g("raison_sociale")),
                "etat_droit_acces": _clean(g("etat")),
                "courriel_titulaire": _clean(g("courriel")),
                "code_postal": _clean(g("code_postal")),
                "role_tiers": _clean(g("role")) or "AUTORISE_CONTRAT_FOURNITURE",
                "date_debut_droit_acces": _as_date(g("date_debut_acces")),
                "date_fin_droit_acces": _as_date(g("date_fin_acces")),
                "perim_publiees": _truthy(g("perim_pub")),
                "perim_informatives": _truthy(g("perim_inf")),
                "perim_contractuelles": _truthy(g("perim_contract")),
                "perim_techniques": _truthy(g("perim_tech")),
                "id_droit_acces": _clean(g("id_droit_acces")),
            }
        )
    return records


def run(file: str, city_id: int | None, dry_run: bool) -> None:
    from app.core.db import SessionLocal
    from app.models.gas import GasPce

    records = parse_file(file)
    print(f"{len(records)} PCE lus depuis {file}")
    by_role: dict[str, int] = {}
    for r in records:
        by_role[r["role_tiers"]] = by_role.get(r["role_tiers"], 0) + 1
    print("  Rôles :", by_role)

    db = SessionLocal()
    created = updated = skipped = 0
    try:
        for r in records:
            existing = (
                db.query(GasPce)
                .filter(GasPce.city_id == city_id, GasPce.id_pce == r["id_pce"])
                .one_or_none()
            )
            if existing is None:
                if dry_run:
                    print(f"[DRY-RUN] Créerait PCE {r['id_pce']} — {r['nom_site']} ({r['role_tiers']})")
                    created += 1
                    continue
                db.add(GasPce(city_id=city_id, **r))
                created += 1
                print(f"  [+] {r['id_pce']} - {r['nom_site']}")
            else:
                changed = False
                for k, v in r.items():
                    if k == "id_pce":
                        continue
                    if getattr(existing, k) != v:
                        if not dry_run:
                            setattr(existing, k, v)
                        changed = True
                if changed:
                    updated += 1
                    print(f"  [~] {r['id_pce']} - mise a jour")
                else:
                    skipped += 1
        if not dry_run:
            db.commit()
        print(f"\nTerminé : {created} créés, {updated} mis à jour, {skipped} inchangés"
              + (" (DRY-RUN, rien écrit)" if dry_run else "."))
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import des droits d'accès GRDF → gas_pces")
    parser.add_argument("--file", required=True, help="Chemin de l'export XLSX GRDF")
    parser.add_argument("--city-id", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(file=args.file, city_id=args.city_id, dry_run=args.dry_run)
