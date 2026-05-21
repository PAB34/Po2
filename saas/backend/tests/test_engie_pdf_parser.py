from app.services.invoice_parsers.engie_pdf import _match_family_total, _normalized_poste, _parse_invoice_line


def test_parse_invoice_line_keeps_negative_engie_adjustment_separate():
    line = "Consommation HC Saison haute du 02/04/26 au 01/05/26 -1 0,03970 -0,04 20.0%"

    parsed = _parse_invoice_line(line, "network")

    assert parsed is not None
    assert parsed["normalized_component"] == "network_variable"
    assert parsed["poste"] == "hch"
    assert parsed["quantity"] == -1.0
    assert parsed["amount_ht"] == -0.04


def test_match_family_total_reads_negative_credit_amount():
    assert _match_family_total("Electricite -24,00") == {"family": "electricity", "amount": -24.0}


def test_normalized_poste_reads_long_french_season_label():
    assert _normalized_poste("Consommation Heures Pleines Haute Saison du 01/01/26 au 10/01/26") == "hph"
