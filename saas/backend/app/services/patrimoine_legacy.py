"""
Import et rapprochement du référentiel patrimoine historique (ASTECH).

Flux cible (aller-retour) : export ASTECH -> import Po2 -> rapprochement / attribution
IGN -> réexport réinjectable dans ASTECH. Ce module couvre l'**aller** : lecture du
classeur, filtrage du périmètre, persistance, et proposition de candidats.

Contraintes de réinjection (données par la collectivité, cf.
`docs/refonte-v1/patrimoine-fichier-historique-rapprochement-decisions.md` §13) :
- le `CODE_BIEN` ne doit jamais être modifié : c'est la clé de mise à jour d'ASTECH ;
- les en-têtes de colonnes ne doivent jamais être modifiés : ils sont donc conservés
  **tels quels** dans `PatrimoineLegacyImport.headers_json` et serviront de gabarit au
  réexport, plutôt que d'être réécrits depuis le code.

Le moteur de reconnaissance réutilise `_site_similarity` du module CVC, déjà en
production pour rapprocher les inventaires DALKIA/SPIE des bâtiments.
"""
from __future__ import annotations

import io
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

import openpyxl
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.city import City
from app.models.patrimoine_legacy import (
    ORIGIN_AUTO,
    ORIGIN_MANUAL,
    STATUS_LINKED,
    STATUS_OUT_OF_SCOPE,
    STATUS_TODO,
    PatrimoineLegacyAsset,
    PatrimoineLegacyImport,
)
from app.services.cvc import _site_similarity

# --- Périmètre par défaut ----------------------------------------------------
# Q2 (périmètre exact) est encore en attente de la référente ASTECH : le filtre est
# donc paramétrable, et non figé. Défaut = le bâti encore en service.
DEFAULT_GENRES = ("BATI",)
# 'O' = sorti du parc. Le fichier historique conserve les biens désaffectés.
EXCLUDED_HORSPARC = "O"

# Q4 : les biens hors Sète ne sont pas traités. On n'écarte QUE ceux dont la commune
# est explicitement autre : 41 bâtiments sétois n'ont aucune commune renseignée et
# seraient perdus par une lecture littérale de la règle.
SETE_INSEE = "34301"
SETE_NAMES = {"sete", "cette"}

# Colonnes ASTECH lues (orthographe de `Feuil1`, gabarit retenu).
_KEY_COLUMNS = ("CODE_BIEN", "CODEBIEN")
_COLUMN_MAP = {
    "designation": "DESIGNATION",
    "nomcourt": "NOMCOURT",
    "genre": "GENRE",
    "categ": "CATEG",
    "categ_des": "CATEG_DES",
    "souscat_des": "SOUSCAT_DES",
    "horsparc": "HORSPARC",
    "code_parent": "CODE_PARENT",
    "source_norue": "NORUE",
    "source_bister": "BISTER",
    "source_libelvoie": "LIBELVOIE",
    "source_codpost": "CODPOST",
    "source_ville": "VILLE",
    "source_commune": "COMMUNE",
    "source_refcad": "REFCAD",
}
# Longueurs déclarées sur le modèle : on tronque proprement plutôt que de laisser la
# base rejeter une ligne (le fichier historique contient des libellés très longs).
_MAX_LENGTHS = {
    "designation": 255, "nomcourt": 255, "genre": 20, "categ": 20, "categ_des": 120,
    "souscat_des": 120, "horsparc": 2, "code_parent": 40, "source_norue": 40,
    "source_bister": 40, "source_libelvoie": 255, "source_codpost": 10,
    "source_ville": 120, "source_commune": 10, "source_refcad": 40,
}

# Seuil de rattachement automatique (Q5 : on rattache les évidences, modifiables ensuite).
AUTO_LINK_SCORE = 0.90
# En dessous, aucun candidat n'est proposé : mieux vaut une case vide qu'une piste fausse.
CANDIDATE_MIN_SCORE = 0.50
# Écart minimal entre le 1er et le 2e candidat pour qu'un rattachement soit « évident ».
# Sans ce garde-fou, « TENNIS » se rattache seul à un bâtiment parmi plusieurs voisins.
AMBIGUITY_GAP = 0.05
# Au-dessus, le nom est identique au bâtiment cible : la présence d'un second candidat
# proche ne doit pas empêcher le rattachement. Mesuré sur le fichier réel : sans cette
# exception, « ECOLE ELEMENTAIRE PAUL BERT » -> « ECOLE ELEMENTAIRE PAUL BERT » (score 1,0)
# était bloqué à cause d'une école voisine au nom ressemblant.
EXACT_MATCH_SCORE = 0.98


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _normalize_ascii(value: Any) -> str:
    if not value:
        return ""
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value.lower()).strip()


# ---------------------------------------------------------------------------
# Lecture du classeur ASTECH
# ---------------------------------------------------------------------------

def _find_header_row(worksheet, max_scan: int = 6) -> tuple[int, list[str]] | None:
    """Localise la ligne d'en-têtes : `Feuil1` la place en ligne 2, `BAT` en ligne 1."""
    for row_index, row in enumerate(
        worksheet.iter_rows(min_row=1, max_row=max_scan, values_only=True), start=1
    ):
        values = [("" if cell is None else str(cell).strip()) for cell in row]
        upper = {v.upper() for v in values if v}
        if any(key in upper for key in _KEY_COLUMNS) and "DESIGNATION" in upper:
            return row_index, values
    return None


def parse_astech_workbook(raw_bytes: bytes) -> dict[str, Any]:
    """Retourne la feuille exploitable, ses en-têtes **à l'octet près**, et ses lignes.

    Le classeur contient plusieurs feuilles dont les en-têtes divergent (`Feuil1` :
    317 colonnes, clé `CODE_BIEN` renseignée ; `BAT` : 122 colonnes, clé `CODEBIEN`
    vidée). On retient la feuille dont la clé est **effectivement renseignée**, car
    c'est elle qui porte le gabarit natif ASTECH.
    """
    workbook = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    best: dict[str, Any] | None = None
    for worksheet in workbook.worksheets:
        found = _find_header_row(worksheet)
        if found is None:
            continue
        header_row, headers = found
        upper_headers = [h.upper() for h in headers]
        key_index = next(
            (upper_headers.index(key) for key in _KEY_COLUMNS if key in upper_headers), None
        )
        if key_index is None:
            continue
        rows = [
            row
            for row in worksheet.iter_rows(min_row=header_row + 1, values_only=True)
            if any(cell is not None and str(cell).strip() for cell in row)
        ]
        filled_keys = sum(
            1 for row in rows if key_index < len(row) and _text(row[key_index]) is not None
        )
        candidate = {
            "sheet_name": worksheet.title,
            "header_row": header_row,
            "headers": headers,
            "key_index": key_index,
            "key_header": headers[key_index],
            "rows": rows,
            "filled_keys": filled_keys,
        }
        if best is None or filled_keys > best["filled_keys"]:
            best = candidate
    if best is None:
        raise ValueError(
            "Aucune feuille exploitable : il faut une ligne d'en-têtes contenant "
            "CODE_BIEN (ou CODEBIEN) et DESIGNATION."
        )
    if best["filled_keys"] == 0:
        raise ValueError(
            f"La colonne « {best['key_header']} » est vide dans toutes les feuilles du "
            "classeur. Le code bien est la clé de rapprochement : redemander un export "
            "ASTECH avec cette colonne renseignée."
        )
    return best


# ---------------------------------------------------------------------------
# Périmètre
# ---------------------------------------------------------------------------

def _is_out_of_scope_commune(commune: str | None, ville: str | None) -> bool:
    """Vrai seulement si la commune est explicitement autre que Sète.

    Une commune absente n'est PAS hors périmètre : 41 bâtiments manifestement sétois
    (WC publics, restaurants scolaires…) n'ont aucune commune renseignée.
    """
    code = _text(commune)
    name = _normalize_ascii(ville)
    if code and code != SETE_INSEE:
        return True
    if not code and name and name not in SETE_NAMES:
        return True
    return False


def _row_in_scope(values: dict[str, Any], genres: tuple[str, ...], include_out_of_park: bool) -> bool:
    genre = (_text(values.get("genre")) or "").upper()
    if genres and genre not in genres:
        return False
    if not include_out_of_park and (_text(values.get("horsparc")) or "").upper() == EXCLUDED_HORSPARC:
        return False
    return True


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def _extract_values(row: tuple[Any, ...], header_index: dict[str, int]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field, column in _COLUMN_MAP.items():
        index = header_index.get(column)
        text = _text(row[index]) if index is not None and index < len(row) else None
        limit = _MAX_LENGTHS.get(field)
        if text is not None and limit is not None and len(text) > limit:
            text = text[:limit]
        values[field] = text
    return values


def import_astech_file(
    db: Session,
    *,
    city_id: int | None,
    filename: str,
    raw_bytes: bytes,
    genres: tuple[str, ...] = DEFAULT_GENRES,
    include_out_of_park: bool = False,
    batch: str | None = None,
) -> dict[str, Any]:
    """Charge un export ASTECH. **Idempotent** : rejouer le même fichier met à jour les
    biens existants (clé `CODE_BIEN`) sans dupliquer ni perdre les rattachements validés.
    """
    parsed = parse_astech_workbook(raw_bytes)
    headers: list[str] = parsed["headers"]
    header_index = {header.upper(): position for position, header in enumerate(headers) if header}
    key_index: int = parsed["key_index"]
    batch_name = batch or f"astech_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    created = updated = skipped_scope = skipped_out_of_city = skipped_no_key = 0

    for row in parsed["rows"]:
        code_bien = _text(row[key_index]) if key_index < len(row) else None
        if not code_bien:
            skipped_no_key += 1
            continue
        values = _extract_values(row, header_index)
        if not _row_in_scope(values, genres, include_out_of_park):
            skipped_scope += 1
            continue

        out_of_scope = _is_out_of_scope_commune(values.get("source_commune"), values.get("source_ville"))
        if out_of_scope:
            skipped_out_of_city += 1

        asset = db.scalar(
            select(PatrimoineLegacyAsset).where(
                PatrimoineLegacyAsset.city_id == city_id,
                PatrimoineLegacyAsset.code_bien == code_bien,
            )
        )
        is_new = asset is None
        if asset is None:
            asset = PatrimoineLegacyAsset(city_id=city_id, code_bien=code_bien, status=STATUS_TODO)

        for field, value in values.items():
            setattr(asset, field, value)
        asset.import_batch = batch_name
        asset.source_row_number = None
        # Payload complet : indispensable pour réémettre le fichier au format ASTECH.
        asset.source_payload_json = json.dumps(
            {
                header: ("" if position >= len(row) or row[position] is None else str(row[position]))
                for position, header in enumerate(headers)
                if header
            },
            ensure_ascii=False,
        )
        # Le statut d'un bien déjà traité n'est jamais rétrogradé par un réimport.
        if out_of_scope and asset.status == STATUS_TODO:
            asset.status = STATUS_OUT_OF_SCOPE
        elif not out_of_scope and asset.status == STATUS_OUT_OF_SCOPE:
            asset.status = STATUS_TODO

        db.add(asset)
        created += 1 if is_new else 0
        updated += 0 if is_new else 1

    import_row = db.scalar(
        select(PatrimoineLegacyImport).where(
            PatrimoineLegacyImport.city_id == city_id,
            PatrimoineLegacyImport.batch == batch_name,
        )
    )
    if import_row is None:
        import_row = PatrimoineLegacyImport(city_id=city_id, batch=batch_name)
    import_row.filename = filename[:255]
    import_row.sheet_name = str(parsed["sheet_name"])[:120]
    import_row.header_row = int(parsed["header_row"])
    # En-têtes conservés tels quels : gabarit obligatoire pour la réinjection ASTECH.
    import_row.headers_json = json.dumps(headers, ensure_ascii=False)
    import_row.total_rows = len(parsed["rows"])
    import_row.imported_rows = created + updated
    import_row.skipped_rows = skipped_scope + skipped_no_key
    db.add(import_row)
    db.commit()

    return {
        "batch": batch_name,
        "sheet_name": parsed["sheet_name"],
        "header_row": parsed["header_row"],
        "columns": len([h for h in headers if h]),
        "total_rows": len(parsed["rows"]),
        "created": created,
        "updated": updated,
        "skipped_scope": skipped_scope,
        "skipped_no_key": skipped_no_key,
        "out_of_scope_commune": skipped_out_of_city,
    }


# ---------------------------------------------------------------------------
# Reconnaissance des noms
# ---------------------------------------------------------------------------

def _load_building_targets(db: Session, city_id: int | None) -> list[tuple[int, str, str | None]]:
    """Bâtiments cibles. Q3 : la cible d'un rattachement est un `Building`, jamais un `Site`."""
    statement = select(Building.id, Building.nom_batiment, Building.adresse_reconstituee)
    if city_id is not None:
        statement = statement.where(Building.city_id == city_id)
    return [(row[0], row[1] or "", row[2]) for row in db.execute(statement) if row[1]]


def _address_bonus(asset: PatrimoineLegacyAsset, address: str | None) -> float:
    """Départage entre candidats de score voisin — jamais une moyenne pondérée.

    Mélanger nom et adresse dans un score unique dégrade le résultat (mesuré : 92 -> 60
    rapprochements sûrs), parce qu'une ligne sur cinq n'a pas de voie et que les adresses
    Po2 sont écrites autrement. L'adresse ne sert donc qu'à départager.
    """
    voie = _normalize_ascii(asset.source_libelvoie)
    if not voie or not address:
        return 0.0
    target = _normalize_ascii(address).lstrip("0123456789 ")
    if not target:
        return 0.0
    tokens = {token for token in voie.split() if len(token) > 2}
    if not tokens:
        return 0.0
    hits = sum(1 for token in tokens if token in target)
    return 0.02 * (hits / len(tokens))


def _best_candidate(
    asset: PatrimoineLegacyAsset, targets: list[tuple[int, str, str | None]]
) -> dict[str, Any]:
    scored: list[tuple[float, int, str]] = []
    for building_id, name, address in targets:
        score = max(
            _site_similarity(asset.nomcourt, name),
            _site_similarity(asset.designation, name),
        )
        if score <= 0:
            continue
        scored.append((min(1.0, score + _address_bonus(asset, address)), building_id, name))
    if not scored:
        return {"id": None, "label": None, "score": 0.0, "reason": None, "ambiguous": False}

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_id, best_label = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if best_score < CANDIDATE_MIN_SCORE:
        return {"id": None, "label": None, "score": round(best_score, 3), "reason": None, "ambiguous": False}
    # Deux bâtiments quasi équivalents : on propose, on ne tranche pas. Sauf si le nom
    # est identique à la cible — un second candidat proche ne rend pas l'exact douteux.
    ambiguous = best_score < EXACT_MATCH_SCORE and (best_score - runner_up) < AMBIGUITY_GAP
    return {
        "id": best_id,
        "label": best_label,
        "score": round(best_score, 3),
        "reason": (
            "plusieurs bâtiments proches"
            if ambiguous
            else "nom identique" if best_score >= 0.999 else "nom approchant"
        ),
        "ambiguous": ambiguous,
    }


def compute_candidates(
    db: Session, city_id: int | None, *, auto_link: bool = True
) -> dict[str, int]:
    """(Re)calcule les candidats des biens non traités, et rattache les évidences.

    Q5 : le rattachement automatique est validé, avec modification manuelle toujours
    possible ensuite. Un bien déjà rattaché à la main n'est jamais recalculé.
    """
    targets = _load_building_targets(db, city_id)
    statement = select(PatrimoineLegacyAsset).where(PatrimoineLegacyAsset.status == STATUS_TODO)
    if city_id is not None:
        statement = statement.where(PatrimoineLegacyAsset.city_id == city_id)

    scanned = proposed = 0
    eligible: list[tuple[PatrimoineLegacyAsset, dict[str, Any]]] = []
    for asset in db.scalars(statement):
        scanned += 1
        candidate = _best_candidate(asset, targets)
        asset.candidate_building_id = candidate["id"]
        asset.candidate_label = candidate["label"]
        asset.candidate_score = candidate["score"] or None
        asset.candidate_reason = candidate["reason"]
        if candidate["id"] is not None:
            proposed += 1
        if (
            auto_link
            and candidate["id"] is not None
            and candidate["score"] >= AUTO_LINK_SCORE
            and not candidate["ambiguous"]
        ):
            eligible.append((asset, candidate))
        db.add(asset)

    # Second garde-fou : si plusieurs biens revendiquent le même bâtiment, le
    # rattachement n'est plus une évidence (cas « PAUL LANGEVIN » : maternelle,
    # élémentaire et restaurant scolaire portent le même nom court). La relation
    # N codes bien -> 1 bâtiment reste permise, mais elle se valide à la main.
    claims: dict[int, int] = {}
    for _, candidate in eligible:
        claims[candidate["id"]] = claims.get(candidate["id"], 0) + 1

    linked = 0
    for asset, candidate in eligible:
        if claims.get(candidate["id"], 0) > 1:
            asset.candidate_reason = "plusieurs biens visent ce bâtiment"
            db.add(asset)
            continue
        asset.building_id = candidate["id"]
        asset.status = STATUS_LINKED
        asset.link_origin = ORIGIN_AUTO
        db.add(asset)
        linked += 1

    db.commit()
    return {"scanned": scanned, "proposed": proposed, "auto_linked": linked}


# ---------------------------------------------------------------------------
# Consultation et décision
# ---------------------------------------------------------------------------

def list_assets(
    db: Session,
    city_id: int | None,
    *,
    status: str | None = None,
    genre: str | None = None,
    search: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[PatrimoineLegacyAsset]:
    statement = select(PatrimoineLegacyAsset)
    if city_id is not None:
        statement = statement.where(PatrimoineLegacyAsset.city_id == city_id)
    if status:
        statement = statement.where(PatrimoineLegacyAsset.status == status)
    if genre:
        statement = statement.where(PatrimoineLegacyAsset.genre == genre)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            PatrimoineLegacyAsset.designation.ilike(pattern)
            | PatrimoineLegacyAsset.nomcourt.ilike(pattern)
            | PatrimoineLegacyAsset.code_bien.ilike(pattern)
        )
    statement = statement.order_by(
        PatrimoineLegacyAsset.candidate_score.desc().nullslast(),
        PatrimoineLegacyAsset.code_bien.asc(),
    ).limit(limit).offset(offset)
    return list(db.scalars(statement))


def counts_by_status(db: Session, city_id: int | None) -> dict[str, int]:
    statement = select(PatrimoineLegacyAsset.status, func.count(PatrimoineLegacyAsset.id))
    if city_id is not None:
        statement = statement.where(PatrimoineLegacyAsset.city_id == city_id)
    counts = {status: count for status, count in db.execute(statement.group_by(PatrimoineLegacyAsset.status))}
    counts["total"] = sum(counts.values())
    return counts


def get_asset_or_none(db: Session, city_id: int | None, asset_id: int) -> PatrimoineLegacyAsset | None:
    statement = select(PatrimoineLegacyAsset).where(PatrimoineLegacyAsset.id == asset_id)
    if city_id is not None:
        statement = statement.where(PatrimoineLegacyAsset.city_id == city_id)
    return db.scalar(statement)


def update_asset(
    db: Session,
    asset: PatrimoineLegacyAsset,
    *,
    status: str | None = None,
    building_id: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    notes: str | None = None,
    clear_building: bool = False,
) -> PatrimoineLegacyAsset:
    """Décision utilisateur. Le `code_bien` n'est jamais modifiable : c'est la clé de
    mise à jour d'ASTECH."""
    if clear_building:
        asset.building_id = None
        asset.link_origin = None
    elif building_id is not None:
        asset.building_id = building_id
        asset.status = STATUS_LINKED
        asset.link_origin = ORIGIN_MANUAL
    if status is not None:
        asset.status = status
    if latitude is not None:
        asset.latitude = latitude
    if longitude is not None:
        asset.longitude = longitude
    if notes is not None:
        asset.notes = notes.strip() or None
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def resolve_city_id(db: Session, city_id: int | None) -> int | None:
    if city_id is not None:
        return city_id
    return db.scalar(select(City.id).order_by(City.id.asc()).limit(1))
