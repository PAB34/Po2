"""Outil de métré thermique — socle (étape 1).

Projets, import de plans PDF (une planche par page), nature et niveau suggérés à partir du
nom de fichier, échelle déclarée puis contrôlée par une cote.

Unités : les coordonnées d'une planche sont en points PDF (1 pt = 25,4/72 mm sur le papier).
À l'échelle 1/N, 1 pt vaut donc 0,3528 × N mm réels. Vérifié sur le plan niveau 0 du projet
d'essai : l'emprise des murs mesure 31,82 m à 1/100, soit la cote imprimée.
Voir `docs/thermique/00-audit-existant-faisabilite.md`.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import unicodedata
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import THERMIQUE_EXTERNAL_ROLE
from app.core.security import get_password_hash
from app.models.thermique import ThermiqueDocument, ThermiqueProject, ThermiqueSheet
from app.models.user import User
from app.services.auth import get_user_by_email
from app.services.thermique_raster import raster_root

PT_TO_MM = 25.4 / 72.0
SHEET_NATURES = ("plan", "coupe", "facade", "plan_masse", "autre")
ALLOWED_ROTATIONS = (0, 90, 180, 270)


class ThermiqueError(ValueError):
    """Erreur métier dont le message est destiné à l'utilisateur."""


# --- Échelle ----------------------------------------------------------------


def paper_pt_to_real_m(length_pt: float, denominator: float) -> float:
    return length_pt * PT_TO_MM * denominator / 1000.0


def denominator_from_measure(length_pt: float, real_length_m: float) -> float:
    if length_pt <= 0 or real_length_m <= 0:
        raise ThermiqueError("La mesure et la longueur réelle doivent être positives.")
    return real_length_m * 1000.0 / (length_pt * PT_TO_MM)


# --- Suggestions à l'import ---------------------------------------------------


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).upper()


def suggest_nature_and_level(filename: str) -> tuple[str | None, str | None]:
    """Nature et niveau probables d'une planche, d'après le nom du fichier.

    Les PDF de plans n'ont en général aucun texte lisible (textes vectorisés à l'impression) :
    le nom du fichier est le seul indice fiable. La suggestion est toujours validée par
    l'utilisateur.
    """
    text = _normalize(Path(filename).stem)
    if "COUPE" in text:
        return "coupe", None
    if "ELEV" in text or "FACADE" in text:
        return "facade", None
    if "MASSE" in text or "IMPLANTATION" in text or "SITUATION" in text:
        return "plan_masse", None
    if "TOITURE" in text or "TERRASSE" in text:
        return "plan", "Toiture"
    match = re.search(r"NIVEAU\s*_?(-?\d+)", text)
    if match:
        return "plan", f"Niveau {int(match.group(1))}"
    match = re.search(r"(?<![A-Z])R\s*\+\s*(\d+)", text)
    if match:
        return "plan", f"R+{int(match.group(1))}"
    if re.search(r"(?<![A-Z])RDC(?![A-Z])", text):
        return "plan", "RDC"
    if re.search(r"SOUS[\s_-]?SOL", text):
        return "plan", "Sous-sol"
    match = re.search(r"ETAGE\s*_?(\d+)", text)
    if match:
        return "plan", f"Étage {int(match.group(1))}"
    if "PLAN" in text or "NIVEAU" in text:
        return "plan", None
    return None, None


# --- Lecture PDF et stockage --------------------------------------------------


def read_pdf_pages(data: bytes) -> list[tuple[float, float]]:
    """Largeur et hauteur (pt) de chaque page. Ne lit pas le contenu graphique."""
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ThermiqueError("Ce PDF est protégé par un mot de passe.")
        pages = [(float(page.mediabox.width), float(page.mediabox.height)) for page in reader.pages]
    except ThermiqueError:
        raise
    except Exception as exc:  # pypdf lève des exceptions de types variés sur un fichier abîmé
        raise ThermiqueError("Ce PDF est illisible ou endommagé.") from exc
    if not pages:
        raise ThermiqueError("Ce PDF ne contient aucune page.")
    return pages


def max_upload_bytes() -> int:
    return settings.thermique_max_upload_mb * 1024 * 1024


def _project_dir(project_id: int) -> Path:
    return Path(settings.thermique_storage_dir) / f"projet_{project_id}"


def document_path(document: ThermiqueDocument) -> Path:
    return _project_dir(document.project_id) / document.stored_filename


# --- Projets ------------------------------------------------------------------


def list_projects(db: Session, user: User) -> list[ThermiqueProject]:
    statement = (
        select(ThermiqueProject)
        .where(ThermiqueProject.owner_user_id == user.id)
        .order_by(ThermiqueProject.updated_at.desc(), ThermiqueProject.id.desc())
    )
    return list(db.scalars(statement))


def get_project_for_user(db: Session, user: User, project_id: int) -> ThermiqueProject | None:
    """Un projet n'est visible que de son propriétaire (étape 1 : pas de partage)."""
    project = db.get(ThermiqueProject, project_id)
    if project is None or project.owner_user_id != user.id:
        return None
    return project


def create_project(db: Session, user: User, name: str, description: str | None) -> ThermiqueProject:
    project = ThermiqueProject(
        owner_user_id=user.id,
        name=name.strip(),
        description=(description or "").strip() or None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: ThermiqueProject, changes: dict[str, Any]) -> ThermiqueProject:
    if "name" in changes and changes["name"] is not None:
        name = changes["name"].strip()
        if not name:
            raise ThermiqueError("Le nom du projet est obligatoire.")
        project.name = name
    if "description" in changes:
        project.description = (changes["description"] or "").strip() or None
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: ThermiqueProject) -> None:
    folder = _project_dir(project.id)
    db.delete(project)
    db.commit()
    shutil.rmtree(folder, ignore_errors=True)


# --- Fichiers -----------------------------------------------------------------


def add_document(
    db: Session,
    project: ThermiqueProject,
    filename: str,
    data: bytes,
    user: User,
) -> ThermiqueDocument:
    extension = Path(filename).suffix.lower()
    if extension in (".dxf", ".dwg"):
        raise ThermiqueError(
            "Les fichiers DXF et DWG seront pris en charge à l'étape 2. Importez le PDF pour l'instant."
        )
    if extension != ".pdf":
        raise ThermiqueError("Format non pris en charge : importez un fichier PDF.")
    if len(data) > max_upload_bytes():
        raise ThermiqueError(f"Fichier trop volumineux (maximum {settings.thermique_max_upload_mb} Mo).")
    if b"%PDF" not in data[:1024]:
        raise ThermiqueError("Ce fichier n'est pas un PDF.")

    pages = read_pdf_pages(data)
    sha256 = hashlib.sha256(data).hexdigest()
    duplicate = db.scalar(
        select(ThermiqueDocument).where(
            ThermiqueDocument.project_id == project.id,
            ThermiqueDocument.sha256 == sha256,
        )
    )
    if duplicate is not None:
        raise ThermiqueError(f"Ce fichier est déjà importé dans le projet ({duplicate.original_filename}).")

    stored_filename = f"{uuid.uuid4().hex}.pdf"
    folder = _project_dir(project.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / stored_filename
    path.write_bytes(data)

    try:
        document = ThermiqueDocument(
            project_id=project.id,
            original_filename=filename[:255],
            stored_filename=stored_filename,
            file_format="pdf",
            size_bytes=len(data),
            sha256=sha256,
            page_count=len(pages),
            uploaded_by_user_id=user.id,
        )
        db.add(document)
        db.flush()

        nature, level = suggest_nature_and_level(filename)
        stem = Path(filename).stem
        for index, (width, height) in enumerate(pages):
            label = stem if len(pages) == 1 else f"{stem} - p. {index + 1}"
            db.add(
                ThermiqueSheet(
                    project_id=project.id,
                    document_id=document.id,
                    page_index=index,
                    label=label[:200],
                    nature=None,
                    nature_suggested=nature,
                    level_label=level,
                    rotation_deg=0,
                    page_width_pt=width,
                    page_height_pt=height,
                )
            )
        project.updated_at = document.created_at or project.updated_at
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    db.refresh(document)
    return document


def delete_document(db: Session, document: ThermiqueDocument) -> None:
    path = document_path(document)
    raster_folders = [raster_root(document.project_id, sheet.id) for sheet in document.sheets]
    db.delete(document)
    db.commit()
    path.unlink(missing_ok=True)
    for folder in raster_folders:
        shutil.rmtree(folder, ignore_errors=True)


# --- Planches -----------------------------------------------------------------


def update_sheet(db: Session, sheet: ThermiqueSheet, changes: dict[str, Any]) -> ThermiqueSheet:
    if "label" in changes and changes["label"] is not None:
        sheet.label = changes["label"].strip()[:200] or sheet.label
    if "nature" in changes:
        nature = changes["nature"]
        if nature is not None and nature not in SHEET_NATURES:
            raise ThermiqueError("Nature de planche inconnue.")
        sheet.nature = nature
    if "level_label" in changes:
        sheet.level_label = (changes["level_label"] or "").strip()[:80] or None
    if "rotation_deg" in changes and changes["rotation_deg"] is not None:
        rotation = int(changes["rotation_deg"]) % 360
        if rotation not in ALLOWED_ROTATIONS:
            raise ThermiqueError("La rotation doit être un multiple de 90°.")
        sheet.rotation_deg = rotation
    if "scale_denominator" in changes:
        denominator = changes["scale_denominator"]
        sheet.scale_denominator = float(denominator) if denominator else None
        sheet.scale_source = "declaree" if denominator else None
    db.commit()
    db.refresh(sheet)
    return sheet


def calibrate_sheet(
    db: Session,
    sheet: ThermiqueSheet,
    p1: list[float],
    p2: list[float],
    real_length_m: float,
    apply: bool,
) -> ThermiqueSheet:
    """Contrôle l'échelle par une cote : deux points cliqués et la longueur réelle lue.

    Sans échelle déclarée, l'échelle déduite de la cote est appliquée d'office. Sinon elle
    ne remplace l'échelle déclarée que sur demande (`apply`).
    """
    length_pt = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if length_pt < 1.0:
        raise ThermiqueError("Les deux points sont trop proches pour contrôler l'échelle.")
    denominator = denominator_from_measure(length_pt, real_length_m)
    sheet.calibration_json = json.dumps(
        {
            "p1": [round(p1[0], 3), round(p1[1], 3)],
            "p2": [round(p2[0], 3), round(p2[1], 3)],
            "length_pt": round(length_pt, 3),
            "real_length_m": real_length_m,
        }
    )
    if apply or sheet.scale_denominator is None:
        sheet.scale_denominator = round(denominator, 2)
        sheet.scale_source = "cote"
    db.commit()
    db.refresh(sheet)
    return sheet


def sheet_status(sheet: ThermiqueSheet) -> str:
    if sheet.nature is None:
        return "a_classer"
    if sheet.scale_denominator is None:
        return "a_mettre_a_l_echelle"
    return "prete"


def sheet_calibration(sheet: ThermiqueSheet) -> dict[str, Any] | None:
    if not sheet.calibration_json:
        return None
    raw = json.loads(sheet.calibration_json)
    length_pt = float(raw["length_pt"])
    real_length_m = float(raw["real_length_m"])
    measured_m = None
    ecart_pct = None
    if sheet.scale_denominator:
        measured_m = paper_pt_to_real_m(length_pt, sheet.scale_denominator)
        ecart_pct = (measured_m - real_length_m) / real_length_m * 100.0
    return {
        "p1": raw["p1"],
        "p2": raw["p2"],
        "length_pt": length_pt,
        "real_length_m": real_length_m,
        "denominator_from_cote": round(denominator_from_measure(length_pt, real_length_m), 2),
        "measured_m": round(measured_m, 3) if measured_m is not None else None,
        "ecart_pct": round(ecart_pct, 2) if ecart_pct is not None else None,
    }


# --- Sérialisation ------------------------------------------------------------


def serialize_sheet(sheet: ThermiqueSheet) -> dict[str, Any]:
    return {
        "id": sheet.id,
        "project_id": sheet.project_id,
        "document_id": sheet.document_id,
        "page_index": sheet.page_index,
        "label": sheet.label,
        "nature": sheet.nature,
        "nature_suggested": sheet.nature_suggested,
        "level_label": sheet.level_label,
        "scale_denominator": sheet.scale_denominator,
        "scale_source": sheet.scale_source,
        "rotation_deg": sheet.rotation_deg,
        "page_width_pt": sheet.page_width_pt,
        "page_height_pt": sheet.page_height_pt,
        "status": sheet_status(sheet),
        "calibration": sheet_calibration(sheet),
    }


def serialize_document(document: ThermiqueDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "project_id": document.project_id,
        "original_filename": document.original_filename,
        "file_format": document.file_format,
        "size_bytes": document.size_bytes,
        "page_count": document.page_count,
        "created_at": document.created_at,
        "sheets": [serialize_sheet(sheet) for sheet in document.sheets],
    }


def serialize_project(project: ThermiqueProject) -> dict[str, Any]:
    sheets = [sheet for document in project.documents for sheet in document.sheets]
    return {
        "id": project.id,
        "owner_user_id": project.owner_user_id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "document_count": len(project.documents),
        "sheet_count": len(sheets),
        "sheets_ready": sum(1 for sheet in sheets if sheet_status(sheet) == "prete"),
    }


def serialize_project_detail(project: ThermiqueProject) -> dict[str, Any]:
    return {
        **serialize_project(project),
        "documents": [serialize_document(document) for document in project.documents],
    }


# --- Comptes bureaux d'études ---------------------------------------------------


def create_external_account(db: Session, email: str, nom: str, prenom: str, password: str) -> User:
    """Compte limité à l'outil thermique : aucune ville, aucun accès aux données Po2."""
    email = email.strip().lower()
    if "@" not in email:
        raise ThermiqueError("Adresse email invalide.")
    if get_user_by_email(db, email) is not None:
        raise ThermiqueError("Un compte existe déjà avec cet email.")
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        nom=nom.strip(),
        prenom=prenom.strip(),
        city_id=None,
        role=THERMIQUE_EXTERNAL_ROLE,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
