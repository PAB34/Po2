from datetime import date
from decimal import Decimal

from app.models.bpu import (
    BpuDocument,
    BpuFixedCharge,
    BpuPriceComponent,
    BpuSegment,
    BpuTimePeriod,
)
from app.services.invoice_bpu import (
    FixedChargeReference,
    HistoricalBpuPrice,
    fixed_charge_references_from_rows,
    historical_bpu_prices_from_rows,
    historical_segment_code_for_site,
    normalize_bpu_supplier,
    resolve_fixed_charge,
    resolve_historical_bpu_price,
)


def test_historical_bpu_rows_become_invoice_references() -> None:
    references = historical_bpu_prices_from_rows(
        [
            (
                BpuDocument(
                    id=4,
                    supplier="EDF",
                    valid_year=2024,
                    lot_number=1,
                    pdf_filename="BPU 2024 LOT 1 Elec.pdf",
                ),
                BpuSegment(id=8, segment_code="C4"),
                BpuTimePeriod(id=12, period_code="HPH"),
                BpuPriceComponent(component_type="fourniture", price_value_eur_per_mwh=Decimal("88.17")),
            )
        ]
    )

    assert references == [
        HistoricalBpuPrice(
            document_id=4,
            supplier="EDF",
            valid_year=2024,
            lot_number=1,
            segment_code="C4",
            period_code="HPH",
            component_type="fourniture",
            price_eur_per_mwh=Decimal("88.17"),
            pdf_filename="BPU 2024 LOT 1 Elec.pdf",
        )
    ]


def test_resolve_historical_bpu_price_requires_exact_period_context() -> None:
    reference = HistoricalBpuPrice(
        document_id=4,
        supplier="EDF",
        valid_year=2024,
        lot_number=1,
        segment_code="C4",
        period_code="HPH",
        component_type="fourniture",
        price_eur_per_mwh=Decimal("88.17"),
        pdf_filename="BPU 2024 LOT 1 Elec.pdf",
    )
    site = {"segment": "C4", "period_start": date(2024, 2, 1)}

    assert resolve_historical_bpu_price(
        [reference],
        site,
        {"normalized_component": "supply", "poste": "hph"},
    ) == reference
    assert resolve_historical_bpu_price(
        [reference],
        site,
        {"normalized_component": "supply", "poste": "hpe"},
    ) is None
    assert resolve_historical_bpu_price(
        [reference],
        {"segment": "C4", "period_start": date(2025, 2, 1)},
        {"normalized_component": "supply", "poste": "hph"},
    ) is None


def test_resolve_historical_bpu_price_keeps_ambiguous_market_docs_out() -> None:
    site = {"segment": "C2", "period_start": date(2022, 4, 1)}
    line = {"normalized_component": "capacity", "poste": "pointe"}
    references = [
        HistoricalBpuPrice(
            document_id=1,
            supplier="EDF",
            valid_year=2022,
            lot_number=1,
            segment_code="C2",
            period_code="POINTE",
            component_type="capacite",
            price_eur_per_mwh=Decimal("1.00"),
            pdf_filename="first.pdf",
        ),
        HistoricalBpuPrice(
            document_id=2,
            supplier="EDF",
            valid_year=2022,
            lot_number=1,
            segment_code="C2",
            period_code="POINTE",
            component_type="capacite",
            price_eur_per_mwh=Decimal("2.00"),
            pdf_filename="second.pdf",
        ),
    ]

    assert resolve_historical_bpu_price(references, site, line) is None


def test_bpu_supplier_and_segment_normalization_stays_conservative() -> None:
    assert normalize_bpu_supplier("Electricite de France") == "EDF"
    assert normalize_bpu_supplier("ENGIE Entreprises") == "ENGIE"
    assert historical_segment_code_for_site({"segment": "C5", "site_name": "Eclairage public centre"}) == "C5_EP"
    # R2 : C5 hors EP → BATIMENT (correspondance avec le segment_code en base issu du BPU historique)
    assert historical_segment_code_for_site({"segment": "C5", "site_name": "Gymnase"}) == "BATIMENT"


def test_historical_segment_code_c5_batiment_resolves_to_batiment() -> None:
    # R2 : tous les C5 hors éclairage public → "BATIMENT" (segment stocké en base
    # pour le BPU ENGIE Lot 1 2026 via _normalize_segment("Bâtiment", ...))
    assert historical_segment_code_for_site({"segment": "C5"}) == "BATIMENT"
    assert historical_segment_code_for_site({"segment": "c5", "site_name": "Salle polyvalente"}) == "BATIMENT"
    assert historical_segment_code_for_site({"segment": "C5", "tariff_option_label": "CU4"}) == "BATIMENT"
    # EP reste inchangé
    assert historical_segment_code_for_site({"segment": "C5", "regroupement": "Eclairage public"}) == "C5_EP"
    assert historical_segment_code_for_site({"segment": "C5", "tariff_option_label": "Éclairage public"}) == "C5_EP"


def test_resolve_historical_bpu_price_c5_batiment() -> None:
    # Le moteur doit résoudre un prix ENGIE 2026 C5 Bâtiment / HPH / fourniture
    reference = HistoricalBpuPrice(
        document_id=20,
        supplier="ENGIE",
        valid_year=2026,
        lot_number=1,
        segment_code="BATIMENT",
        period_code="HPH",
        component_type="fourniture",
        price_eur_per_mwh=Decimal("105.91"),
        pdf_filename="2025_18_MS1_BPU_ENGIE_LOT_1.pdf",
    )
    site = {"segment": "C5", "period_start": date(2026, 2, 1)}
    resolved = resolve_historical_bpu_price(
        [reference],
        site,
        {"normalized_component": "supply", "poste": "hph"},
    )
    assert resolved == reference

    # Un site éclairage public ne doit pas matcher le segment BATIMENT
    assert resolve_historical_bpu_price(
        [reference],
        {"segment": "C5", "site_name": "Eclairage public centre", "period_start": date(2026, 2, 1)},
        {"normalized_component": "supply", "poste": "hph"},
    ) is None


def test_normalize_bpu_supplier_recognizes_totalenergies() -> None:
    assert normalize_bpu_supplier("TotalEnergies") == "TOTALENERGIES"
    assert normalize_bpu_supplier("TOTALENERGIES") == "TOTALENERGIES"
    assert normalize_bpu_supplier("Total Energies Gaz") == "TOTALENERGIES"
    assert normalize_bpu_supplier(None) is None
    assert normalize_bpu_supplier("inconnu") is None


def test_historical_segment_code_recognizes_gas_profiles() -> None:
    assert historical_segment_code_for_site({"segment": "T1"}) == "T1"
    assert historical_segment_code_for_site({"segment": "T2"}) == "T2"
    assert historical_segment_code_for_site({"segment": "T3"}) == "T3"
    assert historical_segment_code_for_site({"segment": "T4"}) == "T4"
    assert historical_segment_code_for_site({"segment": "t2"}) == "T2"
    assert historical_segment_code_for_site({"segment": "T5"}) is None


def test_resolve_historical_bpu_price_gas_lot7() -> None:
    reference = HistoricalBpuPrice(
        document_id=10,
        supplier="TOTALENERGIES",
        valid_year=2026,
        lot_number=7,
        segment_code="T2",
        period_code="BASE",
        component_type="cee_precarite",
        price_eur_per_mwh=Decimal("3.06"),
        pdf_filename="BPU_2026_Lots_1_2_et_7.xlsx",
    )
    site = {"segment": "T2", "period_start": date(2026, 3, 1)}

    resolved = resolve_historical_bpu_price(
        [reference],
        site,
        {"normalized_component": "cee_precarite", "poste": "base"},
    )
    assert resolved == reference

    # Un autre profil ne doit pas matcher
    assert resolve_historical_bpu_price(
        [reference],
        {"segment": "T1", "period_start": date(2026, 3, 1)},
        {"normalized_component": "cee_precarite", "poste": "base"},
    ) is None

    # Une année hors validité ne doit pas matcher
    assert resolve_historical_bpu_price(
        [reference],
        {"segment": "T2", "period_start": date(2025, 3, 1)},
        {"normalized_component": "cee_precarite", "poste": "base"},
    ) is None


def test_fixed_charge_references_from_rows() -> None:
    references = fixed_charge_references_from_rows(
        [
            (
                BpuDocument(
                    id=3,
                    supplier="EDF",
                    valid_year=2025,
                    lot_number=1,
                    pdf_filename="EDF_MS1_LOT_1_AVENANT_6_BPU_2025.pdf",
                ),
                BpuFixedCharge(
                    document_id=3,
                    charge_type="branchement_provisoire",
                    charge_label="Abonnement Branchement Provisoire",
                    charge_value=Decimal("120"),
                    charge_unit="€HT/BP/Mois",
                    charge_value_eur_per_month=Decimal("120"),
                    applicable_from=date(2023, 1, 1),
                    applicable_to=date(2025, 12, 31),
                ),
            )
        ]
    )
    assert references == [
        FixedChargeReference(
            document_id=3,
            supplier="EDF",
            charge_type="branchement_provisoire",
            charge_label="Abonnement Branchement Provisoire",
            value_eur_per_month=Decimal("120"),
            pdf_filename="EDF_MS1_LOT_1_AVENANT_6_BPU_2025.pdf",
            valid_from=date(2023, 1, 1),
            valid_to=date(2025, 12, 31),
        )
    ]


def test_resolve_fixed_charge_respects_validity_and_ambiguity() -> None:
    ref = FixedChargeReference(
        document_id=3,
        supplier="EDF",
        charge_type="branchement_provisoire",
        charge_label="Abonnement Branchement Provisoire",
        value_eur_per_month=Decimal("120"),
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
    )
    assert resolve_fixed_charge([ref], "branchement_provisoire", date(2024, 6, 1)) == ref
    # Hors fenêtre de validité
    assert resolve_fixed_charge([ref], "branchement_provisoire", date(2026, 6, 1)) is None
    # Mauvais type
    assert resolve_fixed_charge([ref], "contrat_temporaire", date(2024, 6, 1)) is None

    # Deux documents avec des montants différents pour la même date → abstention
    ref_other = FixedChargeReference(
        document_id=4,
        supplier="EDF",
        charge_type="branchement_provisoire",
        charge_label="Abonnement Branchement Provisoire",
        value_eur_per_month=Decimal("150"),
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
    )
    assert resolve_fixed_charge([ref, ref_other], "branchement_provisoire", date(2024, 6, 1)) is None


def _bat_ref(segment_code, price):
    return HistoricalBpuPrice(
        document_id=30, supplier="ENGIE", valid_year=2026, lot_number=1,
        segment_code=segment_code, period_code="HPH", component_type="fourniture",
        price_eur_per_mwh=Decimal(str(price)), pdf_filename="engie2026.pdf",
    )


def _line():
    return {"normalized_component": "supply", "poste": "hph"}


def test_resolve_granular_batiment_2026_no_regression_and_gain():
    # C5 batiment -> matche la grille granulaire BATIMENT_BT36 (nouveau marche).
    site_c5 = {"segment": "C5", "period_start": date(2026, 2, 1)}
    assert resolve_historical_bpu_price([_bat_ref("BATIMENT_BT36", 105.9)], site_c5, _line()).segment_code == "BATIMENT_BT36"
    # ... et garde la compat avec l'ancien code collapse BATIMENT (pre re-import).
    assert resolve_historical_bpu_price([_bat_ref("BATIMENT", 105.9)], site_c5, _line()).segment_code == "BATIMENT"

    # C4 batiment -> desormais matche BATIMENT_BT (avant : 0 match).
    site_c4 = {"segment": "C4", "period_start": date(2026, 2, 1)}
    assert resolve_historical_bpu_price([_bat_ref("BATIMENT_BT", 107.8)], site_c4, _line()).segment_code == "BATIMENT_BT"
    # C2 batiment -> matche BATIMENT_HTA.
    site_c2 = {"segment": "C2", "period_start": date(2026, 2, 1)}
    assert resolve_historical_bpu_price([_bat_ref("BATIMENT_HTA", 109.5)], site_c2, _line()).segment_code == "BATIMENT_HTA"


def test_resolve_precision_c2_not_lumped():
    # Precision preservee : un site C2 matche la grille C2 exacte (ancien marche)...
    ref_c2 = HistoricalBpuPrice(
        document_id=31, supplier="EDF", valid_year=2025, lot_number=1, segment_code="C2",
        period_code="HPH", component_type="fourniture", price_eur_per_mwh=Decimal("84.47"),
        pdf_filename="edf2025.pdf",
    )
    site_c2 = {"segment": "C2", "period_start": date(2025, 6, 1)}
    assert resolve_historical_bpu_price([ref_c2], site_c2, _line()).segment_code == "C2"
    # ... et ne matche PAS un BATIMENT_BT (mauvais bucket -> pas de faux match).
    assert resolve_historical_bpu_price([_bat_ref("BATIMENT_BT", 107.8)], site_c2, _line()) is None


def test_tension_bucket_and_normalize_batiment():
    from app.scripts.import_bpu_xlsx import _normalize_segment, _tension_bucket
    assert _tension_bucket("HTA") == "HTA"
    assert _tension_bucket("BT > 36 kVA - C4") == "BT"
    assert _tension_bucket("BT ≤ 36 kVA SDT CU4 / MU4") == "BT36"
    assert _tension_bucket("BT") == "BT"
    assert _tension_bucket(None) is None
    # « Bâtiment » 2026 -> code granulaire ; ancien « Sites C4 » -> inchange.
    assert _normalize_segment("Bâtiment", None, "HTA")[0] == "BATIMENT_HTA"
    assert _normalize_segment("Bâtiment", None, "BT ≤ 36 kVA MUDT")[0] == "BATIMENT_BT36"
    assert _normalize_segment("Sites C4", None, None)[0] == "C4"
    assert _normalize_segment("Sites C5 Eclairage Public", None, None)[0] == "C5_EP"


def test_resolve_edf_building_no_poste_matches_c5_bat():
    # Facture EDF batiment C5, ligne fourniture SANS poste (mono-poste) -> C5_BAT_1 / BASE (ancien marche).
    ref = HistoricalBpuPrice(
        document_id=40, supplier="EDF", valid_year=2025, lot_number=3, segment_code="C5_BAT_1",
        period_code="BASE", component_type="fourniture", price_eur_per_mwh=Decimal("105.86"),
        pdf_filename="edf2025_lot3.pdf",
    )
    site = {"segment": "C5", "site_name": "CONSERVATOIRE", "period_start": date(2025, 6, 1)}
    line = {"normalized_component": "supply", "poste": None}  # poste vide -> BASE
    resolved = resolve_historical_bpu_price([ref], site, line)
    assert resolved is not None and resolved.segment_code == "C5_BAT_1"

    # Un site eclairage public (nom explicite) ne matche PAS le batiment C5_BAT (candidats differents).
    site_ep = {"segment": "C5", "site_name": "Eclairage public rue X", "period_start": date(2025, 6, 1)}
    assert resolve_historical_bpu_price([ref], site_ep, line) is None
