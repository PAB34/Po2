"""Suppression des contrôles non pertinents pour l'éclairage public EDF (sujet #4)."""

from app.services.invoice_analysis import _suppress_supplier_specific_controls


def _issues():
    return [
        {"severity": "warning", "code": "SUPPLIER_CONTRACT_MISMATCH", "message": "", "scope": "s"},
        {"severity": "warning", "code": "PERIOD_MISSING", "message": "", "scope": "s"},
        {"severity": "warning", "code": "CONSUMPTION_REFERENCE_MISSING", "message": "", "scope": "s"},
        {"severity": "anomaly", "code": "DOUBLE_BILLING_PERIOD", "message": "", "scope": "s"},
        {"severity": "error", "code": "BPU_PRICE_MISMATCH", "message": "", "scope": "s"},
    ]


def test_edf_suppresses_structural_codes_keeps_real_anomalies():
    issues = _issues()
    _suppress_supplier_specific_controls(issues, "EDF")
    codes = {i["code"] for i in issues}
    assert "SUPPLIER_CONTRACT_MISMATCH" not in codes
    assert "PERIOD_MISSING" not in codes
    assert "CONSUMPTION_REFERENCE_MISSING" not in codes
    # Les vraies anomalies / écarts restent.
    assert codes == {"DOUBLE_BILLING_PERIOD", "BPU_PRICE_MISMATCH"}


def test_engie_is_untouched():
    issues = _issues()
    _suppress_supplier_specific_controls(issues, "ENGIE")
    assert len(issues) == 5


def test_supplier_none_is_untouched():
    issues = _issues()
    _suppress_supplier_specific_controls(issues, None)
    assert len(issues) == 5
