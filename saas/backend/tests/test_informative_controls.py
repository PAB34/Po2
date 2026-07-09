"""Catégorie « informatif » : écart conso ENEDIS + regroupement absent (non bloquants)."""

from app.services.invoice_analysis import _apply_invoice_severity_policy


def test_consumption_and_regroupement_become_info():
    issues = [
        {"severity": "anomaly", "code": "CONSUMPTION_ENEDIS_MISMATCH", "message": "", "scope": "s"},
        {"severity": "warning", "code": "MISSING_REGROUPEMENT", "message": "", "scope": "s"},
        {"severity": "warning", "code": "CONSUMPTION_LOAD_CURVE_MISMATCH", "message": "", "scope": "s"},
        {"severity": "anomaly", "code": "DOUBLE_BILLING_PERIOD", "message": "", "scope": "s"},
    ]
    _apply_invoice_severity_policy(issues)
    by_code = {i["code"]: i["severity"] for i in issues}
    assert by_code["CONSUMPTION_ENEDIS_MISMATCH"] == "info"
    assert by_code["MISSING_REGROUPEMENT"] == "info"
    assert by_code["CONSUMPTION_LOAD_CURVE_MISMATCH"] == "info"
    # Une vraie anomalie reste une anomalie (toujours bloquante).
    assert by_code["DOUBLE_BILLING_PERIOD"] == "anomaly"


def test_info_only_invoice_is_not_blocking():
    """severity « info » ne compte ni en erreur ni en warning → contrôle reste valide."""
    issues = [
        {"severity": "warning", "code": "CONSUMPTION_ENEDIS_MISMATCH", "message": "", "scope": "s"},
        {"severity": "warning", "code": "MISSING_REGROUPEMENT", "message": "", "scope": "s"},
    ]
    _apply_invoice_severity_policy(issues)
    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] in {"warning", "anomaly"})
    assert error_count == 0
    assert warning_count == 0  # → status "valid"
