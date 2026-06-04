"""Detection du code site depuis le detail de prestation DALKIA.

Les sites du Lot 1 utilisent un espace (VDS-ENS 01), les piscines du Lot 2 un tiret
(VDS-PSC-01.01) ; les deux doivent etre detectes et normalises pour s'aligner sur le
referentiel DALKIA importe."""
from __future__ import annotations

import pytest

from app.services.cpe_accounting import _site_code


@pytest.mark.parametrize(
    "detail,expected",
    [
        # Piscines Lot 2 (separateur tiret) -> codes identiques au referentiel L2
        ("VDS-PSC-01.01 - COMPLEXE MAURICE CLAVEL - PISCINE", "VDS-PSC-01.01"),
        ("VDS-PSC-02.1-PISCINE PHILIPPE BIASCAMANO-PISC", "VDS-PSC-02.1"),
        ("VDS-PSC-01.02 gymnase", "VDS-PSC-01.02"),
        # Lot 1 (separateur espace) -> inchange
        ("VDS-ENS 01 Maternelle AGNES VARDA", "VDS-ENS 01"),
        ("VDS-SPORT 02.01 complexe", "VDS-SPORT 02.01"),
        ("VDS-BAM 14 POLICE MUNICIPALE", "VDS-BAM 14"),
        ("CCAS 04 Residence LE THONNAIRE", "CCAS 04"),
        # Pas de code -> None
        ("COMPLEXE MAURICE CLAVEL", None),
        ("BT66.1 - LGT DE FONCTION BIASCAMANO", None),
        ("", None),
        (None, None),
    ],
)
def test_site_code_detection(detail, expected):
    assert _site_code(detail) == expected
