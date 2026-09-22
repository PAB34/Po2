"""Fichier d'étude d'un niveau, import et stockage versionné (lot E2, D53 à D55).

Le fichier est assemblé sur le poste à partir des résultats raster déjà produits. Le serveur
ne relit jamais les vecteurs du PDF : il vérifie le document et transforme seulement le repère
normalisé de la feuille en points PDF grâce à la matrice du rendu pdfium.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.thermique import ThermiqueEtude, ThermiqueEtudeVersion, ThermiqueSheet
from app.models.user import User
from app.services import thermique_enveloppe_pieces as pieces
from app.services.thermique import ThermiqueError

ETUDE_FORMAT = "thermique.etude_niveau"
ETUDE_FORMAT_VERSION = 1
MAX_ETUDE_BYTES = 10 * 1024 * 1024
LOCAL_NATURES = {"chauffe", "circulation", "non_chauffe"}


class EtudeConflict(ThermiqueError):
    """Une étude existe déjà et son remplacement n'a pas été confirmé."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_analyse_portable(manifest: dict[str, Any]) -> dict[str, Any]:
    """Retire les chemins absolus des images de travail tout en gardant le repère géométrique."""
    portable = {key: copy.deepcopy(value) for key, value in manifest.items() if key not in {"overview"}}
    portable["tiles"] = [
        {key: copy.deepcopy(value) for key, value in tile.items() if key != "path"}
        for tile in manifest.get("tiles", [])
    ]
    return portable


def _manifest_enveloppe_portable(manifest: dict[str, Any]) -> dict[str, Any]:
    # Les planches et guides sont des images locales de contrôle. La géométrie nécessaire à E3
    # (bâtiment, trous, tronçons, échelle) reste intégralement dans le fichier.
    return {
        key: copy.deepcopy(value)
        for key, value in manifest.items()
        if key not in {"guide", "planches", "plan_guide"}
    }


def _noms_locaux(analyse: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    objets = [
        objet
        for objet in analyse.get("objects", [])
        if objet.get("category") == "piece" and len(objet.get("points", [])) >= 3
    ]
    noms = [str(objet.get("subtype") or objet.get("id") or "local") for objet in objets]
    homonymes = {nom for nom in noms if noms.count(nom) > 1}
    rangs: dict[str, int] = {}
    resultat = []
    for objet, nom in zip(objets, noms):
        if nom in homonymes:
            rangs[nom] = rangs.get(nom, 0) + 1
            nom = f"{nom} ({rangs[nom]})"
        resultat.append((objet, nom))
    return resultat


def assembler_etude_niveau(
    source: Path,
    niveau: str,
    page_number: int,
    echelle: float,
    analyse: dict[str, Any],
    manifeste: dict[str, Any],
    releve_brut: dict[str, Any],
    restitution: dict[str, Any],
    controle: dict[str, Any],
) -> dict[str, Any]:
    """Assemble le contrat portable importé par l'application, sans appeler d'agent."""
    if analyse.get("uses_pdf_vectors") is not False:
        raise ThermiqueError("L'analyse ne garantit pas une lecture raster sans vecteurs PDF.")
    bibliotheque = restitution.get("enveloppe", {}).get("bibliotheque", {})
    fiches = {fiche.get("piece"): fiche for fiche in bibliotheque.get("fiches_locaux", [])}
    syntheses = {fiche.get("piece"): fiche for fiche in bibliotheque.get("pieces", [])}
    releve_resolu = pieces.decouper_par_piece(copy.deepcopy(releve_brut), manifeste, analyse)

    locaux = []
    for objet, nom in _noms_locaux(analyse):
        identifiant = str(objet.get("id") or "").strip()
        if not identifiant:
            raise ThermiqueError(f"Le local « {nom} » n'a pas d'identifiant stable.")
        fiche = fiches.get(nom)
        if fiche is None:
            raise ThermiqueError(f"Aucune fiche ne correspond au local « {nom} ».")
        demandes = [demande for demande in bibliotheque.get("demandes", []) if demande.get("piece") == nom]
        locaux.append(
            {
                "id": identifiant,
                "nom": nom,
                "nature": objet.get("local") or "chauffe",
                "contour": copy.deepcopy(objet["points"]),
                "surface_m2": fiche.get("surface_m2"),
                "fiche": copy.deepcopy(fiche),
                "synthese": copy.deepcopy(syntheses.get(nom, {})),
                "demandes": copy.deepcopy(demandes),
            }
        )
    if len(locaux) != len(fiches):
        orphelines = sorted(set(fiches) - {local["nom"] for local in locaux})
        raise ThermiqueError(f"Des fiches ne correspondent à aucun local : {', '.join(orphelines)}")

    analyse_portable = {
        key: copy.deepcopy(value)
        for key, value in analyse.items()
        if key not in {"manifest", "usage", "session_id"}
    }
    analyse_portable["manifest"] = _manifest_analyse_portable(analyse.get("manifest", {}))
    manifest_analyse = analyse.get("manifest", {})
    return {
        "format": ETUDE_FORMAT,
        "format_version": ETUDE_FORMAT_VERSION,
        "uses_pdf_vectors": False,
        "niveau": niveau,
        "source": {
            "filename": source.name,
            "sha256": _sha256(source),
            "page_index": page_number - 1,
            "scale_denominator": echelle,
            "viewer_rotation_deg": int(analyse.get("viewer_rotation_deg", manifest_analyse.get("viewer_rotation_deg", 0))),
            "page_width_px": int(manifest_analyse.get("page_width_px", 0)),
            "page_height_px": int(manifest_analyse.get("page_height_px", 0)),
        },
        "analyse": analyse_portable,
        "locaux": locaux,
        "locaux_ecartes": copy.deepcopy(analyse.get("locaux_ecartes", [])),
        "enveloppe": {
            "manifeste": _manifest_enveloppe_portable(manifeste),
            "releve": {
                "elements": copy.deepcopy(releve_resolu.get("elements", [])),
                "raccords": copy.deepcopy(releve_resolu.get("raccords", [])),
                "observations": copy.deepcopy(releve_resolu.get("observations", [])),
            },
            "catalogue": copy.deepcopy(releve_resolu.get("catalogue", [])),
            "synthese_pieces": copy.deepcopy(bibliotheque.get("pieces", [])),
            "fiches_locaux": copy.deepcopy(bibliotheque.get("fiches_locaux", [])),
            "controle": {key: copy.deepcopy(value) for key, value in controle.items() if key != "cellules"},
            "demandes": copy.deepcopy(bibliotheque.get("demandes", [])),
        },
    }


def ecrire_etude_niveau(destination: Path, **kwargs: Any) -> dict[str, Any]:
    contenu = assembler_etude_niveau(**kwargs)
    destination.write_text(json.dumps(contenu, ensure_ascii=False, indent=1), encoding="utf-8")
    return contenu


def _nombre(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ThermiqueError(f"{label} doit être un nombre.")
    return float(value)


def _inverser_transform(transform: list[Any], px: float, py: float) -> list[float]:
    if not isinstance(transform, list) or len(transform) != 6:
        raise ThermiqueError("La transformation du raster est invalide.")
    a, b, c, d, e, f = (_nombre(value, "La transformation") for value in transform)
    determinant = a * d - b * c
    if abs(determinant) < 1e-12:
        raise ThermiqueError("La transformation du raster n'est pas inversible.")
    dx, dy = px - e, py - f
    return [round((d * dx - c * dy) / determinant, 3), round((-b * dx + a * dy) / determinant, 3)]


def valider_et_convertir(
    payload: Any,
    sheet: ThermiqueSheet,
    raster_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Valide le fichier et ajoute à chaque local son contour durable en points PDF."""
    if not isinstance(payload, dict):
        raise ThermiqueError("Le fichier d'étude doit contenir un objet JSON.")
    if payload.get("format") != ETUDE_FORMAT or payload.get("format_version") != ETUDE_FORMAT_VERSION:
        raise ThermiqueError("Format d'étude inconnu ou version non prise en charge.")
    if payload.get("uses_pdf_vectors") is not False:
        raise ThermiqueError("L'étude doit provenir exclusivement de la lecture raster du plan.")
    source = payload.get("source")
    if not isinstance(source, dict):
        raise ThermiqueError("La source de l'étude est absente.")
    if source.get("sha256") != sheet.document.sha256:
        raise ThermiqueError("Cette étude ne correspond pas au PDF de la planche choisie.")
    if source.get("page_index") != sheet.page_index:
        raise ThermiqueError("Cette étude ne correspond pas à la page de la planche choisie.")
    rotation = source.get("viewer_rotation_deg")
    if rotation not in {0, 90, 180, 270} or raster_manifest.get("rotation") != rotation:
        raise ThermiqueError("La rotation de référence de l'étude est invalide.")
    width = _nombre(raster_manifest.get("width_px"), "La largeur du raster")
    height = _nombre(raster_manifest.get("height_px"), "La hauteur du raster")
    source_width = _nombre(source.get("page_width_px"), "La largeur de la source")
    source_height = _nombre(source.get("page_height_px"), "La hauteur de la source")
    if min(width, height, source_width, source_height) <= 0:
        raise ThermiqueError("Les dimensions de la feuille sont invalides.")
    if abs((source_width / source_height) / (width / height) - 1) > 0.01:
        raise ThermiqueError("Les proportions de l'étude ne correspondent pas à la planche choisie.")

    locaux = payload.get("locaux")
    if not isinstance(locaux, list) or not locaux:
        raise ThermiqueError("L'étude ne contient aucun local.")
    contenu = copy.deepcopy(payload)
    ids: set[str] = set()
    for index, local in enumerate(contenu["locaux"], 1):
        if not isinstance(local, dict):
            raise ThermiqueError(f"Le local {index} est invalide.")
        local_id = local.get("id")
        if not isinstance(local_id, str) or not local_id.strip() or local_id in ids:
            raise ThermiqueError("Chaque local doit avoir un identifiant unique et non vide.")
        ids.add(local_id)
        if local.get("nature") not in LOCAL_NATURES:
            raise ThermiqueError(f"La nature du local « {local_id} » est inconnue.")
        if not isinstance(local.get("fiche"), dict) or local["fiche"].get("piece") != local.get("nom"):
            raise ThermiqueError(f"La fiche du local « {local_id} » ne correspond pas à son nom.")
        contour = local.get("contour")
        if not isinstance(contour, list) or len(contour) < 3:
            raise ThermiqueError(f"Le contour du local « {local_id} » doit avoir au moins trois points.")
        contour_pdf = []
        for point in contour:
            if not isinstance(point, list) or len(point) != 2:
                raise ThermiqueError(f"Un point du local « {local_id} » est invalide.")
            x, y = (_nombre(value, "Une coordonnée") for value in point)
            if not 0 <= x <= 1000 or not 0 <= y <= 1000:
                raise ThermiqueError(f"Le contour du local « {local_id} » sort de la feuille.")
            contour_pdf.append(_inverser_transform(raster_manifest["transform"], x * width / 1000, y * height / 1000))
        local["contour_pdf"] = contour_pdf
    return contenu


def get_etude_for_sheet(db: Session, sheet_id: int) -> ThermiqueEtude | None:
    return db.scalar(select(ThermiqueEtude).where(ThermiqueEtude.sheet_id == sheet_id))


def importer_etude(
    db: Session,
    sheet: ThermiqueSheet,
    user: User,
    payload: dict[str, Any],
    raster_manifest: dict[str, Any],
    remplacer: bool = False,
) -> ThermiqueEtude:
    if sheet.nature != "plan":
        raise ThermiqueError("Une étude de niveau ne peut être importée que sur une planche classée comme plan.")
    if sheet.scale_denominator is None:
        raise ThermiqueError("Définissez et contrôlez l'échelle de la planche avant d'importer l'étude.")
    contenu = valider_et_convertir(payload, sheet, raster_manifest)
    etude = get_etude_for_sheet(db, sheet.id)
    if etude is not None and not remplacer:
        raise EtudeConflict("Une étude existe déjà sur cette planche. Confirmez son remplacement.")
    etats = {local["id"]: {"status": "a_verifier", "motif": None} for local in contenu["locaux"]}
    contenu_json = json.dumps(contenu, ensure_ascii=False, separators=(",", ":"))
    etats_json = json.dumps(etats, ensure_ascii=False, separators=(",", ":"))
    if etude is None:
        etude = ThermiqueEtude(
            project_id=sheet.project_id,
            sheet_id=sheet.id,
            format_version=ETUDE_FORMAT_VERSION,
            content_json=contenu_json,
            local_states_json=etats_json,
            imported_by_user_id=user.id,
        )
        db.add(etude)
        db.flush()
        numero = 1
        motif = "import_initial"
    else:
        numero = int(
            db.scalar(
                select(func.max(ThermiqueEtudeVersion.version_number)).where(
                    ThermiqueEtudeVersion.etude_id == etude.id
                )
            )
            or 0
        ) + 1
        motif = "import_remplacement"
        etude.format_version = ETUDE_FORMAT_VERSION
        etude.content_json = contenu_json
        etude.local_states_json = etats_json
        etude.imported_by_user_id = user.id
    db.add(
        ThermiqueEtudeVersion(
            etude_id=etude.id,
            version_number=numero,
            reason=motif,
            content_json=contenu_json,
            local_states_json=etats_json,
            created_by_user_id=user.id,
        )
    )
    db.commit()
    db.refresh(etude)
    return etude


def serialize_etude(db: Session, etude: ThermiqueEtude) -> dict[str, Any]:
    numero = int(
        db.scalar(
            select(func.max(ThermiqueEtudeVersion.version_number)).where(
                ThermiqueEtudeVersion.etude_id == etude.id
            )
        )
        or 0
    )
    return {
        "id": etude.id,
        "project_id": etude.project_id,
        "sheet_id": etude.sheet_id,
        "format_version": etude.format_version,
        "version_number": numero,
        "content": json.loads(etude.content_json),
        "local_states": json.loads(etude.local_states_json),
        "imported_by_user_id": etude.imported_by_user_id,
        "created_at": etude.created_at,
        "updated_at": etude.updated_at,
    }
