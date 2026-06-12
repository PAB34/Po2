from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DjuProfile:
    code: str
    label: str
    heating_base_c: float
    cooling_base_c: float | None
    station_label: str
    source_label: str
    reference_dju: float | None = None
    reference_period: str | None = None
    heating_period: str | None = None
    contractual: bool = False
    compliant_source: bool = False
    notes: str | None = None


DALKIA_CONTRACT_PROFILE = DjuProfile(
    code="dalkia_contractuel",
    label="DALKIA contractuel",
    heating_base_c=18.0,
    cooling_base_c=None,
    station_label="Montpellier",
    source_label="METEOCLIM COSTIC",
    reference_dju=1426.0,
    reference_period="1981-2010",
    heating_period="1er octobre -> 31 mai, puis dates effectives de chauffe",
    contractual=True,
    compliant_source=False,
    notes=(
        "Le contrat impose Montpellier / METEOCLIM COSTIC. Le moteur actuel reconstitue les DJU "
        "depuis Open-Meteo et doit etre qualifie tant que la station/source contractuelle n'est pas branchee."
    ),
)


EXPLOITATION_SETE_PROFILE = DjuProfile(
    code="exploitation_sete",
    label="Exploitation patrimoine Sete",
    heating_base_c=18.0,
    cooling_base_c=22.0,
    station_label="Sete",
    source_label="Open-Meteo archive",
    reference_dju=None,
    reference_period=None,
    heating_period="Reglage exploitation courant",
    contractual=False,
    compliant_source=True,
)


def dju_profile_payload(profile: DjuProfile) -> dict:
    return {
        "profile_code": profile.code,
        "profile_label": profile.label,
        "heating_base_c": profile.heating_base_c,
        "cooling_base_c": profile.cooling_base_c,
        "station_label": profile.station_label,
        "source_label": profile.source_label,
        "reference_dju": profile.reference_dju,
        "reference_period": profile.reference_period,
        "heating_period": profile.heating_period,
        "contractual": profile.contractual,
        "compliant_source": profile.compliant_source,
        "notes": profile.notes,
    }
