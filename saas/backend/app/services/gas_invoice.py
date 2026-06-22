"""
Import + contrôle des factures gaz TotalEnergies (v1 : cohérence structure).

Le fichier source est une table à plat (1 ligne = 1 facture), entièrement
décomposée. Le parsing mappe les 68 colonnes vers `GasInvoice`, puis le moteur
contrôle la cohérence interne :
- prix conso × kWh = montant conso ;
- somme des composantes = total HT ;
- HT + TVA = TTC ;
- m³ × coefficient de conversion = kWh ;
- TVA = assiette × taux (20 % normal, 5,5 % réduit).

Le contrôle prix (BPU gaz lot 7, ATRD/ATRT, TICGN) est prévu en v2.
L'import alimente aussi `gas_pces` pour que la boîte de rapprochement (PO2-PAT-003)
puisse rattacher chaque PCE à un bâtiment.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gas import GasPce
from app.models.gas_bpu import GasBpuPrice
from app.models.gas_invoice import GasInvoice

# Tolérances de contrôle.
_TOL_EUR = 0.5
_TOL_KWH = 10.0
_TOL_PU_MWH = 1.0  # tolérance prix unitaire en €/MWh
_TVA_NORMAL = 0.20
_TVA_REDUIT = 0.055

# Mapping colonne source -> attribut modèle.
_COLMAP_STR = {
    "NUM FACTURE": "num_facture",
    "TYPE DETAIL": "type_detail",
    "REF SITE": "ref_site",
    "PCE": "pce",
    "NOM SITE": "nom_site",
    "LIB REGROUPEMENT": "lib_regroupement",
    "CODE INTERNE": "code_interne",
    "ADRESSE": "adresse",
    "CODE POSTAL": "code_postal",
    "VILLE": "ville",
    "CLASSE DE CONSO": "classe_conso",
    "TARIF D'ACHEMINEMENT": "tarif_acheminement",
    "PROFIL DE CONSOMMATION": "profil_consommation",
    "MATRICULE COMPTEUR": "matricule_compteur",
    "INDEX REEL": "index_reel",
    "TYPE RELEVE": "type_releve",
}
_COLMAP_DATE = {
    "DATE COMPTABLE": "date_comptable",
    "DATE D'ECHEANCE": "date_echeance",
    "DEBUT CONSO": "debut_conso",
    "FIN CONSO": "fin_conso",
    "DERNIERE RELEVE REELLE": "derniere_releve_reelle",
}
_COLMAP_FLOAT = {
    "COEFFICIENT DE CONVERSION": "coeff_conversion",
    "PRIX CONSO GAZ": "prix_conso_gaz",
    "MONTANT CONSO GAZ": "montant_conso_gaz",
    "ABONNEMENT FOURNISSEUR": "abonnement_fournisseur",
    "MONTANT CEE": "montant_cee",
    "MONTANT CEE PRECARITE": "montant_cee_precarite",
    "MONTANT CPB": "montant_cpb",
    "MONTANT INDEXATION": "montant_indexation",
    "ATRT TERME FIXE": "atrt_terme_fixe",
    "ATRD TERME FIXE": "atrd_terme_fixe",
    "ATRD TERME VARIABLE": "atrd_terme_variable",
    "MONTANT AUTRES": "montant_autres",
    "MONTANT TICGN / ACCISE SUR GAZ": "montant_ticgn",
    "MONTANT CTA": "montant_cta",
    "TOTAL HORS TVA": "total_hors_tva",
    "ASSIETTE TVA TN": "assiette_tva_tn",
    "TVA TN": "tva_tn",
    "ASSIETTE TVA TR": "assiette_tva_tr",
    "TVA TR": "tva_tr",
    "TOTAL TTC": "total_ttc",
}
_COLMAP_INT = {
    "CAR ACHEMINEMENT": "car_acheminement",
    "CAR CONSO": "car_conso",
    "TOTAL CONSO KWH": "total_conso_kwh",
    "TOTAL CONSO M3": "total_conso_m3",
}

# Composantes dont la somme doit égaler le total HT.
_HT_COMPONENTS = [
    "montant_conso_gaz", "abonnement_fournisseur", "montant_cee", "montant_cee_precarite",
    "montant_cpb", "montant_indexation", "atrt_terme_fixe", "atrd_terme_fixe",
    "atrd_terme_variable", "montant_autres", "montant_ticgn", "montant_cta",
]


def _s(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _f(value: Any) -> float | None:
    text = _s(value)
    if text is None:
        return None
    try:
        return float(text.replace(" ", "").replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _i(value: Any) -> int | None:
    f = _f(value)
    return int(round(f)) if f is not None else None


def _d(value: Any) -> date | None:
    text = _s(value)
    if text is None:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_rows(raw_bytes: bytes) -> list[dict[str, Any]]:
    df = pd.read_excel(BytesIO(raw_bytes), sheet_name=0, dtype=str).fillna("")
    df.columns = [str(c).strip() for c in df.columns]
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        data: dict[str, Any] = {}
        for col, attr in _COLMAP_STR.items():
            data[attr] = _s(row.get(col))
        for col, attr in _COLMAP_DATE.items():
            data[attr] = _d(row.get(col))
        for col, attr in _COLMAP_FLOAT.items():
            data[attr] = _f(row.get(col))
        for col, attr in _COLMAP_INT.items():
            data[attr] = _i(row.get(col))
        if not data.get("num_facture") or not data.get("pce"):
            continue
        data["raw_json"] = json.dumps({k: _s(v) for k, v in row.to_dict().items()}, ensure_ascii=False)
        rows.append(data)
    return rows


# --------------------------------------------------------------------------- #
# Moteur de contrôle v1
# --------------------------------------------------------------------------- #
def _issue(code: str, family: str, message: str, severity: str) -> dict[str, str]:
    return {"code": code, "family": family, "message": message, "severity": severity}


def load_gas_bpu(db: Session, city_id: int | None, annee: int) -> GasBpuPrice | None:
    """Référence BPU gaz pour l'année (prix identiques sur T1-T4 en 2026).
    Préfère la ligne de la ville, sinon la ligne générique (city_id NULL)."""
    rows = list(db.execute(
        select(GasBpuPrice).where(
            GasBpuPrice.annee == annee,
            (GasBpuPrice.city_id == city_id) | (GasBpuPrice.city_id.is_(None)),
        )
    ).scalars())
    if not rows:
        return None
    rows.sort(key=lambda r: 0 if r.city_id == city_id else 1)
    return rows[0]


def compute_control(inv: GasInvoice, bpu: GasBpuPrice | None = None) -> tuple[str, list[dict[str, str]]]:
    issues: list[dict[str, str]] = []

    pu, kwh, mt = inv.prix_conso_gaz, inv.total_conso_kwh, inv.montant_conso_gaz
    if pu is not None and kwh is not None and mt is not None:
        if abs(pu * kwh - mt) > _TOL_EUR:
            issues.append(_issue(
                "GAS_CONSO_PUXQ", "Arithmétique",
                f"Prix×kWh ({pu * kwh:.2f}) ≠ montant conso ({mt:.2f})", "invalid",
            ))

    if inv.total_hors_tva is not None:
        somme = sum((getattr(inv, c) or 0.0) for c in _HT_COMPONENTS)
        if abs(somme - inv.total_hors_tva) > _TOL_EUR:
            issues.append(_issue(
                "GAS_HT_SUM", "Arithmétique",
                f"Somme composantes ({somme:.2f}) ≠ total HT ({inv.total_hors_tva:.2f})", "invalid",
            ))

    if inv.total_hors_tva is not None and inv.total_ttc is not None:
        tva = (inv.tva_tn or 0.0) + (inv.tva_tr or 0.0)
        if abs(inv.total_hors_tva + tva - inv.total_ttc) > _TOL_EUR:
            issues.append(_issue(
                "GAS_TTC", "Arithmétique",
                f"HT+TVA ({inv.total_hors_tva + tva:.2f}) ≠ TTC ({inv.total_ttc:.2f})", "invalid",
            ))

    if inv.total_conso_m3 is not None and inv.coeff_conversion and inv.total_conso_kwh is not None:
        calc = inv.total_conso_m3 * inv.coeff_conversion
        if abs(calc - inv.total_conso_kwh) > _TOL_KWH:
            issues.append(_issue(
                "GAS_CONVERSION", "Conversion",
                f"m³×coeff ({calc:.0f}) ≠ kWh facturés ({inv.total_conso_kwh})", "review",
            ))

    if inv.assiette_tva_tn is not None and inv.tva_tn is not None:
        if abs(inv.assiette_tva_tn * _TVA_NORMAL - inv.tva_tn) > _TOL_EUR:
            issues.append(_issue(
                "GAS_TVA_TN", "TVA",
                f"TVA normale {inv.tva_tn:.2f} ≠ 20% de {inv.assiette_tva_tn:.2f}", "review",
            ))
    if inv.assiette_tva_tr is not None and inv.tva_tr is not None:
        if abs(inv.assiette_tva_tr * _TVA_REDUIT - inv.tva_tr) > _TOL_EUR:
            issues.append(_issue(
                "GAS_TVA_TR", "TVA",
                f"TVA réduite {inv.tva_tr:.2f} ≠ 5,5% de {inv.assiette_tva_tr:.2f}", "review",
            ))

    # --- Contrôle prix vs BPU lot 7 (fourniture + CPB) ---
    if bpu is not None:
        kwh = inv.total_conso_kwh
        if bpu.fourniture_ht_mwh is not None and inv.prix_conso_gaz is not None:
            pu_mwh = inv.prix_conso_gaz * 1000.0
            if abs(pu_mwh - bpu.fourniture_ht_mwh) > _TOL_PU_MWH:
                issues.append(_issue(
                    "GAS_PRIX_FOURNITURE", "Prix fourniture",
                    f"Prix conso {pu_mwh:.2f} ≠ BPU fourniture ferme {bpu.fourniture_ht_mwh:.2f} €/MWh "
                    f"(prix révisable PEG ou écart à vérifier)", "review",
                ))
        if bpu.cpb_ht_mwh is not None and inv.montant_cpb and kwh:
            eff = inv.montant_cpb / (kwh / 1000.0)
            if abs(eff - bpu.cpb_ht_mwh) > _TOL_PU_MWH:
                issues.append(_issue(
                    "GAS_PRIX_CPB", "Prix CPB",
                    f"CPB {eff:.2f} ≠ BPU {bpu.cpb_ht_mwh:.2f} €/MWh", "review",
                ))

    if any(i["severity"] == "invalid" for i in issues):
        status = "invalid"
    elif issues:
        status = "review"
    else:
        status = "valid"
    return status, issues


def _invoice_year(inv: GasInvoice) -> int | None:
    ref = inv.debut_conso or inv.date_comptable
    return ref.year if ref else None


def _apply_control(inv: GasInvoice, bpu: GasBpuPrice | None = None) -> None:
    status, issues = compute_control(inv, bpu=bpu)
    inv.control_status = status
    inv.control_issues_json = json.dumps(issues, ensure_ascii=False) if issues else None


# --------------------------------------------------------------------------- #
# Alimentation du référentiel PCE (-> boîte de rapprochement)
# --------------------------------------------------------------------------- #
def _upsert_pce(db: Session, city_id: int | None, inv: GasInvoice) -> int | None:
    pce = db.execute(
        select(GasPce).where(GasPce.id_pce == inv.pce, GasPce.city_id == city_id)
    ).scalars().first()
    if pce is None:
        pce = GasPce(city_id=city_id, id_pce=inv.pce, nom_site=inv.nom_site or inv.lib_regroupement)
        db.add(pce)
    if not pce.nom_site:
        pce.nom_site = inv.nom_site or inv.lib_regroupement
    if not pce.code_postal:
        pce.code_postal = inv.code_postal
    if not pce.tarif_acheminement:
        pce.tarif_acheminement = inv.tarif_acheminement
    if not pce.profil_type:
        pce.profil_type = inv.profil_consommation
    if pce.car_actuelle is None and inv.car_conso is not None:
        pce.car_actuelle = inv.car_conso
    return pce.building_id


# --------------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------------- #
def import_invoices(
    db: Session,
    city_id: int | None,
    raw_bytes: bytes,
    force_update: bool = False,
) -> dict[str, Any]:
    rows = parse_rows(raw_bytes)
    batch = datetime.now(timezone.utc).strftime("TE-%Y%m%d%H%M%S")
    summary = {"batch": batch, "rows": len(rows), "created": 0, "updated": 0, "skipped": 0,
               "valid": 0, "review": 0, "invalid": 0}
    _bpu_cache: dict[int, GasBpuPrice | None] = {}

    for data in rows:
        existing = db.execute(
            select(GasInvoice).where(
                GasInvoice.city_id == city_id, GasInvoice.num_facture == data["num_facture"]
            )
        ).scalars().first()

        if existing is not None and not force_update:
            summary["skipped"] += 1
            continue

        if existing is None:
            inv = GasInvoice(city_id=city_id, import_batch=batch)
            db.add(inv)
            summary["created"] += 1
        else:
            inv = existing
            inv.import_batch = batch
            summary["updated"] += 1

        for attr, value in data.items():
            setattr(inv, attr, value)

        db.flush()
        inv.building_id = _upsert_pce(db, city_id, inv) or inv.building_id
        year = _invoice_year(inv)
        bpu = _bpu_cache.setdefault(year, load_gas_bpu(db, city_id, year)) if year else None
        _apply_control(inv, bpu=bpu)
        summary[inv.control_status] = summary.get(inv.control_status, 0) + 1

    db.commit()
    return summary


def recompute_controls(db: Session, city_id: int | None) -> dict[str, int]:
    out = {"valid": 0, "review": 0, "invalid": 0}
    bpu_cache: dict[int, GasBpuPrice | None] = {}
    for inv in db.execute(select(GasInvoice).where(GasInvoice.city_id == city_id)).scalars():
        year = _invoice_year(inv)
        bpu = bpu_cache.setdefault(year, load_gas_bpu(db, city_id, year)) if year else None
        _apply_control(inv, bpu=bpu)
        out[inv.control_status] = out.get(inv.control_status, 0) + 1
    db.commit()
    return out


# --------------------------------------------------------------------------- #
# Lecture / portefeuille
# --------------------------------------------------------------------------- #
def list_invoices(
    db: Session,
    city_id: int | None,
    control_status: str | None = None,
    decision_status: str | None = None,
) -> list[GasInvoice]:
    query = select(GasInvoice).where(GasInvoice.city_id == city_id)
    if control_status:
        query = query.where(GasInvoice.control_status == control_status)
    if decision_status:
        query = query.where(GasInvoice.decision_status == decision_status)
    query = query.order_by(GasInvoice.date_comptable.desc().nullslast(), GasInvoice.id.desc())
    return list(db.execute(query).scalars())


def portfolio(db: Session, city_id: int | None) -> dict[str, Any]:
    invoices = list(db.execute(select(GasInvoice).where(GasInvoice.city_id == city_id)).scalars())
    by_control: dict[str, int] = {}
    by_decision: dict[str, int] = {}
    by_site: dict[str, dict[str, Any]] = {}
    total_ht = total_ttc = 0.0
    total_kwh = 0
    for inv in invoices:
        by_control[inv.control_status] = by_control.get(inv.control_status, 0) + 1
        by_decision[inv.decision_status] = by_decision.get(inv.decision_status, 0) + 1
        total_ht += inv.total_hors_tva or 0.0
        total_ttc += inv.total_ttc or 0.0
        total_kwh += inv.total_conso_kwh or 0
        key = inv.lib_regroupement or inv.nom_site or inv.pce
        cell = by_site.setdefault(key, {"site": key, "pce": inv.pce, "count": 0, "ht": 0.0, "kwh": 0, "linked": inv.building_id is not None})
        cell["count"] += 1
        cell["ht"] += inv.total_hors_tva or 0.0
        cell["kwh"] += inv.total_conso_kwh or 0
    return {
        "count": len(invoices),
        "total_ht": round(total_ht, 2),
        "total_ttc": round(total_ttc, 2),
        "total_kwh": total_kwh,
        "by_control": by_control,
        "by_decision": by_decision,
        "by_site": sorted(by_site.values(), key=lambda c: c["ht"], reverse=True),
    }


def list_bpu(db: Session, city_id: int | None) -> list[GasBpuPrice]:
    rows = list(db.execute(
        select(GasBpuPrice).where(
            (GasBpuPrice.city_id == city_id) | (GasBpuPrice.city_id.is_(None))
        )
    ).scalars())
    rows.sort(key=lambda r: (-r.annee, r.profil))
    return rows


def update_bpu(db: Session, row_id: int, fields: dict[str, Any]) -> GasBpuPrice:
    row = db.get(GasBpuPrice, row_id)
    if row is None:
        raise ValueError("Ligne BPU gaz introuvable.")
    for key in ("fourniture_ht_mwh", "cee_ht_mwh", "cee_precarite_ht_mwh", "cpb_ht_mwh", "go_ht_mwh"):
        if key in fields and fields[key] is not None:
            setattr(row, key, float(fields[key]))
    db.commit()
    db.refresh(row)
    return row


def set_decision(db: Session, city_id: int | None, invoice_id: int, decision_status: str, comment: str | None) -> GasInvoice:
    inv = db.execute(
        select(GasInvoice).where(GasInvoice.id == invoice_id, GasInvoice.city_id == city_id)
    ).scalars().first()
    if inv is None:
        raise ValueError("Facture gaz introuvable.")
    if decision_status not in {"to_review", "approved", "rejected", "dispute_sent"}:
        raise ValueError(f"Décision invalide : {decision_status}")
    inv.decision_status = decision_status
    inv.decision_comment = comment
    db.commit()
    db.refresh(inv)
    return inv
