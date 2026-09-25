"""Fichier d'étude d'un niveau, import et stockage versionné (lots E2 et E3, D53 à D64).

Le fichier est assemblé sur le poste à partir des résultats raster déjà produits. Le serveur
ne relit jamais les vecteurs du PDF : il vérifie le document et transforme seulement le repère
normalisé de la feuille en points PDF grâce à la matrice du rendu pdfium.

Version 2 du contrat (E3) : le fichier porte le **relevé brut** de l'enveloppe plutôt que sa version
déjà rattachée aux pièces, pour que le serveur puisse tout recalculer quand le thermicien déplace un
contour ; et chaque local dit, côté par côté, s'il suit une paroi lue sur le plan ou une simple limite
d'usage (D59). La source de vérité géométrique reste ``analyse["objects"]`` : ``locaux[].contour`` en
est le reflet, régénéré à chaque recalcul.

Version 3 du contrat (F1) : le fichier arrive **déjà calé**. Les contours reculent jusqu'au nu intérieur
mesuré avant d'être écrits (D66), les liaisons du relevé portent leur position sur la feuille (D74), le
tracé reprojeté des éléments d'enveloppe revient dans le fichier pour être dessiné (D75), et la chaîne
se relit elle-même : le rapport de cohérence entre les deux lectures voyage avec l'étude (D77).
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
from app.services import thermique_calage_contours as calage
from app.services import thermique_enveloppe_pieces as pieces
from app.services import thermique_etude_geometrie as geo
from app.services import thermique_fiches_locaux as fiches_locaux
from app.services import thermique_nord
from app.services import thermique_parcours_enveloppe as enveloppe
from app.services.thermique import ThermiqueError

ETUDE_FORMAT = "thermique.etude_niveau"
ETUDE_FORMAT_VERSION = 3
# Versions encore acceptées à l'import. La 2 reste lisible : une étude assemblée avant F1 doit pouvoir
# être réimportée, ne serait-ce que pour revenir en arrière. Elle arrive sans calage ni contrôle de
# cohérence ; le premier recalcul les lui donne, sans jamais retoucher ses contours (D66).
ETUDE_VERSIONS_LUES = (2, 3)
MAX_ETUDE_BYTES = 10 * 1024 * 1024

# Motifs de version écrits par un import, donc sans intervention humaine. Toute autre valeur est une
# retouche du thermicien ; la file d'analyse s'en sert pour ne jamais écraser son travail (D94).
MOTIF_IMPORT_INITIAL = "import_initial"
MOTIF_IMPORT_REMPLACEMENT = "import_remplacement"
MOTIFS_D_IMPORT = (MOTIF_IMPORT_INITIAL, MOTIF_IMPORT_REMPLACEMENT)
LOCAL_NATURES = {"chauffe", "circulation", "non_chauffe", "gaine_technique"}


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
    """Assemble le contrat portable importé par l'application, sans appeler d'agent.

    Le calage des contours sur le nu intérieur mesuré se fait ici, sur le poste, à l'assemblage (D66) :
    le serveur ne retouche jamais une géométrie en silence. Les fiches, la synthèse et la couverture sont
    ensuite régénérées par la chaîne de recalcul, la même qu'après chaque geste d'édition, pour que le
    fichier livré ne puisse pas décrire des contours qu'il n'a pas mesurés.
    """
    if analyse.get("uses_pdf_vectors") is not False:
        raise ThermiqueError("L'analyse ne garantit pas une lecture raster sans vecteurs PDF.")
    bibliotheque = restitution.get("enveloppe", {}).get("bibliotheque", {})
    fiches = {fiche.get("piece"): fiche for fiche in bibliotheque.get("fiches_locaux", [])}
    syntheses = {fiche.get("piece"): fiche for fiche in bibliotheque.get("pieces", [])}
    limites = geo.limites_des_locaux(analyse, manifeste)

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
                "limites": limites.get(identifiant, []),
                "surface_m2": fiche.get("surface_m2"),
                "fiche": copy.deepcopy(fiche),
                "synthese": copy.deepcopy(syntheses.get(nom, {})),
                "demandes": copy.deepcopy(demandes),
            }
        )
    if len(locaux) != len(fiches):
        orphelines = sorted(set(fiches) - {local["nom"] for local in locaux})
        raise ThermiqueError(f"Des fiches ne correspondent à aucun local : {', '.join(orphelines)}")

    # Calage : les contours reculent jusqu'au nu intérieur mesuré, ils ne s'agrandissent jamais (D66).
    analyse_calee, rapport_calage = calage.caler_locaux(analyse, manifeste, releve_brut)
    analyse_portable = {
        key: copy.deepcopy(value)
        for key, value in analyse_calee.items()
        if key not in {"manifest", "usage", "session_id"}
    }
    analyse_portable["manifest"] = _manifest_analyse_portable(analyse.get("manifest", {}))
    manifest_analyse = analyse.get("manifest", {})
    contenu = {
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
            # Le relevé reste **brut** : le rattachement aux pièces se refait à chaque recalcul (E3).
            "releve_brut": {
                "elements": copy.deepcopy(releve_brut.get("elements", [])),
                "catalogue": copy.deepcopy(releve_brut.get("catalogue", [])),
                "observations": copy.deepcopy(releve_brut.get("observations", [])),
            },
            "catalogue": copy.deepcopy(bibliotheque.get("composants", [])),
            "synthese_pieces": copy.deepcopy(bibliotheque.get("pieces", [])),
            "fiches_locaux": copy.deepcopy(bibliotheque.get("fiches_locaux", [])),
            "raccords": copy.deepcopy(bibliotheque.get("raccords", [])),
            "controle": {key: copy.deepcopy(value) for key, value in controle.items() if key != "cellules"},
            "demandes": copy.deepcopy(bibliotheque.get("demandes", [])),
        },
        "calage": {
            "contours_cales": True,
            "appliques": sum(1 for ligne in rapport_calage if ligne.get("applique")),
            "refuses": sum(1 for ligne in rapport_calage if not ligne.get("applique")),
            "locaux_deplaces": rapport_calage,
        },
        "couverture": geo.controler_couverture(
            {local["id"]: local["contour"] for local in locaux}, manifeste, releve_brut
        ),
    }
    # Import différé : l'édition s'appuie sur ce module. Le fichier livré passe par la même chaîne de
    # recalcul que chaque geste d'édition — c'est la garantie qu'il est cohérent avec ses contours calés.
    from app.services import thermique_etude_edition as edition

    return edition.reconstruire(contenu)


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
    version = payload.get("format_version")
    if payload.get("format") != ETUDE_FORMAT or version not in ETUDE_VERSIONS_LUES:
        lues = ", ".join(str(numero) for numero in ETUDE_VERSIONS_LUES)
        raise ThermiqueError(
            f"Format d'étude inconnu ou version non prise en charge (reçue : {version!r}, attendues : {lues})."
        )
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

    enveloppe_etude = payload.get("enveloppe")
    if not isinstance(enveloppe_etude, dict) or not isinstance(enveloppe_etude.get("manifeste"), dict):
        raise ThermiqueError("Le manifeste de l'enveloppe est absent de l'étude.")
    brut = enveloppe_etude.get("releve_brut")
    if not isinstance(brut, dict) or not isinstance(brut.get("elements"), list):
        raise ThermiqueError("Le relevé brut de l'enveloppe est absent : l'étude ne serait pas modifiable.")
    if not isinstance(payload.get("analyse"), dict) or not isinstance(payload["analyse"].get("objects"), list):
        raise ThermiqueError("L'analyse du plan est absente de l'étude.")
    # Une étude v3 arrive calée et relue : sans son rapport de cohérence, on ne saurait pas ce qu'elle vaut.
    # Une v2 est acceptée telle quelle : le premier recalcul lui donnera son rapport.
    if version >= 3 and (
        not isinstance(payload.get("coherence"), dict) or not isinstance(payload["coherence"].get("controles"), list)
    ):
        raise ThermiqueError("Le contrôle de cohérence est absent de l'étude : réassemblez-la avec la chaîne à jour.")

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
    # Le nord est une donnée de la planche, pas du fichier : s'il est déjà posé, l'étude en hérite (D85).
    contenu["nord_deg"] = thermique_nord.azimut_dans_l_image(
        thermique_nord.charger(sheet), raster_manifest["transform"]
    )
    convertir_contours(contenu, raster_manifest["transform"], width, height)
    return contenu


def convertir_contours(contenu: dict[str, Any], transform: list[Any], width: float, height: float) -> None:
    """Ajoute à chaque local son contour durable en points PDF, et contrôle ses limites (D59).

    Appelé à l'import comme après chaque enregistrement : les points PDF restent la géométrie de travail.
    """
    for local in contenu.get("locaux", []):
        local_id = local.get("id")
        contour = local.get("contour")
        if not isinstance(contour, list) or len(contour) < 3:
            raise ThermiqueError(f"Le contour du local « {local_id} » doit avoir au moins trois points.")
        limites = local.get("limites")
        if not isinstance(limites, list) or len(limites) != len(contour):
            raise ThermiqueError(f"Les limites du local « {local_id} » ne suivent pas son contour.")
        if any(limite not in geo.LIMITES for limite in limites):
            raise ThermiqueError(f"Une limite du local « {local_id} » est d'un type inconnu.")
        contour_pdf = []
        for point in contour:
            if not isinstance(point, list) or len(point) != 2:
                raise ThermiqueError(f"Un point du local « {local_id} » est invalide.")
            x, y = (_nombre(value, "Une coordonnée") for value in point)
            if not 0 <= x <= 1000 or not 0 <= y <= 1000:
                raise ThermiqueError(f"Le contour du local « {local_id} » sort de la feuille.")
            contour_pdf.append(_inverser_transform(transform, x * width / 1000, y * height / 1000))
        local["contour_pdf"] = contour_pdf
        # Le tracé de chaque côté suit les contours en points PDF : c'est lui qui porte la cote (D80).
        for cote in (local.get("fiche") or {}).get("cotes", []):
            trace = cote.get("trace")
            if isinstance(trace, list) and trace:
                cote["trace_pdf"] = [
                    _inverser_transform(transform, float(x) * width / 1000, float(y) * height / 1000)
                    for x, y in trace
                ]
    couverture = contenu.get("couverture")
    if isinstance(couverture, dict):
        # Les zones à combler sont dessinées sur le plan : elles passent aussi en points PDF.
        couverture["zones_non_affectees_pdf"] = [
            [_inverser_transform(transform, x * width / 1000, y * height / 1000) for x, y in zone]
            for zone in couverture.get("zones_non_affectees", [])
        ]
    enveloppe_etude = contenu.get("enveloppe")
    if isinstance(enveloppe_etude, dict):
        # Tracé des éléments (D75) et position des liaisons (D74) : dessinés sur le plan, donc en points PDF.
        for objet in enveloppe_etude.get("objets", []):
            objet["points_pdf"] = [
                _inverser_transform(transform, x * width / 1000, y * height / 1000)
                for x, y in objet.get("points", [])
            ]
        for liaison in enveloppe_etude.get("liaisons", []):
            point = liaison.get("point")
            if isinstance(point, list) and len(point) == 2:
                liaison["point_pdf"] = _inverser_transform(
                    transform, float(point[0]) * width / 1000, float(point[1]) * height / 1000
                )


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
    # On enregistre la version réellement importée, pas la plus récente que le serveur sait lire.
    version_lue = int(contenu.get("format_version") or ETUDE_FORMAT_VERSION)
    if etude is None:
        etude = ThermiqueEtude(
            project_id=sheet.project_id,
            sheet_id=sheet.id,
            format_version=version_lue,
            content_json=contenu_json,
            local_states_json=etats_json,
            imported_by_user_id=user.id,
        )
        db.add(etude)
        db.flush()
        numero = 1
        motif = MOTIF_IMPORT_INITIAL
    else:
        numero = int(
            db.scalar(
                select(func.max(ThermiqueEtudeVersion.version_number)).where(
                    ThermiqueEtudeVersion.etude_id == etude.id
                )
            )
            or 0
        ) + 1
        motif = MOTIF_IMPORT_REMPLACEMENT
        etude.format_version = version_lue
        etude.content_json = contenu_json
        etude.local_states_json = etats_json
        etude.imported_by_user_id = user.id
    db.add(
        ThermiqueEtudeVersion(
            etude_id=etude.id,
            version_number=numero,
            reason=motif,
            content_json=contenu_json,
            pieces_json=json.dumps(etat_editable(contenu), ensure_ascii=False, separators=(",", ":")),
            local_states_json=etats_json,
            created_by_user_id=user.id,
        )
    )
    db.commit()
    db.refresh(etude)
    return etude


def etat_editable(contenu: dict[str, Any]) -> list[dict[str, Any]]:
    """Ce que le thermicien peut changer : les objets « pièce » de l'analyse (D64).

    Tout le reste — rattachement, raccords, synthèse, fiches, couverture — se recalcule à l'identique
    depuis ces objets et le relevé brut ; une version n'a donc pas à en garder de copie. Sur le R+1 cela
    ramène une version de 351 Ko à 19 Ko.
    """
    return copy.deepcopy(
        [objet for objet in contenu.get("analyse", {}).get("objects", []) if objet.get("category") == "piece"]
    )


def poser_etat_editable(contenu: dict[str, Any], pieces: list[dict[str, Any]]) -> dict[str, Any]:
    """Remet les pièces d'une version dans le contenu ; l'appelant reconstruit ensuite le reste."""
    resultat = copy.deepcopy(contenu)
    autres = [objet for objet in resultat["analyse"]["objects"] if objet.get("category") != "piece"]
    resultat["analyse"]["objects"] = autres + copy.deepcopy(pieces)
    return resultat


def prochaine_version(db: Session, etude: ThermiqueEtude) -> int:
    dernier = db.scalar(
        select(func.max(ThermiqueEtudeVersion.version_number)).where(ThermiqueEtudeVersion.etude_id == etude.id)
    )
    return int(dernier or 0) + 1


def enregistrer_etude(
    db: Session,
    etude: ThermiqueEtude,
    user: User,
    contenu: dict[str, Any],
    etats: dict[str, Any],
    motif: str,
) -> ThermiqueEtude:
    """Écrit l'état courant et crée une version qui ne garde que ce qui est modifiable (D63, D64)."""
    etude.content_json = json.dumps(contenu, ensure_ascii=False, separators=(",", ":"))
    etude.local_states_json = json.dumps(etats, ensure_ascii=False, separators=(",", ":"))
    db.add(
        ThermiqueEtudeVersion(
            etude_id=etude.id,
            version_number=prochaine_version(db, etude),
            reason=motif,
            content_json=None,
            pieces_json=json.dumps(etat_editable(contenu), ensure_ascii=False, separators=(",", ":")),
            local_states_json=etude.local_states_json,
            created_by_user_id=user.id,
        )
    )
    db.commit()
    db.refresh(etude)
    return etude


def lister_versions(db: Session, etude: ThermiqueEtude) -> list[dict[str, Any]]:
    lignes = db.scalars(
        select(ThermiqueEtudeVersion)
        .where(ThermiqueEtudeVersion.etude_id == etude.id)
        .order_by(ThermiqueEtudeVersion.version_number.desc())
    ).all()
    return [
        {
            "version_number": ligne.version_number,
            "reason": ligne.reason,
            "created_by_user_id": ligne.created_by_user_id,
            "created_at": ligne.created_at,
        }
        for ligne in lignes
    ]


def base_de_version(db: Session, etude: ThermiqueEtude, numero: int) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Contenu complet du dernier import à ou avant `numero`, plus les pièces et états de `numero`."""
    cible = db.scalar(
        select(ThermiqueEtudeVersion).where(
            ThermiqueEtudeVersion.etude_id == etude.id, ThermiqueEtudeVersion.version_number == numero
        )
    )
    if cible is None:
        raise ThermiqueError("Cette version n'existe pas.")
    socle = db.scalars(
        select(ThermiqueEtudeVersion)
        .where(
            ThermiqueEtudeVersion.etude_id == etude.id,
            ThermiqueEtudeVersion.version_number <= numero,
            ThermiqueEtudeVersion.content_json.is_not(None),
        )
        .order_by(ThermiqueEtudeVersion.version_number.desc())
        .limit(1)
    ).first()
    if socle is None:
        raise ThermiqueError("L'import d'origine de cette version est introuvable.")
    pieces = json.loads(cible.pieces_json) if cible.pieces_json else []
    return json.loads(socle.content_json), pieces, json.loads(cible.local_states_json)


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
