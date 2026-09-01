"""Branchement du journal d'annulation sur les routes (décision Q46).

Posé comme **dépendance de routeur** plutôt qu'appelé dans chaque fonction : un relevé
qu'il faut penser à déclencher est un relevé qu'on oublie, et c'est justement l'oubli qui
a produit les écarts entre chemins déjà corrigés (§27, §28). Ici, toute requête écrivante
qui passe par les routeurs concernés est journalisée, sans exception à maintenir.

Le libellé vient du **nom de la fonction de route** : il tient dans un bouton, et dit à
l'utilisateur ce qu'il s'apprête à défaire.
"""
from __future__ import annotations

import sys
from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.services import patrimoine_undo as undo
from app.services.patrimoine_legacy import resolve_city_id

# Libellés lisibles, par nom de fonction de route. Ce qui n'est pas listé garde un libellé
# générique : mieux vaut un intitulé vague qu'une action muette et non annulable.
_LABELS: dict[str, str] = {
    # Écran de rapprochement ASTECH
    "update_asset": "Modification d'un bien ASTECH",
    "convert_asset_to_local": "Bien ASTECH transformé en local",
    "mark_asset_gone": "Bien marqué à supprimer de AS-TECH",
    "create_asset_at_point": "Création d'un bien ASTECH sur la carte",
    "create_asset_from_building": "Bâtiment Po2 ajouté à la liste ASTECH",
    "create_asset_from_local": "Local Po2 ajouté à la liste ASTECH",
    "confirm_proposed_links": "Validation de rattachement(s)",
    "geocode_pending_assets": "Positionnement des biens sur leur adresse",
    "compute_candidates": "Reconnaissance des noms",
    # Patrimoine Po2
    "post_building": "Création d'un bâtiment Po2",
    "put_building": "Renommage / modification d'un bâtiment Po2",
    "remove_building": "Suppression d'un bâtiment Po2",
    "post_local": "Création d'un local Po2",
    "put_local": "Renommage / modification d'un local Po2",
    "remove_local": "Suppression d'un local Po2",
    "post_building_reclassify": "Bâtiment Po2 transformé en local",
    "post_local_reclassify": "Local Po2 transformé en bâtiment",
    "patch_building_position": "Déplacement d'un bâtiment Po2",
    "purge_patrimony_duplicates": "Purge des doublons Po2",
    "post_building_ign_attachment": "Attribution d'un bâtiment IGN",
    "post_building_from_naming_selection": "Création d'un bâtiment depuis le référentiel",
    "delete_buildings": "Suppression de bâtiments Po2",
}

_READ_ONLY = {"GET", "HEAD", "OPTIONS"}


def undo_journal(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Generator[None, None, None]:
    """Journalise l'écriture effectuée par la requête, si elle en fait une.

    En cas d'erreur, rien n'est journalisé : une action qui a échoué n'a rien à défaire,
    et proposer de l'annuler serait le plus sûr moyen de défaire l'action d'avant.
    """
    route = request.scope.get("route")
    name = getattr(route, "name", "") or ""
    # Annuler n'est pas une action journalisable : sinon annuler deux fois défairait
    # l'annulation au lieu de remonter la pile.
    if request.method in _READ_ONLY or name == "undo_last_action":
        yield
        return

    label = _LABELS.get(name, "Action sur le patrimoine")
    context = undo.record(
        db,
        city_id=resolve_city_id(db, current_user.city_id),
        user_id=current_user.id,
        label=label,
    )
    context.__enter__()
    try:
        yield
    except BaseException:
        context.__exit__(*sys.exc_info())
        raise
    else:
        context.__exit__(None, None, None)
