from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.patrimoine_legacy import (
    LegacyAssetOut,
    LegacyConfirmIn,
    LegacyAssetUpdateIn,
    LegacyCandidatesResult,
    LegacyImportResult,
)
from app.services.cities import get_city_by_id
from app.services import patrimoine_legacy as svc
from app.services import patrimoine_legacy_export as export_svc

router = APIRouter(prefix="/patrimoine/legacy", tags=["patrimoine-historique"])


@router.post("/import", response_model=LegacyImportResult)
async def import_astech_export(
    file: UploadFile = File(...),
    genres: str = Query(
        default="BATI,SITE",
        description="Genres ASTECH importés, séparés par des virgules. Défaut = contenu de la feuille BAT. Vide = tous.",
    ),
    include_out_of_park: bool = Query(
        default=True,
        description="Inclure les biens sortis du parc (HORSPARC=O). Défaut : oui, ils font partie de la feuille BAT.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyImportResult:
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")
    selected = tuple(g.strip().upper() for g in genres.split(",") if g.strip()) if genres else ()
    try:
        result = svc.import_astech_file(
            db,
            city_id=svc.resolve_city_id(db, current_user.city_id),
            filename=file.filename or "export_astech.xlsx",
            raw_bytes=raw_bytes,
            genres=selected,
            include_out_of_park=include_out_of_park,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return LegacyImportResult(**result)


@router.post("/candidates", response_model=LegacyCandidatesResult)
def compute_candidates(
    auto_link: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyCandidatesResult:
    result = svc.compute_candidates(
        db, svc.resolve_city_id(db, current_user.city_id), auto_link=auto_link
    )
    return LegacyCandidatesResult(**result)


@router.get("", response_model=list[LegacyAssetOut])
def list_assets(
    status_filter: str | None = Query(default=None, alias="status"),
    genre: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=500, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LegacyAssetOut]:
    assets = svc.list_assets(
        db,
        svc.resolve_city_id(db, current_user.city_id),
        status=status_filter,
        genre=genre,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [LegacyAssetOut.model_validate(asset) for asset in assets]


@router.get("/counts")
def counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    return svc.counts_by_status(db, svc.resolve_city_id(db, current_user.city_id))


@router.post("/confirm")
def confirm_proposed_links(
    payload: LegacyConfirmIn | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Valide les rattachements proposes par le moteur (statut « a confirmer »)."""
    return svc.confirm_proposed(
        db,
        svc.resolve_city_id(db, current_user.city_id),
        asset_ids=payload.asset_ids if payload else None,
    )


@router.get("/export")
def export_astech_workbook(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Classeur de retour ASTECH : feuille réinjectable + traçabilité + à vérifier.

    Les en-têtes sont recopiés à l'octet près depuis le fichier importé — c'est la
    condition de réinjection posée par la collectivité.
    """
    try:
        result = export_svc.build_astech_workbook(
            db, svc.resolve_city_id(db, current_user.city_id)
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return Response(
        content=result["content"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
            # Lus par l'écran pour annoncer le résultat sans rouvrir le fichier.
            "X-Astech-Exported": str(result["exported_rows"]),
            "X-Astech-Review": str(result["review_rows"]),
            "Access-Control-Expose-Headers": "X-Astech-Exported, X-Astech-Review",
        },
    )


@router.get("/export/preview")
def preview_astech_export(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Compte ce qui partirait, sans produire le fichier."""
    try:
        result = export_svc.build_astech_workbook(
            db, svc.resolve_city_id(db, current_user.city_id)
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return {
        "exported_rows": result["exported_rows"],
        "review_rows": result["review_rows"],
        "columns": result["columns"],
        "missing_columns": result["missing_columns"],
        "sheet_name": result["sheet_name"],
    }


@router.post("/reset-all")
def reset_everything(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Remise à zéro totale : l'écran revient à l'état juste après l'import.

    Efface les rattachements, les candidats, les positions posées à la main et les
    décisions « ignoré ». Les biens ASTECH disparaissent alors de la carte — c'est
    normal, ils n'ont pas de coordonnées propres — et « Reconnaître les noms » les y
    ramène. `hors_perimetre` est conservé : c'est un constat de périmètre, pas une
    décision.
    """
    return svc.reset_everything(db, svc.resolve_city_id(db, current_user.city_id))


@router.delete("/import")
def delete_all_imports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Efface tout le référentiel ASTECH importé, pour repartir d'un export neuf.

    ⚠️ Destructif : le travail de rapprochement part avec les biens. Les bâtiments et
    les locaux Po2 créés en cours de route sont conservés — ce sont des données Po2,
    et le moteur les retrouvera au réimport.
    """
    return svc.delete_all_imports(db, svc.resolve_city_id(db, current_user.city_id))


@router.post("/reset-links")
def reset_all_links(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Supprime TOUS les rapprochements ASTECH ↔ Po2 et remet les biens à traiter.

    Les biens « à créer », « ignoré » et « hors périmètre » sont préservés : ce sont des
    décisions de périmètre, pas des rapprochements.
    """
    return svc.reset_all_links(db, svc.resolve_city_id(db, current_user.city_id))


@router.post("/from-building/{building_id}", response_model=LegacyAssetOut, status_code=status.HTTP_201_CREATED)
def create_asset_from_building(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyAssetOut:
    """Ajoute un bâtiment Po2 à la liste ASTECH comme bien « à créer » (décision Q13)."""
    city_id = svc.resolve_city_id(db, current_user.city_id)
    building = svc.get_building_for_city(db, city_id, building_id)
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bâtiment introuvable.")
    return LegacyAssetOut.model_validate(svc.create_asset_from_building(db, city_id, building))


@router.post("/from-local/{local_id}", response_model=LegacyAssetOut, status_code=status.HTTP_201_CREATED)
def create_asset_from_local(
    local_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyAssetOut:
    """Ajoute un local Po2 à la liste ASTECH comme bien « à créer » (décision Q13).

    Même besoin que pour un bâtiment : un `CODE_BIEN` désigne très souvent un local, et
    seuls les bâtiments pouvaient jusqu'ici remonter dans le fichier de retour.
    """
    city_id = svc.resolve_city_id(db, current_user.city_id)
    local = svc.get_local_for_city(db, city_id, local_id)
    if local is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local introuvable.")
    try:
        return LegacyAssetOut.model_validate(svc.create_asset_from_local(db, city_id, local))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/{asset_id}/to-local", response_model=LegacyAssetOut)
def convert_asset_to_local(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyAssetOut:
    """Fait du bien un **local** du bâtiment auquel il est rattaché, en le créant.

    L'écran savait viser un local existant mais pas en créer un : c'est le cas normal
    dès que plusieurs biens ASTECH désignent le même bâtiment.
    """
    asset = svc.get_asset_or_none(db, svc.resolve_city_id(db, current_user.city_id), asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bien historique introuvable.")
    try:
        return LegacyAssetOut.model_validate(svc.convert_asset_to_local(db, asset))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/geocode-pending")
def geocode_pending_assets(
    limit: int = Query(default=25, ge=1, le=100, description="Biens traités par appel."),
    offset: int = Query(default=0, ge=0, description="Échecs déjà constatés, à passer."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Pose sur leur adresse ASTECH les biens qui n'ont aucune position (§25, Q35).

    Par lots : l'écran rappelle jusqu'à épuisement et affiche l'avancement, là où une
    seule requête de 292 géocodages expirerait.
    """
    city_id = svc.resolve_city_id(db, current_user.city_id)
    city = get_city_by_id(db, city_id) if city_id is not None else None
    return svc.geocode_pending_assets(
        db, city_id, city.nom_commune if city is not None else None, limit=limit, offset=offset
    )


@router.post("/{asset_id}/gone", response_model=LegacyAssetOut)
def mark_asset_gone(
    asset_id: int,
    gone: bool = Query(default=True, description="Vrai = à supprimer de AS-TECH ; faux = à garder."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyAssetOut:
    """Marque le bien **à supprimer de AS-TECH**, ou annule cette consigne.

    La ligne est conservée dans Po2 : elle sort du parcours et du réexport, reste
    consultable sous le filtre « A SUPPRIMER DE AS-TECH », et le geste est réversible (Q23).
    """
    asset = svc.get_asset_or_none(db, svc.resolve_city_id(db, current_user.city_id), asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bien historique introuvable.")
    return LegacyAssetOut.model_validate(svc.set_asset_gone(db, asset, gone))


@router.patch("/{asset_id}", response_model=LegacyAssetOut)
def update_asset(
    asset_id: int,
    payload: LegacyAssetUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyAssetOut:
    asset = svc.get_asset_or_none(db, svc.resolve_city_id(db, current_user.city_id), asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bien historique introuvable.")
    # `local_id` etait accepte par le schema mais jamais transmis au service : le menu
    # « Preciser un local » renvoyait 200 sans rien changer. C'est la raison pour
    # laquelle aucun bien n'avait jamais ete rattache au niveau local.
    try:
        updated = svc.update_asset(
            db,
            asset,
            status=payload.status,
            building_id=payload.building_id,
            local_id=payload.local_id,
            designation=payload.designation,
            latitude=payload.latitude,
            longitude=payload.longitude,
            notes=payload.notes,
            clear_building=payload.clear_building,
            clear_candidate=payload.clear_candidate,
        )
    except ValueError as error:
        # Cible disparue (patrimoine reimporte) : message explicite plutot qu'une 500
        # opaque, qui donnait l'impression que le bouton ne faisait rien.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return LegacyAssetOut.model_validate(updated)
