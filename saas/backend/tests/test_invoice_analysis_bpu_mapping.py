from app.services.invoice_analysis import _tariff_code_for_site


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
