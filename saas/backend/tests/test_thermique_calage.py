"""Calage d'une planche sur la référence du projet par deux points communs (S2, D173)."""
from __future__ import annotations

import json
import math
from types import SimpleNamespace

import pytest

from app.services import thermique_calage as calage


def _planche(identifiant: int, echelle: float = 100, calee: dict | None = None):
    return SimpleNamespace(id=identifiant, scale_denominator=echelle, calage_json=json.dumps(calee) if calee else None)


def test_deux_paires_donnent_la_rotation_l_echelle_et_le_decalage():
    # La cible est la source tournée de 90°, doublée et décalée de (100, 50).
    sim = calage.similitude([[0, 0], [100, 0]], [[100, 50], [100, 250]])
    assert calage.appliquer(sim, [0, 0]) == pytest.approx([100, 50])
    assert calage.appliquer(sim, [50, 30]) == pytest.approx([100 - 60, 50 + 100])
    assert math.hypot(sim["a"], sim["b"]) == pytest.approx(2)


def test_deux_points_trop_proches_sont_refuses():
    with pytest.raises(ValueError, match="trop proches"):
        calage.similitude([[0, 0], [5, 0]], [[0, 0], [100, 0]])


def test_une_planche_se_cale_sur_la_reference_directement():
    reference, niveau = _planche(1), _planche(2)
    resultat = calage.caler(niveau, reference, 1, [[0, 0], [100, 0]], [[10, 10], [110, 10]])
    assert calage.appliquer(resultat, [50, 0]) == pytest.approx([60, 10])
    assert resultat["reference_sheet_id"] == 1 and resultat["ecart_echelle_pct"] == 0


def test_une_planche_se_cale_en_chaine_par_une_planche_deja_calee():
    """R+2 calé sur R+1, lui-même calé sur la référence : la chaîne remonte à la référence."""
    r1_vers_ref = calage.similitude([[0, 0], [100, 0]], [[10, 10], [110, 10]])
    r1 = _planche(2, calee={**r1_vers_ref, "reference_sheet_id": 1})
    r2 = _planche(3)
    resultat = calage.caler(r2, r1, 1, [[0, 0], [100, 0]], [[5, 0], [105, 0]])
    # Un point de R+2 passe par R+1 (+5 en x) puis par la référence (+10, +10).
    assert calage.appliquer(resultat, [0, 0]) == pytest.approx([15, 10])


def test_on_ne_se_cale_que_sur_une_planche_calee_et_la_reference_ne_se_cale_pas():
    with pytest.raises(ValueError, match="Calez d'abord"):
        calage.caler(_planche(3), _planche(2), 1, [[0, 0], [100, 0]], [[0, 0], [100, 0]])
    with pytest.raises(ValueError, match="référence ne se cale pas"):
        calage.caler(_planche(1), _planche(2), 1, [[0, 0], [100, 0]], [[0, 0], [100, 0]])


def test_un_rapport_d_echelle_contraire_aux_echelles_declarees_se_voit():
    """Plan au 1/50 calé sur la référence au 1/100 : les longueurs PDF doivent être deux fois plus courtes."""
    resultat = calage.caler(_planche(2, echelle=50), _planche(1, echelle=100), 1, [[0, 0], [200, 0]], [[0, 0], [110, 0]])
    assert resultat["ecart_echelle_pct"] == pytest.approx(10.0)


def test_migration_0087_monte_et_redescend_isolee():
    import importlib.util
    from pathlib import Path

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    moteur = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("thermique_sheets", metadata, sa.Column("id", sa.Integer(), primary_key=True), sa.Column("north_json", sa.Text()))
    metadata.create_all(moteur)
    chemin = Path(__file__).parents[1] / "alembic" / "versions" / "0087_thermique_calage_planche.py"
    spec = importlib.util.spec_from_file_location("migration_0087", chemin)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with moteur.begin() as connexion:
        migration.op = Operations(MigrationContext.configure(connexion))
        migration.upgrade()
        assert "calage_json" in {c["name"] for c in inspect(connexion).get_columns("thermique_sheets")}
        migration.downgrade()
        assert "calage_json" not in {c["name"] for c in inspect(connexion).get_columns("thermique_sheets")}


def test_un_calage_fait_sur_une_ancienne_reference_ne_vaut_plus():
    ancien = _planche(2, calee={**calage.IDENTITE, "reference_sheet_id": 9})
    assert calage.vers_reference(ancien, 1) is None
    assert calage.vers_reference(_planche(1), 1) == calage.IDENTITE
