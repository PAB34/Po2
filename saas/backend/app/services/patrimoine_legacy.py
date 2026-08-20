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
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.city import City
from app.models.local import Local
from app.models.patrimoine_legacy import (
    ORIGIN_AUTO,
    ORIGIN_MANUAL,
    STATUS_IGNORED,
    STATUS_LINKED,
    STATUS_PROPOSED,
    TARGET_BUILDING,
    TARGET_LOCAL,
    STATUS_OUT_OF_SCOPE,
    STATUS_TO_CREATE,
    STATUS_TODO,
    PatrimoineLegacyAsset,
    PatrimoineLegacyImport,
)
from app.services.building_naming import reverse_geocode_point
from app.services.cvc import _site_similarity

# --- Périmètre par défaut ----------------------------------------------------
# Décision utilisateur (2026-08-19) : importer **tous les bâtiments de la feuille
# `BAT`**, c'est-à-dire les genres `BATI` et `SITE`, y compris les biens sortis du
# parc — ils font partie du référentiel à traiter et sont simplement signalés.
# Le filtre reste paramétrable (`genres`, `include_out_of_park`).
DEFAULT_GENRES = ("BATI", "SITE")
DEFAULT_INCLUDE_OUT_OF_PARK = True
# 'O' = sorti du parc. Le fichier historique conserve les biens désaffectés.
EXCLUDED_HORSPARC = "O"

# Q4 : les biens hors Sète ne sont pas traités. On n'écarte QUE ceux dont la commune
# est explicitement autre : 41 bâtiments sétois n'ont aucune commune renseignée et
# seraient perdus par une lecture littérale de la règle.
SETE_INSEE = "34301"
SETE_NAMES = {"sete", "cette"}

# Colonnes ASTECH lues (orthographe de `Feuil1`, gabarit retenu).
# Clé pivot ASTECH. `CODBAR` est un repli : sur la feuille `BAT`, la colonne
# `CODEBIEN` est vide alors que `CODBAR` porte le même code (vérifié : 863/866
# lignes identiques sur l'export réel).
_KEY_COLUMNS = ("CODE_BIEN", "CODEBIEN", "CODBAR")
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

# Provenance de l'adresse resolue, pour la feuille de tracabilite du reexport.
RESOLVED_FROM_BUILDING = "building"
RESOLVED_FROM_REVERSE = "ign_reverse"


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
        key_indexes = [upper_headers.index(key) for key in _KEY_COLUMNS if key in upper_headers]
        if not key_indexes:
            continue
        rows = [
            row
            for row in worksheet.iter_rows(min_row=header_row + 1, values_only=True)
            if any(cell is not None and str(cell).strip() for cell in row)
        ]

        def _filled(index: int) -> int:
            return sum(1 for row in rows if index < len(row) and _text(row[index]) is not None)

        # On retient la colonne clé réellement **renseignée**, pas la première trouvée :
        # sur la feuille `BAT`, `CODEBIEN` est vide alors que `CODBAR` porte le code.
        key_index = max(key_indexes, key=_filled)
        filled_keys = _filled(key_index)
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
    include_out_of_park: bool = DEFAULT_INCLUDE_OUT_OF_PARK,
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

    # Auto-reparation : supprimer le patrimoine Po2 met `building_id` a NULL en cascade
    # (ON DELETE SET NULL). Les biens restaient alors affiches « rattache » ou
    # « a confirmer » alors qu'ils ne pointaient plus vers rien, et disparaissaient de
    # la carte. On les remet a traiter pour qu'ils soient reproposes.
    orphan_statement = select(PatrimoineLegacyAsset).where(
        PatrimoineLegacyAsset.building_id.is_(None),
        PatrimoineLegacyAsset.status.in_([STATUS_LINKED, STATUS_PROPOSED]),
    )
    if city_id is not None:
        orphan_statement = orphan_statement.where(PatrimoineLegacyAsset.city_id == city_id)
    repaired = 0
    for asset in db.scalars(orphan_statement):
        asset.status = STATUS_TODO
        asset.local_id = None
        asset.target_type = TARGET_BUILDING
        asset.link_origin = None
        _clear_resolved_address(asset)
        db.add(asset)
        repaired += 1
    # Candidats perimes : `candidate_building_id` n'a PAS de cle etrangere, il survit
    # donc a une purge du patrimoine. Constate en prod le 2026-08-20 : le referentiel
    # Po2 avait ete reimporte, les batiments avaient de nouveaux identifiants, et les
    # 294 candidats proposes pointaient tous vers des batiments disparus. « Valider ce
    # rattachement » echouait alors sur la contrainte d'integrite.
    known_ids = {target[0] for target in targets}
    stale_statement = select(PatrimoineLegacyAsset).where(
        PatrimoineLegacyAsset.candidate_building_id.is_not(None)
    )
    if city_id is not None:
        stale_statement = stale_statement.where(PatrimoineLegacyAsset.city_id == city_id)
    stale = 0
    for asset in db.scalars(stale_statement):
        if asset.candidate_building_id in known_ids:
            continue
        asset.candidate_building_id = None
        asset.candidate_label = None
        asset.candidate_score = None
        asset.candidate_reason = None
        db.add(asset)
        stale += 1
    if repaired or stale:
        db.commit()

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
        asset.target_type = TARGET_BUILDING
        # Le moteur PROPOSE, il ne valide pas : la confirmation reste humaine.
        asset.status = STATUS_PROPOSED
        asset.link_origin = ORIGIN_AUTO
        # Le rattachement manuel fait hériter l'adresse, le nom et le cadastre du
        # bâtiment ; le rattachement automatique doit en faire autant. Sans cela les
        # biens proposés par le moteur restent sans aucun champ résolu, et le réexport
        # ASTECH n'a rien à écrire pour eux — même une fois confirmés.
        _refresh_inherited_address(db, asset)
        db.add(asset)
        linked += 1

    db.commit()
    return {"scanned": scanned, "proposed": proposed, "auto_linked": linked, "repaired": repaired}


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
    local_id: int | None = None,
    designation: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    notes: str | None = None,
    clear_building: bool = False,
) -> PatrimoineLegacyAsset:
    """Décision utilisateur. Le `code_bien` n'est jamais modifiable : c'est la clé de
    mise à jour d'ASTECH.

    Deux enrichissements automatiques, pour éviter une saisie manuelle :
    - rattachement à un bâtiment Po2 → le bien **hérite de son adresse et de sa position** ;
    - point déplacé sans rattachement → l'adresse est **résolue par géocodage inverse**.
    Dans les deux cas l'adresse d'origine (`source_*`) reste intacte.
    """
    if clear_building:
        asset.building_id = None
        asset.local_id = None
        asset.target_type = TARGET_BUILDING
        asset.link_origin = None
        _clear_resolved_address(asset)
    elif local_id is not None:
        # Cible « local » : le bâtiment porteur reste renseigné, c'est lui qui porte
        # l'adresse, le cadastre et la position — un local n'a rien de tout cela.
        local = db.get(Local, local_id)
        if local is None:
            raise ValueError("Local introuvable.")
        asset.local_id = local_id
        asset.building_id = local.building_id
        asset.target_type = TARGET_LOCAL
        asset.status = STATUS_LINKED
        asset.link_origin = ORIGIN_MANUAL
        building = db.get(Building, local.building_id)
        if building is not None:
            _inherit_building_address(asset, building)
            # Le local peut porter SA propre adresse : le fichier d'inventaire en
            # fournit une par ligne, et l'entrée d'un local diffère parfois de celle
            # du bâtiment. Elle prime alors sur celle du bâtiment porteur.
            _override_with_local_address(asset, local)
            latitude_source = local.latitude if local.latitude is not None else building.latitude
            longitude_source = local.longitude if local.longitude is not None else building.longitude
            if latitude_source is not None and longitude_source is not None:
                asset.latitude = latitude_source
                asset.longitude = longitude_source
                latitude = longitude = None
    elif building_id is not None:
        building = db.get(Building, building_id)
        # Le batiment vise peut avoir disparu : `candidate_building_id` n'a pas de cle
        # etrangere et survit donc a une purge du patrimoine. Constate en prod le
        # 2026-08-20 : le referentiel Po2 avait ete reimporte, les batiments avaient
        # de nouveaux identifiants, et les 294 candidats pointaient tous dans le vide.
        # Sans ce controle, la contrainte d'integrite renvoyait une 500 opaque et le
        # bouton « Valider ce rattachement » semblait ne rien faire.
        if building is None:
            raise ValueError(
                "Ce bâtiment Po2 n'existe plus — le patrimoine a été réimporté depuis. "
                "Relance « 2. Reconnaître les noms » pour recalculer les candidats."
            )
        asset.building_id = building_id
        asset.local_id = None
        asset.target_type = TARGET_BUILDING
        asset.status = STATUS_LINKED
        asset.link_origin = ORIGIN_MANUAL
        if building is not None:
            _adopt_target_name(asset, building.nom_batiment, designation)
            _inherit_building_address(asset, building)
            # Le point ASTECH rejoint le bâtiment : c'est le geste « je dépose le
            # point sur le bâtiment Po2 », il ne doit pas rester à côté.
            if building.latitude is not None and building.longitude is not None:
                asset.latitude = building.latitude
                asset.longitude = building.longitude
                latitude = longitude = None
    if status is not None:
        asset.status = status
    if latitude is not None:
        asset.latitude = latitude
    if longitude is not None:
        asset.longitude = longitude
    moved = (latitude is not None or longitude is not None) and asset.latitude is not None and asset.longitude is not None
    if moved and asset.building_id is None:
        _resolve_address_from_point(asset)
    elif moved:
        # Bien rattaché : le point ASTECH et le bâtiment Po2 ne font plus qu'un.
        # Déplacer ce point unique déplace donc AUSSI le bâtiment Po2, et l'adresse
        # est recalculée pour les deux — c'est le sens du geste demandé.
        _resolve_address_from_point(asset)
        linked = db.get(Building, asset.building_id)
        if linked is not None:
            linked.latitude = asset.latitude
            linked.longitude = asset.longitude
            if asset.resolved_label:
                linked.adresse_reconstituee = asset.resolved_label[:255]
            if asset.resolved_city:
                linked.nom_commune = asset.resolved_city[:255]
            if asset.resolved_postcode:
                linked.code_postal = asset.resolved_postcode[:10]
            db.add(linked)
    if designation is not None:
        # Le nom affiché vient de `nomcourt` sinon de `designation` : on écrit les deux,
        # sinon corriger le libellé ne changerait rien à l'écran. C'est aussi ce qui
        # repartira dans ASTECH — le `code_bien`, lui, reste intouchable.
        cleaned = designation.strip()[:255] or None
        asset.designation = cleaned
        asset.nomcourt = cleaned
    if notes is not None:
        asset.notes = notes.strip() or None
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _adopt_target_name(
    asset: PatrimoineLegacyAsset, target_name: str | None, explicit_designation: str | None
) -> None:
    """Le bien ASTECH prend le nom de la cible Po2 à laquelle on vient de le rattacher.

    C'est la décision Q11, appliquée jusqu'au bout : le nom Po2/IGN gagne et sera
    réécrit dans ASTECH. Le rattachement fait converger les deux référentiels — c'est
    l'objet même du chantier. Le `code_bien` reste la clé, donc renommer ne casse rien
    au cycle suivant.

    Deux garde-fous :
    - une **modification manuelle** passée dans le même appel gagne : l'utilisateur qui
      corrige un nom n'a pas à se le faire écraser par le rattachement ;
    - une cible sans nom ne vide pas le libellé ASTECH, mieux vaut l'ancien que rien.
    """
    if explicit_designation is not None:
        return
    cleaned = (target_name or "").strip()[:255]
    if not cleaned:
        return
    asset.designation = cleaned
    asset.nomcourt = cleaned


def _clear_resolved_address(asset: PatrimoineLegacyAsset) -> None:
    asset.resolved_housenumber = None
    asset.resolved_street = None
    asset.resolved_postcode = None
    asset.resolved_city = None
    asset.resolved_citycode = None
    asset.resolved_label = None
    asset.resolved_source = None
    asset.resolved_name = None
    asset.resolved_section = None
    asset.resolved_numero_plan = None
    asset.resolved_refcad = None


_ADDRESS_PATTERN = re.compile(r"^\s*(\d+\s*[A-Za-z]?)\s+(.+?)\s*$")
# INSEE(5) + prefixe(3) + section(2) + numero de plan(4) : '34301000AK0149'.
_REFERENCE_NORM_PATTERN = re.compile(r"^(\d{5})(\d{3})([0-9A-Z]{2})(\d{4})$")


def _split_reconstituted_address(address: str | None) -> tuple[str | None, str | None]:
    """Sépare '208 AV DU MARECHAL JUIN' en ('208', 'AV DU MARECHAL JUIN').

    Les bâtiments Po2 ne stockent PAS l'adresse découpée (vérifié en prod : les colonnes
    numero_voirie / nom_voie sont vides sur toutes les lignes). Le découpage est donc
    reconstitué ici — le format est régulier — pour pouvoir alimenter NORUE et LIBELVOIE.
    """
    if not address:
        return None, None
    match = _ADDRESS_PATTERN.match(address)
    if match is None:
        return None, _text(address)
    return _text(match.group(1).replace(" ", "")), _text(match.group(2))


def _split_cadastral_reference(reference: str | None) -> tuple[str | None, str | None, str | None]:
    """Extrait (section, numéro de plan, REFCAD) de '34301000AK0149'.

    Le REFCAD attendu par ASTECH fait 5 caractères : section (2) + plan sur 3 chiffres
    (constaté : 'AS023'). Au-delà de 999, la valeur ne rentre pas dans ce format : on ne
    produit alors PAS de REFCAD plutôt que d'écrire une référence tronquée dans le
    référentiel de la collectivité. Section et plan restent disponibles séparément.
    """
    normalized = _text(reference)
    if not normalized:
        return None, None, None
    match = _REFERENCE_NORM_PATTERN.match(normalized.upper())
    if match is None:
        return None, None, None
    section = match.group(3)
    plan = match.group(4)
    plan_number = plan.lstrip("0") or "0"
    refcad = f"{section}{plan_number.zfill(3)}" if len(plan_number) <= 3 else None
    return section, plan, refcad


def _inherit_building_address(asset: PatrimoineLegacyAsset, building: Building) -> None:
    """Le bien reprend **tout** ce que Po2 sait du bâtiment : nom, adresse, cadastre.

    Les champs structurés du bâtiment étant vides en base, on reconstitue le découpage
    depuis `adresse_reconstituee` et `dgfip_reference_norm`, qui eux sont renseignés.
    """
    street = " ".join(part for part in [building.nature_voie, building.nom_voie] if part) or None
    housenumber = building.numero_voirie or None
    if not housenumber or not street:
        parsed_number, parsed_street = _split_reconstituted_address(building.adresse_reconstituee)
        housenumber = housenumber or parsed_number
        street = street or parsed_street

    section, numero_plan, refcad = _split_cadastral_reference(building.dgfip_reference_norm)
    if not section:
        section, numero_plan = building.section or None, building.numero_plan or None
        if section and numero_plan:
            plan_number = numero_plan.lstrip("0") or "0"
            refcad = f"{section}{plan_number.zfill(3)}" if len(plan_number) <= 3 else None

    asset.resolved_name = building.nom_batiment or None
    asset.resolved_housenumber = housenumber
    asset.resolved_street = street
    asset.resolved_postcode = building.code_postal or None
    asset.resolved_city = building.nom_commune or None
    asset.resolved_citycode = (building.dgfip_reference_norm or "")[:5] or None
    asset.resolved_label = building.adresse_reconstituee or (
        " ".join(part for part in [housenumber, street, building.nom_commune] if part) or None
    )
    asset.resolved_section = section
    asset.resolved_numero_plan = numero_plan
    asset.resolved_refcad = refcad
    asset.resolved_source = RESOLVED_FROM_BUILDING


def _override_with_local_address(asset: PatrimoineLegacyAsset, local: Local) -> None:
    """Remplace l'héritage par l'adresse propre du local, quand elle existe.

    Champ par champ : un local peut n'avoir qu'une partie de l'information, et il ne
    faut pas effacer ce que le bâtiment fournissait déjà.
    """
    if local.adresse_reconstituee:
        housenumber, street = _split_reconstituted_address(local.adresse_reconstituee)
        asset.resolved_label = local.adresse_reconstituee[:255]
        if housenumber:
            asset.resolved_housenumber = housenumber
        if street:
            asset.resolved_street = street
    if local.code_postal:
        asset.resolved_postcode = local.code_postal
    if local.nom_commune:
        asset.resolved_city = local.nom_commune
    if local.dgfip_reference_norm:
        section, numero_plan, refcad = _split_cadastral_reference(local.dgfip_reference_norm)
        if section:
            asset.resolved_section = section
            asset.resolved_numero_plan = numero_plan
            asset.resolved_refcad = refcad
            asset.resolved_citycode = local.dgfip_reference_norm[:5]
    if local.nom_local:
        asset.resolved_name = local.nom_local[:255]


def _refresh_inherited_address(db: Session, asset: PatrimoineLegacyAsset) -> None:
    """Réaligne les champs résolus du bien sur son bâtiment porteur.

    Sûr à rejouer : quand `resolved_source` vaut `building`, les champs résolus ne sont
    qu'une **copie** du bâtiment, donc les rafraîchir ne peut rien perdre. On préserve
    en revanche `ign_reverse`, qui est le résultat d'un point posé à la main.

    Nécessaire parce que le bâtiment porteur bouge : renommé, réadressé, réattaché à
    l'IGN. Constaté en prod le 2026-08-19 — deux biens portaient encore le nom
    « École Élémentaire Anatole France » hérité d'un bâtiment renommé depuis, et c'est
    ce nom périmé qui serait reparti dans ASTECH au réexport.
    """
    if asset.building_id is None:
        return
    if asset.resolved_source == RESOLVED_FROM_REVERSE:
        return
    building = db.get(Building, asset.building_id)
    if building is None:
        return
    _inherit_building_address(asset, building)
    if asset.local_id is not None:
        local = db.get(Local, asset.local_id)
        if local is not None:
            _override_with_local_address(asset, local)


def _resolve_address_from_point(asset: PatrimoineLegacyAsset) -> None:
    """Géocodage inverse du point posé. Best effort : jamais bloquant."""
    try:
        found = reverse_geocode_point(asset.latitude, asset.longitude)
    except Exception:
        return
    if not found.get("found"):
        return
    asset.resolved_housenumber = (found.get("housenumber") or None)
    asset.resolved_street = (found.get("street") or None)
    asset.resolved_postcode = (found.get("postcode") or None)
    asset.resolved_city = (found.get("city") or None)
    asset.resolved_citycode = (found.get("citycode") or None)
    asset.resolved_label = (found.get("label") or None)
    asset.resolved_source = RESOLVED_FROM_REVERSE


def resolve_city_id(db: Session, city_id: int | None) -> int | None:
    if city_id is not None:
        return city_id
    return db.scalar(select(City.id).order_by(City.id.asc()).limit(1))


# Préfixe des biens créés depuis Po2 : ils n'ont pas encore de code ASTECH, c'est le
# logiciel de la collectivité qui l'attribuera au réimport (décision Q13, « lignes à
# créer »). Le réexport devra donc émettre ces lignes avec un CODE_BIEN vide.
NEW_ASSET_CODE_PREFIX = "NOUVEAU_"


def create_asset_from_building(
    db: Session, city_id: int | None, building: Building
) -> PatrimoineLegacyAsset:
    """Ajoute un bâtiment Po2 à la liste ASTECH comme bien **à créer**.

    Cas visé : un bâtiment connu de Po2 mais absent du référentiel de la collectivité.
    Il doit remonter dans le réexport pour y être créé, sinon les deux référentiels ne
    convergeront jamais.

    Idempotent : rappeler la fonction pour le même bâtiment renvoie le bien existant.
    """
    existing = db.scalar(
        select(PatrimoineLegacyAsset).where(
            PatrimoineLegacyAsset.city_id == city_id,
            PatrimoineLegacyAsset.building_id == building.id,
        )
    )
    if existing is not None:
        return existing

    asset = PatrimoineLegacyAsset(
        city_id=city_id,
        code_bien=f"{NEW_ASSET_CODE_PREFIX}{building.id}",
        designation=(building.nom_batiment or f"Bâtiment {building.id}")[:255],
        nomcourt=(building.nom_batiment or f"Bâtiment {building.id}")[:255],
        genre="BATI",
        horsparc="N",
        building_id=building.id,
        status=STATUS_TO_CREATE,
        link_origin=ORIGIN_MANUAL,
        latitude=building.latitude,
        longitude=building.longitude,
    )
    _inherit_building_address(asset, building)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_building_for_city(db: Session, city_id: int | None, building_id: int) -> Building | None:
    statement = select(Building).where(Building.id == building_id)
    if city_id is not None:
        statement = statement.where(Building.city_id == city_id)
    return db.scalar(statement)


def confirm_proposed(
    db: Session, city_id: int | None, asset_ids: list[int] | None = None
) -> dict[str, int]:
    """Valide les rattachements proposes par le moteur.

    Sans `asset_ids`, confirme tout ce qui est en attente : sur 78 propositions, les
    confirmer une par une n'apporterait rien une fois la liste relue.
    """
    statement = select(PatrimoineLegacyAsset).where(
        PatrimoineLegacyAsset.status == STATUS_PROPOSED
    )
    if city_id is not None:
        statement = statement.where(PatrimoineLegacyAsset.city_id == city_id)
    if asset_ids:
        statement = statement.where(PatrimoineLegacyAsset.id.in_(asset_ids))

    confirmed = 0
    for asset in db.scalars(statement):
        if asset.building_id is None:
            continue
        asset.status = STATUS_LINKED
        # Filet de sécurité : c'est le dernier passage avant que le bien ne devienne
        # exportable vers ASTECH. On réaligne l'adresse héritée sur le bâtiment tel
        # qu'il est AUJOURD'HUI, pour ne pas réinjecter un nom ou une adresse périmés.
        _refresh_inherited_address(db, asset)
        db.add(asset)
        confirmed += 1
    db.commit()
    return {"confirmed": confirmed}


# Type des locaux nes d'un bien ASTECH : trace leur origine dans le referentiel Po2,
# a cote de 'PRINCIPAL' (import DGFIP) et 'RECLASSEMENT' (reclassement manuel).
LOCAL_TYPE_FROM_ASTECH = "ASTECH"


def convert_asset_to_local(db: Session, asset: PatrimoineLegacyAsset) -> PatrimoineLegacyAsset:
    """Fait du bien ASTECH un **local** du bâtiment auquel il est rattaché.

    C'était le chaînon manquant : l'écran savait viser un local *déjà existant*, mais
    rien ne permettait d'en créer un. Mesuré en prod le 2026-08-20 : 0 bien sur 79
    rattaché au niveau local, alors que c'est le cas de figure normal dès que plusieurs
    biens ASTECH désignent un même bâtiment (le club et ses salles, l'école et son
    restaurant scolaire).

    Le bâtiment porteur **reste** renseigné : c'est lui qui porte l'adresse, le cadastre
    et la position, et donc ce que le bien renverra à ASTECH (décision Q1 du
    2026-08-20). Passer au niveau local précise la structure sans rien retirer.

    Idempotent : un bien déjà rattaché à un local est renvoyé tel quel.
    """
    if asset.building_id is None:
        raise ValueError(
            "Ce bien n'est rattaché à aucun bâtiment Po2 : rattache-le d'abord, "
            "le local sera créé dans ce bâtiment."
        )
    if asset.target_type == TARGET_LOCAL and asset.local_id is not None:
        return asset

    building = db.get(Building, asset.building_id)
    if building is None:
        raise ValueError("Le bâtiment porteur est introuvable.")

    name = (asset.nomcourt or asset.designation or asset.code_bien).strip()[:255]
    # Un local du meme nom existe deja dans ce batiment : on le reutilise plutot que
    # d'en creer un doublon. C'est le cas du TENNIS CLUB DU BARROU, dont le local
    # « SALLE TENNIS CLUB DU BARROU » etait deja en base.
    existing = db.scalar(
        select(Local).where(
            Local.building_id == building.id,
            func.lower(Local.nom_local) == name.lower(),
        )
    )
    local = existing
    if local is None:
        local = Local(
            building_id=building.id,
            nom_local=name,
            type_local=LOCAL_TYPE_FROM_ASTECH,
            # Le local herite de l'adresse et de la position du batiment : un local n'a
            # pas d'adresse propre tant que personne ne lui en donne une, et le laisser
            # vide ferait perdre au bien ce qu'il avait en visant le batiment.
            adresse_reconstituee=building.adresse_reconstituee,
            code_postal=building.code_postal,
            nom_commune=building.nom_commune,
            latitude=building.latitude,
            longitude=building.longitude,
            dgfip_reference_norm=building.dgfip_reference_norm,
        )
        db.add(local)
        db.flush()

    asset.local_id = local.id
    asset.target_type = TARGET_LOCAL
    asset.status = STATUS_LINKED
    asset.link_origin = ORIGIN_MANUAL
    _inherit_building_address(asset, building)
    _override_with_local_address(asset, local)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _drop_inherited_position(db: Session, asset: PatrimoineLegacyAsset) -> None:
    """Efface la position du bien si elle n'est qu'un **emprunt** au bâtiment porteur.

    Un bien ASTECH n'a pas de position à lui : le fichier de la collectivité n'en porte
    qu'une seule sur 444. Quand un bien s'affiche sur la carte, c'est soit parce qu'il
    est rattaché (il prend le point du bâtiment), soit parce qu'on l'a posé à la main.

    Détacher un bien devait donc lui rendre son absence de position. La version
    précédente faisait l'inverse : elle figeait le point du bâtiment dans le bien pour
    qu'il ne disparaisse pas de la carte. Résultat mesuré en prod le 2026-08-20 :
    **73 des 82 positions** étaient des faux points posés exactement sur d'anciens
    bâtiments, contre ~8 réellement placés à la main.

    On ne garde donc que ce qui a été **déplacé volontairement** : une position qui ne
    coïncide pas avec celle du bâtiment porteur.
    """
    if asset.latitude is None or asset.longitude is None or asset.building_id is None:
        return
    building = db.get(Building, asset.building_id)
    if building is None or building.latitude is None or building.longitude is None:
        return
    # ~1 m : en deçà, la position est celle du bâtiment, pas un choix de l'utilisateur.
    if (
        abs(building.latitude - asset.latitude) < 0.00001
        and abs(building.longitude - asset.longitude) < 0.00001
    ):
        asset.latitude = None
        asset.longitude = None


def reset_everything(db: Session, city_id: int | None) -> dict[str, int]:
    """Remise à zéro **totale** : l'écran revient à l'état juste après l'import.

    Plus fort que `reset_all_links` : on efface aussi les positions posées à la main et
    on annule les décisions « ignoré ». Aucun bien ASTECH ne reste alors sur la carte —
    c'est normal, ils n'ont pas de coordonnées propres — et « Reconnaître les noms » les
    y ramène en les rattachant.

    Ce qui **n'est pas** remis à zéro : `hors_perimetre`. Ce n'est pas une décision de
    l'utilisateur mais un constat de périmètre (bien hors Sète, décision Q4), recalculé
    à chaque import. L'annuler ferait remonter dans la file 27 biens qui n'ont rien à
    y faire.
    """
    statement = select(PatrimoineLegacyAsset).where(
        PatrimoineLegacyAsset.status != STATUS_OUT_OF_SCOPE
    )
    if city_id is not None:
        statement = statement.where(PatrimoineLegacyAsset.city_id == city_id)

    reset = 0
    for asset in db.scalars(statement):
        asset.building_id = None
        asset.local_id = None
        asset.target_type = TARGET_BUILDING
        asset.link_origin = None
        asset.latitude = None
        asset.longitude = None
        asset.candidate_building_id = None
        asset.candidate_label = None
        asset.candidate_score = None
        asset.candidate_reason = None
        asset.status = STATUS_TODO
        _clear_resolved_address(asset)
        db.add(asset)
        reset += 1
    db.commit()
    return {"reset": reset}


def delete_all_imports(db: Session, city_id: int | None) -> dict[str, int]:
    """Efface **tout** le référentiel ASTECH importé : les biens et les imports.

    Sert à repartir d'un export neuf. À distinguer de `reset_all_links`, qui ne coupe
    que les rapprochements et garde les biens.

    ⚠️ Destructif : tout le travail de rapprochement part avec les biens — statuts,
    cibles, points posés à la main. C'est à l'écran d'annoncer le compte exact avant
    de le faire.

    Ce qui **reste** délibérément, parce que ce sont désormais des données Po2 et non
    des données ASTECH :
    - les **bâtiments** créés depuis un bien ASTECH (« Créer le bâtiment Po2 ») ;
    - les **locaux** créés depuis un bien ASTECH (« En faire un local »).

    Les uns et les autres seront retrouvés par le moteur de reconnaissance au
    réimport, puisqu'ils portent le nom du bien. Les supprimer ferait perdre du
    patrimoine réel pour effacer un fichier source.
    """
    asset_statement = select(PatrimoineLegacyAsset)
    import_statement = select(PatrimoineLegacyImport)
    if city_id is not None:
        asset_statement = asset_statement.where(PatrimoineLegacyAsset.city_id == city_id)
        import_statement = import_statement.where(PatrimoineLegacyImport.city_id == city_id)

    assets_deleted = 0
    for asset in db.scalars(asset_statement):
        db.delete(asset)
        assets_deleted += 1
    imports_deleted = 0
    for import_row in db.scalars(import_statement):
        db.delete(import_row)
        imports_deleted += 1
    db.commit()
    return {"assets_deleted": assets_deleted, "imports_deleted": imports_deleted}


def reset_all_links(db: Session, city_id: int | None) -> dict[str, int]:
    """Supprime **tous** les rapprochements ASTECH ↔ Po2 et remet les biens à traiter.

    Sert à repartir d'une feuille blanche quand le référentiel Po2 a beaucoup bougé
    (renommages, réimport du patrimoine) : plutôt que de détacher 400 biens un par un,
    on efface et on relance « Reconnaître les noms ».

    Trois choix délibérés :

    - Les biens **`a_creer`** ne sont pas touchés : ils n'existent QUE parce qu'un
      bâtiment Po2 les a créés (décision Q13). Couper leur lien en ferait des lignes
      orphelines sans code ASTECH ni contrepartie.
    - Les décisions **`ignore`** et **`hors_perimetre`** sont conservées : ce ne sont
      pas des rapprochements mais des choix de périmètre, qu'une purge de liens n'a
      aucune raison d'annuler.
    - La **position de travail** (lat/lon) est conservée : c'est souvent un point posé
      à la main, et l'effacer ferait disparaître le bien de la carte — exactement le
      symptôme corrigé en #117.

    L'adresse résolue, elle, est effacée : elle n'était qu'une copie du bâtiment
    porteur, elle n'a plus de source une fois le lien coupé.
    """
    statement = select(PatrimoineLegacyAsset).where(
        PatrimoineLegacyAsset.status != STATUS_TO_CREATE,
        or_(
            PatrimoineLegacyAsset.building_id.is_not(None),
            PatrimoineLegacyAsset.local_id.is_not(None),
        ),
    )
    if city_id is not None:
        statement = statement.where(PatrimoineLegacyAsset.city_id == city_id)

    cleared = 0
    for asset in db.scalars(statement):
        _drop_inherited_position(db, asset)
        asset.building_id = None
        asset.local_id = None
        asset.target_type = TARGET_BUILDING
        asset.link_origin = None
        # Une decision de perimetre n'est pas un rapprochement : elle survit a la purge.
        if asset.status not in (STATUS_IGNORED, STATUS_OUT_OF_SCOPE):
            asset.status = STATUS_TODO
        _clear_resolved_address(asset)
        db.add(asset)
        cleared += 1
    db.commit()
    return {"cleared": cleared}


def list_locals_for_building(db: Session, building_id: int) -> list[Local]:
    return list(
        db.scalars(
            select(Local).where(Local.building_id == building_id).order_by(Local.nom_local.asc())
        )
    )
