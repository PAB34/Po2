from typing import Any

from sqlalchemy.orm import Session

from app.models.billing import BillingBpuLine, BillingConfig, BillingHphcSlot, BillingPriceEntry
from app.services.bpu_templates import get_bpu_template
from app.services.energie import _csv_rows

# Postes horosaisonniers applicables par code tarifaire TURPE
POSTES_BY_TARIFF: dict[str, list[str]] = {
    "CU":   ["base"],
    "LU":   ["base"],
    "CU4":  ["hph", "hch", "hpe", "hce"],
    "MU4":  ["hph", "hch", "hpe", "hce"],
    "MUDT": ["hp", "hc"],
    "C4":   ["hph", "hch", "hpe", "hce"],
    "C2":   ["pointe", "hph", "hch", "hpe", "hce"],
}


def _extract_tariff_code(label: str) -> str:
    """Dérive le code tarifaire normalisé depuis le libellé ENEDIS distribution_tariff."""
    s = label.upper()
    # HTA → toujours C2
    if "HTA" in s:
        return "C2"
    # BT > 36 kVA
    if "BT>36" in s or "BT > 36" in s:
        if "MOYENNE" in s or "TURPE 4" in s or "MUDT" in s:
            return "MUDT"
        return "C4"
    # BT ≤ 36 kVA — ordre important : LU avant CU pour éviter les faux-positifs
    if "LONGUE UTILISATION" in s:
        return "LU"
    if "COURTE UTILISATION" in s and ("PLEINE" in s or "CREUSE" in s or "DEUX SAISONS" in s):
        return "CU4"
    if "MOYENNE UTILISATION" in s and ("PLEINE" in s or "CREUSE" in s or "DEUX SAISONS" in s):
        return "MU4"
    if "COURTE UTILISATION" in s:
        return "CU"
    if "MOYENNE UTILISATION" in s:
        return "MUDT"
    return "AUTRE"


def get_supplier_groups(db: Session, city_id: int) -> list[dict[str, Any]]:
    contracts = _csv_rows("enedis_contracts.csv")

    by_supplier: dict[str, dict[str, Any]] = {}
    for row in contracts:
        supplier = (row.get("0_contractor") or "").strip() or "Inconnu"
        label = (row.get("0_distribution_tariff") or "").strip()
        code = _extract_tariff_code(label)
        uid = row.get("usage_point_id", "")

        if supplier not in by_supplier:
            by_supplier[supplier] = {"prm_ids": [], "tariff_codes": {}, "tariff_counts": {}}
        if uid:
            by_supplier[supplier]["prm_ids"].append(uid)
        by_supplier[supplier]["tariff_codes"][code] = label
        by_supplier[supplier]["tariff_counts"][code] = by_supplier[supplier]["tariff_counts"].get(code, 0) + 1

    config_rows = db.query(BillingConfig).filter_by(city_id=city_id).all()
    seeded_defaults = False
    for cfg in config_rows:
        seeded_defaults = ensure_default_bpu_lines(db, cfg) or seeded_defaults
    if seeded_defaults:
        db.commit()

    configs = {c.supplier: c for c in config_rows}
    configs_with_bpu = {row[0] for row in db.query(BillingBpuLine.config_id).distinct().all()}

    # Ordre d'affichage cohérent avec le BPU (BT≤36 → BT>36 → HTA)
    tariff_order = ["CU", "CU4", "MU4", "LU", "MUDT", "C4", "C2", "AUTRE"]

    result = []
    for supplier, data in sorted(by_supplier.items()):
        cfg = configs.get(supplier)
        sorted_codes = sorted(data["tariff_codes"].keys(), key=lambda c: tariff_order.index(c) if c in tariff_order else 99)
        result.append(
            {
                "supplier": supplier,
                "prm_count": len(data["prm_ids"]),
                "prm_ids": data["prm_ids"],
                "tariff_codes": sorted_codes,
                "tariff_prm_counts": data["tariff_counts"],
                "config_id": cfg.id if cfg else None,
                "lot": cfg.lot if cfg else None,
                "has_hphc": cfg.has_hphc if cfg else False,
                "representative_prm_id": cfg.representative_prm_id if cfg else None,
                "is_configured": cfg is not None and cfg.lot is not None and cfg.id in configs_with_bpu,
            }
        )
    return result


def get_configs(db: Session, city_id: int) -> list[BillingConfig]:
    return db.query(BillingConfig).filter_by(city_id=city_id).order_by(BillingConfig.supplier).all()


def get_config(db: Session, config_id: int, city_id: int) -> BillingConfig | None:
    return db.query(BillingConfig).filter_by(id=config_id, city_id=city_id).first()


def upsert_supplier_config(
    db: Session,
    city_id: int,
    supplier: str,
    lot: str | None,
    has_hphc: bool | None = None,
    representative_prm_id: str | None = None,
) -> BillingConfig:
    cfg = db.query(BillingConfig).filter_by(city_id=city_id, supplier=supplier).first()
    if cfg:
        if lot is not None:
            cfg.lot = lot
        if has_hphc is not None:
            cfg.has_hphc = has_hphc
        if representative_prm_id is not None:
            cfg.representative_prm_id = representative_prm_id
    else:
        cfg = BillingConfig(
            city_id=city_id,
            supplier=supplier,
            tariff_code=None,
            lot=lot,
            has_hphc=has_hphc or False,
            representative_prm_id=representative_prm_id,
        )
        db.add(cfg)
    db.flush()
    ensure_default_bpu_lines(db, cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def patch_config(
    db: Session,
    cfg: BillingConfig,
    lot: str | None,
    has_hphc: bool | None,
    representative_prm_id: str | None,
) -> BillingConfig:
    if lot is not None:
        cfg.lot = lot
    if has_hphc is not None:
        cfg.has_hphc = has_hphc
    if representative_prm_id is not None:
        cfg.representative_prm_id = representative_prm_id
    db.flush()
    ensure_default_bpu_lines(db, cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def delete_config(db: Session, cfg: BillingConfig) -> None:
    db.query(BillingBpuLine).filter_by(config_id=cfg.id).delete()
    db.query(BillingPriceEntry).filter_by(config_id=cfg.id).delete()
    db.query(BillingHphcSlot).filter_by(config_id=cfg.id).delete()
    db.delete(cfg)
    db.commit()


def get_prices(db: Session, config_id: int) -> list[BillingPriceEntry]:
    return (
        db.query(BillingPriceEntry)
        .filter_by(config_id=config_id)
        .order_by(BillingPriceEntry.year, BillingPriceEntry.component)
        .all()
    )


def replace_prices(db: Session, config_id: int, entries: list[dict]) -> list[BillingPriceEntry]:
    db.query(BillingPriceEntry).filter_by(config_id=config_id).delete()
    objs = [
        BillingPriceEntry(
            config_id=config_id,
            year=e.get("year"),
            component=e["component"],
            value=e["value"],
            unit=e.get("unit"),
        )
        for e in entries
    ]
    db.add_all(objs)
    db.commit()
    for o in objs:
        db.refresh(o)
    return objs


def get_hphc_slots(db: Session, config_id: int) -> list[BillingHphcSlot]:
    return (
        db.query(BillingHphcSlot)
        .filter_by(config_id=config_id)
        .order_by(BillingHphcSlot.day_type, BillingHphcSlot.start_time)
        .all()
    )


def replace_hphc_slots(db: Session, config_id: int, slots: list[dict]) -> list[BillingHphcSlot]:
    db.query(BillingHphcSlot).filter_by(config_id=config_id).delete()
    objs = [
        BillingHphcSlot(
            config_id=config_id,
            day_type=s["day_type"],
            start_time=s["start_time"],
            end_time=s["end_time"],
            period=s["period"],
        )
        for s in slots
    ]
    db.add_all(objs)
    db.commit()
    for o in objs:
        db.refresh(o)
    return objs


def get_bpu_lines(db: Session, config_id: int) -> list[BillingBpuLine]:
    cfg = db.query(BillingConfig).filter_by(id=config_id).first()
    if cfg is not None and ensure_default_bpu_lines(db, cfg):
        db.commit()

    return (
        db.query(BillingBpuLine)
        .filter_by(config_id=config_id)
        .order_by(BillingBpuLine.year, BillingBpuLine.tariff_code, BillingBpuLine.poste)
        .all()
    )


def ensure_default_bpu_lines(db: Session, cfg: BillingConfig) -> bool:
    """Seed current BPU lines from the selected lot template when none exist yet."""
    if not cfg.lot:
        return False

    template = get_bpu_template(cfg.lot)
    if not template:
        return False

    has_current_lines = (
        db.query(BillingBpuLine.id)
        .filter(BillingBpuLine.config_id == cfg.id, BillingBpuLine.year.is_(None))
        .first()
        is not None
    )
    if has_current_lines:
        return False

    db.add_all(
        [
            BillingBpuLine(
                config_id=cfg.id,
                year=None,
                tariff_code=line["tariff_code"],
                poste=line["poste"],
                pu_fourniture=line["pu_fourniture"],
                pu_capacite=line["pu_capacite"],
                pu_cee=line["pu_cee"],
                pu_go=line["pu_go"],
                pu_total=line["pu_total"],
                observation=line["observation"],
            )
            for line in template
        ]
    )
    return True


def replace_bpu_lines(db: Session, config_id: int, lines: list[dict]) -> list[BillingBpuLine]:
    db.query(BillingBpuLine).filter_by(config_id=config_id).delete()
    objs = [
        BillingBpuLine(
            config_id=config_id,
            year=ln.get("year"),
            tariff_code=ln["tariff_code"],
            poste=ln["poste"],
            pu_fourniture=ln.get("pu_fourniture"),
            pu_capacite=ln.get("pu_capacite"),
            pu_cee=ln.get("pu_cee"),
            pu_go=ln.get("pu_go"),
            pu_total=ln.get("pu_total"),
            observation=ln.get("observation"),
        )
        for ln in lines
    ]
    db.add_all(objs)
    db.commit()
    for o in objs:
        db.refresh(o)
    return objs
