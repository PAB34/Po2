"""Persistance en base des donnees d'import DALKIA."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cpe import CpeContractReference, CpeSite
from app.models.cpe_dalkia import (
    CpeDalkiaRefApe,
    CpeDalkiaRefBpu,
    CpeDalkiaRefCible,
    CpeDalkiaRefImport,
    CpeDalkiaRefP1Gaz,
    CpeDalkiaRefP1Tarif,
    CpeDalkiaRefP2P3,
    CpeDalkiaRefRecap,
    CpeDalkiaRefSite,
)
from app.models.user import User
from app.services.cpe_dalkia_import import DalkiaParseResult

P1_GAZ_ACOMPTE_KIND = "p1_gaz_acompte"


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


def get_bpu_for_import(
    db: Session, import_id: int, categorie: str | None = None
) -> list[CpeDalkiaRefBpu]:
    stmt = select(CpeDalkiaRefBpu).where(CpeDalkiaRefBpu.import_id == import_id)
    if categorie is not None:
        stmt = stmt.where(CpeDalkiaRefBpu.categorie == categorie)
    return list(db.scalars(stmt.order_by(CpeDalkiaRefBpu.categorie, CpeDalkiaRefBpu.code)))


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

    # P1 gaz : composants de prix + coefficients de revision par tarif (en-tete Annexe 6)
    for trf in result.p1_tarifs:
        db.add(CpeDalkiaRefP1Tarif(
            import_id=batch.id,
            city_id=city_id,
            type_tarif=trf.type_tarif,
            p0_fournisseur=trf.p0_fournisseur,
            ref_peg=trf.ref_peg,
            terme_acheminement=trf.terme_acheminement,
            obligation_cee=trf.obligation_cee,
            ticgn=trf.ticgn,
            marge_exploitant_pct=trf.marge_exploitant_pct,
            prix_unitaire_ht=trf.prix_unitaire_ht,
            coef_a=trf.coef_a, coef_b=trf.coef_b, coef_c=trf.coef_c,
            coef_d=trf.coef_d, coef_e=trf.coef_e,
        ))

    # BPU travaux P3 (Annexe 7) — catalogue
    for b in result.bpu_rows:
        db.add(CpeDalkiaRefBpu(
            import_id=batch.id,
            city_id=city_id,
            categorie=b.categorie,
            famille=b.famille,
            code=b.code,
            libelle=b.libelle,
            specificite=b.specificite,
            unite=b.unite,
            cout_unitaire=b.cout_unitaire,
            cout_nuit=b.cout_nuit,
            cout_samedi=b.cout_samedi,
            cout_dimanche=b.cout_dimanche,
            coefficient=b.coefficient,
            coefficient_max=b.coefficient_max,
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


BPU_P2P3_POSTES = ("P2", "P2-4", "P3", "P3-4")


def normalize_p2p3_poste(billed_item: str | None) -> str:
    """Normalise un billed_item P2/P3 : majuscules, point -> tiret (P2.4 == P2-4)."""
    return (billed_item or "").strip().upper().replace(".", "-")


def resolve_dalkia_p2p3_forfait(
    db: Session, *, code_site: str, year: int, billed_item: str, city_id: int | None
) -> float | None:
    """Forfait contractuel annuel (base) P2/P3 du référentiel DALKIA actif, ou None.

    Correspondance billed_item ↔ colonne, validée sur données réelles (VDS-ENS 01 2026) :
      - P2   → p2_total_ht − p2_4_ht  (P2 récurrent = P2.1+P2.2+P2.3, hors P2.4)
      - P2-4 → p2_4_ht                (P2.4, objectifs)
      - P3   → p3_total_ht − p3_4_ht  (P3 récurrent, hors travaux obligatoires)
      - P3-4 → p3_4_ht                (P3.4, travaux obligatoires)
    Les autres postes facturés (P2-11, P2-2, P1, P1EAU…) n'ont pas de correspondance dans le
    référentiel (4 buckets P2 + 4 P3) → retourne None : ils ne sont pas contrôlés.
    """
    item = normalize_p2p3_poste(billed_item)
    if item not in BPU_P2P3_POSTES:
        return None
    stmt = (
        select(CpeDalkiaRefP2P3)
        .join(CpeDalkiaRefImport, CpeDalkiaRefP2P3.import_id == CpeDalkiaRefImport.id)
        .where(
            CpeDalkiaRefImport.is_active.is_(True),
            CpeDalkiaRefP2P3.code_site == code_site,
            CpeDalkiaRefP2P3.period_year == year,
        )
    )
    if city_id is not None:
        stmt = stmt.where(CpeDalkiaRefImport.city_id == city_id)
    row = db.scalars(stmt).first()
    if row is None:
        return None
    if item == "P2-4":
        return row.p2_4_ht
    if item == "P3-4":
        return row.p3_4_ht
    if item == "P2":
        return None if row.p2_total_ht is None else round(row.p2_total_ht - (row.p2_4_ht or 0.0), 2)
    # item == "P3"
    return None if row.p3_total_ht is None else round(row.p3_total_ht - (row.p3_4_ht or 0.0), 2)


def _derive_categorie(code_site: str) -> str:
    """Catégorie d'un site CPE déduite de son code (ENS/SPORT/BAM/CULT/PSC/CCAS)."""
    c = (code_site or "").upper()
    for key in ("SPORT", "ENS", "BAM", "CULT", "PSC", "CCAS"):
        if key in c:
            return key
    return "AUTRE"


def sync_cpe_sites_from_dalkia(db: Session, *, city_id: int | None, ref_year: int = 2026) -> dict:
    """Crée / met à jour `cpe_sites` (volet performance) depuis le référentiel DALKIA actif.

    Source unique = imports DALKIA actifs : `cpe_dalkia_ref_sites` (code, nom, lot),
    `cpe_dalkia_ref_cibles` (NB gaz/élec, DJU, qECS de `ref_year`), `cpe_dalkia_ref_p1_gaz`
    (tarif, PCE). Upsert idempotent par `code_site` — réexécutable après chaque avenant.

    Comme `cpe_sites.code_site` provient du même référentiel que `cpe_dalkia_ref_cibles`,
    le NB par année (`resolve_nb_for_year`) sera systématiquement aligné (badge DLK).
    """
    imp_stmt = select(CpeDalkiaRefImport).where(CpeDalkiaRefImport.is_active.is_(True))
    if city_id is not None:
        imp_stmt = imp_stmt.where(CpeDalkiaRefImport.city_id == city_id)
    imports = list(db.scalars(imp_stmt))

    created: list[str] = []
    updated: list[str] = []

    for imp in imports:
        for rs in db.scalars(select(CpeDalkiaRefSite).where(CpeDalkiaRefSite.import_id == imp.id)):
            def _cible(fluid: str):
                return db.scalars(select(CpeDalkiaRefCible).where(
                    CpeDalkiaRefCible.import_id == imp.id,
                    CpeDalkiaRefCible.code_site == rs.code_site,
                    CpeDalkiaRefCible.fluid == fluid,
                    CpeDalkiaRefCible.period_year == ref_year,
                )).first()

            cible_gaz = _cible("GAZ")
            cible_elec = _cible("ELEC")
            p1 = db.scalars(select(CpeDalkiaRefP1Gaz).where(
                CpeDalkiaRefP1Gaz.import_id == imp.id,
                CpeDalkiaRefP1Gaz.code_site == rs.code_site,
            )).first()
            pce = (p1.pce if p1 else None)
            if pce in ("-", ""):
                pce = None

            fields = dict(
                city_id=rs.city_id if rs.city_id is not None else city_id,
                nom_site=rs.nom_batiment or rs.code_site,
                categorie=_derive_categorie(rs.code_site),
                nb_mwh_pci=(cible_gaz.nb_mwhpci if cible_gaz and cible_gaz.nb_mwhpci is not None else 0.0),
                cible_elec_mwh=(cible_elec.nb_mwhpci if cible_elec else None),
                tarif=(p1.type_tarif if p1 else None),
                pce=pce,
                dju_reference=(cible_gaz.dju_reference if cible_gaz and cible_gaz.dju_reference else 1426.0),
                q_ecs_mwh_pci_per_m3=(cible_gaz.q_ecs if cible_gaz else None),
                actif=True,
            )

            existing = db.scalars(select(CpeSite).where(CpeSite.code_site == rs.code_site)).first()
            if existing is not None:
                for k, v in fields.items():
                    setattr(existing, k, v)
                db.add(existing)
                updated.append(rs.code_site)
            else:
                db.add(CpeSite(code_site=rs.code_site, **fields))
                created.append(rs.code_site)

    db.commit()
    return {"created": len(created), "updated": len(updated), "total": len(created) + len(updated)}


def resolve_p1_gaz_tarif(db: Session, *, code_site: str, city_id: int | None) -> str | None:
    """Type de tarif gaz (T1..T4) d'un site depuis l'import DALKIA actif (Annexe 6), ou None."""
    stmt = (
        select(CpeDalkiaRefP1Gaz.type_tarif)
        .join(CpeDalkiaRefImport, CpeDalkiaRefP1Gaz.import_id == CpeDalkiaRefImport.id)
        .where(
            CpeDalkiaRefImport.is_active.is_(True),
            CpeDalkiaRefP1Gaz.code_site == code_site,
            CpeDalkiaRefP1Gaz.type_tarif.is_not(None),
        )
    )
    if city_id is not None:
        stmt = stmt.where(CpeDalkiaRefImport.city_id == city_id)
    return db.scalars(stmt).first()


def sync_p1_reference_from_recap(db: Session, import_batch: CpeDalkiaRefImport) -> dict:
    """Met a jour la reference contractuelle d'acompte P1 gaz depuis le RECAP MARCHE.

    Lit `cpe_dalkia_ref_recap` (metric `p1_total_ht`) par annee pour l'import donne et
    upsert `cpe_contract_references` (kind `p1_gaz_acompte`) consommee par le controle
    `_control_p1_gaz_acompte_against_dpgf`. Decision : le RECAP fait foi (le fichier DALKIA
    sera maintenu a jour), donc l'annual_amount_ht est ecrase par la valeur RECAP.

    Les metadonnees (contract_code, billed_item, installment_count, tolerances, formule)
    sont clonees depuis une reference P1 existante de la commune : on ne devine jamais le
    contract_code. Sans reference modele, on n'ecrit rien et on retourne une erreur explicite.
    """
    city_id = import_batch.city_id

    # 1. Montants P1 par annee depuis le RECAP de cet import
    recap_stmt = select(CpeDalkiaRefRecap).where(
        CpeDalkiaRefRecap.import_id == import_batch.id,
        CpeDalkiaRefRecap.metric == "p1_total_ht",
        CpeDalkiaRefRecap.period_year.is_not(None),
        CpeDalkiaRefRecap.value.is_not(None),
    )
    amounts_by_year: dict[int, float] = {}
    for row in db.scalars(recap_stmt):
        # Defensif : si plusieurs lignes pour une annee, on garde la plus grande valeur.
        prev = amounts_by_year.get(row.period_year)
        if prev is None or row.value > prev:
            amounts_by_year[row.period_year] = row.value

    if not amounts_by_year:
        return {
            "ok": False,
            "reason": "no_recap_p1",
            "message": "Aucun montant P1 (p1_total_ht) dans le RECAP de cet import (normal pour le Lot 2 sans gaz).",
            "updated": [], "created": [],
        }

    # 2. Reference modele existante (ne jamais inventer le contract_code)
    tmpl_stmt = select(CpeContractReference).where(
        CpeContractReference.reference_kind == P1_GAZ_ACOMPTE_KIND,
        CpeContractReference.market == "P1",
    )
    if city_id is not None:
        tmpl_stmt = tmpl_stmt.where(CpeContractReference.city_id == city_id)
    template = db.scalars(
        tmpl_stmt.order_by(CpeContractReference.active.desc(), CpeContractReference.year.desc())
    ).first()

    if template is None:
        return {
            "ok": False,
            "reason": "no_template",
            "message": (
                "Aucune reference P1 (p1_gaz_acompte) existante pour cette commune : "
                "creer d'abord la reference contractuelle (contract_code, postes inclus) "
                "depuis le module CPE, puis relancer la synchronisation."
            ),
            "updated": [], "created": [],
        }

    note = f"Synchronise depuis RECAP MARCHE (import #{import_batch.id}) le {datetime.utcnow():%Y-%m-%d}"
    updated: list[int] = []
    created: list[int] = []

    for year, amount in sorted(amounts_by_year.items()):
        existing = db.scalars(
            select(CpeContractReference).where(
                CpeContractReference.city_id == city_id,
                CpeContractReference.contract_code == template.contract_code,
                CpeContractReference.reference_kind == P1_GAZ_ACOMPTE_KIND,
                CpeContractReference.year == year,
                CpeContractReference.market == "P1",
                CpeContractReference.billed_item == template.billed_item,
            )
        ).first()
        if existing is not None:
            existing.annual_amount_ht = round(amount, 2)
            existing.notes = note
            db.add(existing)
            updated.append(year)
        else:
            db.add(CpeContractReference(
                city_id=city_id,
                contract_code=template.contract_code,
                contract_label=template.contract_label,
                reference_kind=P1_GAZ_ACOMPTE_KIND,
                year=year,
                market="P1",
                billed_item=template.billed_item,
                annual_amount_ht=round(amount, 2),
                expected_amount_ht=None,
                installment_count=template.installment_count or 4,
                expected_period_months=template.expected_period_months or "3,6,9",
                included_billed_items=template.included_billed_items,
                formula=template.formula,
                tolerance_pct=template.tolerance_pct,
                tolerance_eur=template.tolerance_eur,
                active=True,
                notes=note,
            ))
            created.append(year)

    db.commit()
    return {
        "ok": True,
        "contract_code": template.contract_code,
        "billed_item": template.billed_item,
        "updated": updated,
        "created": created,
        "amounts_by_year": {str(y): round(a, 2) for y, a in sorted(amounts_by_year.items())},
        "message": f"{len(updated)} reference(s) mise(s) a jour, {len(created)} creee(s) depuis le RECAP.",
    }
