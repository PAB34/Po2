from sqlalchemy import select, func as sa_func
from sqlalchemy.orm import Session

from app.models.equipment import BuildingEquipment, EquipmentReference
from app.schemas.equipment import (
    BuildingEquipmentBulkItem,
    BuildingEquipmentCreate,
    BuildingEquipmentUpdate,
    ETAT_COEFFICIENTS,
    EquipmentStateCounts,
)


def _compute_remaining_life(ref: EquipmentReference, etat: str) -> float:
    ref_years = ref.sypemi_reference_annees or 0
    coeff = ETAT_COEFFICIENTS.get(etat, 0.0)
    return round(ref_years * coeff, 1)


def list_equipment_references(db: Session) -> list[EquipmentReference]:
    statement = select(EquipmentReference).order_by(
        EquipmentReference.code_niveau_1,
        EquipmentReference.code_niveau_2,
        EquipmentReference.id_ligne,
    )
    return list(db.scalars(statement))


def get_equipment_ref_or_none(db: Session, ref_id: int) -> EquipmentReference | None:
    return db.scalar(select(EquipmentReference).where(EquipmentReference.id == ref_id))


def list_building_equipments(db: Session, building_id: int) -> list[dict]:
    statement = (
        select(BuildingEquipment, EquipmentReference)
        .join(EquipmentReference, BuildingEquipment.equipment_ref_id == EquipmentReference.id)
        .where(BuildingEquipment.building_id == building_id)
        .order_by(EquipmentReference.code_niveau_1, EquipmentReference.code_niveau_2, EquipmentReference.id_ligne)
    )
    results = db.execute(statement).all()
    items = []
    for be, er in results:
        item = {
            "id": be.id,
            "building_id": be.building_id,
            "equipment_ref_id": be.equipment_ref_id,
            "etat": be.etat,
            "quantite": be.quantite,
            "commentaire": be.commentaire,
            "duree_vie_restante": be.duree_vie_restante,
            "created_at": be.created_at,
            "updated_at": be.updated_at,
            "equipment_ref": {
                "id": er.id,
                "id_ligne": er.id_ligne,
                "code_niveau_1": er.code_niveau_1,
                "libelle_niveau_1": er.libelle_niveau_1,
                "code_niveau_2": er.code_niveau_2,
                "libelle_niveau_2": er.libelle_niveau_2,
                "niveau_3": er.niveau_3,
                "niveau_4": er.niveau_4,
                "niveau_5": er.niveau_5,
                "equipement": er.equipement,
                "sypemi_mini_annees": er.sypemi_mini_annees,
                "sypemi_reference_annees": er.sypemi_reference_annees,
                "sypemi_maxi_annees": er.sypemi_maxi_annees,
                "fiche_cee": er.fiche_cee,
            },
        }
        items.append(item)
    return items


def create_building_equipment(
    db: Session, building_id: int, payload: BuildingEquipmentCreate
) -> BuildingEquipment:
    ref = get_equipment_ref_or_none(db, payload.equipment_ref_id)
    if ref is None:
        raise ValueError(f"Référence équipement {payload.equipment_ref_id} introuvable.")
    remaining = _compute_remaining_life(ref, payload.etat.value)
    be = BuildingEquipment(
        building_id=building_id,
        equipment_ref_id=payload.equipment_ref_id,
        etat=payload.etat.value,
        quantite=payload.quantite.value,
        commentaire=payload.commentaire,
        duree_vie_restante=remaining,
    )
    db.add(be)
    db.commit()
    db.refresh(be)
    return be


def bulk_create_building_equipments(
    db: Session, building_id: int, items: list[BuildingEquipmentBulkItem]
) -> list[BuildingEquipment]:
    refs_ids = [item.equipment_ref_id for item in items]
    refs_stmt = select(EquipmentReference).where(EquipmentReference.id.in_(refs_ids))
    refs_map = {r.id: r for r in db.scalars(refs_stmt)}

    created = []
    for item in items:
        ref = refs_map.get(item.equipment_ref_id)
        if ref is None:
            raise ValueError(f"Référence équipement {item.equipment_ref_id} introuvable.")
        remaining = _compute_remaining_life(ref, item.etat.value)
        be = BuildingEquipment(
            building_id=building_id,
            equipment_ref_id=item.equipment_ref_id,
            etat=item.etat.value,
            quantite=item.quantite.value,
            commentaire=item.commentaire,
            duree_vie_restante=remaining,
        )
        db.add(be)
        created.append(be)
    db.commit()
    for be in created:
        db.refresh(be)
    return created


def update_building_equipment(
    db: Session, be: BuildingEquipment, payload: BuildingEquipmentUpdate
) -> BuildingEquipment:
    ref = get_equipment_ref_or_none(db, be.equipment_ref_id)
    if payload.etat is not None:
        be.etat = payload.etat.value
    if payload.quantite is not None:
        be.quantite = payload.quantite.value
    if payload.commentaire is not None:
        be.commentaire = payload.commentaire
    if ref is not None:
        be.duree_vie_restante = _compute_remaining_life(ref, be.etat)
    db.commit()
    db.refresh(be)
    return be


def delete_building_equipment(db: Session, be: BuildingEquipment) -> None:
    db.delete(be)
    db.commit()


def get_building_equipment_or_none(
    db: Session, building_id: int, equipment_id: int
) -> BuildingEquipment | None:
    return db.scalar(
        select(BuildingEquipment).where(
            BuildingEquipment.id == equipment_id,
            BuildingEquipment.building_id == building_id,
        )
    )


def compute_building_equipment_summary(db: Session, building_id: int) -> EquipmentStateCounts:
    statement = select(BuildingEquipment).where(BuildingEquipment.building_id == building_id)
    equipments = list(db.scalars(statement))
    counts = EquipmentStateCounts()
    if not equipments:
        return counts

    total_ratio = 0.0
    refs_cache: dict[int, EquipmentReference | None] = {}

    for eq in equipments:
        counts.total += 1
        if eq.etat == "obsolete":
            counts.obsolete += 1
        elif eq.etat == "degrade":
            counts.degrade += 1
        elif eq.etat == "moyen":
            counts.moyen += 1
        elif eq.etat == "neuf":
            counts.neuf += 1

        if eq.equipment_ref_id not in refs_cache:
            refs_cache[eq.equipment_ref_id] = get_equipment_ref_or_none(db, eq.equipment_ref_id)
        ref = refs_cache[eq.equipment_ref_id]
        ref_years = ref.sypemi_reference_annees if ref else 0
        if ref_years and ref_years > 0:
            total_ratio += eq.duree_vie_restante / ref_years
        else:
            total_ratio += 0

    counts.score_sante = round((total_ratio / counts.total) * 100, 1) if counts.total > 0 else None
    return counts


def compute_all_buildings_summaries(db: Session, building_ids: list[int]) -> dict[int, EquipmentStateCounts]:
    if not building_ids:
        return {}

    statement = (
        select(BuildingEquipment, EquipmentReference)
        .join(EquipmentReference, BuildingEquipment.equipment_ref_id == EquipmentReference.id)
        .where(BuildingEquipment.building_id.in_(building_ids))
    )
    results = db.execute(statement).all()

    summaries: dict[int, EquipmentStateCounts] = {}
    for be, er in results:
        if be.building_id not in summaries:
            summaries[be.building_id] = EquipmentStateCounts()
        counts = summaries[be.building_id]
        counts.total += 1
        if be.etat == "obsolete":
            counts.obsolete += 1
        elif be.etat == "degrade":
            counts.degrade += 1
        elif be.etat == "moyen":
            counts.moyen += 1
        elif be.etat == "neuf":
            counts.neuf += 1

        ref_years = er.sypemi_reference_annees or 0

    for bid, counts in summaries.items():
        pass

    for bid in summaries:
        counts = summaries[bid]
        total_ratio = 0.0
        count = 0
        for be, er in results:
            if be.building_id == bid:
                ref_years = er.sypemi_reference_annees or 0
                if ref_years > 0:
                    total_ratio += be.duree_vie_restante / ref_years
                count += 1
        counts.score_sante = round((total_ratio / count) * 100, 1) if count > 0 else None

    return summaries
