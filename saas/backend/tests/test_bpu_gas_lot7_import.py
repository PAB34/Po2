import pandas as pd

from app.scripts.import_bpu_gas_lot7 import parse_gas_lot7_frame


def test_parse_gas_lot7_frame_preserves_distinct_gas_components() -> None:
    frame = pd.DataFrame(
        [
            {
                "Période": 2026,
                "Profil gaz": "T2",
                "Niveau de consommation": "Entre 6 000 et 300 000 kWh/an",
                "PU fourniture ferme 2026\n(EUR HT/MWh)": 35.23,
                "PU CEE classique 2026\n(EUR HT/MWh)": 3.89,
                "PU CEE précarité 2026\n(EUR HT/MWh)": 3.06,
                "PU CPB 2026\n(EUR HT/MWh)": 0.41,
                "PU GO 2026\n(EUR HT/MWh)": 16.25,
                "Observation": "CEE provisoires.",
            }
        ]
    )

    profiles = parse_gas_lot7_frame(frame)

    assert len(profiles) == 1
    assert profiles[0].profile == "T2"
    assert profiles[0].cee_classique == 3.89
    assert profiles[0].cee_precarite == 3.06
    assert profiles[0].cpb == 0.41
