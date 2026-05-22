"""Import CSV des relevés mensuels DALKIA.

Format attendu (DALKIA envoie avant le 5e jour ouvrable du mois) :
  code_site, nom_site, nom_compteur, date_releve, qt_mwh_pci, etat_chauffe, volume_ecs_m3 (optionnel)

Les séparateurs acceptés : virgule, point-virgule, tabulation.
La ligne d'en-tête est requise.

Colonnes reconnues (insensibles à la casse) :
  - code_site    → code site CPE (ex: "VDS-ENS 02")
  - qt_mwh_pci  → consommation gaz mensuelle en MWhPCI
  - volume_ecs_m3 → volume ECS mensuel (m³), optionnel
  - etat_chauffe → O/N/1/0/True/False
  - annee, mois  → si date_releve absent
  - date_releve  → YYYY-MM-DD ou MM/YYYY ou YYYY-MM
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.schemas.cpe import CpeGazReleveCreate, CpeImportResult
from app.services.cpe import get_site_by_code, upsert_releve

LOG = logging.getLogger(__name__)

_BOOL_TRUE = {"o", "oui", "1", "true", "vrai", "x"}
_BOOL_FALSE = {"n", "non", "0", "false", "faux", ""}


def _detect_delimiter(sample: str) -> str:
    for d in (";", ",", "\t"):
        if d in sample:
            return d
    return ","


def _parse_bool(val: str) -> bool | None:
    v = val.strip().lower()
    if v in _BOOL_TRUE:
        return True
    if v in _BOOL_FALSE:
        return False
    return None


def _parse_date(val: str) -> tuple[int, int] | None:
    """Retourne (annee, mois) depuis diverses formes de date."""
    val = val.strip()
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%m/%Y", "%d/%m/%Y"):
        try:
            d = date.strptime(val, fmt) if len(val) > 7 else None
            if d:
                return d.year, d.month
        except (ValueError, AttributeError):
            pass
    # tentative YYYY-MM
    parts = val.replace("/", "-").split("-")
    if len(parts) >= 2:
        try:
            y, m = int(parts[0]), int(parts[1])
            if 2000 <= y <= 2100 and 1 <= m <= 12:
                return y, m
            # MM/YYYY
            y2, m2 = int(parts[1]), int(parts[0])
            if 2000 <= y2 <= 2100 and 1 <= m2 <= 12:
                return y2, m2
        except ValueError:
            pass
    return None


def _normalize_header(h: str) -> str:
    return (
        h.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("ô", "o")
    )


def import_releves_csv(
    db: Session,
    content: str | bytes,
    source: str = "csv_dalkia",
) -> CpeImportResult:
    """Parse et importe le fichier CSV de relevés mensuels DALKIA.

    Returns: CpeImportResult avec le bilan de l'import.
    """
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = content.decode("latin-1", errors="replace")

    sample = content[:2000]
    delimiter = _detect_delimiter(sample)

    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

    # Normalise les noms de colonnes
    if reader.fieldnames is None:
        return CpeImportResult(
            nb_lignes=0, nb_inseres=0, nb_mis_a_jour=0, nb_erreurs=1,
            erreurs=["Fichier vide ou sans en-tête"], sites_inconnus=[]
        )

    raw_headers = list(reader.fieldnames)
    header_map = {_normalize_header(h): h for h in raw_headers}

    def _col(norm: str) -> str | None:
        """Retourne le nom original de la colonne normalisée, ou None."""
        return header_map.get(norm)

    col_code = _col("code_site")
    col_qt = _col("qt_mwh_pci") or _col("consommation_gaz") or _col("qt") or _col("kwh_pci")
    col_ecs = _col("volume_ecs_m3") or _col("ecs_m3") or _col("ecs")
    col_chauffe = _col("etat_chauffe") or _col("etat_marche") or _col("chauffe")
    col_date = _col("date_releve") or _col("date") or _col("mois_annee")
    col_annee = _col("annee")
    col_mois = _col("mois")

    if col_code is None:
        return CpeImportResult(
            nb_lignes=0, nb_inseres=0, nb_mis_a_jour=0, nb_erreurs=1,
            erreurs=["Colonne 'code_site' introuvable dans le CSV"],
            sites_inconnus=[]
        )

    nb_lignes = nb_inseres = nb_mis_a_jour = nb_erreurs = 0
    erreurs: list[str] = []
    sites_inconnus: set[str] = set()

    for i, row in enumerate(reader, start=2):  # ligne 1 = en-tête
        nb_lignes += 1
        code = (row.get(col_code) or "").strip()
        if not code:
            continue

        # Résolution du site
        site = get_site_by_code(db, code)
        if site is None:
            sites_inconnus.add(code)
            nb_erreurs += 1
            continue

        # Résolution annee/mois
        annee = mois = None
        if col_date:
            parsed = _parse_date(row.get(col_date, ""))
            if parsed:
                annee, mois = parsed
        if annee is None and col_annee and col_mois:
            try:
                annee = int(row.get(col_annee, 0))
                mois = int(row.get(col_mois, 0))
            except (ValueError, TypeError):
                pass
        if annee is None or mois is None or not (1 <= mois <= 12):
            erreurs.append(f"Ligne {i} [{code}] : date/mois invalide")
            nb_erreurs += 1
            continue

        # Valeurs
        qt = None
        if col_qt:
            try:
                raw_qt = (row.get(col_qt) or "").replace(",", ".").strip()
                if raw_qt:
                    qt = float(raw_qt)
            except ValueError:
                erreurs.append(f"Ligne {i} [{code}] : qt_mwh_pci invalide ({row.get(col_qt)})")
                nb_erreurs += 1
                continue

        ecs = None
        if col_ecs:
            try:
                raw_ecs = (row.get(col_ecs) or "").replace(",", ".").strip()
                if raw_ecs:
                    ecs = float(raw_ecs)
            except ValueError:
                pass

        chauffe = None
        if col_chauffe:
            chauffe = _parse_bool(row.get(col_chauffe, ""))

        # Sauvegarde
        try:
            existing_count = db.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(
                    __import__("sqlalchemy", fromlist=["func"]).func.count()
                ).select_from(
                    __import__("app.models.cpe", fromlist=["CpeGazReleve"]).CpeGazReleve
                ).where(
                    __import__("app.models.cpe", fromlist=["CpeGazReleve"]).CpeGazReleve.cpe_site_id == site.id,
                    __import__("app.models.cpe", fromlist=["CpeGazReleve"]).CpeGazReleve.annee == annee,
                    __import__("app.models.cpe", fromlist=["CpeGazReleve"]).CpeGazReleve.mois == mois,
                )
            ).scalar()

            upsert_releve(
                db,
                site.id,
                CpeGazReleveCreate(annee=annee, mois=mois, qt_mwh_pci=qt, volume_ecs_m3=ecs, etat_chauffe=chauffe),
                source=source,
            )

            if existing_count:
                nb_mis_a_jour += 1
            else:
                nb_inseres += 1

        except Exception as exc:
            LOG.warning("Erreur import ligne %d [%s] : %s", i, code, exc)
            erreurs.append(f"Ligne {i} [{code}] : {exc}")
            nb_erreurs += 1

    return CpeImportResult(
        nb_lignes=nb_lignes,
        nb_inseres=nb_inseres,
        nb_mis_a_jour=nb_mis_a_jour,
        nb_erreurs=nb_erreurs,
        erreurs=erreurs[:50],  # cap à 50 messages
        sites_inconnus=sorted(sites_inconnus),
    )
