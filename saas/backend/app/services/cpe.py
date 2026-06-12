"""Service CPE DALKIA — moteur de calcul et CRUD.

Formules contractuelles (CCTPM Art. 11) :
    N'B = NB × (DJU_réels / DJU_ref)
    NC  = QT – (m × qECS)
    I   = ½ × min(N'B – NC, N'B × 0.15) × Pu   si NC < N'B
    P   = (NC – N'B) × Pu                         si NC > N'B

DJU contractuels : base 18°C, méthode COSTIC, station Montpellier, référence 1 426 DJU.
Les DJU réels sont lus depuis le CSV produit par dju_sync (Open-Meteo → COSTIC).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.cpe import CpeConsoReleve, CpeGazReleve, CpePrixGaz, CpeResultatAnnuel, CpeSite
from app.models.cpe_dalkia import CpeDalkiaRefCible, CpeDalkiaRefImport, CpeDalkiaRefP2P3
from app.schemas.cpe import (
    CpeBilanAnnuel,
    CpeConsoCoverageSite,
    CpeConsoFluideSummary,
    CpeConsoSynthese,
    CpeConsoUnknownSite,
    CpeDjuAnnuel,
    CpeGazReleveCreate,
    CpePrixGazCreate,
    CpeResultatAnnuelOut,
    CpeSiteBilanItem,
    CpeSiteCreate,
    CpeSiteOut,
    CpeSiteUpdate,
)
from app.services.dju_profiles import (
    DALKIA_CONTRACT_PROFILE,
    dju_heating_column,
    dju_profile_payload,
    is_dalkia_heating_month,
    read_dju_rows,
    safe_float,
)

LOG = logging.getLogger(__name__)

DJU_COL = dju_heating_column(DALKIA_CONTRACT_PROFILE)
DJU_REFERENCE = DALKIA_CONTRACT_PROFILE.reference_dju or 1426.0

# Seuils de révision NB (CCTPM)
SEUIL_REVISION_1 = 0.08   # > 8% → déclenchement sur 2 saisons
SEUIL_REVISION_2 = 0.12   # > 12% → déclenchement immédiat (1 saison)

# Conversion PCS → PCI (OS N°3 donne des prix en €/MWhPCS, formule CPE en MWhPCI)
# Pu_PCI = Pu_PCS × ratio_PCS_PCI
# ratio ≈ 1.1068 pour le gaz naturel distribué à Sète (zone GRDF Languedoc-Roussillon)
# Source : GRDF données de qualité du gaz — affinement possible via API GRDF ADICT
PCS_PCI_RATIO = 1.1068


# ── Moteur de calcul (fonctions pures) ───────────────────────────────────────

def calcul_n_prime_b(nb: float, dju_reels: float, dju_ref: float = DJU_REFERENCE) -> float:
    """N'B = NB × (DJU_réels / DJU_ref) — correction climatique."""
    if dju_ref <= 0:
        return nb
    return nb * (dju_reels / dju_ref)


def calcul_nc(qt: float, m: float, q_ecs: float | None) -> float:
    """NC = QT – (m × qECS).

    Si qECS est inconnu (None) ou m=0, NC = QT (pas d'ECS gaz à déduire).
    """
    if q_ecs is None or m <= 0:
        return qt
    return max(qt - (m * q_ecs), 0.0)


def calcul_interessement(n_prime_b: float, nc: float, pu: float) -> dict[str, Any]:
    """Calcule l'intéressement ou la pénalité CPE.

    Returns:
        dict avec clés : type_resultat, montant_ht, ecart, p2_4_taux
    """
    ecart = n_prime_b - nc

    if n_prime_b <= 0:
        return {
            "type_resultat": "insuffisant",
            "montant_ht": 0.0,
            "ecart": ecart,
            "p2_4_taux": 1.0,
        }

    if ecart > 0:
        # Intéressement : DALKIA adresse une facture à la collectivité
        imax = n_prime_b * 0.15
        i = 0.5 * min(ecart, imax) * pu
        return {
            "type_resultat": "interessement",
            "montant_ht": round(i, 2),
            "ecart": ecart,
            "p2_4_taux": 1.0,
        }
    elif ecart < 0:
        # Pénalité : DALKIA adresse un avoir à la collectivité (100%, sans plafond)
        p = abs(ecart) * pu
        return {
            "type_resultat": "penalite",
            "montant_ht": round(p, 2),
            "ecart": ecart,
            "p2_4_taux": 0.5,
        }
    else:
        return {
            "type_resultat": "equilibre",
            "montant_ht": 0.0,
            "ecart": 0.0,
            "p2_4_taux": 1.0,
        }


# ── Lecture DJU depuis le profil DALKIA ──────────────────────────────────────

def get_dju_annuel(annee: int) -> CpeDjuAnnuel:
    """Retourne les DJU chauffage du profil DALKIA pour l'exercice demandé.

    Le contrat fixe Montpellier / METEOCLIM COSTIC, base 18°C et référence 1 426 DJU
    (octobre-mai). Tant que la source METEOCLIM n'est pas branchée, le CSV dédié est
    alimenté par Open-Meteo Montpellier et reste marqué non opposable.
    """
    profile = dju_profile_payload(DALKIA_CONTRACT_PROFILE)
    rows = read_dju_rows(DALKIA_CONTRACT_PROFILE)
    if not rows:
        return CpeDjuAnnuel(annee=annee, dju_total=0.0, nb_jours=0, source="fichier_absent", **profile)

    total = 0.0
    nb_jours = 0

    try:
        for row in rows:
            date_str = row.get("date", "")
            if len(date_str) < 10:
                continue
            try:
                y = int(date_str[:4])
                month = int(date_str[5:7])
            except ValueError:
                continue
            if y != annee or not is_dalkia_heating_month(month):
                continue
            val = safe_float(row.get(DJU_COL))
            if val is not None:
                total += val
                nb_jours += 1
    except Exception as exc:
        LOG.warning("Erreur lecture DJU CSV : %s", exc)
        return CpeDjuAnnuel(annee=annee, dju_total=0.0, nb_jours=0, source="erreur_lecture", **profile)

    return CpeDjuAnnuel(
        annee=annee,
        dju_total=round(total, 2),
        nb_jours=nb_jours,
        source="open_meteo_montpellier_costic_indicatif",
        **profile,
    )


# ── CRUD CpeSite ──────────────────────────────────────────────────────────────

def get_sites(db: Session, city_id: int | None = None, actifs_seulement: bool = False) -> list[CpeSite]:
    q = select(CpeSite)
    if city_id is not None:
        q = q.where(CpeSite.city_id == city_id)
    if actifs_seulement:
        q = q.where(CpeSite.actif.is_(True))
    q = q.order_by(CpeSite.categorie, CpeSite.code_site)
    return list(db.scalars(q).all())


def get_site(db: Session, site_id: int) -> CpeSite | None:
    return db.get(CpeSite, site_id)


def get_site_by_code(db: Session, code_site: str) -> CpeSite | None:
    return db.scalars(select(CpeSite).where(CpeSite.code_site == code_site)).first()


def create_site(db: Session, payload: CpeSiteCreate) -> CpeSite:
    site = CpeSite(**payload.model_dump())
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def update_site(db: Session, site: CpeSite, payload: CpeSiteUpdate) -> CpeSite:
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(site, field, value)
    db.commit()
    db.refresh(site)
    return site


# ── CRUD CpeGazReleve ─────────────────────────────────────────────────────────

def get_releves(db: Session, site_id: int, annee: int | None = None) -> list[CpeGazReleve]:
    q = select(CpeGazReleve).where(CpeGazReleve.cpe_site_id == site_id)
    if annee is not None:
        q = q.where(CpeGazReleve.annee == annee)
    q = q.order_by(CpeGazReleve.annee, CpeGazReleve.mois)
    return list(db.scalars(q).all())


def upsert_releve(
    db: Session,
    site_id: int,
    payload: CpeGazReleveCreate,
    source: str = "saisie_manuelle",
) -> CpeGazReleve:
    """Insère ou met à jour le relevé mensuel d'un site."""
    existing = db.scalars(
        select(CpeGazReleve).where(
            CpeGazReleve.cpe_site_id == site_id,
            CpeGazReleve.annee == payload.annee,
            CpeGazReleve.mois == payload.mois,
        )
    ).first()

    if existing:
        if payload.qt_mwh_pci is not None:
            existing.qt_mwh_pci = payload.qt_mwh_pci
        if payload.volume_ecs_m3 is not None:
            existing.volume_ecs_m3 = payload.volume_ecs_m3
        if payload.etat_chauffe is not None:
            existing.etat_chauffe = payload.etat_chauffe
        if payload.notes is not None:
            existing.notes = payload.notes
        existing.source = source
        existing.date_import = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        releve = CpeGazReleve(
            cpe_site_id=site_id,
            annee=payload.annee,
            mois=payload.mois,
            qt_mwh_pci=payload.qt_mwh_pci,
            volume_ecs_m3=payload.volume_ecs_m3,
            etat_chauffe=payload.etat_chauffe,
            source=source,
            notes=payload.notes,
        )
        db.add(releve)
        db.commit()
        db.refresh(releve)
        return releve


# ── CRUD CpePrixGaz ───────────────────────────────────────────────────────────

def get_prix_gaz(db: Session, annee: int, tarif: str | None = None) -> CpePrixGaz | None:
    """Retourne le prix gaz pour un exercice et un tarif donné.

    tarif = 'T1' | 'T2' | 'T3' (OS N°3) ou None pour un Pu global/fallback.
    Si le tarif exact est absent, tente un fallback sur None (prix global).
    """
    q = select(CpePrixGaz).where(CpePrixGaz.annee == annee)
    if tarif is not None:
        q = q.where(CpePrixGaz.tarif == tarif)
    else:
        q = q.where(CpePrixGaz.tarif.is_(None))
    result = db.scalars(q).first()
    # Fallback : si tarif spécifique absent, tente None (Pu global)
    if result is None and tarif is not None:
        result = db.scalars(
            select(CpePrixGaz)
            .where(CpePrixGaz.annee == annee, CpePrixGaz.tarif.is_(None))
        ).first()
    return result


def get_all_prix_gaz(db: Session, annee: int) -> list[CpePrixGaz]:
    """Retourne tous les prix gaz d'un exercice (tous tarifs)."""
    return list(db.scalars(select(CpePrixGaz).where(CpePrixGaz.annee == annee)).all())


def upsert_prix_gaz(db: Session, payload: CpePrixGazCreate) -> CpePrixGaz:
    existing = get_prix_gaz(db, payload.annee, payload.tarif)
    if existing:
        existing.pu_eur_mwh_pci = payload.pu_eur_mwh_pci
        existing.source = payload.source
        existing.notes = payload.notes
        db.commit()
        db.refresh(existing)
        return existing
    prix = CpePrixGaz(**payload.model_dump())
    db.add(prix)
    db.commit()
    db.refresh(prix)
    return prix


# ── Calcul du résultat annuel ─────────────────────────────────────────────────

def get_conso_releves(db: Session, site_id: int, annee: int | None = None) -> list[CpeConsoReleve]:
    """Relevés de consommation multi-fluides d'un site (tous fluides, par mois)."""
    stmt = select(CpeConsoReleve).where(CpeConsoReleve.cpe_site_id == site_id)
    if annee is not None:
        stmt = stmt.where(CpeConsoReleve.annee == annee)
    return list(db.scalars(stmt.order_by(
        CpeConsoReleve.fluide, CpeConsoReleve.annee, CpeConsoReleve.mois
    )))


def get_conso_synthese(db: Session, annee: int, city_id: int | None = None) -> CpeConsoSynthese:
    """Synthese portefeuille des consommations multi-fluides importees depuis DALKIA."""
    sites_actifs = get_sites(db, city_id=city_id, actifs_seulement=True)
    sites_by_id = {s.id: s for s in sites_actifs}

    stmt = select(CpeConsoReleve).where(CpeConsoReleve.annee == annee)
    if city_id is not None:
        stmt = stmt.where(or_(CpeConsoReleve.city_id == city_id, CpeConsoReleve.city_id.is_(None)))
    releves = list(db.scalars(stmt))

    unit_by_fluide = {"GAZ": "MWh PCS", "ELEC": "MWh", "CHALEUR": "MWh", "ECS": "m3", "EAU": "m3"}
    energy_fluides = {"GAZ", "ELEC", "CHALEUR"}

    fluides: dict[str, dict[str, Any]] = {}
    coverage: dict[int, dict[str, Any]] = {}
    unknown: dict[str, dict[str, Any]] = {}

    for releve in releves:
        is_energy = releve.fluide in energy_fluides
        value = releve.energie_mwh if is_energy else releve.consommation
        value = value or 0.0

        f = fluides.setdefault(
            releve.fluide,
            {"total": 0.0, "sites": set(), "months": set(), "nb_releves": 0, "nb_estimes": 0},
        )
        f["total"] += value
        f["months"].add((releve.code_site, releve.mois))
        f["nb_releves"] += releve.nb_releves
        f["nb_estimes"] += releve.nb_estimes
        if releve.cpe_site_id is not None:
            f["sites"].add(releve.cpe_site_id)
            c = coverage.setdefault(releve.cpe_site_id, {"mois": set(), "fluides": set()})
            c["mois"].add(releve.mois)
            c["fluides"].add(releve.fluide)
        else:
            u = unknown.setdefault(
                releve.code_site,
                {
                    "contract_code": releve.contract_code,
                    "fluides": set(),
                    "months": set(),
                    "energy": 0.0,
                    "volume": 0.0,
                    "nb_estimes": 0,
                },
            )
            u["contract_code"] = releve.contract_code or u["contract_code"]
            u["fluides"].add(releve.fluide)
            u["months"].add((releve.fluide, releve.mois))
            if is_energy:
                u["energy"] += value
            else:
                u["volume"] += value
            u["nb_estimes"] += releve.nb_estimes

    covered_site_ids = set(coverage.keys()) & set(sites_by_id.keys())
    missing_sites = [s for s in sites_actifs if s.id not in covered_site_ids]

    fluide_order = {"GAZ": 0, "ELEC": 1, "CHALEUR": 2, "ECS": 3, "EAU": 4}
    fluide_summaries = [
        CpeConsoFluideSummary(
            fluide=fluide,
            total=round(data["total"], 3),
            unite=unit_by_fluide.get(fluide, ""),
            nb_sites=len(data["sites"]),
            nb_mois=len(data["months"]),
            nb_releves=data["nb_releves"],
            nb_estimes=data["nb_estimes"],
        )
        for fluide, data in sorted(fluides.items(), key=lambda item: fluide_order.get(item[0], 99))
    ]

    sites_sans_conso = [
        CpeConsoCoverageSite(
            site_id=site.id,
            code_site=site.code_site,
            nom_site=site.nom_site,
            categorie=site.categorie,
            mois_couverts=0,
            fluides=[],
        )
        for site in missing_sites
    ]

    sites_inconnus = [
        CpeConsoUnknownSite(
            code_site=code,
            contract_code=data["contract_code"],
            fluides=sorted(data["fluides"], key=lambda f: fluide_order.get(f, 99)),
            nb_mois=len(data["months"]),
            total_energie_mwh=round(data["energy"], 3) if data["energy"] else None,
            total_volume=round(data["volume"], 3) if data["volume"] else None,
            nb_estimes=data["nb_estimes"],
        )
        for code, data in sorted(unknown.items())
    ]

    return CpeConsoSynthese(
        annee=annee,
        nb_sites_actifs=len(sites_actifs),
        nb_sites_couverts=len(covered_site_ids),
        nb_sites_sans_conso=len(sites_sans_conso),
        nb_sites_inconnus=len(sites_inconnus),
        fluides=fluide_summaries,
        sites_sans_conso=sites_sans_conso,
        sites_inconnus=sites_inconnus,
    )


def resolve_nb_for_year_detailed(db: Session, site: CpeSite, annee: int) -> tuple[float, str]:
    """NB contractuel de l'exercice + sa source.

    Lit la cible GAZ « NB » de l'import DALKIA actif pour (code_site, annee).
    Le contrat révise le NB chaque année (les travaux APE réduisent la cible à partir
    de leur année de réalisation), alors que `CpeSite.nb_mwh_pci` est un scalaire unique.

    Retourne (nb, source) avec source :
      - "dalkia" : NB issu de la cible importée de l'année demandée ;
      - "site"   : fallback sur `site.nb_mwh_pci` (aucun import actif, site hors périmètre
                   DALKIA, code_site non aligné, ou NB DALKIA nul/0). Comportement alors
                   strictement identique à l'historique.

    La source permet de détecter à l'écran un éventuel décalage de `code_site` entre
    `cpe_sites` (seed) et `cpe_dalkia_ref_cibles` (import).
    """
    stmt = (
        select(CpeDalkiaRefCible.nb_mwhpci)
        .join(CpeDalkiaRefImport, CpeDalkiaRefCible.import_id == CpeDalkiaRefImport.id)
        .where(
            CpeDalkiaRefImport.is_active.is_(True),
            CpeDalkiaRefCible.fluid == "GAZ",
            CpeDalkiaRefCible.code_site == site.code_site,
            CpeDalkiaRefCible.period_year == annee,
            CpeDalkiaRefCible.nb_mwhpci.is_not(None),
        )
    )
    if site.city_id is not None:
        stmt = stmt.where(CpeDalkiaRefImport.city_id == site.city_id)
    nb = db.scalars(stmt).first()
    if nb is not None and nb > 0:
        return nb, "dalkia"
    return site.nb_mwh_pci, "site"


def resolve_nb_for_year(db: Session, site: CpeSite, annee: int) -> float:
    """NB contractuel de l'exercice (cf. resolve_nb_for_year_detailed)."""
    return resolve_nb_for_year_detailed(db, site, annee)[0]


def resolve_cible_elec_for_year(db: Session, site: CpeSite, annee: int) -> tuple[float | None, str]:
    """Cible de consommation ÉLECTRIQUE de l'exercice + sa source.

    Lit la cible ELEC (Annexe 5.2) de l'import DALKIA actif pour (code_site, annee).
    Sources : "dalkia" (cible importée de l'année) ; "site" (fallback `site.cible_elec_mwh`) ;
    "absente" (aucune cible). Pas de correction DJU (l'élec n'est pas thermosensible comme le gaz).
    """
    stmt = (
        select(CpeDalkiaRefCible)
        .join(CpeDalkiaRefImport, CpeDalkiaRefCible.import_id == CpeDalkiaRefImport.id)
        .where(
            CpeDalkiaRefImport.is_active.is_(True),
            CpeDalkiaRefCible.fluid == "ELEC",
            CpeDalkiaRefCible.code_site == site.code_site,
            CpeDalkiaRefCible.period_year == annee,
        )
    )
    if site.city_id is not None:
        stmt = stmt.where(CpeDalkiaRefImport.city_id == site.city_id)
    row = db.scalars(stmt).first()
    if row is not None:
        cible = row.nb_mwhpci if row.nb_mwhpci else row.qt_global_mwhpci
        if cible and cible > 0:
            return cible, "dalkia"
    if site.cible_elec_mwh and site.cible_elec_mwh > 0:
        return site.cible_elec_mwh, "site"
    return None, "absente"


def build_elec_performance(db: Session, annee: int, city_id: int | None = None) -> dict[str, Any]:
    """Suivi de performance ÉLECTRIQUE par site : cible vs conso réelle (logique IPMVP option B).

    HORS intéressement (l'élec n'a pas d'intéressement € — cf. CCTPM §11) : informatif, alimente
    l'engagement vérifié par IPMVP et l'objectif global qui conditionne P2.4.

    La conso réelle est le cumul à date (partielle si < 12 mois). Pour une comparaison **équitable**,
    l'écart est calculé contre la **cible au prorata de la période** (cible annuelle × mois/12), et
    non contre la cible annuelle — sinon un cumul de 5 mois paraît ~−90 % sous la cible.
    """
    items: list[dict[str, Any]] = []
    total_cible = 0.0           # cible annuelle (sites suivis)
    total_cible_periode = 0.0   # cible au prorata des mois disponibles
    total_conso = 0.0
    nb_suivis = 0
    nb_avec_cible = 0

    for site in get_sites(db, city_id=city_id, actifs_seulement=True):
        cible, cible_source = resolve_cible_elec_for_year(db, site, annee)
        if cible is not None:
            nb_avec_cible += 1

        conso_stmt = select(CpeConsoReleve).where(
            CpeConsoReleve.fluide == "ELEC",
            CpeConsoReleve.annee == annee,
            or_(CpeConsoReleve.cpe_site_id == site.id, CpeConsoReleve.code_site == site.code_site),
        )
        releves = list(db.scalars(conso_stmt))
        mois = {r.mois for r in releves if r.energie_mwh is not None}
        nb_mois = len(mois)
        conso = sum(r.energie_mwh for r in releves if r.energie_mwh is not None) or None

        cible_periode = ecart = ecart_pct = None
        if cible and conso is not None and nb_mois > 0:
            cible_periode = round(cible * nb_mois / 12.0, 2)
            ecart = round(conso - cible_periode, 2)  # vs cible au prorata (équitable)
            ecart_pct = round(ecart / cible_periode, 4) if cible_periode else None

        if cible is None:
            statut = "sans_cible"
        elif conso is None:
            statut = "sans_conso"
        else:
            statut = "suivi"
            nb_suivis += 1
            total_cible += cible
            total_cible_periode += cible_periode or 0.0
            total_conso += conso

        items.append({
            "site_id": site.id,
            "code_site": site.code_site,
            "nom_site": site.nom_site,
            "cible_mwh": round(cible, 2) if cible is not None else None,
            "cible_periode_mwh": cible_periode,
            "cible_source": cible_source,
            "conso_reelle_mwh": round(conso, 2) if conso is not None else None,
            "nb_mois": nb_mois,
            "ecart_mwh": ecart,
            "ecart_pct": ecart_pct,
            "statut": statut,
        })

    total_cible = round(total_cible, 2)
    total_cible_periode = round(total_cible_periode, 2)
    total_conso = round(total_conso, 2)
    return {
        "annee": annee,
        "nb_sites": len(items),
        "nb_avec_cible": nb_avec_cible,
        "nb_suivis": nb_suivis,
        "total_cible_mwh": total_cible,
        "total_cible_periode_mwh": total_cible_periode,
        "total_conso_mwh": total_conso,
        "total_ecart_mwh": round(total_conso - total_cible_periode, 2),
        "total_ecart_pct": round((total_conso - total_cible_periode) / total_cible_periode, 4) if total_cible_periode else None,
        "has_data": nb_suivis > 0,
        "items": items,
    }


def build_p24_objective(db: Session, annee: int, city_id: int | None = None) -> dict[str, Any]:
    """Indicateur P2.4 : objectif d'économie d'énergie global atteint ? → redevance 100 % / 50 %.

    Base contractuelle (CCTPM §11.3) : « si les objectifs d'économies d'énergie sont atteints
    (au global), P2.4 facturé 100 % ; sinon 50 % ». Le % objectif est défini dans l'Acte
    d'Engagement et **déjà encodé dans les cibles** (NB gaz, cible élec). Donc « atteint au
    global » = consommation réelle globale ≤ cible globale, sans seuil inventé.

    Global cible = Σ N'B gaz (cible recalée DJU) + Σ cible élec.
    Global réel  = Σ NC gaz (conso corrigée ECS) + Σ conso élec réelle.
    Le montant P2.4 vient de l'Annexe 3.1 (cpe_dalkia_ref_p2p3.p2_4_ht, import actif, année).
    ⚠️ Données cumulées à date : verdict définitif au décompte de fin d'exercice.
    """
    bilan = get_bilan_annuel(db, annee, city_id=city_id)
    gas_cible = 0.0
    gas_reel = 0.0
    gas_sites = 0
    gas_mois_min = 12
    for it in bilan.sites:
        if it.n_prime_b is not None and it.nc_cumul is not None:
            gas_cible += it.n_prime_b
            gas_reel += it.nc_cumul
            gas_sites += 1
            gas_mois_min = min(gas_mois_min, it.nb_mois_releves)

    elec = build_elec_performance(db, annee, city_id=city_id)
    # Cible élec AU PRORATA des mois disponibles (cohérent avec le gaz N'B, déjà période-consistant
    # via DJU cumulé). Sinon une cible annuelle face à une conso partielle fausse l'économie.
    elec_cible = elec["total_cible_periode_mwh"]
    elec_reel = elec["total_conso_mwh"]

    global_cible = round(gas_cible + elec_cible, 2)
    global_reel = round(gas_reel + elec_reel, 2)
    economie_mwh = round(global_cible - global_reel, 2)  # > 0 = objectif atteint
    economie_pct = round(economie_mwh / global_cible, 4) if global_cible else None

    # Montant P2.4 contractuel de l'année (Annexe 3.1, imports actifs)
    p24_stmt = (
        select(CpeDalkiaRefP2P3.p2_4_ht)
        .join(CpeDalkiaRefImport, CpeDalkiaRefP2P3.import_id == CpeDalkiaRefImport.id)
        .where(
            CpeDalkiaRefImport.is_active.is_(True),
            CpeDalkiaRefP2P3.period_year == annee,
            CpeDalkiaRefP2P3.p2_4_ht.is_not(None),
        )
    )
    if city_id is not None:
        p24_stmt = p24_stmt.where(CpeDalkiaRefImport.city_id == city_id)
    p24_montant = round(sum(v for v in db.scalars(p24_stmt) if v) or 0.0, 2)

    has_data = (gas_sites > 0 or elec["nb_suivis"] > 0) and global_cible > 0
    objectif_atteint = has_data and economie_mwh >= 0
    taux = 1.0 if objectif_atteint else 0.5
    p24_facturable = round(p24_montant * taux, 2)
    p24_a_risque = round(p24_montant * 0.5, 2)  # part perdue si objectif non atteint

    return {
        "annee": annee,
        "has_data": has_data,
        "objectif_atteint": objectif_atteint,
        "global_cible_mwh": global_cible,
        "global_reel_mwh": global_reel,
        "economie_mwh": economie_mwh,
        "economie_pct": economie_pct,
        "gas_cible_mwh": round(gas_cible, 2),
        "gas_reel_mwh": round(gas_reel, 2),
        "gas_sites": gas_sites,
        "elec_cible_mwh": round(elec_cible, 2),
        "elec_reel_mwh": round(elec_reel, 2),
        "elec_sites": elec["nb_suivis"],
        "elec_sites_avec_cible": elec["nb_avec_cible"],
        "p24_montant_ht": p24_montant,
        "p24_taux": taux,
        "p24_facturable_ht": p24_facturable,
        "p24_a_risque_ht": p24_a_risque,
        "gas_mois_min": gas_mois_min if gas_sites > 0 else 0,
        "complet": gas_sites > 0 and gas_mois_min >= 12,
    }


def calculer_resultat_site(
    db: Session,
    site_id: int,
    annee: int,
    dju_reels: float | None = None,
    pu_mwh: float | None = None,
) -> CpeResultatAnnuel:
    """Calcule et persiste le résultat annuel d'intéressement pour un site.

    Si dju_reels non fourni, lit les DJU du profil contractuel DALKIA.
    Si pu_mwh non fourni, lit depuis cpe_prix_gaz.
    """
    site = db.get(CpeSite, site_id)
    if site is None:
        raise ValueError(f"Site CPE {site_id} introuvable")

    # DJU réels
    if dju_reels is None:
        dju_info = get_dju_annuel(annee)
        dju_reels = dju_info.dju_total if dju_info.nb_jours > 0 else None

    # Prix gaz — lookup par tarif du site (T1/T2/T3, OS N°3)
    if pu_mwh is None:
        prix = get_prix_gaz(db, annee, site.tarif)
        pu_mwh = prix.pu_eur_mwh_pci if prix else None

    # Relevés mensuels
    releves = get_releves(db, site_id, annee)
    nb_mois = len([r for r in releves if r.qt_mwh_pci is not None])
    qt_total = sum(r.qt_mwh_pci for r in releves if r.qt_mwh_pci is not None)
    m_ecs_total = sum(r.volume_ecs_m3 for r in releves if r.volume_ecs_m3 is not None)

    # Si pas de données m ECS dans les relevés, utilise la référence annuelle
    if m_ecs_total == 0 and site.ecs_ref_m3_an > 0:
        m_ecs_total = site.ecs_ref_m3_an

    # NB contractuel de l'exercice (cible DALKIA par année, fallback scalaire site)
    nb_exercice = resolve_nb_for_year(db, site, annee)

    # Calculs
    n_prime_b = calcul_n_prime_b(nb_exercice, dju_reels, site.dju_reference) if dju_reels else None
    nc = calcul_nc(qt_total, m_ecs_total, site.q_ecs_mwh_pci_per_m3) if qt_total else None

    # Intéressement / pénalité
    fin = {}
    if n_prime_b is not None and nc is not None and pu_mwh is not None:
        fin = calcul_interessement(n_prime_b, nc, pu_mwh)
    else:
        fin = {"type_resultat": None, "montant_ht": None, "ecart": None, "p2_4_taux": 1.0}

    # Écart relatif pour détection révision NB
    ecart_pct = None
    alerte = False
    if nb_exercice > 0 and nc is not None:
        ecart_pct = (nc - nb_exercice) / nb_exercice
        alerte = abs(ecart_pct) >= SEUIL_REVISION_2  # 1 saison suffit pour 12%

    # Statut
    if nb_mois == 0:
        statut = "partiel"
    elif nb_mois < 12:
        statut = "partiel"
    elif pu_mwh is None or dju_reels is None:
        statut = "partiel"
    else:
        statut = "calcule"

    # Upsert résultat
    existing = db.scalars(
        select(CpeResultatAnnuel).where(
            CpeResultatAnnuel.cpe_site_id == site_id,
            CpeResultatAnnuel.annee == annee,
        )
    ).first()

    data = {
        "cpe_site_id": site_id,
        "annee": annee,
        "dju_reels": dju_reels,
        "dju_reference": site.dju_reference,
        "nb": nb_exercice,
        "n_prime_b": n_prime_b,
        "qt_total": qt_total if qt_total else None,
        "m_ecs_total": m_ecs_total if m_ecs_total else None,
        "nc": nc,
        "pu_mwh": pu_mwh,
        "ecart": fin.get("ecart"),
        "type_resultat": fin.get("type_resultat"),
        "montant_ht": fin.get("montant_ht"),
        "p2_4_taux": fin.get("p2_4_taux", 1.0),
        "ecart_pct": ecart_pct,
        "alerte_revision_nb": alerte,
        "statut": statut,
        "nb_mois_renseignes": nb_mois,
        "computed_at": datetime.utcnow(),
    }

    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        resultat = CpeResultatAnnuel(**data)
        db.add(resultat)
        db.commit()
        db.refresh(resultat)
        return resultat


def get_resultat_site(db: Session, site_id: int, annee: int) -> CpeResultatAnnuel | None:
    return db.scalars(
        select(CpeResultatAnnuel).where(
            CpeResultatAnnuel.cpe_site_id == site_id,
            CpeResultatAnnuel.annee == annee,
        )
    ).first()


# ── Bilan annuel multi-sites ──────────────────────────────────────────────────

def get_bilan_annuel(db: Session, annee: int, city_id: int | None = None) -> CpeBilanAnnuel:
    """Retourne le bilan CPE consolidé pour tous les sites d'un exercice."""
    sites = get_sites(db, city_id=city_id, actifs_seulement=True)

    dju_info = get_dju_annuel(annee)
    dju_reels = dju_info.dju_total if dju_info.nb_jours > 0 else None

    # Prix par tarif — {tarif_str_ou_None: pu_pci}
    prix_list = get_all_prix_gaz(db, annee)
    prix_par_tarif: dict[str | None, float] = {p.tarif: p.pu_eur_mwh_pci for p in prix_list}
    # Pu T2 pour affichage KPI (tarif le plus courant)
    pu_mwh_display = prix_par_tarif.get("T2") or prix_par_tarif.get(None)
    # Dict pour le frontend : uniquement les tarifs nommés
    prix_tarifs: dict[str, float] = {k: v for k, v in prix_par_tarif.items() if k is not None}

    items: list[CpeSiteBilanItem] = []
    total_interessement = 0.0
    total_penalite = 0.0
    nb_complets = 0

    for site in sites:
        # Prix applicable à ce site
        pu_site = prix_par_tarif.get(site.tarif) if site.tarif else None
        if pu_site is None and site.tarif is not None:
            # Fallback sur prix global si tarif spécifique absent
            pu_site = prix_par_tarif.get(None)

        releves = get_releves(db, site.id, annee)
        nb_mois = len([r for r in releves if r.qt_mwh_pci is not None])
        qt_cumul = sum(r.qt_mwh_pci for r in releves if r.qt_mwh_pci is not None) or None
        m_ecs = sum(r.volume_ecs_m3 for r in releves if r.volume_ecs_m3 is not None)
        if m_ecs == 0 and site.ecs_ref_m3_an > 0:
            m_ecs = site.ecs_ref_m3_an

        nb_exercice, nb_source = resolve_nb_for_year_detailed(db, site, annee)
        nc_cumul = calcul_nc(qt_cumul, m_ecs, site.q_ecs_mwh_pci_per_m3) if qt_cumul else None
        n_prime_b = calcul_n_prime_b(nb_exercice, dju_reels, site.dju_reference) if dju_reels else None

        fin: dict[str, Any] = {}
        if n_prime_b is not None and nc_cumul is not None and pu_site is not None:
            fin = calcul_interessement(n_prime_b, nc_cumul, pu_site)

        if nb_mois == 12 and pu_site and dju_reels:
            nb_complets += 1
            if fin.get("type_resultat") == "interessement":
                total_interessement += fin.get("montant_ht") or 0.0
            elif fin.get("type_resultat") == "penalite":
                total_penalite += fin.get("montant_ht") or 0.0

        # Charge le résultat persisté si disponible
        resultat_db = get_resultat_site(db, site.id, annee)
        resultat_out = CpeResultatAnnuelOut.model_validate(resultat_db) if resultat_db else None

        statut = "partiel" if nb_mois < 12 else ("calcule" if pu_site and dju_reels else "partiel")

        items.append(CpeSiteBilanItem(
            site=CpeSiteOut.model_validate(site),
            resultat=resultat_out,
            nb_mois_releves=nb_mois,
            nb_exercice=nb_exercice,
            nb_source=nb_source,
            qt_cumul=qt_cumul,
            nc_cumul=nc_cumul,
            n_prime_b=n_prime_b,
            ecart=fin.get("ecart"),
            type_resultat=fin.get("type_resultat"),
            montant_ht=fin.get("montant_ht"),
            statut=statut,
        ))

    return CpeBilanAnnuel(
        annee=annee,
        dju_reels=dju_reels,
        dju_reference=DJU_REFERENCE,
        pu_mwh=pu_mwh_display,
        prix_tarifs=prix_tarifs,
        nb_sites_actifs=len(sites),
        nb_sites_complets=nb_complets,
        total_interessement_ht=round(total_interessement, 2),
        total_penalite_ht=round(total_penalite, 2),
        solde_ht=round(total_interessement - total_penalite, 2),
        sites=items,
    )
