"""
Référentiel patrimoine historique de la collectivité (ASTECH) — aller-retour.

`PatrimoineLegacyImport` : un export ASTECH chargé dans Po2. Conserve le **gabarit**
du fichier (nom de feuille, ligne d'en-têtes, liste des en-têtes à l'octet près) car
ASTECH ne réimporte le fichier modifié que si les en-têtes ET le code bien sont
strictement inchangés.

`PatrimoineLegacyAsset` : un bien du fichier ASTECH, identifié par son `CODE_BIEN`.
Le code bien est la **clé pivot permanente** : c'est lui qui rapproche les cycles
successifs (import → traitement → réexport → réimport dans ASTECH), et c'est la clé
de mise à jour côté ASTECH. Il n'est jamais réécrit ni normalisé.

Relation **N codes bien → 1 bâtiment** : plusieurs biens ASTECH (des locaux) peuvent
désigner le même bâtiment Po2.

Le payload d'origine de chaque ligne est conservé intégralement (`source_payload_json`)
pour pouvoir réémettre un fichier au format attendu par ASTECH.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# Statuts de traitement d'un bien historique.
STATUS_TODO = "a_traiter"
# Rattache par le moteur, **a confirmer** : un rattachement automatique n'est pas une
# validation. `lie` signifie « valide par un humain ».
STATUS_PROPOSED = "propose"
STATUS_LINKED = "lie"
STATUS_IGNORED = "ignore"
STATUS_OUT_OF_SCOPE = "hors_perimetre"
STATUS_TO_CREATE = "a_creer"
# Le bien n'a plus lieu d'etre dans AS-TECH : Po2 demande sa suppression cote
# collectivite. Affiche « A SUPPRIMER DE AS-TECH ». A ne pas confondre avec `ignore`,
# qui dit « je ne traite pas ce bien » alors qu'il reste au referentiel. On conserve la
# ligne plutot que de l'effacer : un re-import du meme fichier ne la ressuscite pas en
# silence, et l'operatrice peut revenir sur sa decision (Q23).
#
# La VALEUR reste `disparu` : le libelle a change apres coup (2026-08-21), renommer la
# cle imposerait une migration de donnees pour un simple affichage.
STATUS_GONE = "disparu"

# Cibles autorisées. Le site n'en est pas une : il regroupe plusieurs bâtiments et ne
# porte ni position ni parcelle (décision Q15/Q16). Les sites restent néanmoins dans la
# plateforme, ils assurent la hiérarchie Site > Bâtiment > Local.
TARGET_BUILDING = "building"
TARGET_LOCAL = "local"

# Origine du rattachement, pour la feuille de traçabilité du réexport.
ORIGIN_AUTO = "auto"
ORIGIN_MANUAL = "manuel"
ORIGIN_IGN = "ign"


class PatrimoineLegacyImport(Base):
    __tablename__ = "patrimoine_legacy_imports"
    __table_args__ = (
        UniqueConstraint("city_id", "batch", name="uq_legacy_import_city_batch"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    batch: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Ligne d'en-têtes (1-indexée) : `Feuil1` la place en ligne 2, `BAT` en ligne 1.
    header_row: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # En-têtes recopiés tels quels : gabarit obligatoire pour la réinjection ASTECH.
    headers_json: Mapped[str] = mapped_column(Text, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PatrimoineLegacyAsset(Base):
    __tablename__ = "patrimoine_legacy_assets"
    __table_args__ = (
        UniqueConstraint("city_id", "code_bien", name="uq_legacy_asset_city_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)

    # --- Clé pivot ASTECH : jamais modifiée, jamais normalisée -----------------
    code_bien: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    # --- Identité du bien telle qu'exportée par ASTECH -------------------------
    designation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nomcourt: Mapped[str | None] = mapped_column(String(255), nullable=True)
    genre: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    categ: Mapped[str | None] = mapped_column(String(20), nullable=True)
    categ_des: Mapped[str | None] = mapped_column(String(120), nullable=True)
    souscat_des: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # 'O' = sorti du parc (bien qui n'est plus utilisé).
    horsparc: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    code_parent: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    # --- Adresse source, telle quelle (non normalisée) -------------------------
    source_norue: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_bister: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_libelvoie: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_codpost: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_ville: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_commune: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    source_refcad: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # --- Rattachement au référentiel Po2 (N codes bien -> 1 cible) -------------
    # `building_id` est le **bâtiment porteur résolu** : pour une cible « local », c'est
    # le bâtiment parent. Seuls les bâtiments portent adresse, position et cadastre, donc
    # c'est toujours lui qui alimente l'héritage, la carte et le réexport.
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    local_id: Mapped[int | None] = mapped_column(
        ForeignKey("locals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 'building' ou 'local'. Le SITE est exclu (Q15) : ni coordonnées, ni cadastre.
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, default=TARGET_BUILDING)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_TODO, index=True
    )
    link_origin: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # --- Candidat proposé par le moteur de reconnaissance ---------------------
    candidate_building_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Point de travail : posé/déplacé sur la carte avant attribution IGN ----
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Adresse résolue depuis le point posé (géocodage inverse) --------------
    # Stockée À CÔTÉ de l'adresse d'origine (`source_*`), jamais à sa place : le
    # fichier ASTECH reste intact, et le réexport a besoin des deux pour tracer
    # l'ancienne et la nouvelle valeur.
    resolved_housenumber: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolved_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_postcode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    resolved_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resolved_citycode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    resolved_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 'ign_reverse' (point posé à la main) ou 'building' (hérité du bâtiment Po2).
    resolved_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Nom retenu — décision Q11 : le nom Po2/IGN gagne et sera réécrit dans ASTECH.
    resolved_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_section: Mapped[str | None] = mapped_column(String(10), nullable=True)
    resolved_numero_plan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Référence telle qu'attendue par ASTECH : section + numéro de plan sur 3 chiffres.
    resolved_refcad: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # --- Traçabilité + gabarit de réexport ------------------------------------
    import_batch: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Les 317 colonnes d'origine, conservées pour réémettre le fichier ASTECH.
    source_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
