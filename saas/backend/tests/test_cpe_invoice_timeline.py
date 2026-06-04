"""Le controle calendrier ne doit pas signaler d'incoherence pour un ACOMPTE dont l'echeance
est fixee a la fin de la periode facturee (ex. 31/03) et qui est edite juste apres (01/04).
Il ne signale une vraie incoherence que si l'echeance precede aussi la fin de periode."""
from __future__ import annotations

from datetime import date

from app.models.cpe import CpeFinanceInvoice, CpeFinanceLine
from app.services.cpe_accounting import _control_invoice_timeline


def _invoice(invoice_date, due_date, period_start, period_end) -> CpeFinanceInvoice:
    return CpeFinanceInvoice(
        city_id=1,
        invoice_number="X",
        contract_code="C00190116O",
        invoice_date=invoice_date,
        due_date=due_date,
        period_start=period_start,
        period_end=period_end,
        total_ht=1000.0,
    )


_ANCHOR = CpeFinanceLine(city_id=1, row_number=1, market="P1", billed_item="P1", amount_ht=1000.0)


def test_acompte_echeance_fin_periode_editee_apres_is_coherent():
    """Echeance 31/03 = fin de periode, edition 01/04 (apres) -> coherent (ex CFN8)."""
    inv = _invoice(date(2026, 4, 1), date(2026, 3, 31), date(2026, 1, 1), date(2026, 3, 31))
    control = _control_invoice_timeline(inv, _ANCHOR)
    assert control.status == "ok"


def test_acompte_mensuel_echeance_fin_periode_is_coherent():
    """Acompte mensuel : echeance 31/01 = fin de periode, edition 25/02 -> coherent (ex LE97)."""
    inv = _invoice(date(2026, 2, 25), date(2026, 1, 31), date(2026, 1, 1), date(2026, 1, 31))
    control = _control_invoice_timeline(inv, _ANCHOR)
    assert control.status == "ok"


def test_acompte_echeance_debut_periode_editee_apres_is_coherent():
    """Echeance 01/05 = debut de periode, edition 04/05 (acompte) -> coherent (ex HGA8)."""
    inv = _invoice(date(2026, 5, 4), date(2026, 5, 1), date(2026, 5, 1), date(2026, 5, 31))
    control = _control_invoice_timeline(inv, _ANCHOR)
    assert control.status == "ok"


def test_regularisation_editee_longtemps_apres_echeance_is_coherent():
    """Regularisation : echeance dans la periode, edition 8 mois plus tard -> coherent (ex ZFXGP4)."""
    inv = _invoice(date(2025, 12, 9), date(2025, 3, 24), date(2025, 3, 1), date(2025, 3, 31))
    control = _control_invoice_timeline(inv, _ANCHOR)
    assert control.status == "ok"


def test_echeance_avant_debut_periode_is_error():
    """Echeance 15/12/2025 anterieure au debut de periode 01/01/2026 -> vraie incoherence."""
    inv = _invoice(date(2026, 1, 5), date(2025, 12, 15), date(2026, 1, 1), date(2026, 3, 31))
    control = _control_invoice_timeline(inv, _ANCHOR)
    assert control.status == "error"


def test_normal_invoice_echeance_apres_edition_is_coherent():
    """Facture classique : echeance posterieure a l'edition -> coherent."""
    inv = _invoice(date(2026, 4, 1), date(2026, 5, 1), date(2026, 1, 1), date(2026, 3, 31))
    control = _control_invoice_timeline(inv, _ANCHOR)
    assert control.status == "ok"


def test_periode_inversee_is_error():
    """Debut de periode posterieur a la fin -> incoherence inchangee."""
    inv = _invoice(date(2026, 4, 1), date(2026, 5, 1), date(2026, 3, 31), date(2026, 1, 1))
    control = _control_invoice_timeline(inv, _ANCHOR)
    assert control.status == "error"
