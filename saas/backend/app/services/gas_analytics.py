"""
Analytics gaz — suivi temporel et rapprochement avec le P1 GAZ DALKIA.

Deux usages métier (besoin utilisateur) :

1. **Suivi temporel** : `monthly_series()` agrège les relevés `gas_consumptions`
   (GRDF) par mois, par PCE ou par bâtiment.

2. **Rapprochement P1** : `reconcile_p1()` compare, par PCE × année, la
   consommation réelle GRDF à la quantité contractuelle facturée dans le P1 GAZ
   DALKIA (`cpe_dalkia_ref_p1_gaz.qt_mwhpcs`).

⚠️ **Unités** — point clé validé contre les modèles : GRDF restitue l'`energie`
en **kWh PCS** ; la quantité P1 DALKIA (`qt_mwhpcs`) est en **MWh PCS**. Les deux
sont donc directement comparables via `kWh / 1000`. La conversion PCS→PCI
(`grdf_pcs_to_pci`) ne sert que pour comparer à une cible NB (MWh PCI), pas au P1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cpe import CpeConsoReleve, CpeSite
from app.models.cpe_dalkia import CpeDalkiaRefImport, CpeDalkiaRefP1Gaz
from app.models.gas import GasConsumption, GasPce


@dataclass
class MonthlyPoint:
    annee: int
    mois: int
    energie_kwh: int
    mwh_pcs: float


@dataclass
class MonthlySeries:
    id_pce: str
    nom_site: str | None
    points: list[MonthlyPoint] = field(default_factory=list)
    total_kwh: int = 0


def monthly_series(
    db: Session,
    city_id: int | None,
    id_pce: str | None = None,
    building_id: int | None = None,
    type_conso: str = "Publiée",
) -> list[MonthlySeries]:
    """Série mensuelle de consommation GRDF, par PCE.

    Filtre optionnel par `id_pce` ou par `building_id` (via `gas_pces`).
    """
    pce_q = db.query(GasPce).filter(GasPce.city_id == city_id)
    if id_pce:
        pce_q = pce_q.filter(GasPce.id_pce == id_pce)
    if building_id is not None:
        pce_q = pce_q.filter(GasPce.building_id == building_id)
    pces = pce_q.all()

    out: list[MonthlySeries] = []
    for pce in pces:
        rows = (
            db.query(GasConsumption)
            .filter(
                GasConsumption.pce_id == pce.id,
                GasConsumption.type_conso == type_conso,
                GasConsumption.energie_kwh.isnot(None),
            )
            .order_by(GasConsumption.date_debut)
            .all()
        )
        buckets: dict[tuple[int, int], int] = {}
        for r in rows:
            key = (r.date_debut.year, r.date_debut.month)
            buckets[key] = buckets.get(key, 0) + (r.energie_kwh or 0)
        points = [
            MonthlyPoint(annee=y, mois=m, energie_kwh=kwh, mwh_pcs=round(kwh / 1000.0, 3))
            for (y, m), kwh in sorted(buckets.items())
        ]
        out.append(
            MonthlySeries(
                id_pce=pce.id_pce,
                nom_site=pce.nom_site,
                points=points,
                total_kwh=sum(p.energie_kwh for p in points),
            )
        )
    return out


@dataclass
class P1ReconcileItem:
    id_pce: str
    code_site: str | None
    nom_site: str | None
    grdf_mwh_pcs: float          # mesuré GRDF (kWh/1000)
    dalkia_p1_qt_mwhpcs: float | None  # quantité contractuelle P1 (MWh PCS)
    dalkia_conso_mwh: float | None     # conso déclarée DALKIA (cpe_conso_releves GAZ)
    p1_total_ht: float | None
    ecart_mwh: float | None
    ecart_pct: float | None
    statut: str                  # ok | ecart | blocked


def _grdf_year_mwh_pcs(db: Session, pce_id: int, year: int) -> float:
    start, end = date(year, 1, 1), date(year, 12, 31)
    rows = (
        db.query(GasConsumption)
        .filter(
            GasConsumption.pce_id == pce_id,
            GasConsumption.type_conso == "Publiée",
            GasConsumption.energie_kwh.isnot(None),
            GasConsumption.date_debut >= start,
            GasConsumption.date_debut <= end,
        )
        .all()
    )
    return round(sum(r.energie_kwh or 0 for r in rows) / 1000.0, 3)


def reconcile_p1(db: Session, city_id: int | None, year: int) -> list[P1ReconcileItem]:
    """Rapproche la conso GRDF réelle de la quantité P1 GAZ DALKIA, par PCE × année.

    `statut` :
      - `blocked` : pas de référence P1 pour ce PCE/année (désalignement PCE ou hors périmètre) ;
      - `ecart`   : |écart| au-delà de `grdf_ecart_tolerance_pct` ;
      - `ok`      : sinon.
    """
    tol = settings.grdf_ecart_tolerance_pct
    active_import = (
        db.query(CpeDalkiaRefImport)
        .filter(CpeDalkiaRefImport.city_id == city_id, CpeDalkiaRefImport.is_active.is_(True))
        .order_by(CpeDalkiaRefImport.id.desc())
        .first()
    )

    items: list[P1ReconcileItem] = []
    pces = db.query(GasPce).filter(GasPce.city_id == city_id).all()
    for pce in pces:
        grdf_mwh = _grdf_year_mwh_pcs(db, pce.id, year)
        if grdf_mwh == 0:
            continue  # rien collecté → on n'affiche pas une fausse comparaison

        # Référence P1 contractuelle pour ce PCE × année (import actif)
        p1_qt = p1_total = None
        code_site = None
        if active_import is not None:
            p1 = (
                db.query(CpeDalkiaRefP1Gaz)
                .filter(
                    CpeDalkiaRefP1Gaz.import_id == active_import.id,
                    CpeDalkiaRefP1Gaz.pce == pce.id_pce,
                    CpeDalkiaRefP1Gaz.period_year == year,
                )
                .first()
            )
            if p1 is not None:
                p1_qt = p1.qt_mwhpcs
                p1_total = p1.p10_total_ht
                code_site = p1.code_site

        # Conso déclarée DALKIA (info complémentaire), via code_site
        dalkia_conso = None
        if code_site is None:
            site = (
                db.query(CpeSite)
                .filter(CpeSite.city_id == city_id, CpeSite.pce == pce.id_pce)
                .first()
            )
            code_site = site.code_site if site else None
        if code_site:
            releves = (
                db.query(CpeConsoReleve)
                .filter(
                    CpeConsoReleve.city_id == city_id,
                    CpeConsoReleve.code_site == code_site,
                    CpeConsoReleve.fluide == "GAZ",
                    CpeConsoReleve.annee == year,
                )
                .all()
            )
            if releves:
                dalkia_conso = round(sum(r.energie_mwh or 0 for r in releves), 3)

        if p1_qt is None:
            statut, ecart_mwh, ecart_pct = "blocked", None, None
        else:
            ecart_mwh = round(grdf_mwh - p1_qt, 3)
            ecart_pct = round((ecart_mwh / p1_qt) * 100, 2) if p1_qt else None
            statut = "ecart" if (ecart_pct is not None and abs(ecart_pct) > tol) else "ok"

        items.append(
            P1ReconcileItem(
                id_pce=pce.id_pce,
                code_site=code_site,
                nom_site=pce.nom_site,
                grdf_mwh_pcs=grdf_mwh,
                dalkia_p1_qt_mwhpcs=p1_qt,
                dalkia_conso_mwh=dalkia_conso,
                p1_total_ht=p1_total,
                ecart_mwh=ecart_mwh,
                ecart_pct=ecart_pct,
                statut=statut,
            )
        )
    return items
