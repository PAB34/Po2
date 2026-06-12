"""Registre déclaratif des fournisseurs d'énergie facturant la Ville.

Source unique de vérité pour la dimension multi-fournisseur de /energie/factures :
qui facture quoi (énergie), quel distributeur sert de référence de contrôle, sur
quel périmètre, et si l'import automatique de ses factures est déjà supporté.

Le distributeur (ENEDIS / GRDF) n'est PAS un fournisseur : il fournit la donnée
mesurée qui sert à contrôler la facture, pas un montant à payer.
"""

from __future__ import annotations

from dataclasses import dataclass

ELECTRICITY = "electricity"
GAS = "gas"

ENERGY_LABELS = {
    ELECTRICITY: "Électricité",
    GAS: "Gaz",
}


@dataclass(frozen=True)
class SupplierProfile:
    code: str           # identifiant canonique stocké en base (supplier_guess)
    label: str          # libellé d'affichage
    energy: str         # ELECTRICITY | GAS
    distributor: str | None  # référentiel de contrôle (ENEDIS / GRDF)
    scope_hint: str     # périmètre métier indicatif
    xlsx_supported: bool  # un parseur d'import existe-t-il déjà ?


SUPPLIERS: dict[str, SupplierProfile] = {
    "ENGIE": SupplierProfile(
        code="ENGIE",
        label="ENGIE",
        energy=ELECTRICITY,
        distributor="ENEDIS",
        scope_hint="Électricité bâtiments ville",
        xlsx_supported=True,
    ),
    "EDF": SupplierProfile(
        code="EDF",
        label="EDF",
        energy=ELECTRICITY,
        distributor="ENEDIS",
        scope_hint="Électricité éclairage public",
        xlsx_supported=False,
    ),
    "TOTALENERGIES": SupplierProfile(
        code="TOTALENERGIES",
        label="TotalEnergies",
        energy=GAS,
        distributor="GRDF",
        scope_hint="Gaz bâtiments ville",
        xlsx_supported=False,
    ),
}

# Variantes de libellé rencontrées (factures, anciens imports) -> code canonique.
_ALIASES = {
    "ENGIE": "ENGIE",
    "EDF": "EDF",
    "ELECTRICITE DE FRANCE": "EDF",
    "ÉLECTRICITÉ DE FRANCE": "EDF",
    "TOTAL": "TOTALENERGIES",
    "TOTALENERGIES": "TOTALENERGIES",
    "TOTAL ENERGIES": "TOTALENERGIES",
    "TOTALENERGIES GAZ": "TOTALENERGIES",
}


def normalize_code(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().upper()
    if key in SUPPLIERS:
        return key
    return _ALIASES.get(key)


def get(value: str | None) -> SupplierProfile | None:
    code = normalize_code(value)
    return SUPPLIERS.get(code) if code else None


def energy_for(value: str | None, default: str = ELECTRICITY) -> str:
    profile = get(value)
    return profile.energy if profile else default


def detect_from_filename(filename: str | None) -> SupplierProfile | None:
    if not filename:
        return None
    upper = filename.upper()
    if "ENGIE" in upper:
        return SUPPLIERS["ENGIE"]
    if "EDF" in upper or "ELECTRICITE" in upper:
        return SUPPLIERS["EDF"]
    if "TOTAL" in upper:
        return SUPPLIERS["TOTALENERGIES"]
    return None
