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
    CalibrationRequest,
    ComponentCreate,
    ComponentEvaluate,
    ComponentImport,
    ComponentUpdate,
    ExternalAccountCreate,
    ExternalAccountRead,
    ProjectCreate,
    ProjectDetail,
    ProjectRead,
    ProjectUpdate,
    RasterManifest,
    SheetRead,
    SheetUpdate,
    UploadResult,
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
