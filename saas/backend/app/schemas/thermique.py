from datetime import datetime

from typing import Any, Literal

from pydantic import BaseModel, Field


class SheetNord(BaseModel):
    """Flèche du nord tracée sur la planche, en points PDF : p2 est la pointe, du côté du nord."""

    p1: list[float]
    p2: list[float]
    longueur_pt: float


class SheetCalibration(BaseModel):
    p1: list[float]
    p2: list[float]
    length_pt: float
    real_length_m: float
    denominator_from_cote: float
    # Échelle usuelle dont l'écart tient dans la précision du clic (ex. 99,97 → 100), sinon null (D203).
    standard_scale: float | None
    # Précision de la cote, en % : ce qu'un clic de travers explique (1 pt sur la longueur cliquée).
    precision_pct: float | None = None
    measured_m: float | None
    ecart_pct: float | None


class SheetRead(BaseModel):
    id: int
    project_id: int
    document_id: int
    page_index: int
    label: str
    nature: str | None
    nature_suggested: str | None
    level_label: str | None
    scale_denominator: float | None
    scale_source: str | None
    rotation_deg: int
    page_width_pt: float
    page_height_pt: float
    status: str
    calibration: SheetCalibration | None
    nord: SheetNord | None = None
    # Calage sur la planche de référence (S2, D173) : similitude a, b, tx, ty et ses points d'appui.
    calage: dict[str, Any] | None = None


class DocumentRead(BaseModel):
    id: int
    project_id: int
    original_filename: str
    file_format: str
    size_bytes: int
    page_count: int
    created_at: datetime
    sheets: list[SheetRead]


class ProjectRead(BaseModel):
    id: int
    owner_user_id: int
    name: str
    description: str | None
    reference_sheet_id: int | None
    created_at: datetime
    updated_at: datetime
    document_count: int
    sheet_count: int
    sheets_ready: int


class ProjectDetail(ProjectRead):
    documents: list[DocumentRead]


class UploadError(BaseModel):
    filename: str
    message: str


class UploadResult(BaseModel):
    project: ProjectDetail
    imported: list[str]
    errors: list[UploadError]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    reference_sheet_id: int | None = None


class SheetUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    nature: str | None = None
    level_label: str | None = Field(default=None, max_length=80)
    rotation_deg: int | None = None
    scale_denominator: float | None = Field(default=None, gt=0, le=10000)


class CalageRequest(BaseModel):
    """Deux points de la planche et les deux mêmes points sur une planche déjà calée, en points PDF."""

    cible_sheet_id: int
    points: list[list[float]] = Field(min_length=2, max_length=2)
    points_cible: list[list[float]] = Field(min_length=2, max_length=2)


class NordRequest(BaseModel):
    """Flèche du nord : p1 sa base, p2 **sa pointe, du côté du nord**, en points PDF."""

    p1: list[float] = Field(min_length=2, max_length=2)
    p2: list[float] = Field(min_length=2, max_length=2)
    tout_le_projet: bool = True


class CalibrationRequest(BaseModel):
    p1: list[float] = Field(min_length=2, max_length=2)
    p2: list[float] = Field(min_length=2, max_length=2)
    real_length_m: float = Field(gt=0, le=10000)
    apply: bool = False


class ExternalAccountCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    nom: str = Field(min_length=1, max_length=120)
    prenom: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class ExternalAccountRead(BaseModel):
    id: int
    email: str
    nom: str
    prenom: str
    role: str


class RasterLevel(BaseModel):
    z: int
    width: int
    height: int
    cols: int
    rows: int


class RasterManifest(BaseModel):
    sheet_id: int
    rotation: int
    tile_size: int
    width_px: int
    height_px: int
    scale: float
    # PDF (pt) → pixels du niveau le plus fin : px = a·x + c·y + e ; py = b·x + d·y + f
    transform: list[float]
    levels: list[RasterLevel]
    # Tuiles non blanches par niveau ("x_y") ; les autres sont blanches.
    tiles: dict[str, list[str]]
    build_seconds: float
    tile_url: str


class ComponentCreate(BaseModel):
    categorie: str
    nom: str | None = Field(default=None, max_length=200)
    code: str | None = Field(default=None, max_length=20)
    statut: str | None = None
    composition: dict | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ComponentUpdate(BaseModel):
    nom: str | None = Field(default=None, max_length=200)
    code: str | None = Field(default=None, max_length=20)
    statut: str | None = None
    composition: dict | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ComponentImport(BaseModel):
    modele_id: int


class ComponentEvaluate(BaseModel):
    categorie: str
    composition: dict


class EraseAllRequest(BaseModel):
    # Le mot « EFFACER », tapé par l'utilisateur, confirme l'effacement de tous ses projets.
    confirmation: str = Field(default="", max_length=20)


class EtudeRead(BaseModel):
    id: int
    project_id: int
    sheet_id: int
    format_version: int
    version_number: int
    content: dict[str, Any]
    local_states: dict[str, dict[str, Any]]
    imported_by_user_id: int | None
    created_at: datetime
    updated_at: datetime




class ElementReference(BaseModel):
    """Un élément relevé, désigné par sa position sur l'enveloppe (F4)."""

    troncon: str
    debut_m: float
    fin_m: float


class EtudeOperation(BaseModel):
    """Un geste du thermicien sur un local (E3, D61) ou sur un élément d'enveloppe (F4, D99)."""

    type: Literal[
        "modifier",
        "couper",
        "fusionner",
        "local_ajouter",
        "local_supprimer",
        "element_confirmer",
        "element_corriger",
        "element_ecarter",
        "element_reactiver",
        "pont_ajouter",
        "paroi_retracer",
    ]
    id: str | None = None
    # Mur retracé (D240) : début et fin le long de la façade, et la composition copiée.
    debut_m: float | None = None
    fin_m: float | None = None
    modele: dict[str, Any] | None = None
    # Pont posé par le thermicien (remarque C) : son point et son type.
    point_pdf: list[float] | None = None
    type_pont: Literal["angle_sortant", "angle_rentrant", "about_refend"] | None = None
    reference_pont: str | None = None
    # Position calculée par l'écran pour un pont posé : le serveur la vérifie (P5, D164).
    troncon: str | None = None
    abscisse_m: float | None = None
    ids: list[str] | None = None
    contour: list[list[float]] | None = None
    contour_pdf: list[list[float]] | None = None
    segment: list[list[float]] | None = None
    segment_pdf: list[list[float]] | None = None
    nature: Literal["chauffe", "circulation", "non_chauffe", "gaine_technique", "exterieur"] | None = None
    nom: str | None = None
    noms: list[str] | None = None
    # Hauteur sous plafond fini d'un local (S5, D178), ou son retrait au profit de celle des coupes.
    hauteur_m: float | None = None
    retirer_hauteur: bool | None = None
    # Gestes sur un élément d'enveloppe.
    element: ElementReference | None = None
    changes: dict[str, Any] | None = None
    portee: Literal["cet_element", "partout"] | None = None
    motif: str | None = None


class EtudeRemodelage(BaseModel):
    # Une passe sur les ponts juge les 77 liaisons du R+1 en un seul enregistrement : l'ancien plafond de
    # 50 gestes refusait tout le lot (erreur 422, 2026-09-28). Le plafond garde une borne, pas un frein.
    operations: list[EtudeOperation] = Field(default_factory=list, max_length=2000)


class EtudeEnregistrement(EtudeRemodelage):
    local_id: str | None = None
    motif: str = "validation_local"
    valider: bool = True


class EtudeApercu(BaseModel):
    """Résultat d'un « Remodéliser » : rien n'est écrit en base."""

    content: dict[str, Any]
    couverture: dict[str, Any]
    voisins_modifies: list[str]
    bloquant: str | None = None


class EtudeVersionRead(BaseModel):
    version_number: int
    reason: str
    created_by_user_id: int | None
    created_at: datetime


class TravailRead(BaseModel):
    """Un niveau dans la file d'analyse (D92)."""

    id: int
    project_id: int
    sheet_id: int
    label: str
    level_label: str | None
    type: str = "niveau"
    statut: str
    rang: int
    message: str | None
    pris_a: datetime | None
    fini_a: datetime | None
    created_at: datetime


class TravailEcarte(BaseModel):
    sheet_id: int
    label: str
    motif: str


class MiseEnFileResult(BaseModel):
    ajoutes: list[TravailRead]
    ecartes: list[TravailEcarte]


class TravailConsignes(BaseModel):
    """Ce que le relais doit passer à ``run_etude_niveau.py`` pour ce niveau."""

    travail_id: int
    type: str = "niveau"
    sheet_id: int
    label: str = ""
    nature: str | None = None
    project_id: int
    document_id: int
    niveau: str
    page: int
    rotation: int
    echelle: float | None


class TravailIncident(BaseModel):
    message: str


class LectureCoupes(BaseModel):
    """Ce que rend le relais pour un travail « traits » (un plan) ou « coupes » (une planche) (S5, D181)."""

    traits: list[dict[str, Any]] | None = None
    vues: list[dict[str, Any]] | None = None


class VueCorrigee(BaseModel):
    """Le cadre redessiné (deux coins opposés, points PDF de la planche) et/ou le haut d'une vue (D205)."""

    cadre: list[float] | None = Field(default=None, min_length=4, max_length=4)
    haut: str | None = None
    # Renommage et reclassement par le thermicien (D206).
    nom: str | None = None
    nature: str | None = None


class VueTracee(BaseModel):
    """Une vue tracée à la main (D231) : nom, nature, cadre (deux coins, points PDF), haut dans la page."""

    nom: str = Field(min_length=1, max_length=80)
    nature: str
    cadre: list[float] = Field(min_length=4, max_length=4)
    haut: str


class TraitTrace(BaseModel):
    """Le trait d'une coupe tracé à la main sur le plan : deux points et le côté regardé (D209)."""

    vue_id: int
    points: list[list[float]] = Field(min_length=2, max_length=2)
    sens: list[float] = Field(min_length=2, max_length=2)


class HauteurConfirmee(BaseModel):
    """Deux clics dans la coupe, en points PDF de sa planche : sol fini puis plafond fini d'une pièce (D191)."""

    sol: list[float] = Field(min_length=2, max_length=2)
    plafond: list[float] = Field(min_length=2, max_length=2)


class MenuiserieConfirmee(BaseModel):
    """Deux coins opposés d'une menuiserie sur l'élévation (points PDF de sa planche), et à quoi la hauteur
    s'applique : tout le composant (`largeur_cm` absent, D200) ou une baie de cette largeur."""

    coins: list[list[float]] = Field(min_length=2, max_length=2)
    composant: str = Field(min_length=1, max_length=40)
    largeur_cm: float | None = None


class ModeleMesure(BaseModel):
    """Un modèle de menuiserie : deux coins opposés sur une coupe ou une élévation, et son nom (D219)."""

    coins: list[list[float]] = Field(min_length=2, max_length=2)
    nom: str = Field(min_length=1, max_length=60)


class HauteursDuPlan(BaseModel):
    sheet_id: int
    locaux: dict[str, dict[str, Any]]
    coupes: list[dict[str, Any]]
    traits_sans_vue: list[str]
    # Coupes dont le trait n'a pu être ni relevé ni déduit (D190) : sans numéros de pièces communs.
    coupes_non_situees: list[str] = []
    traits: list[dict[str, Any]]
