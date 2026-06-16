from app.services.invoice_analysis import _resolve_bpu_fallback_source, _tariff_code_for_site


def test_fallback_source_prefers_historical_then_configured() -> None:
    # R3 : tracer la source de prix réellement utilisée par le contrôle BPU
    assert _resolve_bpu_fallback_source(3, 0, "configured") == "historical"
    assert _resolve_bpu_fallback_source(0, 5, "configured") == "configured"
    assert _resolve_bpu_fallback_source(0, 5, "canonical_xlsx") == "canonical_xlsx"
    assert _resolve_bpu_fallback_source(2, 4, "canonical_xlsx") == "mixed"
    assert _resolve_bpu_fallback_source(0, 0, "configured") is None


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
