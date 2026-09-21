"""API de l'outil de métré thermique (thermique.patrimoineaucarre.com).

Ouverte à tout compte actif, Po2 ou bureau d'études : on passe par
`get_authenticated_user`, pas par `get_current_user` qui refuse les comptes externes.
Seules les tuiles d'images passent par une adresse signée (une balise <img> ne peut
pas envoyer d'en-tête d'authentification).
"""
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_authenticated_user
from app.core.db import get_db
from app.core.roles import is_admin_role, is_external_role
from app.models.thermique import ThermiqueDocument, ThermiqueProject, ThermiqueSheet
from app.models.user import User
from app.schemas.thermique import (
    CalqueDesignation,
    CalqueElements,
    CalqueExclusion,
    CalquePick,
    CalqueZone,
    CalqueZoneAction,
    CalqueZoneDesignate,
    CalibrationRequest,
    ComponentCreate,
    ComponentEvaluate,
    ComponentImport,
    ComponentUpdate,
    DetectContourRequest,
    EnvelopeProposal,
    EraseAllRequest,
    ExternalAccountCreate,
    ExternalAccountRead,
    LevelCreate,
    LevelUpdate,
    NorthRequest,
    ProjectCreate,
    ProjectDetail,
    ProjectRead,
    ProjectUpdate,
    RasterManifest,
    RoomAdd,
    RoomDetect,
    RoomMerge,
    RoomSplit,
    RoomTrace,
    RoomUpdate,
    SectionHeightsRequest,
    SheetRead,
    SheetUpdate,
    SuperpositionValidate,
    UploadResult,
    VisionObjectCreate,
    VisionObjectUpdate,
    WallTypeAccept,
    ZoneCreate,
    ZoneUpdate,
)
from app.services import (
    thermique_calques,
    thermique_detection,
    thermique_enveloppe,
    thermique_metre,
    thermique_pieces,
    thermique_superposition,
    thermique_vision,
)
from app.services.thermique import (
    ALLOWED_ROTATIONS,
    ThermiqueError,
    add_document,
    calibrate_sheet,
    create_external_account,
    create_project,
    delete_document,
    delete_project,
    document_path,
    get_project_for_user,
    delete_all_projects,
    list_projects,
    max_upload_bytes,
    serialize_project,
    serialize_project_detail,
    serialize_sheet,
    update_project,
    update_sheet,
)
from app.services.thermique_composants import (
    copy_component,
    create_component,
    delete_component,
    evaluate,
    get_component_for_user,
    list_components,
    serialize_component,
    update_component,
)
from app.services.thermique_raster import (
    check_tile_signature,
    ensure_raster,
    load_manifest,
    raster_dir,
    tile_url,
    white_tile_png,
)

from thermique_moteur import composants as moteur_composants
from thermique_moteur import metre as moteur_metre
from thermique_moteur import parois
from thermique_moteur.bibliotheque import elements as bibliotheque_elements
from thermique_moteur.bibliotheque import materiaux as bibliotheque_materiaux
from thermique_moteur.bibliotheque import menuiseries as bibliotheque_menuiseries

LOG = logging.getLogger(__name__)
TILE_CACHE_HEADERS = {"Cache-Control": "private, max-age=43200"}

router = APIRouter(prefix="/thermique", tags=["thermique"])


@router.get("/bibliotheque/menuiseries")
def read_library_windows(user: User = Depends(get_authenticated_user)) -> dict:
    """Édition en vigueur de la bibliothèque des menuiseries (valeurs, sources, contrôles)."""
    return bibliotheque_menuiseries.charger_edition()


@router.get("/bibliotheque/menuiseries/fermeture")
def compute_library_closure(uw: float, r: float, user: User = Depends(get_authenticated_user)) -> dict:
    """Ujour-nuit et Uws d'une fenêtre équipée d'une fermeture (interpolation autorisée)."""
    try:
        return bibliotheque_menuiseries.calcul_fermeture(uw, r)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/bibliotheque/materiaux")
def read_library_materials(user: User = Depends(get_authenticated_user)) -> dict:
    """Édition en vigueur de la bibliothèque des matériaux (λ utiles par défaut, sources, contrôles)."""
    return bibliotheque_materiaux.charger_edition()


@router.get("/bibliotheque/elements")
def read_library_elements(user: User = Depends(get_authenticated_user)) -> dict:
    """Édition en vigueur des résistances tabulées (briques, blocs, planchers, isolants en vrac, cloisons)."""
    return bibliotheque_elements.charger_edition()


@router.post("/bibliotheque/parois/calcul")
def compute_wall(paroi: dict, user: User = Depends(get_authenticated_user)) -> dict:
    """Up d'une paroi opaque en couches, de l'intérieur vers l'extérieur (méthode Th-Bât)."""
    try:
        return parois.calculer_paroi(paroi, bibliotheque_materiaux.index_materiaux(), bibliotheque_elements.index_elements())
    except parois.ParoiError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/bibliotheque/parois/epaisseur-isolant")
def compute_insulation_thickness(demande: dict, user: User = Depends(get_authenticated_user)) -> dict:
    """Épaisseur minimale de la couche isolante pour atteindre un U cible."""
    try:
        return parois.epaisseur_isolant(
            demande.get("paroi") or {},
            int(demande.get("index_isolant", -1)),
            float(demande.get("u_cible", 0)),
            bibliotheque_materiaux.index_materiaux(),
            elements=bibliotheque_elements.index_elements(),
        )
    except (parois.ParoiError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _project_or_404(db: Session, user: User, project_id: int) -> ThermiqueProject:
    project = get_project_for_user(db, user, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")
    return project


def _document_or_404(db: Session, user: User, document_id: int) -> ThermiqueDocument:
    document = db.get(ThermiqueDocument, document_id)
    if document is None or get_project_for_user(db, user, document.project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable.")
    return document


def _sheet_or_404(db: Session, user: User, sheet_id: int) -> ThermiqueSheet:
    sheet = db.get(ThermiqueSheet, sheet_id)
    if sheet is None or get_project_for_user(db, user, sheet.project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planche introuvable.")
    return sheet


# --- Bibliothèque de projet et modèles (docs/thermique/bibliotheque-projet-decisions.md) ---------


def _component_or_404(db: Session, user: User, component_id: int):
    component = get_component_for_user(db, user, component_id)
    if component is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Composant introuvable.")
    return component


def _bad_request(exc: ThermiqueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/composants/categories")
def read_component_categories(user: User = Depends(get_authenticated_user)) -> dict:
    """Catégories de la bibliothèque (murs, planchers, menuiseries, ponts thermiques) et statuts."""
    return {"categories": moteur_composants.CATEGORIES, "statuts": moteur_composants.STATUTS}


@router.post("/composants/evaluer")
def evaluate_component(payload: ComponentEvaluate, user: User = Depends(get_authenticated_user)) -> dict:
    """Résultat d'une composition sans l'enregistrer (aperçu pendant la saisie)."""
    try:
        return evaluate(payload.categorie, payload.composition)
    except ThermiqueError as exc:
        raise _bad_request(exc) from exc


@router.get("/projects/{project_id}/composants")
def read_project_components(
    project_id: int, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
) -> list[dict]:
    project = _project_or_404(db, user, project_id)
    return [serialize_component(c) for c in list_components(db, user, project)]


@router.post("/projects/{project_id}/composants", status_code=status.HTTP_201_CREATED)
def create_project_component(
    project_id: int, payload: ComponentCreate, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
) -> dict:
    project = _project_or_404(db, user, project_id)
    try:
        return serialize_component(create_component(db, user, project, payload.model_dump()))
    except ThermiqueError as exc:
        raise _bad_request(exc) from exc


@router.post("/projects/{project_id}/composants/importer", status_code=status.HTTP_201_CREATED)
def import_model_into_project(
    project_id: int, payload: ComponentImport, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
) -> dict:
    """Copie un modèle du compte dans le projet (copie indépendante)."""
    project = _project_or_404(db, user, project_id)
    model = _component_or_404(db, user, payload.modele_id)
    if model.project_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce composant n'est pas un modèle.")
    try:
        return serialize_component(copy_component(db, user, model, project))
    except ThermiqueError as exc:
        raise _bad_request(exc) from exc


@router.get("/modeles")
def read_models(db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)) -> list[dict]:
    """Modèles réutilisables du compte (« Ma bibliothèque »)."""
    return [serialize_component(c) for c in list_components(db, user, None)]


@router.post("/modeles", status_code=status.HTTP_201_CREATED)
def create_model(payload: ComponentCreate, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)) -> dict:
    try:
        return serialize_component(create_component(db, user, None, payload.model_dump()))
    except ThermiqueError as exc:
        raise _bad_request(exc) from exc


@router.patch("/composants/{component_id}")
def update_component_route(
    component_id: int, payload: ComponentUpdate, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
) -> dict:
    component = _component_or_404(db, user, component_id)
    try:
        return serialize_component(update_component(db, user, component, payload.model_dump(exclude_unset=True)))
    except ThermiqueError as exc:
        raise _bad_request(exc) from exc


@router.delete("/composants/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_component_route(
    component_id: int, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
) -> Response:
    delete_component(db, _component_or_404(db, user, component_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/composants/{component_id}/dupliquer", status_code=status.HTTP_201_CREATED)
def duplicate_component_route(
    component_id: int, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
) -> dict:
    """Copie dans la même bibliothèque (projet ou modèles), avec le code suivant libre."""
    component = _component_or_404(db, user, component_id)
    project = db.get(ThermiqueProject, component.project_id) if component.project_id else None
    try:
        return serialize_component(copy_component(db, user, component, project, suffix=" (copie)"))
    except ThermiqueError as exc:
        raise _bad_request(exc) from exc


@router.post("/composants/{component_id}/modele", status_code=status.HTTP_201_CREATED)
def save_component_as_model(
    component_id: int, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
) -> dict:
    """« Enregistrer comme modèle » : copie du composant d'un projet dans les modèles du compte."""
    component = _component_or_404(db, user, component_id)
    try:
        return serialize_component(copy_component(db, user, component, None))
    except ThermiqueError as exc:
        raise _bad_request(exc) from exc


def _prebuild_rasters(jobs: list[tuple[Path, int, Path]]) -> None:
    """Rend les planches importées en tâche de fond : la première ouverture est immédiate."""
    for pdf_path, page_index, out_dir in jobs:
        try:
            ensure_raster(pdf_path, page_index, 0, out_dir)
        except Exception:
            LOG.exception("Rendu en tuiles impossible pour %s (page %s)", pdf_path, page_index)


@router.get("/projects", response_model=list[ProjectRead])
def read_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> list[dict]:
    return [serialize_project(project) for project in list_projects(db, user)]


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project_route(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    return serialize_project(create_project(db, user, payload.name, payload.description))


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    return serialize_project_detail(_project_or_404(db, user, project_id))


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project_route(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    project = _project_or_404(db, user, project_id)
    try:
        project = update_project(db, project, payload.model_dump(exclude_unset=True))
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return serialize_project(project)


@router.post("/projects/tout-effacer")
def erase_all_projects_route(
    payload: EraseAllRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Efface tous les projets du compte (les modèles réutilisables sont gardés)."""
    if payload.confirmation.strip().upper() != "EFFACER":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tapez EFFACER pour confirmer l'effacement.")
    return {"projets_effaces": delete_all_projects(db, user)}


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_route(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> Response:
    delete_project(db, _project_or_404(db, user, project_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/projects/{project_id}/documents", response_model=UploadResult)
def upload_documents(
    project_id: int,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Importe un ou plusieurs fichiers ; un fichier refusé n'empêche pas les autres."""
    project = _project_or_404(db, user, project_id)
    limit = max_upload_bytes()
    imported: list[str] = []
    errors: list[dict] = []
    jobs: list[tuple[Path, int, Path]] = []
    for upload in files:
        filename = upload.filename or "plan.pdf"
        data = upload.file.read(limit + 1)
        try:
            document = add_document(db, project, filename, data, user)
        except ThermiqueError as exc:
            errors.append({"filename": filename, "message": str(exc)})
            continue
        imported.append(filename)
        jobs.extend(
            (document_path(document), sheet.page_index, raster_dir(project.id, sheet.id, 0)) for sheet in document.sheets
        )
    if jobs:
        background_tasks.add_task(_prebuild_rasters, jobs)
    db.refresh(project)
    return {"project": serialize_project_detail(project), "imported": imported, "errors": errors}


@router.get("/documents/{document_id}/file")
def read_document_file(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> FileResponse:
    document = _document_or_404(db, user, document_id)
    path = document_path(document)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier absent du stockage.")
    return FileResponse(path, media_type="application/pdf", headers={"Cache-Control": "private, max-age=3600"})


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_route(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> Response:
    delete_document(db, _document_or_404(db, user, document_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/sheets/{sheet_id}", response_model=SheetRead)
def update_sheet_route(
    sheet_id: int,
    payload: SheetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    sheet = _sheet_or_404(db, user, sheet_id)
    try:
        sheet = update_sheet(db, sheet, payload.model_dump(exclude_unset=True))
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return serialize_sheet(sheet)


@router.post("/sheets/{sheet_id}/calibration", response_model=SheetRead)
def calibrate_sheet_route(
    sheet_id: int,
    payload: CalibrationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    sheet = _sheet_or_404(db, user, sheet_id)
    try:
        sheet = calibrate_sheet(db, sheet, payload.p1, payload.p2, payload.real_length_m, payload.apply)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return serialize_sheet(sheet)


@router.get("/sheets/{sheet_id}/raster", response_model=RasterManifest)
def read_sheet_raster(
    sheet_id: int,
    rotation: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Fiche des tuiles de la planche (rendue à la première demande si besoin)."""
    sheet = _sheet_or_404(db, user, sheet_id)
    angle = sheet.rotation_deg if rotation is None else rotation % 360
    if angle not in ALLOWED_ROTATIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La rotation doit être un multiple de 90°.")
    path = document_path(sheet.document)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier absent du stockage.")
    try:
        manifest = ensure_raster(path, sheet.page_index, angle, raster_dir(sheet.project_id, sheet.id, angle))
    except Exception as exc:
        LOG.exception("Rendu en tuiles impossible pour la planche %s", sheet.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Rendu de la planche impossible."
        ) from exc
    return {**manifest, "sheet_id": sheet.id, "tile_url": tile_url(sheet.id, angle)}


@router.get("/sheets/{sheet_id}/tiles/{rotation}/{z}/{x}/{y}.png", include_in_schema=False)
def read_sheet_tile(
    sheet_id: int,
    rotation: int,
    z: int,
    x: int,
    y: int,
    e: int,
    s: str,
    db: Session = Depends(get_db),
) -> Response:
    if not check_tile_signature(sheet_id, rotation, e, s):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Adresse de tuile invalide ou expirée.")
    sheet = db.get(ThermiqueSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planche introuvable.")
    directory = raster_dir(sheet.project_id, sheet_id, rotation)
    manifest = load_manifest(directory)
    if manifest is None or not 0 <= z < len(manifest["levels"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tuile introuvable.")
    level = manifest["levels"][z]
    if not (0 <= x < level["cols"] and 0 <= y < level["rows"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tuile introuvable.")
    path = directory / str(z) / f"{x}_{y}.png"
    if path.is_file():
        return FileResponse(path, media_type="image/png", headers=TILE_CACHE_HEADERS)
    return Response(content=white_tile_png(), media_type="image/png", headers=TILE_CACHE_HEADERS)


# --- Métré sur les plans (lot M1) ------------------------------------------------------------------


def _level_or_404(db: Session, user: User, level_id: int):
    level = thermique_metre.get_level_for_user(db, user, level_id)
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Niveau introuvable.")
    return level


def _zone_or_404(db: Session, user: User, zone_id: int):
    zone = thermique_metre.get_zone_for_user(db, user, zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracé introuvable.")
    return zone


def _metre_action(db: Session, project: ThermiqueProject, action) -> dict:
    """Exécute une modification du métré et renvoie le métré complet recalculé."""
    try:
        action()
    except (ThermiqueError, moteur_metre.MetreError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return thermique_metre.serialize_metre(db, project)


@router.get("/projects/{project_id}/metre")
def read_metre(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    return thermique_metre.serialize_metre(db, _project_or_404(db, user, project_id))


@router.post("/projects/{project_id}/niveaux", status_code=status.HTTP_201_CREATED)
def create_level_route(
    project_id: int,
    payload: LevelCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    project = _project_or_404(db, user, project_id)
    return _metre_action(db, project, lambda: thermique_metre.create_level(db, project, payload.model_dump(exclude_unset=True)))


@router.post("/projects/{project_id}/niveaux/depuis-planches")
def create_levels_from_sheets_route(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    project = _project_or_404(db, user, project_id)
    return _metre_action(db, project, lambda: thermique_metre.create_levels_from_sheets(db, project))


@router.patch("/niveaux/{level_id}")
def update_level_route(
    level_id: int,
    payload: LevelUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    level = _level_or_404(db, user, level_id)
    project = db.get(ThermiqueProject, level.project_id)
    return _metre_action(
        db, project, lambda: thermique_metre.update_level(db, project, level, payload.model_dump(exclude_unset=True))
    )


@router.delete("/niveaux/{level_id}")
def delete_level_route(
    level_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    level = _level_or_404(db, user, level_id)
    project = db.get(ThermiqueProject, level.project_id)
    return _metre_action(db, project, lambda: thermique_metre.delete_level(db, level))


@router.post("/projects/{project_id}/nord")
def set_north_route(
    project_id: int,
    payload: NorthRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    project = _project_or_404(db, user, project_id)
    level = _level_or_404(db, user, payload.niveau_id)
    if level.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Niveau introuvable.")
    return _metre_action(db, project, lambda: thermique_metre.set_north(db, project, level, payload.p1, payload.p2))


@router.post("/niveaux/{level_id}/zones", status_code=status.HTTP_201_CREATED)
def create_zone_route(
    level_id: int,
    payload: ZoneCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    level = _level_or_404(db, user, level_id)
    project = db.get(ThermiqueProject, level.project_id)
    return _metre_action(db, project, lambda: thermique_metre.create_zone(db, level, payload.model_dump()))


@router.patch("/zones/{zone_id}")
def update_zone_route(
    zone_id: int,
    payload: ZoneUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    zone = _zone_or_404(db, user, zone_id)
    project = db.get(ThermiqueProject, zone.project_id)
    return _metre_action(db, project, lambda: thermique_metre.update_zone(db, zone, payload.model_dump(exclude_unset=True)))


@router.delete("/zones/{zone_id}")
def delete_zone_route(
    zone_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    zone = _zone_or_404(db, user, zone_id)
    project = db.get(ThermiqueProject, zone.project_id)
    return _metre_action(db, project, lambda: thermique_metre.delete_zone(db, zone))


@router.post("/niveaux/{level_id}/detecter-contour")
def detect_contour_route(
    level_id: int,
    payload: DetectContourRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Propose le contour au nu intérieur du niveau (lecture du plan : 10 à 15 s la première fois)."""
    level = _level_or_404(db, user, level_id)
    project = db.get(ThermiqueProject, level.project_id)
    try:
        found = thermique_metre.detect_contour(db, level, payload.remplacer)
    except (ThermiqueError, moteur_metre.MetreError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        LOG.exception("Détection du contour impossible pour le niveau %s", level_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Détection du contour impossible.") from exc
    return {**thermique_metre.serialize_metre(db, project), "detection": found}


@router.post("/niveaux/{level_id}/detecter-lignes")
def detect_lines_route(
    level_id: int,
    payload: DetectContourRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Propose le nu intérieur et le nu extérieur du niveau, déduits des murs lus sur les vecteurs du plan."""
    level = _level_or_404(db, user, level_id)
    project = db.get(ThermiqueProject, level.project_id)
    try:
        found = thermique_metre.detect_lines(db, level, payload.remplacer)
    except (ThermiqueError, moteur_metre.MetreError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        LOG.exception("Détection des deux lignes impossible pour le niveau %s", level_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Détection des deux lignes impossible.") from exc
    return {**thermique_metre.serialize_metre(db, project), "detection_lignes": found}


@router.post("/niveaux/{level_id}/proposer-enveloppe")
def propose_envelope_route(
    level_id: int,
    payload: EnvelopeProposal,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Propose le nu extérieur et le nu intérieur du niveau à partir des calques désignés (étape « Enveloppe »)."""
    level = _level_or_404(db, user, level_id)
    project = db.get(ThermiqueProject, level.project_id)
    try:
        found = thermique_enveloppe.propose_envelope(
            db, level, payload.fermeture_cm / 100, payload.remplacer, tuple(dict.fromkeys(payload.lignes))
        )
    except (ThermiqueError, moteur_metre.MetreError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        LOG.exception("Proposition de l'enveloppe impossible pour le niveau %s", level_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Proposition de l'enveloppe impossible.") from exc
    return {**thermique_metre.serialize_metre(db, project), "proposition_enveloppe": found}


@router.post("/zones/{zone_id}/detecter-murs")
def detect_walls_route(
    zone_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Lit l'épaisseur des murs et la position de l'isolant le long du tracé (quelques secondes)."""
    zone = _zone_or_404(db, user, zone_id)
    project = db.get(ThermiqueProject, zone.project_id)
    try:
        found = thermique_metre.detect_walls(db, zone)
    except (ThermiqueError, moteur_metre.MetreError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        LOG.exception("Lecture des murs impossible pour le tracé %s", zone_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lecture des murs impossible.") from exc
    return {**thermique_metre.serialize_metre(db, project), "detection_murs": found}


@router.post("/zones/{zone_id}/types-murs")
def accept_wall_type_route(
    zone_id: int,
    payload: WallTypeAccept,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    zone = _zone_or_404(db, user, zone_id)
    project = db.get(ThermiqueProject, zone.project_id)
    return _metre_action(
        db, project, lambda: thermique_metre.accept_wall_type(db, user, zone, payload.epaisseur_m, payload.composant_id)
    )


@router.get("/sheets/{sheet_id}/coupe")
def read_sheet_section(
    sheet_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Planchers repérés sur une coupe et hauteurs par niveau dans les deux sens de lecture."""
    sheet = _sheet_or_404(db, user, sheet_id)
    try:
        return thermique_metre.sheet_section(sheet)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Lecture de la coupe impossible pour la planche %s", sheet_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lecture de la coupe impossible.") from exc


@router.get("/projects/{project_id}/calques")
def read_project_calques(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Calques désignés du projet, comptés sur chaque plan (lecture des plans : quelques secondes la première fois)."""
    project = _project_or_404(db, user, project_id)
    try:
        return thermique_calques.list_designations(db, project)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Lecture des calques impossible pour le projet %s", project_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lecture des calques impossible.") from exc


def _calques_action(db: Session, project: ThermiqueProject, action) -> dict:
    try:
        action()
        return thermique_calques.list_designations(db, project)
    except ThermiqueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/projects/{project_id}/calques")
def create_project_calque(
    project_id: int,
    payload: CalqueDesignation,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Donne une nature à une famille d'éléments (signature + forme), sur tous les plans du projet."""
    project = _project_or_404(db, user, project_id)
    return _calques_action(
        db, project, lambda: thermique_calques.save_designation(db, project, payload.signature, payload.forme, payload.nature, payload.perimetre)
    )


@router.delete("/projects/{project_id}/calques/{regle_id}")
def delete_project_calque(
    project_id: int,
    regle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    project = _project_or_404(db, user, project_id)
    return _calques_action(db, project, lambda: thermique_calques.delete_designation(db, project, regle_id))


@router.post("/projects/{project_id}/calques/{regle_id}/exclusions")
def toggle_project_calque_exclusion(
    project_id: int,
    regle_id: int,
    payload: CalqueExclusion,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Retire un élément d'un calque désigné, ou l'y remet."""
    project = _project_or_404(db, user, project_id)
    return _calques_action(
        db, project, lambda: thermique_calques.toggle_exclusion(db, project, regle_id, payload.planche_id, payload.element)
    )


@router.post("/projects/{project_id}/calques/elements")
def set_project_calque_elements(
    project_id: int,
    payload: CalqueElements,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Nature d'éléments seuls (sans report sur leurs semblables), ou retrait de cette désignation."""
    project = _project_or_404(db, user, project_id)
    sheet = _sheet_or_404(db, user, payload.planche_id)
    if sheet.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planche introuvable.")
    return _calques_action(
        db, project, lambda: thermique_calques.set_elements(db, project, sheet, payload.elements, payload.nature)
    )


@router.post("/sheets/{sheet_id}/calques/zone/designer")
def designate_sheet_calque_zone(
    sheet_id: int,
    payload: CalqueZoneDesignate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Lasso « Désigner » : nature des types de traits cochés, sur tous les plans ou dans la zone seulement."""
    sheet = _sheet_or_404(db, user, sheet_id)
    project = db.get(ThermiqueProject, sheet.project_id)
    familles = [(f.signature, f.forme) for f in payload.familles]
    return _calques_action(
        db,
        project,
        lambda: thermique_calques.designate_zone(
            db, project, sheet, payload.contour, familles, payload.nature, payload.portee == "familles", payload.perimetre
        ),
    )


@router.post("/sheets/{sheet_id}/calques/designer")
def pick_sheet_calque(
    sheet_id: int,
    payload: CalquePick,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Élément sous le clic et ses semblables sur les plans du projet."""
    sheet = _sheet_or_404(db, user, sheet_id)
    project = db.get(ThermiqueProject, sheet.project_id)
    try:
        return thermique_calques.pick_element(db, project, sheet, payload.x, payload.y, payload.tolerance)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Désignation impossible sur la planche %s", sheet_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Désignation impossible.") from exc


@router.post("/sheets/{sheet_id}/calques/zone")
def read_sheet_calque_zone(
    sheet_id: int,
    payload: CalqueZone,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Calques désignés présents dans un lasso, avec leurs éléments actifs et retirés."""
    sheet = _sheet_or_404(db, user, sheet_id)
    project = db.get(ThermiqueProject, sheet.project_id)
    try:
        return thermique_calques.zone_summary(project, sheet, payload.contour)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/sheets/{sheet_id}/calques/zone/appliquer")
def apply_sheet_calque_zone(
    sheet_id: int,
    payload: CalqueZoneAction,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Retire des calques choisis tous leurs éléments situés dans le lasso, ou les y remet."""
    sheet = _sheet_or_404(db, user, sheet_id)
    project = db.get(ThermiqueProject, sheet.project_id)
    return _calques_action(
        db,
        project,
        lambda: thermique_calques.apply_zone(
            db, project, sheet, payload.contour, payload.regles, payload.action == "retirer"
        ),
    )


@router.get("/sheets/{sheet_id}/calques/famille")
def read_sheet_calque_family(
    sheet_id: int,
    signature: str,
    forme: str,
    perimetre: str = "partout",
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Éléments d'une famille sur la planche, dans la portée demandée, pour les surligner."""
    sheet = _sheet_or_404(db, user, sheet_id)
    try:
        return thermique_calques.family_elements(db.get(ThermiqueProject, sheet.project_id), sheet, signature, forme, perimetre)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/sheets/{sheet_id}/calques/designes")
def read_sheet_calques(
    sheet_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Éléments désignés de la planche, regroupés par nature."""
    sheet = _sheet_or_404(db, user, sheet_id)
    try:
        return thermique_calques.sheet_designations(db.get(ThermiqueProject, sheet.project_id), sheet)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/projects/{project_id}/superposition")
def read_project_superposition(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Plans du projet, niveau de référence et superpositions validées (étape E2)."""
    return thermique_superposition.overview(db, _project_or_404(db, user, project_id))


@router.get("/projects/{project_id}/superposition/proposition")
def read_superposition_proposal(
    project_id: int,
    planche_id: int,
    reference_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Translation proposée pour poser un plan sur la référence."""
    project = _project_or_404(db, user, project_id)
    try:
        return thermique_superposition.propose(db, project, planche_id, reference_id)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Superposition impossible pour la planche %s", planche_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Superposition impossible.") from exc


@router.post("/projects/{project_id}/superposition")
def validate_superposition(
    project_id: int,
    payload: SuperpositionValidate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Valide la superposition d'un plan sur la référence (enregistrée comme calage de son niveau)."""
    project = _project_or_404(db, user, project_id)
    try:
        return thermique_superposition.validate(db, project, payload.reference_id, payload.planche_id, payload.dx, payload.dy)
    except ThermiqueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/projects/{project_id}/superposition/{sheet_id}")
def reset_superposition(
    project_id: int,
    sheet_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    project = _project_or_404(db, user, project_id)
    try:
        return thermique_superposition.reset(db, project, sheet_id)
    except ThermiqueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _room_or_404(db: Session, user: User, room_id: int):
    room = thermique_pieces.get_room(db, room_id)
    if room is None or get_project_for_user(db, user, room.project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pièce introuvable.")
    return room


def _rooms_action(db: Session, sheet: ThermiqueSheet, action, background: BackgroundTasks | None = None) -> dict:
    """Exécute une action sur les pièces puis renvoie celles de la planche ; lance la lecture des noms au besoin."""
    project = db.get(ThermiqueProject, sheet.project_id)
    try:
        lire = action(project)
    except ThermiqueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if lire and background is not None:
        background.add_task(thermique_pieces.read_names, sheet.id)
    result = thermique_pieces.list_rooms(db, project, sheet)
    if lire and background is not None:
        result["lecture_noms"] = "en_cours"
    return result


@router.post("/sheets/{sheet_id}/detection-auto")
def start_auto_detection(
    sheet_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Lance « Tout détecter » sur la planche : objets, pièces, noms, enveloppe (étape E-auto, §18)."""
    sheet = _sheet_or_404(db, user, sheet_id)
    project = db.get(ThermiqueProject, sheet.project_id)
    try:
        etat = thermique_detection.start(db, project, sheet)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if etat.get("en_cours"):
        background.add_task(thermique_detection.run, sheet.id)
    return etat


@router.get("/sheets/{sheet_id}/detection-auto")
def read_auto_detection(sheet_id: int, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)) -> dict:
    """Avancement et bilan de la détection automatique de la planche."""
    return thermique_detection.etat(_sheet_or_404(db, user, sheet_id))


@router.post("/sheets/{sheet_id}/vision-analysis")
def start_vision_analysis(
    sheet_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Analyse le rendu raster de la planche par IA, sans lire les vecteurs du PDF."""
    sheet = _sheet_or_404(db, user, sheet_id)
    project = db.get(ThermiqueProject, sheet.project_id)
    try:
        current = thermique_vision.start(project, sheet)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    launch = current.pop("_launch", False)
    if launch:
        background.add_task(thermique_vision.run, sheet.id)
    return current


@router.get("/sheets/{sheet_id}/vision-analysis")
def read_vision_analysis(
    sheet_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    return thermique_vision.state(_sheet_or_404(db, user, sheet_id))


@router.patch("/sheets/{sheet_id}/vision-objects/{object_id}")
def update_vision_object(
    sheet_id: int,
    object_id: str,
    payload: VisionObjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    sheet = _sheet_or_404(db, user, sheet_id)
    try:
        return thermique_vision.update_object(sheet, object_id, payload.model_dump(exclude_unset=True))
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/sheets/{sheet_id}/vision-objects")
def create_vision_object(
    sheet_id: int,
    payload: VisionObjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    sheet = _sheet_or_404(db, user, sheet_id)
    try:
        return thermique_vision.create_object(sheet, payload.model_dump())
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/sheets/{sheet_id}/vision-objects/{object_id}")
def delete_vision_object(
    sheet_id: int,
    object_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    sheet = _sheet_or_404(db, user, sheet_id)
    try:
        return thermique_vision.delete_object(sheet, object_id)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/sheets/{sheet_id}/pieces")
def read_sheet_rooms(sheet_id: int, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)) -> dict:
    """Pièces de la planche, état de la lecture des noms et calques de limite disponibles (étape E3)."""
    sheet = _sheet_or_404(db, user, sheet_id)
    return _rooms_action(db, sheet, lambda project: False)


@router.post("/sheets/{sheet_id}/pieces/detecter")
def detect_sheet_rooms(
    sheet_id: int,
    payload: RoomDetect,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Détecte les pièces fermées par les calques désignés ; les noms sont lus en tâche de fond."""
    sheet = _sheet_or_404(db, user, sheet_id)
    return _rooms_action(
        db, sheet, lambda project: thermique_pieces.detect_rooms(db, project, sheet, payload.fermeture_cm / 100), background
    )


@router.post("/sheets/{sheet_id}/pieces")
def add_sheet_room(
    sheet_id: int,
    payload: RoomAdd,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Ajoute la pièce qui contient le point cliqué."""
    sheet = _sheet_or_404(db, user, sheet_id)
    return _rooms_action(
        db, sheet, lambda project: thermique_pieces.add_room_at(db, project, sheet, payload.x, payload.y, payload.fermeture_cm / 100), background
    )


@router.post("/sheets/{sheet_id}/pieces/tracer")
def trace_sheet_room(
    sheet_id: int,
    payload: RoomTrace,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Crée une pièce depuis ses sommets, sans classification préalable des éléments du plan."""
    sheet = _sheet_or_404(db, user, sheet_id)
    return _rooms_action(db, sheet, lambda project: thermique_pieces.trace_room(db, project, sheet, payload.contour), background)


@router.post("/sheets/{sheet_id}/pieces/fusion")
def merge_sheet_rooms(
    sheet_id: int, payload: RoomMerge, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
) -> dict:
    sheet = _sheet_or_404(db, user, sheet_id)
    return _rooms_action(db, sheet, lambda project: thermique_pieces.merge_rooms(db, project, sheet, payload.ids))


@router.get("/pieces/{room_id}/composants")
def read_room_components(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)) -> dict:
    """Ce qui borde ce local, côté par côté : familles collées au contour et longueur de contact."""
    room = _room_or_404(db, user, room_id)
    sheet = db.get(ThermiqueSheet, room.sheet_id)
    project = db.get(ThermiqueProject, sheet.project_id)
    try:
        return thermique_pieces.room_components(db, project, sheet, room)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/pieces/{room_id}")
def update_room(room_id: int, payload: RoomUpdate, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)) -> dict:
    """Nom saisi, classe choisie (chauffé, non chauffé, extérieur), ou contour corrigé à la main."""
    room = _room_or_404(db, user, room_id)
    sheet = db.get(ThermiqueSheet, room.sheet_id)
    return _rooms_action(db, sheet, lambda project: thermique_pieces.update_room(db, room, payload.model_dump(exclude_unset=True)))


@router.delete("/pieces/{room_id}")
def delete_room(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)) -> dict:
    room = _room_or_404(db, user, room_id)
    sheet = db.get(ThermiqueSheet, room.sheet_id)
    return _rooms_action(db, sheet, lambda project: thermique_pieces.delete_room(db, room))


@router.post("/pieces/{room_id}/decoupe")
def split_room(room_id: int, payload: RoomSplit, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)) -> dict:
    """Coupe une pièce en deux le long d'un trait."""
    room = _room_or_404(db, user, room_id)
    sheet = db.get(ThermiqueSheet, room.sheet_id)
    return _rooms_action(db, sheet, lambda project: thermique_pieces.split_room(db, project, room, payload.p1, payload.p2))


@router.get("/sheets/{sheet_id}/murs")
def read_sheet_walls(
    sheet_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Murs coupés du plan lus sur les vecteurs du PDF, en polygones, avec les types par épaisseur."""
    sheet = _sheet_or_404(db, user, sheet_id)
    try:
        return thermique_metre.sheet_walls(sheet)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Détection des murs impossible pour la planche %s", sheet_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Détection des murs impossible.") from exc


@router.post("/projects/{project_id}/hauteurs-coupe")
def apply_section_heights_route(
    project_id: int,
    payload: SectionHeightsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    project = _project_or_404(db, user, project_id)
    sheet = _sheet_or_404(db, user, payload.planche_id)
    return _metre_action(
        db,
        project,
        lambda: thermique_metre.apply_section_heights(
            db, project, sheet, payload.dessin, payload.sens_montant, payload.premier_intervalle
        ),
    )


@router.get("/sheets/{sheet_id}/traits")
def read_sheet_traits(
    sheet_id: int,
    seuil: float | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> dict:
    """Traits épais de la planche (faces de murs), pour aimanter le tracé du métré."""
    sheet = _sheet_or_404(db, user, sheet_id)
    if seuil is not None and not 0 <= seuil <= 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seuil d'épaisseur hors limites.")
    try:
        return thermique_metre.sheet_traits(sheet, seuil)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Lecture des traits impossible pour la planche %s", sheet.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lecture des traits de la planche impossible."
        ) from exc


@router.post(
    "/admin/external-accounts",
    response_model=ExternalAccountRead,
    status_code=status.HTTP_201_CREATED,
)
def create_external_account_route(
    payload: ExternalAccountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
) -> User:
    """Création d'un compte bureau d'études, réservée aux administrateurs Po2."""
    if is_external_role(user.role) or not is_admin_role(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")
    try:
        return create_external_account(db, payload.email, payload.nom, payload.prenom, payload.password)
    except ThermiqueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
