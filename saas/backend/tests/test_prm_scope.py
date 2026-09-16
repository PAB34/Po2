"""Périmètre des PRM : un PRM désactivé sort de tous les calculs, sans être supprimé.

Contexte : les factures du marché 2024-FCS-03 mélangent les points de livraison de la
Ville et ceux de Sète Agglopôle Méditerranée. La plateforme ne traite que la Ville, et
aucun champ des factures ne sépare les deux périmètres (même titulaire, même marché,
même référence client). La mise à l'écart passe donc par
`EnergyAccountingSiteMapping.active`.

Voir docs/refonte-v1/enedis-referentiel-prm-qualite-decisions.md (décision D5).
"""

import io
from datetime import date

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.invoice import (
    EnergyAccountingSiteMapping,
    EnergyInvoice,
    EnergyInvoiceImport,
    EnergyInvoiceLine,
    EnergyInvoicePeriod,
    EnergyInvoiceSite,
)
from app.services import energie_accounting, power_real_costs
from app.services.prm_scope import inactive_prm_ids, is_in_scope

PRM_VILLE = "24300000000001"
PRM_AGGLO = "30002400000002"


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _invoice_with_sites(db, prms, *, normalized_code="network_fixed_total"):
    imp = EnergyInvoiceImport(
        city_id=1, uploaded_by_user_id=1, original_filename="f.pdf", stored_filename="s.pdf",
        storage_path="/tmp/s.pdf", file_size_bytes=1, sha256="y" * 64, invoice_number="INV-9",
    )
    db.add(imp)
    db.flush()
    inv = EnergyInvoice(city_id=1, import_id=imp.id, supplier="ENGIE", invoice_number="INV-9")
    db.add(inv)
    db.flush()
    for prm in prms:
        site = EnergyInvoiceSite(invoice_id=inv.id, prm_id=prm, site_name=f"Site {prm}")
        db.add(site)
        db.flush()
        period = EnergyInvoicePeriod(
            invoice_site_id=site.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            subscribed_power_kva=36.0,
        )
        db.add(period)
        db.flush()
        db.add(
            EnergyInvoiceLine(
                invoice_period_id=period.id,
                poste="Acheminement",
                normalized_code=normalized_code,
                amount_ht=100.0,
            )
        )
    db.commit()
    db.refresh(imp)
    return imp


def _deactivate(db, prm):
    db.add(EnergyAccountingSiteMapping(city_id=1, prm_id=prm, site_name="Agglo", active=False))
    db.commit()


def test_prm_actif_par_defaut(db):
    """Sans ligne de matrice, aucun PRM n'est écarté : on ne masque que sur décision."""
    _invoice_with_sites(db, [PRM_VILLE, PRM_AGGLO])
    assert inactive_prm_ids(db, 1) == set()


def test_prm_desactive_est_hors_perimetre(db):
    _deactivate(db, PRM_AGGLO)
    inactive = inactive_prm_ids(db, 1)
    assert inactive == {PRM_AGGLO}
    assert is_in_scope(PRM_VILLE, inactive) is True
    assert is_in_scope(PRM_AGGLO, inactive) is False


def test_site_sans_prm_reste_dans_le_perimetre(db):
    """Un site non identifiable n'est jamais écarté : rien ne prouve qu'il est hors périmètre."""
    _deactivate(db, PRM_AGGLO)
    inactive = inactive_prm_ids(db, 1)
    assert is_in_scope(None, inactive) is True
    assert is_in_scope("   ", inactive) is True


def test_desactivation_limitee_a_la_collectivite(db):
    """La désactivation vaut pour une collectivité, pas pour les autres comptes."""
    _deactivate(db, PRM_AGGLO)
    assert inactive_prm_ids(db, 1) == {PRM_AGGLO}
    assert inactive_prm_ids(db, 2) == set()


def test_couts_puissance_ignorent_le_prm_desactive(db):
    """Le calcul des coûts de puissance réels ne doit plus voir le PRM écarté."""
    _invoice_with_sites(db, [PRM_VILLE, PRM_AGGLO])

    avant = power_real_costs.get_real_power_costs_by_prm(db, city_id=1)
    assert set(avant) == {PRM_VILLE, PRM_AGGLO}

    _deactivate(db, PRM_AGGLO)
    apres = power_real_costs.get_real_power_costs_by_prm(db, city_id=1)
    assert set(apres) == {PRM_VILLE}


def test_fiche_de_liaison_ignore_le_prm_desactive(db):
    """La fiche de liaison finances ne doit pas contenir de ligne hors périmètre."""
    imp = _invoice_with_sites(db, [PRM_VILLE, PRM_AGGLO], normalized_code="Abonnement")

    rows = energie_accounting.resolve_invoice_codification(db, imp)
    assert {r.prm_id for r in rows} == {PRM_VILLE, PRM_AGGLO}

    _deactivate(db, PRM_AGGLO)
    rows = energie_accounting.resolve_invoice_codification(db, imp)
    assert {r.prm_id for r in rows} == {PRM_VILLE}


def test_la_mise_a_l_ecart_survit_a_un_nouvel_import_de_factures(db):
    """Le masquage est durable : réimporter des factures ne ramène pas le PRM.

    C'est le cas d'usage normal — de nouvelles factures arrivent chaque mois et
    portent les mêmes PRM. Le pré-remplissage de la matrice ne doit pas réactiver un
    point déjà mis hors périmètre.
    """
    _invoice_with_sites(db, [PRM_VILLE, PRM_AGGLO])
    _deactivate(db, PRM_AGGLO)

    # Nouvel import : mêmes PRM, nouvelle facture.
    _invoice_with_sites(db, [PRM_VILLE, PRM_AGGLO])
    energie_accounting.bootstrap_site_mappings_from_invoices(db, city_id=1)

    assert inactive_prm_ids(db, 1) == {PRM_AGGLO}
    assert set(power_real_costs.get_real_power_costs_by_prm(db, city_id=1)) == {PRM_VILLE}


def test_la_mise_a_l_ecart_survit_a_un_reimport_de_codification(db):
    """Le classeur de codification ne doit pas réactiver un PRM hors périmètre.

    Le classeur porte les axes comptables, pas le périmètre : il ne doit jamais
    remettre dans les calculs un point qui en a été sorti.
    """
    _invoice_with_sites(db, [PRM_VILLE, PRM_AGGLO])
    _deactivate(db, PRM_AGGLO)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sites vers codes"
    ws.append(["PRM", "Nom du site", "Service", "Libellé service", "Fonction", "Antenne"])
    ws.append([PRM_AGGLO, "STEP Mèze", "S100", "Bâtiments", "F20", "ANT-A"])
    buf = io.BytesIO()
    wb.save(buf)

    res = energie_accounting.import_codification_workbook(
        db, buf.getvalue(), filename="codif.xlsx", city_id=1
    )
    assert res.site_mappings_updated == 1

    assert inactive_prm_ids(db, 1) == {PRM_AGGLO}


def test_les_donnees_restent_en_base(db):
    """On masque, on ne supprime pas : les lignes de facture sont intactes."""
    _invoice_with_sites(db, [PRM_VILLE, PRM_AGGLO])
    _deactivate(db, PRM_AGGLO)

    sites = db.query(EnergyInvoiceSite).all()
    assert {s.prm_id for s in sites} == {PRM_VILLE, PRM_AGGLO}
    assert db.query(EnergyInvoiceLine).count() == 2
