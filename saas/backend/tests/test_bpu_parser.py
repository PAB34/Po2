from app.models.bpu import COMPONENT_CAPACITE, COMPONENT_CEE, COMPONENT_FOURNITURE, COMPONENT_GO
from app.services.bpu import (
    _detect_component_header,
    _detect_segment_code,
    _extract_components_from_table_line,
    _extract_segments,
)


def test_detect_component_header_preserves_column_order() -> None:
    assert _detect_component_header("Poste Fourniture Capacite CEE GO Total") == [
        COMPONENT_FOURNITURE,
        COMPONENT_CAPACITE,
        COMPONENT_CEE,
        COMPONENT_GO,
    ]


def test_extract_components_from_table_line_maps_prices_to_header_order() -> None:
    components = _extract_components_from_table_line(
        "HPH     142,50      4,10      8,25      1,70      156,55",
        [COMPONENT_FOURNITURE, COMPONENT_CAPACITE, COMPONENT_CEE, COMPONENT_GO],
    )

    assert components == [
        (COMPONENT_FOURNITURE, 142.50),
        (COMPONENT_CAPACITE, 4.10),
        (COMPONENT_CEE, 8.25),
        (COMPONENT_GO, 1.70),
    ]


def test_extract_segments_reads_layout_table_rows() -> None:
    text = """
    BT <= 36 kVA - CU4
    Poste       Fourniture      Capacite      CEE      GO
    HPH         142,50          4,10          8,25     1,70
    HCH         115,00          3,90          7,80     1,50
    """

    segments = _extract_segments(text, default_unit="EUR/MWh")

    assert len(segments) == 1
    assert segments[0].segment_code == "CU4"
    assert [period.period_code for period in segments[0].periods] == ["HPH", "HCH"]

    hph_components = segments[0].periods[0].components
    assert [(c.component_type, c.price_value) for c in hph_components] == [
        (COMPONENT_FOURNITURE, 142.50),
        (COMPONENT_CAPACITE, 4.10),
        (COMPONENT_CEE, 8.25),
        (COMPONENT_GO, 1.70),
    ]


def test_detect_segment_code_prefers_tariff_option_over_voltage_family() -> None:
    assert _detect_segment_code("BT <= 36 kVA - CU4") == "CU4"
