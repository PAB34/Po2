"""Rapprochement des libellés de site CVC ↔ patrimoine.

Cas issus du parc réel de Sète (audit 2026-08-17) : la similarité de chaîne brute
ratait des synonymes évidents et rapprochait des bâtiments de nature différente
partageant un patronyme. Ces tests verrouillent les deux comportements.
"""
from __future__ import annotations

import pytest

from app.services.cvc import (
    _normalize_site_label,
    _site_key_tokens,
    _site_labels_compatible,
    _site_similarity,
    _site_type_tokens,
)

SEUIL = 0.72


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("VDS-ENS 17.03 GS - Elémentaire PAUL LANGEVIN (SUD)", "elementaire paul langevin sud"),
        ("VDS-BAM 06 Ateliers MENUISERIE", "ateliers menuiserie"),
        ("CCAS 10 VILLA D'ESTE", "villa d este"),
        ("EGLISE ST JOSEPH", "eglise saint joseph"),
    ],
)
def test_normalize_strips_codification_and_expands_aliases(raw, expected):
    assert _normalize_site_label(raw) == expected


@pytest.mark.parametrize(
    "source, target",
    [
        # Synonyme SAINT/ST + mot intercalé : ratés par la similarité brute (0,70).
        ("EGLISE SAINT JOSEPH", "EGLISE CATHOLIQUE ST JOSEPH"),
        # Préfixe « LES NOUVEAUX » : même bâtiment.
        ("BAINS DOUCHES", "LES NOUVEAUX BAINS DOUCHES"),
        # Préfixe de codification interne à retirer.
        ("VDS-ENS 17.03 GS - Elémentaire PAUL LANGEVIN (SUD)", "Elémentaire PAUL LANGEVIN"),
        # Libellé source contenu dans un libellé patrimoine plus long.
        ("AMITIE DE LA CORNICHE", "ESPACE DE L AMITIE DE LA CORNICHE - BOULEVARD"),
    ],
)
def test_vrais_rapprochements_atteignent_le_seuil(source, target):
    assert _site_similarity(source, target) >= SEUIL


@pytest.mark.parametrize(
    "source, target, motif",
    [
        # Nature différente malgré le patronyme commun (le faux positif observé).
        ("STADE LOUIS MICHEL", "RESTAURANT SCOLAIRE LOUISE MICHEL", "nature"),
        # Même nature mais nom distinctif différent.
        ("CIMETIERE MARIN", "CIMETIERE LE PY", "nom distinctif"),
        # Aucun token distinctif commun.
        ("AMITIE DE LA CORNICHE", "QUAI DE LA CONSIGNE", "aucun token commun"),
        ("CLASSE RELAIS", "LA PASSERELLE", "aucun token commun"),
    ],
)
def test_faux_positifs_sont_rejetes(source, target, motif):
    assert _site_similarity(source, target) == 0.0, motif


def test_garde_fou_nature_batiment():
    assert _site_type_tokens("STADE LOUIS MICHEL") == {"stade"}
    assert _site_type_tokens("RESTAURANT SCOLAIRE LOUISE MICHEL") == {"restaurant"}
    assert not _site_labels_compatible("STADE LOUIS MICHEL", "RESTAURANT SCOLAIRE LOUISE MICHEL")


def test_garde_fou_tokens_distinctifs():
    assert _site_key_tokens("CIMETIERE MARIN") == {"marin"}
    assert _site_key_tokens("CIMETIERE LE PY") == {"py"}
    assert not _site_labels_compatible("CIMETIERE MARIN", "CIMETIERE LE PY")


def test_nature_absente_d_un_cote_reste_compatible():
    # « AMITIE DE LA CORNICHE » ne porte pas de nature : ne pas rejeter d'office.
    assert _site_labels_compatible("AMITIE DE LA CORNICHE", "ESPACE DE L AMITIE DE LA CORNICHE")


def test_libelle_vide_ne_matche_pas():
    assert _site_similarity("", "EGLISE SAINT JOSEPH") == 0.0
    assert _site_similarity("EGLISE SAINT JOSEPH", None) == 0.0
