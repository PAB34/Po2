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
import re
import unicodedata
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.schemas.cpe import CpeGazReleveCreate, CpeImportResult
from app.services.cpe import PCS_PCI_RATIO, get_site_by_code, upsert_releve
from app.services.cpe_accounting import get_current_cpe_contract_codes

# Regex d'extraction du code site CPE depuis le libellé "SITE" de l'export DALKIA détaillé
# (ex: "SETE GYMNASE VINCENT FERRARI VDS-SPORT 05" -> "VDS-SPORT 05").
_CODE_SITE_RE = re.compile(r"(?:VDS-[A-Z]+|CCAS)\s+\d+(?:\.\d+)*", re.IGNORECASE)

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


def _ascii_key(s: str) -> str:
    """Normalise un en-tête (sans accents, sans casse, espaces compactés) pour le matcher."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(s.lower().split())


def _extract_code_site(libelle: str) -> str | None:
    """Extrait le code site CPE en fin de libellé SITE (dernier motif reconnu)."""
    matches = _CODE_SITE_RE.findall(libelle or "")
    if not matches:
        return None
    # findall avec groupe non capturant -> renvoie les correspondances entières
    return re.sub(r"\s+", " ", matches[-1].strip().upper())


def _is_dalkia_detailed(fieldnames: list[str]) -> bool:
    """Détecte le vrai export DALKIA 'consommation détaillée' à ses colonnes."""
    keys = {_ascii_key(h) for h in fieldnames}
    return "type de compteur" in keys and any(k.startswith("date du rel") for k in keys) and "consommation" in keys


# TYPE DE COMPTEUR (export) -> code fluide normalisé
_FLUID_MAP = {"gaz": "GAZ", "electricite": "ELEC", "ecs": "ECS", "eau": "EAU", "chaleur": "CHALEUR"}


def _import_dalkia_detailed(
    db: Session,
    rows: list[dict],
    header_map: dict[str, str],
    source: str,
    city_id: int | None = None,
) -> CpeImportResult:
    """Importe l'export DALKIA détaillé (1 ligne par compteur × relevé, multi-fluides).

    Deux écritures :
      - `cpe_conso_releves` : TOUS les fluides (GAZ/ELEC/ECS/EAU/CHALEUR) par site × mois,
        avec énergie MWh, unité et qualité (réel vs estimé/panne) — pour le suivi/présentation.
      - `cpe_gaz_releves` : sous-ensemble gaz (MWh PCS→PCI) + ECS (m³) pour l'intéressement,
        uniquement pour les sites rattachés à un CpeSite.
    Seuls les contrats CPE Ville DALKIA sont retenus (filtre CODE CONTRAT).
    """
    from sqlalchemy import func, select

    from app.models.cpe import CpeConsoReleve, CpeGazReleve

    def col(*aliases: str) -> str | None:
        for a in aliases:
            if a in header_map:
                return header_map[a]
        for k, orig in header_map.items():
            if any(k.startswith(a) for a in aliases):
                return orig
        return None

    c_site = col("site")
    c_type = col("type de compteur")
    c_date = col("date du rel", "date du releve")
    c_conso = col("consommation")
    c_pcs = col("mwh pcs")
    c_contrat = col("code contrat")
    c_nature = col("nature evenement", "nature")
    c_unite = col("unite")

    def _num(v: str | None) -> float:
        try:
            return float((v or "").replace(",", ".").strip() or 0.0)
        except ValueError:
            return 0.0

    # agrégat par (code, fluide, annee, mois)
    agg: dict[tuple[str, str, int, int], dict] = defaultdict(
        lambda: {"conso": 0.0, "energie": 0.0, "unite": None, "n": 0, "n_est": 0, "contrat": None}
    )
    nb_lignes = 0
    nb_hors_cpe = 0
    erreurs: list[str] = []

    for row in rows:
        nb_lignes += 1
        contrat = (row.get(c_contrat, "") if c_contrat else "").strip().upper()
        code = _extract_code_site(row.get(c_site, "") if c_site else "")
        if not code:
            continue
        parsed = _parse_date(row.get(c_date, "") if c_date else "")
        if not parsed:
            continue
        annee, mois = parsed
        current_contract_codes = get_current_cpe_contract_codes(db, city_id=city_id, year=annee)
        if c_contrat and contrat and contrat not in current_contract_codes:
            nb_hors_cpe += 1
            continue
        fluide = _FLUID_MAP.get(_ascii_key(row.get(c_type, "") if c_type else ""))
        if not fluide:
            continue
        unite = (row.get(c_unite, "") if c_unite else "").strip() or None
        nature = _ascii_key(row.get(c_nature, "") if c_nature else "")

        a = agg[(code, fluide, annee, mois)]
        a["contrat"] = contrat or a["contrat"]
        a["unite"] = unite or a["unite"]
        a["n"] += 1
        if nature and nature != "releve normal":
            a["n_est"] += 1
        a["conso"] += _num(row.get(c_conso) if c_conso else None)
        if fluide == "GAZ":
            a["energie"] += _num(row.get(c_pcs) if c_pcs else None)         # MWh PCS
        elif fluide in ("ELEC", "CHALEUR"):
            a["energie"] += _num(row.get(c_conso) if c_conso else None) / 1000.0  # kWh -> MWh

    # --- Écriture cpe_conso_releves (tous fluides) ---
    nb_conso = 0
    sites_inconnus: set[str] = set()
    for (code, fluide, annee, mois), a in sorted(agg.items()):
        site = get_site_by_code(db, code)
        if site is None:
            sites_inconnus.add(code)
        energie = round(a["energie"], 4) if fluide in ("GAZ", "ELEC", "CHALEUR") else None
        existing = db.scalars(
            select(CpeConsoReleve).where(
                CpeConsoReleve.code_site == code, CpeConsoReleve.fluide == fluide,
                CpeConsoReleve.annee == annee, CpeConsoReleve.mois == mois,
            )
        ).first()
        fields = dict(
            city_id=(site.city_id if site else None),
            cpe_site_id=(site.id if site else None),
            code_site=code, contract_code=a["contrat"], fluide=fluide, annee=annee, mois=mois,
            consommation=round(a["conso"], 3), unite=a["unite"], energie_mwh=energie,
            nb_releves=a["n"], nb_estimes=a["n_est"],
            qualite=("reel" if a["n_est"] == 0 else "partiel"), source=source,
        )
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            db.add(existing)
        else:
            db.add(CpeConsoReleve(**fields))
            nb_conso += 1

    # --- Écriture cpe_gaz_releves (intéressement) : gaz+ECS par site rattaché ---
    nb_inseres = nb_mis_a_jour = nb_erreurs = 0
    gaz_ecs: dict[tuple[str, int, int], dict] = defaultdict(lambda: {"gaz_pcs": 0.0, "ecs_m3": 0.0})
    for (code, fluide, annee, mois), a in agg.items():
        if fluide == "GAZ":
            gaz_ecs[(code, annee, mois)]["gaz_pcs"] += a["energie"]
        elif fluide == "ECS":
            gaz_ecs[(code, annee, mois)]["ecs_m3"] += a["conso"]

    for (code, annee, mois), v in sorted(gaz_ecs.items()):
        site = get_site_by_code(db, code)
        if site is None:
            continue
        qt_pci = round(v["gaz_pcs"] / PCS_PCI_RATIO, 4) if v["gaz_pcs"] else None
        ecs = round(v["ecs_m3"], 3) if v["ecs_m3"] else None
        if qt_pci is None and ecs is None:
            continue
        try:
            existing = db.execute(
                select(func.count()).select_from(CpeGazReleve).where(
                    CpeGazReleve.cpe_site_id == site.id,
                    CpeGazReleve.annee == annee, CpeGazReleve.mois == mois,
                )
            ).scalar()
            upsert_releve(
                db, site.id,
                CpeGazReleveCreate(annee=annee, mois=mois, qt_mwh_pci=qt_pci, volume_ecs_m3=ecs, etat_chauffe=None),
                source=source,
            )
            if existing:
                nb_mis_a_jour += 1
            else:
                nb_inseres += 1
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Erreur import conso [%s %s-%s] : %s", code, annee, mois, exc)
            erreurs.append(f"[{code} {annee}-{mois:02d}] : {exc}")
            nb_erreurs += 1

    db.commit()

    notes = [f"(info) {nb_conso} relevés conso multi-fluides enregistrés"]
    if nb_hors_cpe:
        notes.append(f"(info) {nb_hors_cpe} lignes hors marché CPE Ville ignorées")
    erreurs = notes + erreurs

    return CpeImportResult(
        nb_lignes=nb_lignes,
        nb_inseres=nb_inseres,
        nb_mis_a_jour=nb_mis_a_jour,
        nb_erreurs=nb_erreurs,
        erreurs=erreurs[:50],
        sites_inconnus=sorted(sites_inconnus),
    )


def import_releves_csv(
    db: Session,
    content: str | bytes,
    source: str = "csv_dalkia",
    city_id: int | None = None,
) -> CpeImportResult:
    """Parse et importe le fichier CSV de relevés mensuels DALKIA.

    Détecte automatiquement deux formats :
      - l'export DALKIA détaillé `consommation_detaillee_*` (multi-fluides, 1 ligne/compteur/relevé) ;
      - le format simple historique (code_site, qt_mwh_pci, ...).

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

    # Format DALKIA détaillé ?
    if reader.fieldnames and _is_dalkia_detailed(list(reader.fieldnames)):
        header_map = {_ascii_key(h): h for h in reader.fieldnames}
        return _import_dalkia_detailed(db, list(reader), header_map, source, city_id=city_id)

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
