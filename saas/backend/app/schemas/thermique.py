from datetime import datetime

from pydantic import BaseModel, Field


class SheetCalibration(BaseModel):
    p1: list[float]
    p2: list[float]
    length_pt: float
    real_length_m: float
    denominator_from_cote: float
    # Échelle usuelle à moins de 1 % de celle déduite de la cote (ex. 99,97 → 100), sinon null.
    standard_scale: float | None
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


class SheetUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    nature: str | None = None
    level_label: str | None = Field(default=None, max_length=80)
    rotation_deg: int | None = None
    scale_denominator: float | None = Field(default=None, gt=0, le=10000)


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
