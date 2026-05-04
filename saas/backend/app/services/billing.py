from typing import Any

from sqlalchemy.orm import Session

from app.models.billing import BillingConfig, BillingHphcSlot, BillingPriceEntry
from app.services.energie import _csv_rows


def _extract_tariff_code(label: str) -> str:
    s = label.upper()
    if "CU4" in s:
        return "CU4"
    if "MU4" in s:
        return "MU4"
    if "MUDT" in s:
        return "MUDT"
    if ("COURTE UTILISATION" in s or " CU " in s) and (
        "PLEINE" in s or "CREUSE" in s or "HP" in s or "HC" in s or "4 POSTE" in s
    ):
        return "CU4"
    if ("MOYENNE UTILISATION" in s or " MU " in s) and (
        "PLEINE" in s or "CREUSE" in s or "HP" in s or "HC" in s or "4 POSTE" in s
    ):
        return "MU4"
    if "LONGUE UTILISATION" in s or " LU " in s:
        return "LU"
    if "COURTE UTILISATION" in s or " CU " in s:
        return "CU"
    if "MOYENNE UTILISATION" in s or " MU " in s:
        return "MU"
    if "BASE" in s:
        return "BASE"
    if "HP" in s or "HC" in s or "HEURE PLEINE" in s or "HEURE CREUSE" in s:
        return "HPHC"
    if "C2" in s:
        return "C2"
    if "C4" in s:
        return "C4"
    if "LU" in s:
        return "LU"
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
            by_supplier[supplier] = {"prm_ids": [], "tariff_codes": {}}
        if uid:
            by_supplier[supplier]["prm_ids"].append(uid)
        by_supplier[supplier]["tariff_codes"][code] = label

    configs = {c.supplier: c for c in db.query(BillingConfig).filter_by(city_id=city_id).all()}

    result = []
    for supplier, data in sorted(by_supplier.items()):
        cfg = configs.get(supplier)
        result.append(
            {
                "supplier": supplier,
                "prm_count": len(data["prm_ids"]),
                "prm_ids": data["prm_ids"],
                "tariff_codes": sorted(data["tariff_codes"].keys()),
                "config_id": cfg.id if cfg else None,
                "lot": cfg.lot if cfg else None,
                "has_hphc": cfg.has_hphc if cfg else False,
                "is_configured": cfg is not None and cfg.representative_prm_id is not None,
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
    has_hphc: bool,
    representative_prm_id: str | None,
) -> BillingConfig:
    cfg = db.query(BillingConfig).filter_by(city_id=city_id, supplier=supplier).first()
    if cfg:
        if lot is not None:
            cfg.lot = lot
        cfg.has_hphc = has_hphc
        if representative_prm_id is not None:
            cfg.representative_prm_id = representative_prm_id
    else:
        cfg = BillingConfig(
            city_id=city_id,
            supplier=supplier,
            tariff_code=None,
            lot=lot,
            has_hphc=has_hphc,
            representative_prm_id=representative_prm_id,
        )
        db.add(cfg)
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
    db.commit()
    db.refresh(cfg)
    return cfg


def delete_config(db: Session, cfg: BillingConfig) -> None:
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
