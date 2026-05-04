from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.billing import (
    BillingConfigCreate,
    BillingConfigOut,
    BillingConfigPatch,
    BillingGroupItem,
    BillingHphcSlotIn,
    BillingHphcSlotOut,
    BillingPriceEntryIn,
    BillingPriceEntryOut,
)
from app.services.billing import (
    create_config,
    delete_config,
    get_billing_groups,
    get_config,
    get_configs,
    get_hphc_slots,
    get_prices,
    patch_config,
    replace_hphc_slots,
    replace_prices,
)

router = APIRouter(prefix="/billing", tags=["billing"])


def _require_city(user: User) -> int:
    if user.city_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Utilisateur sans ville associée")
    return user.city_id


def _get_cfg_or_404(db: Session, config_id: int, city_id: int):
    cfg = get_config(db, config_id, city_id)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration introuvable")
    return cfg


@router.get("/groups", response_model=list[BillingGroupItem])
def list_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return get_billing_groups(db, city_id)


@router.get("/configs", response_model=list[BillingConfigOut])
def list_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return get_configs(db, city_id)


@router.post("/configs", response_model=BillingConfigOut, status_code=status.HTTP_201_CREATED)
def create_billing_config(
    payload: BillingConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return create_config(db, city_id, payload.supplier, payload.tariff_code, payload.tariff_label, payload.has_hphc, payload.representative_prm_id)


@router.patch("/configs/{config_id}", response_model=BillingConfigOut)
def update_billing_config(
    config_id: int,
    payload: BillingConfigPatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    cfg = _get_cfg_or_404(db, config_id, city_id)
    return patch_config(db, cfg, payload.has_hphc, payload.representative_prm_id, payload.tariff_label)


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_billing_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    cfg = _get_cfg_or_404(db, config_id, city_id)
    delete_config(db, cfg)


@router.get("/configs/{config_id}/prices", response_model=list[BillingPriceEntryOut])
def list_prices(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return get_prices(db, config_id)


@router.put("/configs/{config_id}/prices", response_model=list[BillingPriceEntryOut])
def set_prices(
    config_id: int,
    entries: list[BillingPriceEntryIn],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return replace_prices(db, config_id, [e.model_dump() for e in entries])


@router.get("/configs/{config_id}/hphc-slots", response_model=list[BillingHphcSlotOut])
def list_hphc_slots(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return get_hphc_slots(db, config_id)


@router.put("/configs/{config_id}/hphc-slots", response_model=list[BillingHphcSlotOut])
def set_hphc_slots(
    config_id: int,
    slots: list[BillingHphcSlotIn],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return replace_hphc_slots(db, config_id, [s.model_dump() for s in slots])
