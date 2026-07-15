"""Parseur EDF : lignes fourniture par poste (kWh + prix unitaire dérivé)."""
from __future__ import annotations

from app.services.invoice_parsers.edf_csv import _supply_lines


def test_supply_lines_par_poste_avec_prix_unitaire():
    row = {
        "consommation_kwh_base": "937", "montant_htva_base": "99.19",
        "consommation_kwh_hp": "0", "montant_htva_hp": "0",
        "consommation_kwh_hpsh": "982", "montant_htva_hpsh": "106.02",  # -> hph
        "total_fourniture_elec_ht_euros": "205.21", "conso_elec_facturee_kwh": "1919",
    }
    lines = _supply_lines(row, "2025-01-01", "2025-01-31")
    by = {l["poste"]: l for l in lines}
    assert set(by) == {"base", "hph"}
    assert by["base"]["quantity"] == 937.0
    assert round(by["base"]["unit_price_ht"] * 1000, 2) == 105.86  # = BPU C5_BAT_1 BASE
    assert by["hph"]["quantity"] == 982.0
    assert round(by["hph"]["unit_price_ht"] * 1000, 2) == 107.96  # = BPU C4 HPH
    for l in lines:
        assert l["normalized_component"] == "supply" and l["unit_price_ht"] is not None


def test_supply_lines_repli_base_quand_pas_de_detail():
    # Pas de détail par poste -> repli BASE = total fourniture / conso totale.
    row = {"total_fourniture_elec_ht_euros": "126.32", "conso_elec_facturee_kwh": "1170"}
    lines = _supply_lines(row, None, None)
    assert len(lines) == 1 and lines[0]["poste"] == "base"
    assert round(lines[0]["unit_price_ht"] * 1000, 2) == 107.97  # 126.32/1170
