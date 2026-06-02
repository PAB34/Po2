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

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cpe import CpeGazReleve, CpePrixGaz, CpeResultatAnnuel, CpeSite
from app.models.cpe_dalkia import CpeDalkiaRefCible, CpeDalkiaRefImport
from app.schemas.cpe import (
    CpeBilanAnnuel,
    CpeDjuAnnuel,
    CpeGazReleveCreate,
    CpePrixGazCreate,
    CpeResultatAnnuelOut,
    CpeSiteBilanItem,
    CpeSiteCreate,
    CpeSiteOut,
    CpeSiteUpdate,
)

LOG = logging.getLogger(__name__)

DJU_COL = "dju_chauffage_base_18"
DJU_REFERENCE = 1426.0

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


# ── Lecture DJU depuis CSV dju_sete.csv ──────────────────────────────────────

def get_dju_annuel(annee: int) -> CpeDjuAnnuel:
    """Retourne le cumul annuel de DJU chauffage base 18°C pour Sète.

    Lit le fichier DJU/dju_sete.csv produit par dju_sync (Open-Meteo → méthode COSTIC).
    Pour l'intéressement contractuel, on utilise les DJU de la saison de chauffe
    correspondant à l'exercice (01/01/N → 31/12/N, approche calendaire).
    """
    csv_path = Path(settings.energie_dir) / "DJU" / "dju_sete.csv"
    if not csv_path.exists():
        return CpeDjuAnnuel(annee=annee, dju_total=0.0, nb_jours=0, source="fichier_absent")

    total = 0.0
    nb_jours = 0
    prefix = str(annee)

    try:
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get("date", "")
                if not date_str.startswith(prefix):
                    continue
                val = row.get(DJU_COL, "")
                if val not in ("", None):
                    try:
                        total += float(val)
                        nb_jours += 1
                    except ValueError:
                        pass
    except Exception as exc:
        LOG.warning("Erreur lecture DJU CSV : %s", exc)
        return CpeDjuAnnuel(annee=annee, dju_total=0.0, nb_jours=0, source="erreur_lecture")

    return CpeDjuAnnuel(
        annee=annee,
        dju_total=round(total, 2),
        nb_jours=nb_jours,
        source="open_meteo_costic",
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

def resolve_nb_for_year(db: Session, site: CpeSite, annee: int) -> float:
    """NB contractuel de l'exercice demandé.

    Lit la cible GAZ « NB » de l'import DALKIA actif pour (code_site, annee).
    Le contrat révise le NB chaque année (les travaux APE réduisent la cible à partir
    de leur année de réalisation), alors que `CpeSite.nb_mwh_pci` est un scalaire unique.

    Fallback sur `site.nb_mwh_pci` si aucune cible DALKIA n'existe pour cette année
    (aucun import actif, site hors périmètre DALKIA, ou code_site non aligné) — le
    comportement est alors strictement identique à l'historique.
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
        return nb
    return site.nb_mwh_pci


def calculer_resultat_site(
    db: Session,
    site_id: int,
    annee: int,
    dju_reels: float | None = None,
    pu_mwh: float | None = None,
) -> CpeResultatAnnuel:
    """Calcule et persiste le résultat annuel d'intéressement pour un site.

    Si dju_reels non fourni, lit depuis dju_sete.csv.
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

        nb_exercice = resolve_nb_for_year(db, site, annee)
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
