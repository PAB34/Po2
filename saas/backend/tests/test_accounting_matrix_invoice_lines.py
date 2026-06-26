from app.services import accounting_matrix_invoice_lines as invoice_line_svc


def test_source_normalization_accepts_frontend_and_backend_spellings():
    assert invoice_line_svc._normalize_source("energy-import") == "energy_import"
    assert invoice_line_svc._normalize_source("gas-totalenergies") == "gas_totalenergies"
    assert invoice_line_svc._normalize_source("cpe_dalkia") == "cpe_dalkia"
    assert invoice_line_svc._normalize_source(" fluides-import ") == "fluides_import"
