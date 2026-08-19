"""Normalisation des adresses avant géocodage IGN.

Le référentiel patrimoine stocke les numéros de voirie zéro-comblés (`0208 AV DU
MARECHAL JUIN`). L'API GeoPF interprète mal ces zéros initiaux : elle rend le
centroïde de la rue au lieu du numéro exact, ce qui dégrade l'attachement IGN.

Le cas qui échouait vraiment est celui du **suffixe bis/ter collé au numéro**
(`0005B`) : sans lettre dans le motif, il n'y a aucune frontière de mot après les
chiffres et les zéros restaient. Constaté sur le référentiel réel : 5 adresses sur 177.
Vérifié auprès de GeoPF : `0005B BD JOLIOT CURIE` rend la rue seule, `5B BD JOLIOT
CURIE` rend bien le numéro `5bis`.
"""
from __future__ import annotations

import pytest

from app.services.building_naming import _strip_leading_zeros_in_address


@pytest.mark.parametrize(
    ("source", "attendu"),
    [
        # Numéro simple : cas déjà couvert auparavant.
        ("0208 AV DU MARECHAL JUIN", "208 AV DU MARECHAL JUIN"),
        ("0002 Impasse DE LA BORDIGUE", "2 Impasse DE LA BORDIGUE"),
        ("0875 QUAI DES MOULINS", "875 QUAI DES MOULINS"),
        # Suffixe bis/ter : le cas qui restait cassé.
        ("0005B BD JOLIOT CURIE", "5B BD JOLIOT CURIE"),
        ("0011B RUE DU DEPUTE MOLLE", "11B RUE DU DEPUTE MOLLE"),
        ("0030B AV VICTOR HUGO", "30B AV VICTOR HUGO"),
    ],
)
def test_retire_les_zeros_initiaux(source: str, attendu: str):
    assert _strip_leading_zeros_in_address(source) == attendu


@pytest.mark.parametrize(
    "source",
    [
        # Référence cadastrale normalisée : INSEE + préfixe + section + plan.
        # La mutiler casserait le rattachement à la parcelle.
        "34301000AI0009",
        # Millésime dans un nom de voie : aucun zéro initial, rien à toucher.
        "RUE DU 8 MAI 1945",
        "AVENUE DES EAUX BLANCHES",
        "",
    ],
)
def test_ne_touche_pas_aux_valeurs_sans_zeros_initiaux(source: str):
    assert _strip_leading_zeros_in_address(source) == source
