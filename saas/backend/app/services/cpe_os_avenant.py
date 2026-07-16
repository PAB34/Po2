"""Service layer for CPE DALKIA OS / avenant preparation dossiers."""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cpe_contract_change import CpeContractChangeLine, CpeContractChangeRequest
from app.models.cpe_dalkia import (
    CpeDalkiaRefImport,
    CpeDalkiaRefP1Elec,
    CpeDalkiaRefP1Gaz,
    CpeDalkiaRefP2P3,
    CpeDalkiaRefSite,
)
from app.schemas.cpe_os_avenant import CpeOsAvenantRequestCreate, CpeOsAvenantRequestUpdate

CONTRACT_END_YEAR = 2033
VALID_STATUSES = {
    "draft",
    "sent_to_dalkia",
    "dalkia_completed",
    "pending_collectivity_validation",
    "os_ready",
    "os_signed",
    "in_service",
    "included_in_avenant",
    "cancelled",
}


def _city_filter(query, model, city_id: int | None):
    if city_id is None:
        return query
    return query.where(model.city_id == city_id)


def _active_import_ids(db: Session, city_id: int | None, lot: int | None = None) -> list[int]:
    query = select(CpeDalkiaRefImport.id).where(CpeDalkiaRefImport.is_active.is_(True))
    query = _city_filter(query, CpeDalkiaRefImport, city_id)
    if lot is not None:
        query = query.where(CpeDalkiaRefImport.lot == lot)
    return list(db.scalars(query).all())


def _sum_for_site(db: Session, model, column_name: str, *, import_ids: list[int], code_site: str, year: int) -> float:
    if not import_ids:
        return 0.0
    value = db.scalar(
        select(func.coalesce(func.sum(getattr(model, column_name)), 0.0)).where(
            model.import_id.in_(import_ids),
            model.code_site == code_site,
            model.period_year == year,
        )
    )
    return float(value or 0.0)


def reference_for_site(
    db: Session,
    city_id: int | None,
    *,
    code_site: str,
    year: int,
    lot: int | None = None,
) -> dict[str, Any]:
    import_ids = _active_import_ids(db, city_id, lot)
    site = None
    if import_ids:
        site = db.scalars(
            select(CpeDalkiaRefSite)
            .where(CpeDalkiaRefSite.import_id.in_(import_ids), CpeDalkiaRefSite.code_site == code_site)
            .order_by(CpeDalkiaRefSite.id.desc())
        ).first()
    gaz = db.scalars(
        select(CpeDalkiaRefP1Gaz)
        .where(
            CpeDalkiaRefP1Gaz.import_id.in_(import_ids) if import_ids else False,
            CpeDalkiaRefP1Gaz.code_site == code_site,
            CpeDalkiaRefP1Gaz.period_year == year,
        )
        .order_by(CpeDalkiaRefP1Gaz.id.desc())
    ).first() if import_ids else None
    return {
        "code_site": code_site,
        "site_name": site.nom_batiment if site else code_site,
        "lot": site.lot if site else lot,
        "pce": gaz.pce if gaz else None,
        "tarif": gaz.type_tarif if gaz else None,
        "p1_gaz_annual_ht": _sum_for_site(db, CpeDalkiaRefP1Gaz, "p10_total_ht", import_ids=import_ids, code_site=code_site, year=year),
        "p1_elec_annual_ht": _sum_for_site(db, CpeDalkiaRefP1Elec, "p10_total_ht", import_ids=import_ids, code_site=code_site, year=year),
        "p2_annual_ht": _sum_for_site(db, CpeDalkiaRefP2P3, "p2_total_ht", import_ids=import_ids, code_site=code_site, year=year),
        "p3_annual_ht": _sum_for_site(db, CpeDalkiaRefP2P3, "p3_total_ht", import_ids=import_ids, code_site=code_site, year=year),
    }


def list_site_options(db: Session, city_id: int | None, *, year: int, lot: int | None = None) -> list[dict[str, Any]]:
    import_ids = _active_import_ids(db, city_id, lot)
    if not import_ids:
        return []
    query = select(CpeDalkiaRefSite).where(CpeDalkiaRefSite.import_id.in_(import_ids))
    if lot is not None:
        query = query.where(CpeDalkiaRefSite.lot == lot)
    sites = db.scalars(query.order_by(CpeDalkiaRefSite.lot, CpeDalkiaRefSite.code_site)).all()
    options = []
    seen: set[str] = set()
    for site in sites:
        if site.code_site in seen:
            continue
        seen.add(site.code_site)
        ref = reference_for_site(db, city_id, code_site=site.code_site, year=year, lot=site.lot)
        total = ref["p1_gaz_annual_ht"] + ref["p1_elec_annual_ht"] + ref["p2_annual_ht"] + ref["p3_annual_ht"]
        options.append({**ref, "total_annual_ht": round(total, 2)})
    return options


def _year_ratio(effective_date: date | None) -> float:
    if effective_date is None:
        return 1.0
    start = date(effective_date.year, 1, 1)
    end = date(effective_date.year + 1, 1, 1)
    return max(0.0, min(1.0, (end - effective_date).days / (end - start).days))


def _delta(action: str, current: float | None, target: float | None) -> float:
    current_value = float(current or 0.0)
    target_value = float(target or 0.0)
    if action == "remove":
        return -current_value if current is not None else -target_value
    if action == "modify":
        return target_value - current_value
    return target_value


def _line_impact(line: CpeContractChangeLine) -> dict[str, float]:
    action = line.action
    p1_gaz = _delta(action, line.current_p1_gaz_annual_ht, line.p1_gaz_annual_ht)
    p1_elec = _delta(action, line.current_p1_elec_annual_ht, line.p1_elec_annual_ht)
    p2 = _delta(action, line.current_p2_annual_ht, line.p2_annual_ht)
    p3 = _delta(action, line.current_p3_annual_ht, line.p3_annual_ht)
    return {"p1_gaz_annual_ht": p1_gaz, "p1_elec_annual_ht": p1_elec, "p2_annual_ht": p2, "p3_annual_ht": p3}


def build_impact(request: CpeContractChangeRequest, lines: list[CpeContractChangeLine]) -> dict[str, Any]:
    totals = {"p1_gaz_annual_ht": 0.0, "p1_elec_annual_ht": 0.0, "p2_annual_ht": 0.0, "p3_annual_ht": 0.0}
    for line in lines:
        impact = _line_impact(line)
        for key, value in impact.items():
            totals[key] += value
    p1 = totals["p1_gaz_annual_ht"] + totals["p1_elec_annual_ht"]
    annual = p1 + totals["p2_annual_ht"] + totals["p3_annual_ht"]
    ratio = _year_ratio(request.effective_date)
    year = request.effective_date.year if request.effective_date else None
    remaining_years = (CONTRACT_END_YEAR - year + ratio) if year else 1.0
    return {
        **{key: round(value, 2) for key, value in totals.items()},
        "p1_annual_ht": round(p1, 2),
        "total_annual_ht": round(annual, 2),
        "first_year_prorata_ht": round(annual * ratio, 2),
        "remaining_market_ht": round(annual * max(0.0, remaining_years), 2),
        "effective_year": year,
        "first_year_ratio": round(ratio, 4),
    }


def _request_to_dict(db: Session, request: CpeContractChangeRequest) -> dict[str, Any]:
    lines = list(
        db.scalars(
            select(CpeContractChangeLine)
            .where(CpeContractChangeLine.request_id == request.id)
            .order_by(CpeContractChangeLine.id)
        ).all()
    )
    return {**request.__dict__, "lines": lines, "impact": build_impact(request, lines)}


def list_requests(db: Session, city_id: int | None) -> list[dict[str, Any]]:
    query = select(CpeContractChangeRequest)
    query = _city_filter(query, CpeContractChangeRequest, city_id)
    requests = db.scalars(query.order_by(CpeContractChangeRequest.created_at.desc(), CpeContractChangeRequest.id.desc())).all()
    return [_request_to_dict(db, request) for request in requests]


def get_request(db: Session, city_id: int | None, request_id: int) -> dict[str, Any] | None:
    query = select(CpeContractChangeRequest).where(CpeContractChangeRequest.id == request_id)
    query = _city_filter(query, CpeContractChangeRequest, city_id)
    request = db.scalars(query).first()
    return _request_to_dict(db, request) if request else None


def _hydrate_line(db: Session, city_id: int | None, request: CpeContractChangeRequest, raw: dict[str, Any]) -> dict[str, Any]:
    data = dict(raw)
    action = data["action"]
    code_site = data.get("code_site")
    year = request.effective_date.year if request.effective_date else date.today().year
    if code_site and action in {"remove", "modify"}:
        ref = reference_for_site(db, city_id, code_site=code_site, year=year, lot=data.get("lot") or request.lot)
        data.setdefault("site_name", ref["site_name"])
        data["site_name"] = data.get("site_name") or ref["site_name"]
        data["lot"] = data.get("lot") or ref["lot"]
        data["pce"] = data.get("pce") or ref["pce"]
        data["tarif"] = data.get("tarif") or ref["tarif"]
        data["current_p1_gaz_annual_ht"] = data.get("current_p1_gaz_annual_ht") if data.get("current_p1_gaz_annual_ht") is not None else ref["p1_gaz_annual_ht"]
        data["current_p1_elec_annual_ht"] = data.get("current_p1_elec_annual_ht") if data.get("current_p1_elec_annual_ht") is not None else ref["p1_elec_annual_ht"]
        data["current_p2_annual_ht"] = data.get("current_p2_annual_ht") if data.get("current_p2_annual_ht") is not None else ref["p2_annual_ht"]
        data["current_p3_annual_ht"] = data.get("current_p3_annual_ht") if data.get("current_p3_annual_ht") is not None else ref["p3_annual_ht"]
        if action == "remove":
            data["p1_gaz_annual_ht"] = data.get("p1_gaz_annual_ht") if data.get("p1_gaz_annual_ht") is not None else ref["p1_gaz_annual_ht"]
            data["p1_elec_annual_ht"] = data.get("p1_elec_annual_ht") if data.get("p1_elec_annual_ht") is not None else ref["p1_elec_annual_ht"]
            data["p2_annual_ht"] = data.get("p2_annual_ht") if data.get("p2_annual_ht") is not None else ref["p2_annual_ht"]
            data["p3_annual_ht"] = data.get("p3_annual_ht") if data.get("p3_annual_ht") is not None else ref["p3_annual_ht"]
    data["site_name"] = data.get("site_name") or data.get("code_site") or "Site a preciser"
    return data


def create_request(db: Session, city_id: int | None, user_id: int | None, payload: CpeOsAvenantRequestCreate) -> dict[str, Any]:
    request = CpeContractChangeRequest(
        city_id=city_id,
        created_by_user_id=user_id,
        title=payload.title,
        change_type=payload.change_type,
        lot=payload.lot,
        effective_date=payload.effective_date,
        reason=payload.reason,
        requester_name=payload.requester_name,
        dalkia_contact_email=payload.dalkia_contact_email,
        notes=payload.notes,
    )
    db.add(request)
    db.flush()
    for line_payload in payload.lines:
        data = _hydrate_line(db, city_id, request, line_payload.model_dump())
        db.add(CpeContractChangeLine(request_id=request.id, city_id=city_id, **data))
    db.commit()
    db.refresh(request)
    return _request_to_dict(db, request)


def update_request(
    db: Session,
    city_id: int | None,
    request_id: int,
    payload: CpeOsAvenantRequestUpdate,
) -> dict[str, Any] | None:
    query = select(CpeContractChangeRequest).where(CpeContractChangeRequest.id == request_id)
    query = _city_filter(query, CpeContractChangeRequest, city_id)
    request = db.scalars(query).first()
    if request is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in VALID_STATUSES:
        raise ValueError("INVALID_STATUS")
    for key, value in data.items():
        setattr(request, key, value)
    db.commit()
    db.refresh(request)
    return _request_to_dict(db, request)