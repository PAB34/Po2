"""Comparaison entre deux versions d'import DALKIA — « synthèse des modifications ».

Chaque import est un snapshot conservé (cf. lignée `cpe_dalkia_ref_imports` /
`cpe_dpgf_p1_imports`). Ce module compare deux snapshots et restitue les écarts, pour le
journal du marché (pastilles) et la vue « Comparer ».

- `build_master_diff` : entre deux imports MAÎTRES (avenant vs base/précédent) — sites
  entrés/sortis, montants P1 gaz/élec/P2/P3 (année réf), marché global, cibles modifiées.
- `build_dpgf_summary` : pour un import DPGF P1 — totaux des 3 niveaux par année + écart de
  révision (Rév Temp / Rév T° & prix vs contrat) ; écarts vs une version DPGF précédente si fournie.

Aucun nouveau parsing : tout est déjà en base (snapshots conservés).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cpe_dalkia import (
    CpeDalkiaRefCible,
    CpeDalkiaRefImport,
    CpeDalkiaRefP1Elec,
    CpeDalkiaRefP1Gaz,
    CpeDalkiaRefP2P3,
    CpeDalkiaRefSite,
)
from app.models.cpe_dpgf_p1 import DPGF_P1_LEVELS, CpeDpgfP1Import, CpeDpgfP1Line
from app.models.user import User
from app.services.cpe_dalkia_db import get_import_by_id


def _import_meta(imp: CpeDalkiaRefImport | CpeDpgfP1Import) -> dict[str, Any]:
    return {
        "id": imp.id,
        "filename": imp.filename,
        "import_date": imp.import_date.isoformat(),
        "is_active": imp.is_active,
    }


def _sum(db: Session, model, col: str, import_id: int, year: int | None = None) -> float:
    stmt = select(func.sum(getattr(model, col))).where(model.import_id == import_id)
    if year is not None:
        stmt = stmt.where(model.period_year == year)
    return db.scalar(stmt) or 0.0


def _site_codes(db: Session, import_id: int) -> set[str]:
    return {
        c for c in db.scalars(
            select(CpeDalkiaRefSite.code_site).where(CpeDalkiaRefSite.import_id == import_id)
        )
    }


def _cibles_map(db: Session, import_id: int, fluid: str) -> dict[tuple[str, int], float]:
    """{(code_site, year): nb_mwhpci} pour un fluide d'un import."""
    out: dict[tuple[str, int], float] = {}
    for row in db.scalars(
        select(CpeDalkiaRefCible).where(
            CpeDalkiaRefCible.import_id == import_id, CpeDalkiaRefCible.fluid == fluid
        )
    ):
        if row.nb_mwhpci is not None:
            out[(row.code_site, row.period_year)] = round(row.nb_mwhpci, 3)
    return out


def _count_cibles_modifiees(db: Session, from_id: int, to_id: int, fluid: str) -> int:
    a = _cibles_map(db, from_id, fluid)
    b = _cibles_map(db, to_id, fluid)
    keys = set(a) | set(b)
    return sum(1 for k in keys if a.get(k) != b.get(k))


def _poste_delta(db: Session, label: str, model, col: str, from_id: int, to_id: int, year: int) -> dict[str, Any]:
    f = round(_sum(db, model, col, from_id, year), 2)
    t = round(_sum(db, model, col, to_id, year), 2)
    return {"poste": label, "from_ht": f, "to_ht": t, "delta_ht": round(t - f, 2)}


def _marche_total(db: Session, import_id: int) -> float:
    return round(
        _sum(db, CpeDalkiaRefP1Gaz, "p10_total_ht", import_id)
        + _sum(db, CpeDalkiaRefP1Elec, "p10_total_ht", import_id)
        + _sum(db, CpeDalkiaRefP2P3, "p2_total_ht", import_id)
        + _sum(db, CpeDalkiaRefP2P3, "p3_total_ht", import_id),
        2,
    )


def build_master_diff(
    db: Session, current_user: User, to_id: int, from_id: int | None = None, ref_year: int = 2026
) -> dict[str, Any]:
    """Compare un import maître (``to_id``) à un autre (``from_id``, défaut = base du lot)."""
    to_imp = get_import_by_id(db, to_id, current_user)
    if to_imp is None:
        return {"ok": False, "reason": "not_found", "message": "Import cible introuvable."}

    if from_id is not None:
        from_imp = get_import_by_id(db, from_id, current_user)
    else:
        stmt = select(CpeDalkiaRefImport).where(
            CpeDalkiaRefImport.lot == to_imp.lot, CpeDalkiaRefImport.id != to_id
        )
        if current_user.city_id is not None:
            stmt = stmt.where(CpeDalkiaRefImport.city_id == current_user.city_id)
        from_imp = db.scalars(stmt.order_by(CpeDalkiaRefImport.import_date.asc())).first()

    if from_imp is None:
        return {"ok": False, "reason": "no_baseline", "message": "Aucune version antérieure à comparer (c'est la base)."}

    sa = _site_codes(db, from_imp.id)
    sb = _site_codes(db, to_imp.id)
    entres = sorted(sb - sa)
    sortis = sorted(sa - sb)

    postes = [
        _poste_delta(db, "P1 gaz", CpeDalkiaRefP1Gaz, "p10_total_ht", from_imp.id, to_imp.id, ref_year),
        _poste_delta(db, "P1 élec", CpeDalkiaRefP1Elec, "p10_total_ht", from_imp.id, to_imp.id, ref_year),
        _poste_delta(db, "P2", CpeDalkiaRefP2P3, "p2_total_ht", from_imp.id, to_imp.id, ref_year),
        _poste_delta(db, "P3", CpeDalkiaRefP2P3, "p3_total_ht", from_imp.id, to_imp.id, ref_year),
    ]
    postes = [p for p in postes if p["from_ht"] or p["to_ht"]]

    marche_from = _marche_total(db, from_imp.id)
    marche_to = _marche_total(db, to_imp.id)
    cibles_gaz = _count_cibles_modifiees(db, from_imp.id, to_imp.id, "GAZ")
    cibles_elec = _count_cibles_modifiees(db, from_imp.id, to_imp.id, "ELEC")

    # Pastilles courtes pour le journal
    chips: list[str] = []
    if entres:
        chips.append(f"+{len(entres)} site{'s' if len(entres) > 1 else ''}")
    if sortis:
        chips.append(f"−{len(sortis)} site{'s' if len(sortis) > 1 else ''}")
    for p in postes:
        if abs(p["delta_ht"]) >= 1:
            sign = "+" if p["delta_ht"] > 0 else "−"
            chips.append(f"{p['poste']} {sign}{abs(round(p['delta_ht'] / 1000)) } k€")
    if cibles_gaz:
        chips.append(f"cibles gaz ×{cibles_gaz}")
    if cibles_elec:
        chips.append(f"cibles élec ×{cibles_elec}")
    if not chips:
        chips.append("aucun écart détecté")

    return {
        "ok": True,
        "ref_year": ref_year,
        "from_import": _import_meta(from_imp),
        "to_import": _import_meta(to_imp),
        "sites_entres": entres,
        "sites_sortis": sortis,
        "nb_sites_from": len(sa),
        "nb_sites_to": len(sb),
        "postes": postes,
        "marche_total_from_ht": marche_from,
        "marche_total_to_ht": marche_to,
        "marche_delta_ht": round(marche_to - marche_from, 2),
        "cibles_gaz_modifiees": cibles_gaz,
        "cibles_elec_modifiees": cibles_elec,
        "chips": chips,
    }


def _dpgf_totals_by_level_year(db: Session, import_id: int) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    for row in db.scalars(select(CpeDpgfP1Line).where(CpeDpgfP1Line.import_id == import_id)):
        out.setdefault(row.level, {})
        out[row.level][row.period_year] = round(
            out[row.level].get(row.period_year, 0.0) + (row.p10_total_ht or 0.0), 2
        )
    return out


def build_dpgf_summary(
    db: Session, current_user: User, to_id: int, ref_year: int = 2026
) -> dict[str, Any]:
    """Synthèse d'un DPGF P1 : totaux par niveau + écart de révision vs contrat (par année)."""
    stmt = select(CpeDpgfP1Import).where(CpeDpgfP1Import.id == to_id)
    if current_user.city_id is not None:
        stmt = stmt.where(CpeDpgfP1Import.city_id == current_user.city_id)
    imp = db.scalars(stmt).first()
    if imp is None:
        return {"ok": False, "reason": "not_found", "message": "DPGF introuvable."}

    totals = _dpgf_totals_by_level_year(db, to_id)
    years = sorted({y for lv in totals.values() for y in lv})
    contrat = totals.get("contrat", {})
    rev_temp = totals.get("rev_temp", {})
    rev_prix = totals.get("rev_temp_prix", {})

    by_year = [
        {
            "year": y,
            "contrat": round(contrat.get(y, 0.0), 2),
            "rev_temp": round(rev_temp.get(y, 0.0), 2),
            "rev_temp_prix": round(rev_prix.get(y, 0.0), 2),
            "delta_rev_temp": round(rev_temp.get(y, 0.0) - contrat.get(y, 0.0), 2),
            "delta_rev_temp_prix": round(rev_prix.get(y, 0.0) - contrat.get(y, 0.0), 2),
        }
        for y in years
    ]

    d_rev = round(rev_temp.get(ref_year, 0.0) - contrat.get(ref_year, 0.0), 2)
    chips: list[str] = []
    if rev_temp.get(ref_year):
        sign = "+" if d_rev >= 0 else "−"
        chips.append(f"Rév Temp {sign}{abs(round(d_rev / 1000))} k€")
    if not chips:
        chips.append("P1 révisé")

    return {
        "ok": True,
        "ref_year": ref_year,
        "import": _import_meta(imp),
        "levels": [lv for lv in DPGF_P1_LEVELS if lv in totals],
        "by_year": by_year,
        "chips": chips,
    }
