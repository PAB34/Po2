"""Modeles pour les tables de reference du marche CPE DALKIA.

Ces tables sont alimentees par l'import du fichier contractuel DALKIA
(L1 et L2) et servent de reference pour le controle des factures.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CpeDalkiaRefImport(Base):
    """Historique des imports du fichier contractuel DALKIA."""

    __tablename__ = "cpe_dalkia_ref_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    lot: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    import_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    nb_sites: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_p2p3_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_cibles_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_p1_gaz_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_ape_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_recap_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Qualification de l'acte contractuel (saisie utilisateur, journal du marche)
    acte_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    acte_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_effet: Mapped[date | None] = mapped_column(Date, nullable=True)


class CpeDalkiaRefSite(Base):
    """Liste de reference des sites du marche CPE DALKIA."""

    __tablename__ = "cpe_dalkia_ref_sites"
    __table_args__ = (
        UniqueConstraint("import_id", "code_site", name="uq_dalkia_site_per_import"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    lot: Mapped[int] = mapped_column(Integer, nullable=False)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    nom_batiment: Mapped[str] = mapped_column(String(255), nullable=False)
    entite: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lot_label: Mapped[str | None] = mapped_column(String(40), nullable=True)


class CpeDalkiaRefP2P3(Base):
    """Montants P2 et P3 par site x periode."""

    __tablename__ = "cpe_dalkia_ref_p2p3"
    __table_args__ = (
        UniqueConstraint("import_id", "code_site", "period_idx", name="uq_dalkia_p2p3"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    period_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    p2_1_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2_2_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2_3_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2_4_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2_total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_1_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_2_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_3_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_4_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)


class CpeDalkiaRefCible(Base):
    """Cibles de consommation par site x periode x fluide.

    Pas de contrainte unique sur (code_site, fluid, period_idx) : un meme site peut avoir
    plusieurs lignes par periode (sous-compteurs, PV...).
    """

    __tablename__ = "cpe_dalkia_ref_cibles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    fluid: Mapped[str] = mapped_column(String(10), nullable=False)
    period_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ref_globale_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref_qt_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    dju_reference: Mapped[float | None] = mapped_column(Float, nullable=True)
    qt_global_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    nb_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    q_ecs: Mapped[float | None] = mapped_column(Float, nullable=True)
    qt_ecs: Mapped[float | None] = mapped_column(Float, nullable=True)


class CpeDalkiaRefP1Gaz(Base):
    """Fourniture gaz P1 par site x periode."""

    __tablename__ = "cpe_dalkia_ref_p1_gaz"
    __table_args__ = (
        UniqueConstraint("import_id", "code_site", "period_idx", name="uq_dalkia_p1_gaz"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    pce: Mapped[str | None] = mapped_column(String(30), nullable=True)
    type_tarif: Mapped[str | None] = mapped_column(String(10), nullable=True)
    prix_unitaire_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    atrd_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    cta_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_fixe_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    period_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qt_mwhpcs: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_var_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)


class CpeDalkiaRefP1Elec(Base):
    """Fourniture electricite P1 par site x periode (Annexe 6.2 - P1 ELEC_PSE).

    Concerne le Lot 2 (piscines) ou la PSE P1 electricite est RETENUE : DALKIA fournit
    l'electricite, facturee comme le P1 gaz (cf. OUV11-MGPE L2, art 7.2.1 CCAP). Le Lot 1
    n'a pas de P1 elec (PSE non retenue).
    """

    __tablename__ = "cpe_dalkia_ref_p1_elec"
    __table_args__ = (
        UniqueConstraint("import_id", "code_site", "period_idx", name="uq_dalkia_p1_elec"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    pdl: Mapped[str | None] = mapped_column(String(30), nullable=True)
    prix_unitaire_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    period_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qt_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_var_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)


class CpeDalkiaRefApe(Base):
    """Travaux APE par site (plusieurs lignes possibles)."""

    __tablename__ = "cpe_dalkia_ref_ape"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    nom_batiment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    situation_initiale_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    description_ape: Mapped[str | None] = mapped_column(Text, nullable=True)
    annee_achevement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    montant_ape_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    cee_mwh_cumac: Mapped[float | None] = mapped_column(Float, nullable=True)
    cee_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    subvention_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    gain_energetique_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    situation_nouvelle_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    annee_engagement_nouvelle_cible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    emission_co2_evitee: Mapped[float | None] = mapped_column(Float, nullable=True)
    production_enr_auto_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    production_enr_vendue_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    recette_vente_energie_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    ratio_ht_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class CpeDalkiaRefRecap(Base):
    """Recapitulatif financier global du marche (feuille RECAP MARCHE), format long.

    Stocke chaque metrique financiere par periode : engagements de consommation
    GAZ/ELEC/PV, redevances P1/P2/P3, sensibilisation, travaux, bilan marche.
    """

    __tablename__ = "cpe_dalkia_ref_recap"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    section: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    metric_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    period_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    period_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)


class CpeDalkiaRefP1Tarif(Base):
    """Composants de prix gaz + coefficients de revision Pu par tarif (en-tete Annexe 6).

    Formule : Pu_GAZ = Pu_0 x (a + b x PEG/PEG0 + c x TVD/TVD0 + d x CEE/CEE0 + e x TICGN/TICGN0).
    Les composants sont les valeurs de base (periode 0) ; a+b+c+d+e = 1 par construction.
    """

    __tablename__ = "cpe_dalkia_ref_p1_tarifs"
    __table_args__ = (
        UniqueConstraint("import_id", "type_tarif", name="uq_dalkia_p1_tarif"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    type_tarif: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    p0_fournisseur: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref_peg: Mapped[float | None] = mapped_column(Float, nullable=True)
    terme_acheminement: Mapped[float | None] = mapped_column(Float, nullable=True)
    obligation_cee: Mapped[float | None] = mapped_column(Float, nullable=True)
    ticgn: Mapped[float | None] = mapped_column(Float, nullable=True)
    marge_exploitant_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    prix_unitaire_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    coef_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    coef_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    coef_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    coef_d: Mapped[float | None] = mapped_column(Float, nullable=True)
    coef_e: Mapped[float | None] = mapped_column(Float, nullable=True)


class CpeDalkiaRefBpu(Base):
    """Bordereau de prix unitaires travaux P3 (Annexe 7) — catalogue de reference.

    categorie : prestation (ENT/ENR/T/C/AM) | taux_horaire | coefficient (CF/CST).
    Sert de base au controle des devis P3 (codes, prix unitaires, taux, coefficients).
    """

    __tablename__ = "cpe_dalkia_ref_bpu"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    categorie: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    famille: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    libelle: Mapped[str | None] = mapped_column(Text, nullable=True)
    specificite: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unite: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cout_unitaire: Mapped[float | None] = mapped_column(Float, nullable=True)
    cout_nuit: Mapped[float | None] = mapped_column(Float, nullable=True)
    cout_samedi: Mapped[float | None] = mapped_column(Float, nullable=True)
    cout_dimanche: Mapped[float | None] = mapped_column(Float, nullable=True)
    coefficient: Mapped[float | None] = mapped_column(Float, nullable=True)
    coefficient_max: Mapped[float | None] = mapped_column(Float, nullable=True)
