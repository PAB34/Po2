from types import SimpleNamespace

from app.services.cvc import _resolve_family


def ref(id_ligne: int, code: str, niveau_3: str | None, niveau_4: str | None, equipement: str):
    return SimpleNamespace(
        id=id_ligne,
        id_ligne=id_ligne,
        code_niveau_2=code,
        niveau_3=niveau_3,
        niveau_4=niveau_4,
        equipement=equipement,
    )


REFS = [
    ref(27, "A.1.1", "Menuiseries", None, "Vitrage"),
    ref(34, "A.1.2", "Voirie", None, "Chaussée"),
    ref(58, "A.1.2", "Pompe d'exhaure", None, "Pompe"),
    ref(68, "A.1.3", "Menuiseries intérieures", None, "Grilles de ventilation"),
    ref(91, "A.2.1", "Traitement d'eau", None, "Pompe doseuse"),
    ref(92, "A.2.1", "Traitement d'eau", None, "Filtre à sable"),
    ref(97, "A.2.1", "ECS", None, "Ballon de stockage d'eau chaude"),
    ref(118, "A.2.2", "Courant fort :", "Distribution Basse Tension", "Armoire électrique"),
    ref(162, "A.2.3", "Gestion technique", None, "Point de GTB/GTC"),
    ref(163, "A.2.3", "Production de chaleur :", None, "Chaudiere de type condensation"),
    ref(169, "A.2.3", "Production de chaleur :", None, "Chaudiere murale"),
    ref(179, "A.2.3", "Distribution de chaleur :", None, "Echangeur a plaques"),
    ref(181, "A.2.3", "Distribution de chaleur :", None, "Vannes, robinets, filtres"),
    ref(186, "A.2.3", "Distribution de chaleur :", "Pompes", "Circulateur chauffage"),
    ref(188, "A.2.3", "Distribution de chaleur :", None, "Vase d'expansion"),
    ref(213, "A.2.3", "Production de froid :", None, "Echangeur eau glacee"),
    ref(207, "A.2.3", "Production de froid :", "Générateur de production d'eau glacée", "Groupe à vis"),
    ref(221, "A.2.3", "Installation aérauliques :", "Centrales de traitement d'air", "CTA simple ou double flux à récupération d'énergie"),
    ref(236, "A.2.3", "Installations dites autonomes :", None, "Split - Multi-split"),
    ref(238, "A.2.3", "Pompes à chaleur Air/Air, Air/Eau, Eau/Eau", None, "PAC de type Air / Eau"),
    ref(307, "A.2.9", "Service de Reprographie :", None, "Plieuse"),
]


def resolve(famille: str, designation: str, marque: str | None = None, modele: str | None = None):
    return _resolve_family(famille, REFS, {}, designation, marque, modele)


def test_split_system_uses_cvc_split_reference():
    result = resolve("Split system", "UE clim DAIKIN 3", "Daikin", "RXB50CV1B")

    assert result is not None
    assert result.id_ligne == 236


def test_armoire_electrique_keeps_electrical_reference():
    result = resolve("Armoire électrique", "Tableau électrique")

    assert result is not None
    assert result.id_ligne == 118


def test_generic_other_does_not_fuzzy_match():
    result = resolve("Autre à qualifier", "Ensemble radiateurs")

    assert result is None


def test_cta_uses_air_handling_reference():
    result = resolve("Centrale Traitement Air", "CTA double flux")

    assert result is not None
    assert result.id_ligne == 221


def test_filter_does_not_fuzzy_match_to_vitrage():
    result = resolve("Filtre", "Filtre")

    assert result is None


def test_pac_uses_heat_pump_reference():
    result = resolve("Pompe à Chaleur", "UE Thermodynamique", "Daikin")

    assert result is not None
    assert result.id_ligne == 238


def test_counter_with_pac_label_stays_unmatched():
    result = resolve("Compteur", "CPT elec PAC")

    assert result is None


def test_cta_with_split_brand_keeps_air_handling_reference():
    result = resolve("Centrale Traitement Air", "CTA DAIKIN")

    assert result is not None
    assert result.id_ligne == 221


def test_boiler_with_heat_pump_brand_does_not_match_split_or_pac():
    result = resolve("Chaudiere", "Chaudiere Atlantic")

    assert result is not None
    assert result.id_ligne == 163


def test_vase_expansion_uses_expansion_vessel_reference():
    result = resolve("Vase expansion", "Vase expansion chauffage")

    assert result is not None
    assert result.id_ligne == 188


def test_gtb_gtc_uses_control_point_reference():
    result = resolve("GTB / GTC", "Automate GTB")

    assert result is not None
    assert result.id_ligne == 162
