"""Persistance en base des donnees d'import DALKIA."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cpe_dalkia import (
    CpeDalkiaRefApe,
    CpeDalkiaRefCible,
    CpeDalkiaRefImport,
    CpeDalkiaRefP1Gaz,
    CpeDalkiaRefP2P3,
    CpeDalkiaRefRecap,
    CpeDalkiaRefSite,
)
from app.models.user import User
from app.services.cpe_dalkia_import import DalkiaParseResult


def get_active_imports(db: Session, current_user: User) -> list[CpeDalkiaRefImport]:
    stmt = select(CpeDalkiaRefImport).where(CpeDalkiaRefImport.is_active.is_(True))
    if current_user.city_id is not None:
        stmt = stmt.where(CpeDalkiaRefImport.city_id == current_user.city_id)
    return list(db.scalars(stmt.order_by(CpeDalkiaRefImport.import_date.desc())))


def get_import_by_id(db: Session, import_id: int, current_user: User) -> CpeDalkiaRefImport | None:
    stmt = select(CpeDalkiaRefImport).where(CpeDalkiaRefImport.id == import_id)
    if current_user.city_id is not None:
        stmt = stmt.where(CpeDalkiaRefImport.city_id == current_user.city_id)
    return db.scalar(stmt)


def get_sites_for_import(db: Session, import_id: int) -> list[CpeDalkiaRefSite]:
    return list(db.scalars(
        select(CpeDalkiaRefSite)
        .where(CpeDalkiaRefSite.import_id == import_id)
        .order_by(CpeDalkiaRefSite.code_site)
    ))


def get_p2p3_for_import(
    db: Session, import_id: int, period_year: int | None = None
) -> list[CpeDalkiaRefP2P3]:
    stmt = select(CpeDalkiaRefP2P3).where(CpeDalkiaRefP2P3.import_id == import_id)
    if period_year is not None:
        stmt = stmt.where(CpeDalkiaRefP2P3.period_year == period_year)
    return list(db.scalars(stmt.order_by(CpeDalkiaRefP2P3.code_site, CpeDalkiaRefP2P3.period_idx)))


def get_cibles_for_import(
    db: Session, import_id: int, fluid: str | None = None, period_year: int | None = None
) -> list[CpeDalkiaRefCible]:
    stmt = select(CpeDalkiaRefCible).where(CpeDalkiaRefCible.import_id == import_id)
    if fluid is not None:
        stmt = stmt.where(CpeDalkiaRefCible.fluid == fluid)
    if period_year is not None:
        stmt = stmt.where(CpeDalkiaRefCible.period_year == period_year)
    return list(db.scalars(stmt.order_by(CpeDalkiaRefCible.code_site, CpeDalkiaRefCible.fluid, CpeDalkiaRefCible.period_idx)))


def get_ape_for_import(db: Session, import_id: int) -> list[CpeDalkiaRefApe]:
    return list(db.scalars(
        select(CpeDalkiaRefApe)
        .where(CpeDalkiaRefApe.import_id == import_id)
        .order_by(CpeDalkiaRefApe.code_site)
    ))


def get_recap_for_import(
    db: Session, import_id: int, section: str | None = None
) -> list[CpeDalkiaRefRecap]:
    stmt = select(CpeDalkiaRefRecap).where(CpeDalkiaRefRecap.import_id == import_id)
    if section is not None:
        stmt = stmt.where(CpeDalkiaRefRecap.section == section)
    return list(db.scalars(stmt.order_by(
        CpeDalkiaRefRecap.section, CpeDalkiaRefRecap.category,
        CpeDalkiaRefRecap.metric, CpeDalkiaRefRecap.period_year,
    )))


def persist_dalkia_import(
    db: Session,
    result: DalkiaParseResult,
    current_user: User,
    deactivate_previous: bool = True,
) -> CpeDalkiaRefImport:
    """
    Persiste un import DALKIA en base.
    Si deactivate_previous=True, les imports precedents du meme lot sont marques is_active=False.
    Les donnees de l'import precedent actif sont conservees (pour audit), seule la mise a jour
    des references actives est effectuee via is_active.
    """
    city_id = current_user.city_id

    if deactivate_previous:
        prev_stmt = (
            select(CpeDalkiaRefImport)
            .where(
                CpeDalkiaRefImport.lot == result.lot,
                CpeDalkiaRefImport.is_active.is_(True),
            )
        )
        if city_id is not None:
            prev_stmt = prev_stmt.where(CpeDalkiaRefImport.city_id == city_id)
        for prev in db.scalars(prev_stmt):
            prev.is_active = False
            db.add(prev)

    batch = CpeDalkiaRefImport(
        city_id=city_id,
        lot=result.lot,
        filename=result.filename,
        nb_sites=len(result.sites),
        nb_p2p3_rows=len(result.p2p3_rows),
        nb_cibles_rows=len(result.cibles_gaz) + len(result.cibles_elec),
        nb_p1_gaz_rows=len(result.p1_gaz),
        nb_ape_rows=len(result.ape_rows),
        nb_recap_rows=len(result.recap_rows),
        is_active=True,
        notes=f"Warnings: {len(result.warnings)}" if result.warnings else None,
    )
    db.add(batch)
    db.flush()  # obtenir batch.id

    # Sites
    for site in result.sites:
        db.add(CpeDalkiaRefSite(
            import_id=batch.id,
            city_id=city_id,
            lot=site.lot,
            code_site=site.code_site,
            nom_batiment=site.nom_batiment,
            entite=site.entite,
            lot_label=site.lot_label,
        ))

    # P2/P3
    for row in result.p2p3_rows:
        db.add(CpeDalkiaRefP2P3(
            import_id=batch.id,
            city_id=city_id,
            code_site=row.code_site,
            period_idx=row.period_idx,
            period_label=row.period_label,
            period_year=row.period_year,
            p2_1_ht=row.p2_1_ht, p2_2_ht=row.p2_2_ht, p2_3_ht=row.p2_3_ht,
            p2_4_ht=row.p2_4_ht, p2_total_ht=row.p2_total_ht,
            p3_1_ht=row.p3_1_ht, p3_2_ht=row.p3_2_ht, p3_3_ht=row.p3_3_ht,
            p3_4_ht=row.p3_4_ht, p3_total_ht=row.p3_total_ht,
        ))

    # Cibles GAZ + ELEC
    for row in result.cibles_gaz + result.cibles_elec:
        db.add(CpeDalkiaRefCible(
            import_id=batch.id,
            city_id=city_id,
            code_site=row.code_site,
            fluid=row.fluid,
            period_idx=row.period_idx,
            period_label=row.period_label,
            period_year=row.period_year,
            ref_globale_mwhpci=row.ref_globale_mwhpci,
            ref_qt_mwhpci=row.ref_qt_mwhpci,
            dju_reference=row.dju_reference,
            qt_global_mwhpci=row.qt_global_mwhpci,
            nb_mwhpci=row.nb_mwhpci,
            q_ecs=row.q_ecs,
            qt_ecs=row.qt_ecs,
        ))

    # P1 gaz
    for row in result.p1_gaz:
        db.add(CpeDalkiaRefP1Gaz(
            import_id=batch.id,
            city_id=city_id,
            code_site=row.code_site,
            pce=row.pce,
            type_tarif=row.type_tarif,
            prix_unitaire_ht=row.prix_unitaire_ht,
            atrd_ht=row.atrd_ht,
            cta_ht=row.cta_ht,
            p10_fixe_ht=row.p10_fixe_ht,
            period_idx=row.period_idx,
            period_label=row.period_label,
            period_year=row.period_year,
            qt_mwhpcs=row.qt_mwhpcs,
            p10_var_ht=row.p10_var_ht,
            p10_total_ht=row.p10_total_ht,
        ))

    # APE
    for row in result.ape_rows:
        db.add(CpeDalkiaRefApe(
            import_id=batch.id,
            city_id=city_id,
            code_site=row.code_site,
            nom_batiment=row.nom_batiment,
            situation_initiale_mwhpci=row.situation_initiale_mwhpci,
            description_ape=row.description_ape,
            annee_achevement=row.annee_achevement,
            montant_ape_ht=row.montant_ape_ht,
            cee_mwh_cumac=row.cee_mwh_cumac,
            cee_eur=row.cee_eur,
            subvention_ht=row.subvention_ht,
            gain_energetique_mwhpci=row.gain_energetique_mwhpci,
            situation_nouvelle_mwhpci=row.situation_nouvelle_mwhpci,
            annee_engagement_nouvelle_cible=row.annee_engagement_nouvelle_cible,
            emission_co2_evitee=row.emission_co2_evitee,
            production_enr_auto_mwh=row.production_enr_auto_mwh,
            production_enr_vendue_mwh=row.production_enr_vendue_mwh,
            recette_vente_energie_ht=row.recette_vente_energie_ht,
            ratio_ht_mwhpci=row.ratio_ht_mwhpci,
            commentaires=row.commentaires,
        ))

    # RECAP MARCHE (recapitulatif financier global)
    for row in result.recap_rows:
        db.add(CpeDalkiaRefRecap(
            import_id=batch.id,
            city_id=city_id,
            section=row.section,
            category=row.category,
            metric=row.metric,
            metric_label=row.metric_label,
            period_year=row.period_year,
            period_label=row.period_label,
            value=row.value,
            unit=row.unit,
        ))

    db.commit()
    db.refresh(batch)
    return batch
