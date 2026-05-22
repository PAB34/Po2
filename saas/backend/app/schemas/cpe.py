"""Schemas Pydantic pour le module CPE DALKIA."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── CpeSite ──────────────────────────────────────────────────────────────────

class CpeSiteBase(BaseModel):
    code_site: str
    nom_site: str
    categorie: str
    nb_mwh_pci: float
    ecs_ref_m3_an: float
    q_ecs_mwh_pci_per_m3: float | None = None
    dju_reference: float = 1426.0
    cible_elec_mwh: float | None = None
    actif: bool = True
    notes: str | None = None


class CpeSiteCreate(CpeSiteBase):
    city_id: int | None = None


class CpeSiteUpdate(BaseModel):
    nb_mwh_pci: float | None = None
    ecs_ref_m3_an: float | None = None
    q_ecs_mwh_pci_per_m3: float | None = None
    cible_elec_mwh: float | None = None
    actif: bool | None = None
    notes: str | None = None


class CpeSiteOut(CpeSiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    city_id: int | None
    created_at: datetime
    updated_at: datetime


# ── CpeGazReleve ─────────────────────────────────────────────────────────────

class CpeGazReleve(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cpe_site_id: int
    annee: int
    mois: int
    qt_mwh_pci: float | None
    volume_ecs_m3: float | None
    etat_chauffe: bool | None
    source: str
    date_import: datetime
    notes: str | None


class CpeGazReleveCreate(BaseModel):
    annee: int
    mois: int
    qt_mwh_pci: float | None = None
    volume_ecs_m3: float | None = None
    etat_chauffe: bool | None = None
    notes: str | None = None


class CpeGazReleveUpdate(BaseModel):
    qt_mwh_pci: float | None = None
    volume_ecs_m3: float | None = None
    etat_chauffe: bool | None = None
    notes: str | None = None


# ── CpePrixGaz ───────────────────────────────────────────────────────────────

class CpePrixGazOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    annee: int
    pu_eur_mwh_pci: float
    source: str
    notes: str | None
    updated_at: datetime


class CpePrixGazCreate(BaseModel):
    annee: int
    pu_eur_mwh_pci: float
    source: str = "saisie_manuelle"
    notes: str | None = None


# ── CpeResultatAnnuel ────────────────────────────────────────────────────────

class CpeResultatAnnuelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cpe_site_id: int
    annee: int
    dju_reels: float | None
    dju_reference: float
    nb: float
    n_prime_b: float | None
    qt_total: float | None
    m_ecs_total: float | None
    nc: float | None
    pu_mwh: float | None
    ecart: float | None
    type_resultat: str | None
    montant_ht: float | None
    p2_4_taux: float
    ecart_pct: float | None
    alerte_revision_nb: bool
    statut: str
    nb_mois_renseignes: int
    computed_at: datetime


# ── Bilan annuel (vue d'ensemble multi-sites) ─────────────────────────────────

class CpeSiteBilanItem(BaseModel):
    """Résultat synthétique d'un site pour le bilan annuel."""
    site: CpeSiteOut
    resultat: CpeResultatAnnuelOut | None
    nb_mois_releves: int
    qt_cumul: float | None
    nc_cumul: float | None
    n_prime_b: float | None
    ecart: float | None
    type_resultat: str | None
    montant_ht: float | None
    statut: str


class CpeBilanAnnuel(BaseModel):
    """Vue d'ensemble du bilan CPE pour un exercice."""
    annee: int
    dju_reels: float | None
    dju_reference: float
    pu_mwh: float | None
    nb_sites_actifs: int
    nb_sites_complets: int
    total_interessement_ht: float
    total_penalite_ht: float
    solde_ht: float  # positif = facture DALKIA, négatif = avoir DALKIA
    sites: list[CpeSiteBilanItem]


# ── Import CSV ────────────────────────────────────────────────────────────────

class CpeImportResult(BaseModel):
    nb_lignes: int
    nb_inseres: int
    nb_mis_a_jour: int
    nb_erreurs: int
    erreurs: list[str]
    sites_inconnus: list[str]


# ── DJU ──────────────────────────────────────────────────────────────────────

class CpeDjuAnnuel(BaseModel):
    annee: int
    dju_total: float
    nb_jours: int
    source: str
