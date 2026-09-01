"""Retour arrière sur l'écran de rapprochement ASTECH (décision Q46).

Le principe tient en une phrase : **on enregistre l'état d'avant, et annuler le réécrit.**
Pas d'action inverse reconstituée à la main — celle-ci se trompe dès que l'opération a des
effets de bord (adresse héritée, position recopiée, cascade de suppression), et c'est
précisément ce genre d'écart qui a produit les surprises des semaines passées.

Le relevé passe par les événements de la session SQLAlchemy plutôt que par des appels
explicites dans chaque service : ce qui est écrit est relevé, y compris ce qu'aucun service
ne mentionne — les lignes supprimées en cascade, les colonnes modifiées par un `onupdate`.
Un relevé qu'on doit penser à appeler est un relevé qu'on oublie.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import delete as sql_delete, event, insert, inspect, select, update as sql_update
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.local import Local
from app.models.patrimoine_legacy import PatrimoineLegacyAsset
from app.models.patrimoine_undo import PatrimoineUndoEntry

# Les trois tables que l'écran fait bouger. Volontairement limité : un journal qui
# couvrirait toute la base serait à la fois énorme et impossible à rejouer sûrement.
TRACKED = (Building, Local, PatrimoineLegacyAsset)

# Ordre de dépendance : un local ne peut pas être réinséré avant son bâtiment, et un
# bâtiment ne peut pas être supprimé avant les lignes qui le référencent.
_TABLE_ORDER = {"buildings": 0, "locals": 1, "patrimoine_legacy_assets": 2}

# Au-delà, l'action est un geste de masse (import, remise à zéro, purge) : on ne
# journalise pas. Ces gestes ont leur propre confirmation, et conserver 444 payloads
# ASTECH à chaque import coûterait plus cher que le service rendu.
MAX_ROWS = 300

# Profondeur de pile conservée par collectivité.
KEEP_ENTRIES = 40

_MODELS_BY_TABLE = {model.__tablename__: model for model in TRACKED}

# Colonnes de tenue de registre, jamais restaurées. Deux raisons : les remettre en arrière
# n'a aucun sens métier, et `updated_at` vaut, au moment du relevé, une fonction SQL non
# encore évaluée — la réécrire reviendrait à tenter d'insérer « now() » comme du texte
# dans une colonne de date.
_SKIP_COLUMNS = {"created_at", "updated_at"}


def _row_values(obj: Any) -> dict[str, Any]:
    """Toutes les colonnes de la ligne, sérialisables en JSON."""
    values: dict[str, Any] = {}
    for column in obj.__table__.columns:
        if column.name in _SKIP_COLUMNS:
            continue
        value = getattr(obj, column.name, None)
        values[column.name] = value.isoformat() if isinstance(value, datetime) else value
    return values


def _identity(obj: Any) -> int | None:
    """Clé primaire de l'objet, SANS déclencher de chargement.

    Lire `obj.id` sur une instance expirée provoquerait une requête — et, en plein
    `before_flush`, un rechargement au pire moment.
    """
    identity = inspect(obj).identity
    return identity[0] if identity else None


def _db_row(session: Session, obj: Any) -> dict[str, Any] | None:
    """L'état de la ligne TEL QU'IL EST EN BASE, avant que le flush ne l'écrase.

    On ne peut pas le lire dans l'objet : après un `commit`, ses attributs sont expirés,
    et lui affecter une nouvelle valeur ne charge pas l'ancienne — l'historique
    SQLAlchemy ne connaît alors que la valeur d'arrivée. Un journal bâti là-dessus
    enregistrerait « avant = après » et n'annulerait rien.

    La lecture passe par la connexion plutôt que par la session : un `session.execute`
    déclencherait un flush automatique, en plein flush.
    """
    pk = _identity(obj)
    if pk is None:
        return None
    table = obj.__table__
    row = session.connection().execute(select(table).where(table.c.id == pk)).mappings().first()
    if row is None:
        return None
    return {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in row.items()
        if key not in _SKIP_COLUMNS
    }


class UndoRecorder:
    """Relève, le temps d'une requête, ce que la session écrit sur les tables suivies."""

    def __init__(self) -> None:
        # Clé = l'objet lui-même : son identifiant n'existe pas encore pour une création.
        self._before: dict[Any, dict[str, Any] | None] = {}
        self._deleted: set[Any] = set()
        self.overflow = False

    def _capture(self, session: Session, flush_context: Any, instances: Any = None) -> None:
        for obj in session.new:
            if isinstance(obj, TRACKED) and obj not in self._before:
                self._before[obj] = None
        for obj in session.dirty:
            if not isinstance(obj, TRACKED) or obj in self._before:
                continue
            if not session.is_modified(obj, include_collections=False):
                continue
            self._before[obj] = _db_row(session, obj)
        for obj in session.deleted:
            if not isinstance(obj, TRACKED):
                continue
            # Une ligne peut être créée puis supprimée dans la même requête : son état
            # d'avant reste « rien », et l'annulation n'a donc rien à réinsérer.
            self._before.setdefault(obj, _db_row(session, obj))
            self._deleted.add(obj)
        if len(self._before) > MAX_ROWS:
            self.overflow = True

    def snapshots(self, session: Session) -> list[dict[str, Any]]:
        """Les clichés, une fois l'action committée et les identifiants attribués."""
        rows: list[dict[str, Any]] = []
        for obj, before in self._before.items():
            after = None if obj in self._deleted else _db_row(session, obj)
            pk = (before or after or {}).get("id")
            if pk is None or before == after:
                continue
            rows.append({"table": obj.__table__.name, "pk": pk, "before": before, "after": after})
        return rows


def record(db: Session, *, city_id: int | None, user_id: int | None, label: str):
    """Contexte qui journalise l'action en cours, si elle écrit quelque chose.

    S'utilise autour d'un appel de service **déjà committé** : l'entrée de journal est
    écrite dans un second temps, pour que l'échec du journal ne puisse jamais faire
    échouer l'action de l'utilisateur.
    """
    return _RecordContext(db, city_id=city_id, user_id=user_id, label=label)


class _RecordContext:
    def __init__(self, db: Session, *, city_id: int | None, user_id: int | None, label: str) -> None:
        self.db = db
        self.city_id = city_id
        self.user_id = user_id
        self.label = label
        self.recorder = UndoRecorder()

    def __enter__(self) -> "_RecordContext":
        # `before_flush` : la base porte encore l'état d'avant, c'est le seul moment où
        # on peut le lire. Les identifiants des créations, eux, sont relus après coup.
        event.listen(self.db, "before_flush", self.recorder._capture)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        event.remove(self.db, "before_flush", self.recorder._capture)
        if exc_type is not None or self.city_id is None:
            return False
        rows = self.recorder.snapshots(self.db)
        if not rows:
            return False
        # Un geste de masse n'est pas journalisé — mais il pose quand même une borne, sans
        # snapshots. Sans elle, « Annuler » après un import remonterait silencieusement à
        # l'action d'AVANT l'import et défairait tout autre chose que ce qu'on croit.
        too_large = self.recorder.overflow or len(rows) > MAX_ROWS
        entry = PatrimoineUndoEntry(
            city_id=self.city_id,
            user_id=self.user_id,
            label=f"{self.label} — trop vaste pour être annulée" if too_large else self.label,
            snapshots_json="[]" if too_large else json.dumps(rows, ensure_ascii=False, default=str),
        )
        self.db.add(entry)
        self.db.commit()
        _trim(self.db, self.city_id)
        return False


def _trim(db: Session, city_id: int) -> None:
    """Ne garde que les dernières entrées : ce journal rattrape, il n'archive pas."""
    keep = db.scalars(
        select(PatrimoineUndoEntry.id)
        .where(PatrimoineUndoEntry.city_id == city_id)
        .order_by(PatrimoineUndoEntry.id.desc())
        .limit(KEEP_ENTRIES)
    ).all()
    if len(keep) < KEEP_ENTRIES:
        return
    db.execute(
        sql_delete(PatrimoineUndoEntry).where(
            PatrimoineUndoEntry.city_id == city_id, PatrimoineUndoEntry.id < min(keep)
        )
    )
    db.commit()


def last_entry(db: Session, city_id: int | None) -> PatrimoineUndoEntry | None:
    """La dernière action annulable, ou rien."""
    if city_id is None:
        return None
    return db.scalars(
        select(PatrimoineUndoEntry)
        .where(
            PatrimoineUndoEntry.city_id == city_id,
            PatrimoineUndoEntry.undone_at.is_(None),
        )
        .order_by(PatrimoineUndoEntry.id.desc())
        .limit(1)
    ).first()


def _coerce(model: Any, values: dict[str, Any]) -> dict[str, Any]:
    """Rend au dictionnaire les types que la base attend (dates surtout)."""
    coerced: dict[str, Any] = {}
    for column in model.__table__.columns:
        if column.name not in values:
            continue
        value = values[column.name]
        if isinstance(value, str) and str(column.type).startswith("DATETIME"):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                value = None
        coerced[column.name] = value
    return coerced


def undo_last(db: Session, city_id: int | None) -> dict[str, Any]:
    """Réécrit l'état d'avant la dernière action.

    Les réinsertions descendent la hiérarchie (bâtiment, puis local, puis bien) et les
    suppressions la remontent : c'est la seule façon de ne pas heurter une clé étrangère
    en défaisant une cascade.
    """
    entry = last_entry(db, city_id)
    if entry is None:
        return {"annule": False, "libelle": None, "lignes": 0, "motif": "rien_a_annuler"}

    rows: list[dict[str, Any]] = json.loads(entry.snapshots_json)
    if not rows:
        # Borne posée par un geste de masse : on ne la franchit pas. L'entrée reste en
        # place et bloque définitivement les annulations plus anciennes — c'est voulu,
        # elles ne veulent plus rien dire une fois l'import ou la purge passés.
        return {"annule": False, "libelle": entry.label, "lignes": 0, "motif": "trop_vaste"}
    creations = [row for row in rows if row["before"] is None]
    suppressions = [row for row in rows if row["after"] is None and row["before"] is not None]
    modifications = [
        row for row in rows if row["before"] is not None and row["after"] is not None
    ]

    # 1. Défaire les suppressions : réinsérer, du porteur vers le porté.
    for row in sorted(suppressions, key=lambda r: _TABLE_ORDER.get(r["table"], 9)):
        model = _MODELS_BY_TABLE.get(row["table"])
        if model is None:
            continue
        exists = db.execute(
            select(model.id).where(model.id == row["pk"])  # type: ignore[attr-defined]
        ).first()
        if exists is None:
            db.execute(insert(model.__table__).values(**_coerce(model, row["before"])))

    # 2. Remettre les valeurs d'avant sur ce qui a été modifié.
    for row in modifications:
        model = _MODELS_BY_TABLE.get(row["table"])
        if model is None:
            continue
        db.execute(
            sql_update(model.__table__)
            .where(model.__table__.c.id == row["pk"])
            .values(**_coerce(model, row["before"]))
        )

    # 3. Défaire les créations : supprimer, du porté vers le porteur.
    for row in sorted(creations, key=lambda r: -_TABLE_ORDER.get(r["table"], 9)):
        model = _MODELS_BY_TABLE.get(row["table"])
        if model is None:
            continue
        db.execute(sql_delete(model.__table__).where(model.__table__.c.id == row["pk"]))

    entry.undone_at = datetime.now(timezone.utc)
    db.add(entry)
    db.commit()
    return {"annule": True, "libelle": entry.label, "lignes": len(rows), "motif": None}


def describe(entry: PatrimoineUndoEntry | None) -> dict[str, Any]:
    """Ce que l'écran affiche sur le bouton d'annulation."""
    if entry is None:
        return {"disponible": False, "libelle": None, "lignes": 0, "date": None}
    rows: Iterable[Any] = json.loads(entry.snapshots_json)
    lignes = len(list(rows))
    return {
        # `disponible` dit qu'il y a une dernière action ; `lignes` à 0 dit qu'elle est
        # trop vaste pour être défaite. L'écran doit montrer les deux : un bouton grisé
        # nommé est plus honnête qu'un bouton absent.
        "disponible": lignes > 0,
        "libelle": entry.label,
        "lignes": lignes,
        "date": entry.created_at.isoformat() if entry.created_at else None,
    }
