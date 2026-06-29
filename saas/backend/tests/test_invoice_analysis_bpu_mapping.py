from types import SimpleNamespace

from app.services.invoice_analysis import (
    _bpu_component_field,
    _check_consumption_against_enedis,
    _check_period_continuity,
    _classify_invoice_fixed_charge,
    _resolve_bpu_fallback_source,
    _tariff_code_for_site,
)


def test_fallback_source_prefers_historical_then_configured() -> None:
    # R3 : tracer la source de prix réellement utilisée par le contrôle BPU
    assert _resolve_bpu_fallback_source(3, 0, "configured") == "historical"
    assert _resolve_bpu_fallback_source(0, 5, "configured") == "configured"
    assert _resolve_bpu_fallback_source(0, 5, "canonical_xlsx") == "canonical_xlsx"
    assert _resolve_bpu_fallback_source(2, 4, "canonical_xlsx") == "mixed"
    assert _resolve_bpu_fallback_source(0, 0, "configured") is None


def test_bpu_component_field_maps_gas_components() -> None:
    # R4 part A : composantes gaz lot 7 reconnues (readiness) sans casser l'élec
    assert _bpu_component_field("supply") == "pu_fourniture"
    assert _bpu_component_field("cee") == "pu_cee"
    assert _bpu_component_field("cee_precarite") == "pu_cee_precarite"
    assert _bpu_component_field("cpb") == "pu_cpb"
    assert _bpu_component_field("other") is None
    assert _bpu_component_field(None) is None


def test_classify_invoice_fixed_charge_is_conservative() -> None:
    # R4 part B : détection par libellé des seuls frais fixes contractuels listés
    assert _classify_invoice_fixed_charge("Abonnement Branchement Provisoire") == "branchement_provisoire"
    assert _classify_invoice_fixed_charge("ABONNEMENT CONTRAT TEMPORAIRE") == "contrat_temporaire"
    # "abonnement" générique NON reconnu (éviter faux positifs avec la part fixe TURPE)
    assert _classify_invoice_fixed_charge("Abonnement mensuel") is None
    assert _classify_invoice_fixed_charge("Consommation HPH") is None
    assert _classify_invoice_fixed_charge(None) is None


def test_xlsx_c5_cu_with_four_periods_maps_to_cu4() -> None:
    site = {
        "segment": "C5",
        "tariff_code": "CU",
        "invoice_lines": [
            {"normalized_component": "supply", "poste": "hph"},
            {"normalized_component": "supply", "poste": "hch"},
            {"normalized_component": "supply", "poste": "hpe"},
            {"normalized_component": "supply", "poste": "hce"},
        ],
    }

    assert _tariff_code_for_site(site) == "CU4"


def test_xlsx_c5_cu_base_only_maps_to_cu() -> None:
    site = {
        "segment": "C5",
        "tariff_code": "CU",
        "invoice_lines": [{"normalized_component": "supply", "poste": "base"}],
    }

    assert _tariff_code_for_site(site) == "CU"


def test_xlsx_c2_segment_maps_to_c2_even_without_tariff_label() -> None:
    site = {
        "segment": "C2",
        "tariff_code": "CU",
        "invoice_lines": [{"normalized_component": "supply", "poste": "hph"}],
    }

    assert _tariff_code_for_site(site) == "C2"


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows


class _FakeDb:
    def __init__(self, previous_imports):
        self.previous_imports = previous_imports

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self.previous_imports)


def _invoice_import(**overrides):
    values = {
        "id": 2,
        "city_id": 1,
        "invoice_number": "CURRENT",
        "original_filename": "current.csv",
        "supplier_guess": "EDF",
        "source": "edf_csv_export",
        "sha256": "current-sha",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _period_site(**overrides):
    values = {
        "prm_id": "24381620657920",
        "fic_number": "2010006564690",
        "period_start": "2025-12-16",
        "period_end": "2025-12-31",
        "total_ttc": 645.51,
        "total_consumption_kwh": 1342.0,
    }
    values.update(overrides)
    return values


def test_period_control_explains_exact_duplicate_reissue() -> None:
    previous = _invoice_import(
        id=1,
        invoice_number="10248500902",
        analysis_result={"sites": [_period_site()]},
        analysis_result_json="{}",
    )
    current = _invoice_import(invoice_number="10250533593")
    issues = []
    summary = {"checked_sites": 0, "gaps": 0, "overlaps": 0, "explained_overlaps": 0, "missing_references": 0}

    _check_period_continuity(
        _FakeDb([previous]),
        current,
        [_period_site()],
        lambda severity, code, message, scope="document": issues.append({"severity": severity, "code": code, "message": message, "scope": scope}),
        summary,
        "EDF",
    )

    assert [issue["code"] for issue in issues] == ["DUPLICATE_EXPORT_OR_REISSUE"]
    assert issues[0]["severity"] == "explained"
    assert summary["overlaps"] == 0
    assert summary["explained_overlaps"] == 1


def test_period_control_explains_short_supplier_switch_gap() -> None:
    previous = _invoice_import(
        id=1,
        invoice_number="10248500902",
        supplier_guess="EDF",
        analysis_result={
            "sites": [
                _period_site(
                    fic_number="2010006564690",
                    period_start="2025-12-07",
                    period_end="2025-12-31",
                    total_ttc=332.78,
                    total_consumption_kwh=820.0,
                )
            ]
        },
        analysis_result_json="{}",
    )
    current = _invoice_import(invoice_number="130000078078", supplier_guess="ENGIE", source="engie_xlsx_import")
    issues = []
    summary = {"checked_sites": 0, "gaps": 0, "overlaps": 0, "explained_overlaps": 0, "missing_references": 0}

    _check_period_continuity(
        _FakeDb([previous]),
        current,
        [
            _period_site(
                fic_number="820006337746",
                period_start="2026-01-08",
                period_end="2026-02-07",
                total_ttc=350.0,
                total_consumption_kwh=900.0,
            )
        ],
        lambda severity, code, message, scope="document": issues.append({"severity": severity, "code": code, "message": message, "scope": scope}),
        summary,
        "ENGIE",
    )

    assert [issue["code"] for issue in issues] == ["SUPPLIER_SWITCH_GAP_EXPLAINED"]
    assert issues[0]["severity"] == "explained"
    assert summary["gaps"] == 0
    assert summary["explained_overlaps"] == 1


def test_fixed_charge_only_site_without_period_is_explained_once() -> None:
    site = _period_site(
        prm_id="24329232838393",
        period_start=None,
        period_end=None,
        total_ttc=7.57,
        total_consumption_kwh=None,
        invoice_lines=[
            {"normalized_component": "subscription", "amount_ht": 4.1},
            {"normalized_component": "network_fixed_total", "amount_ht": 1.0},
            {"normalized_component": "cta", "amount_ht": 0.2},
        ],
    )
    current = _invoice_import(invoice_number="10248629137")
    issues = []
    period_summary = {"checked_sites": 0, "gaps": 0, "overlaps": 0, "explained_overlaps": 0, "missing_references": 0}
    consumption_summary = {"checked_sites": 0, "mismatches": 0, "missing_references": 0, "partial_references": 0}

    _check_period_continuity(
        _FakeDb([]),
        current,
        [site],
        lambda severity, code, message, scope="document": issues.append({"severity": severity, "code": code, "message": message, "scope": scope}),
        period_summary,
        "EDF",
    )
    _check_consumption_against_enedis(
        [site],
        lambda severity, code, message, scope="document": issues.append({"severity": severity, "code": code, "message": message, "scope": scope}),
        consumption_summary,
    )

    assert [issue["code"] for issue in issues] == ["FIXED_CHARGE_PERIOD_NOT_APPLICABLE"]
    assert issues[0]["severity"] == "explained"
    assert period_summary["missing_references"] == 0
    assert consumption_summary["missing_references"] == 0
