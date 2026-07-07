"""
Import BPU depuis le fichier xlsx canonique d'extraction manuelle.

Le fichier source (`extraction_tarifs_electricite_BPU.xlsx`) contient 5 onglets :
  - Synthese : KPIs, ignoré ici
  - Sources_PDF : 1 ligne / PDF → BpuDocument
  - Prix_detailles : 173 lignes au format wide → BpuSegment + BpuTimePeriod + BpuPriceComponent
  - Surcouts_fixes : 9 lignes → BpuFixedCharge
  - Controle_qualite : notes d'audit, intégré aux extraction_notes des docs concernés

Usage (dans le conteneur backend) :

    python -m app.scripts.import_bpu_xlsx \\
        --xlsx "/workspace/saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/extraction_tarifs_electricite_BPU.xlsx" \\
        --force

`--force` reset les BPU déjà en BDD (delete + reinsert).
Statut d'extraction = `manual`, confidence = 1.0.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from app.core.db import SessionLocal
from app.models.bpu import (
    COMPONENT_AUTRE,
    COMPONENT_CAPACITE,
    COMPONENT_CEE,
    COMPONENT_FOURNITURE,
    COMPONENT_GO,
    EXTRACTION_MANUAL,
    SEGMENT_TYPE_SITE,
    SEGMENT_TYPE_TENSION,
    SEGMENT_TYPE_USAGE,
    BpuDocument,
    BpuFixedCharge,
    BpuPriceComponent,
    BpuSegment,
    BpuTimePeriod,
)

logger = logging.getLogger(__name__)


DEFAULT_XLSX = Path(
    "/workspace/saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/extraction_tarifs_electricite_BPU.xlsx"
)


# ---------------------------------------------------------------------------
# Parsers / normalisation des champs xlsx
# ---------------------------------------------------------------------------


def _s(value) -> str | None:
    """String safe : retourne None si NaN / vide."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s or None


def _f(value) -> float | None:
    """Float safe : tolère '12,34' / '12.34' / espaces, retourne None si NaN."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    s = _s(value)
    if s is None:
        return None
    s = s.replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_lot(value) -> int | None:
    """'Lot 1' → 1."""
    s = _s(value)
    if not s:
        return None
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def _parse_year(value) -> tuple[int | None, str | None]:
    """'Année / prix' → (valid_year, original_label).

    Exemples :
      '2021'              → (2021, None)
      '2021-2022'         → (2021, '2021-2022')
      '2022 / signé 2023' → (2022, '2022 / signé 2023')
      '2026'              → (2026, None)
    """
    s = _s(value)
    if not s:
        return None, None
    m = re.search(r"(20\d{2})", s)
    year = int(m.group(1)) if m else None
    # Si la chaîne n'est pas exactement l'année, on garde le label original
    label = s if year is None or s != str(year) else None
    return year, label


_RX_MS = re.compile(r"\bMS\s*(\d+)\b", re.IGNORECASE)
_RX_LOT = re.compile(r"\bLOT\s*(\d+)\b", re.IGNORECASE)
_RX_AVENANT_FILE = re.compile(r"AVENANT[\s_-]*(\d+)", re.IGNORECASE)
_RX_V_LABEL = re.compile(r"\bV(\d)\b", re.IGNORECASE)


def _extract_ms_from_label(label: str | None) -> int | None:
    """Extrait MS depuis 'BPU V2 MS1 LOT 3 2025' → 1, 'BPU 2024 MS1 LOT 1' → 1."""
    if not label:
        return None
    m = _RX_MS.search(label)
    return int(m.group(1)) if m else None


def _extract_amendment_from_filename(filename: str) -> int | None:
    """'EDF_MS1_LOT_1_AVENANT_6_BPU_2025.pdf' → 6."""
    m = _RX_AVENANT_FILE.search(filename or "")
    return int(m.group(1)) if m else None


# Mapping segment_code depuis Site / typologie.
# Important : chaque sous-typologie doit produire un segment_code DISTINCT pour
# ne pas collapser plusieurs sites différents (Eclairage public vs Bornes vs
# Bâtiment numéroté) en un seul segment et casser la contrainte unique
# (period_id, component_type).
_SEGMENT_CODE_PATTERNS = [
    # Sous-typologies de C4/C5 — du plus spécifique au plus générique
    (re.compile(r"Sites?\s*C5\s+Bornes", re.IGNORECASE), lambda m: ("C5_BORNES", "site")),
    (re.compile(r"Sites?\s*C5\s+Eclairage\s+Public", re.IGNORECASE), lambda m: ("C5_EP", "site")),
    # Sites C5 bâtiment 1/2/4 Prix → C5_BAT_1 / C5_BAT_2 / C5_BAT_4
    (re.compile(r"Sites?\s*C5\s+b[âa]timent\s+(\d+)", re.IGNORECASE), lambda m: (f"C5_BAT_{m.group(1)}", "site")),
    # Sites C5 bâtiment** (Heures Base) — double étoile prioritaire sur étoile simple
    (re.compile(r"Sites?\s*C5\s+b[âa]timent\*\*", re.IGNORECASE), lambda m: ("C5_BAT_BASE", "site")),
    (re.compile(r"Sites?\s*C5\s+b[âa]timent\*", re.IGNORECASE), lambda m: ("C5_BAT_HCHP", "site")),
    # C5 Bâtiments RAE BT ≤ 36 kVA - variantes (4 cadrans / Heures Base / Heures Creuses-Pleines)
    (re.compile(r"C5\s+B[âa]timents.*RAE.*4\s*cadrans", re.IGNORECASE), lambda m: ("C5_BAT_RAE_4C", "site")),
    (re.compile(r"C5\s+B[âa]timents.*RAE.*Heures?\s+Base", re.IGNORECASE), lambda m: ("C5_BAT_RAE_BASE", "site")),
    (re.compile(r"C5\s+B[âa]timents.*RAE.*Heures?\s+Creuses", re.IGNORECASE), lambda m: ("C5_BAT_RAE_HCHP", "site")),
    (re.compile(r"C5\s+B[âa]timents.*RAE", re.IGNORECASE), lambda m: ("C5_BAT_RAE", "site")),
    # Eclairage public verbeux EDF 2021/2022 : "Eclairage public, panneaux, feux tricolores ... (C5)"
    (re.compile(r"Eclairage\s+public.*\(C5\)", re.IGNORECASE), lambda m: ("C5_EP", "site")),
    # Bornes de recharge véhicules électriques (C4) ou (C5)
    (re.compile(r"Bornes\s+de\s+recharge.*\(C5\)", re.IGNORECASE), lambda m: ("C5_BORNES", "site")),
    (re.compile(r"Bornes\s+de\s+recharge.*\(C4\)", re.IGNORECASE), lambda m: ("C4_BORNES", "site")),
    # Sous-typologies C4
    (re.compile(r"Sites?\s*C4\s+Bornes", re.IGNORECASE), lambda m: ("C4_BORNES", "site")),
    # Sites Cx génériques (C1, C2, C3, C4, C5 sans qualificatif)
    (re.compile(r"Sites?\s*(C[1-5])(?!\w)", re.IGNORECASE), lambda m: (m.group(1).upper(), "site")),
    # Cx isolé entre parenthèses
    (re.compile(r"\((C[1-5])\)", re.IGNORECASE), lambda m: (m.group(1).upper(), "site")),
    # Usages standalone (Bâtiment / Bornes / Eclairage Public seuls)
    (re.compile(r"\bBornes\b", re.IGNORECASE), lambda m: ("BORNES", "usage")),
    (re.compile(r"\bB[âa]timent\b", re.IGNORECASE), lambda m: ("BATIMENT", "usage")),
    (re.compile(r"Eclairage\s+Public", re.IGNORECASE), lambda m: ("ECLAIRAGE_PUBLIC", "usage")),
]


def _tension_bucket(tension: str | None) -> str | None:
    """Bucket tarifaire du nouveau marché depuis la colonne Tension :
    HTA (=C1/C2/C3), BT (BT > 36 kVA = C4), BT36 (BT ≤ 36 kVA = C5). None si indéterminé."""
    if not tension:
        return None
    t = tension.upper().replace(" ", "")
    if "HTA" in t:
        return "HTA"
    if "36" in t:
        return "BT" if ">36" in t else "BT36"  # 'BT>36 kVA' = C4 ; 'BT≤36 kVA' = C5
    if "BT" in t:
        return "BT"  # 'BT' seul (> 36 kVA)
    return None


def _normalize_segment(site_label: str | None, turpe: str | None, tension: str | None) -> tuple[str, str]:
    """Détermine (segment_code, segment_type) depuis les colonnes xlsx.

    Heuristique :
      1. essayer les patterns sur `site_label` (le plus descriptif)
      2. sinon fallback sur `turpe` (Bâtiment / C2 / C4 / Eclairage Public)
      3. sinon fallback sur `tension` (HTA → HTA, BT → BT)

    Note importante : les sous-typologies C4/C5 (Bornes, Eclairage Public,
    Bâtiment numéroté, RAE 4 cadrans, etc.) produisent des codes DISTINCTS
    pour éviter d'écraser plusieurs sites sous le même segment_code. Le nouveau
    marché « Bâtiment » 2026 est en plus subdivisé par tension (BATIMENT_HTA/BT/BT36)
    pour ne pas perdre la distinction de classe (cf. bpu-import-granulaire-2026-decisions).
    """
    if site_label:
        for rx, fn in _SEGMENT_CODE_PATTERNS:
            m = rx.search(site_label)
            if m:
                code, seg_type = fn(m)
                if code == "BATIMENT":
                    bucket = _tension_bucket(tension)
                    if bucket:
                        return f"BATIMENT_{bucket}", seg_type
                return code, seg_type
    if turpe:
        t = turpe.strip()
        m = re.match(r"^(C[1-5])$", t, re.IGNORECASE)
        if m:
            return m.group(1).upper(), SEGMENT_TYPE_SITE
        if "bâtiment" in t.lower() or "batiment" in t.lower():
            bucket = _tension_bucket(tension)
            return (f"BATIMENT_{bucket}" if bucket else "BATIMENT"), SEGMENT_TYPE_USAGE
        if "eclairage" in t.lower() or "éclairage" in t.lower():
            return "ECLAIRAGE_PUBLIC", SEGMENT_TYPE_USAGE
    if tension:
        if "HTA" in tension.upper():
            return "HTA", SEGMENT_TYPE_TENSION
        if "BT" in tension.upper():
            return "BT", SEGMENT_TYPE_TENSION
    # Fallback ultime
    return "INCONNU", SEGMENT_TYPE_SITE


_PERIOD_PATTERNS = [
    (re.compile(r"\bHPH\b|Heures\s+Pleines.*Haute", re.IGNORECASE), "HPH"),
    (re.compile(r"\bHCH\b|Heures\s+Creuses.*Haute", re.IGNORECASE), "HCH"),
    (re.compile(r"\bHPE\b|Heures\s+Pleines.*[BE]asse|Heures\s+Pleines.*[ÉE]t[ée]", re.IGNORECASE), "HPE"),
    (re.compile(r"\bHCE\b|Heures\s+Creuses.*[BE]asse|Heures\s+Creuses.*[ÉE]t[ée]", re.IGNORECASE), "HCE"),
    (re.compile(r"\bHPB\b", re.IGNORECASE), "HPE"),  # Basse = Été = HPE
    (re.compile(r"\bHCB\b", re.IGNORECASE), "HCE"),
    (re.compile(r"\bPOINTE\b", re.IGNORECASE), "POINTE"),
    (re.compile(r"\bHP\b", re.IGNORECASE), "HP"),
    (re.compile(r"\bHC\b", re.IGNORECASE), "HC"),
    (re.compile(r"\bBase\b", re.IGNORECASE), "BASE"),
]


def _normalize_period(period_label: str | None) -> str:
    """'HPH / Heures Pleines - Saison Haute' → 'HPH'."""
    if not period_label:
        return "BASE"
    for rx, code in _PERIOD_PATTERNS:
        if rx.search(period_label):
            return code
    return "BASE"


_CHARGE_TYPE_PATTERNS = [
    (re.compile(r"Branchement\s+Provisoire", re.IGNORECASE), "branchement_provisoire"),
    (re.compile(r"Contrat\s+Temporaire", re.IGNORECASE), "contrat_temporaire"),
    (re.compile(r"Abonnement", re.IGNORECASE), "abonnement"),
]


def _map_charge_type(libelle: str | None) -> str:
    if not libelle:
        return "autre"
    for rx, code in _CHARGE_TYPE_PATTERNS:
        if rx.search(libelle):
            return code
    return "autre"


_RX_PERIOD_RANGE = re.compile(
    r"(\d{1,2}/\d{1,2}/\d{4})\s*(?:au|à)\s*(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE
)


def _parse_applicable_period(value: str | None) -> tuple[date | None, date | None]:
    """'01/01/2023 au 31/12/2025' → (date(2023,1,1), date(2025,12,31))."""
    if not value:
        return None, None
    m = _RX_PERIOD_RANGE.search(value)
    if not m:
        return None, None
    def _d(s: str) -> date | None:
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except ValueError:
            return None
    return _d(m.group(1)), _d(m.group(2))


# ---------------------------------------------------------------------------
# Import principal
# ---------------------------------------------------------------------------


def import_xlsx(xlsx_path: Path, *, force: bool = False) -> dict[str, int]:
    """Importe les 3 onglets xlsx → BDD. Retourne les compteurs."""
    if not xlsx_path.exists():
        raise FileNotFoundError(f"xlsx introuvable : {xlsx_path}")

    logger.info("Lecture du fichier xlsx : %s", xlsx_path)
    sources_df = pd.read_excel(xlsx_path, sheet_name="Sources_PDF")
    prices_df = pd.read_excel(xlsx_path, sheet_name="Prix_detailles")
    charges_df = pd.read_excel(xlsx_path, sheet_name="Surcouts_fixes")
    try:
        controle_df = pd.read_excel(xlsx_path, sheet_name="Controle_qualite")
        controle_notes = "\n".join(
            f"[{_s(r['Point'])}] {_s(r['Détail'])}" for _, r in controle_df.iterrows()
            if _s(r.get('Point'))
        )
    except Exception:  # noqa: BLE001
        controle_notes = ""

    logger.info(
        "Onglets lus : Sources_PDF=%d, Prix_detailles=%d, Surcouts_fixes=%d",
        len(sources_df), len(prices_df), len(charges_df),
    )

    counters = {
        "documents": 0,
        "segments": 0,
        "periods": 0,
        "components": 0,
        "charges": 0,
        "skipped_prices": 0,
        "skipped_charges": 0,
        "errors": 0,
    }
    docs_by_filename: dict[str, BpuDocument] = {}

    with SessionLocal() as session:
        # --- 1. Documents (depuis Sources_PDF) ---
        if force:
            existing_filenames = set(sources_df["Fichier PDF"].dropna())
            n = (
                session.query(BpuDocument)
                .filter(BpuDocument.pdf_filename.in_(existing_filenames))
                .delete(synchronize_session=False)
            )
            logger.info("Force=True : %d BpuDocument supprimés (cascade segments/periods/components/charges).", n)
            session.commit()

        seen_keys: dict[tuple, str] = {}
        for _, row in sources_df.iterrows():
            pdf_filename = _s(row.get("Fichier PDF"))
            supplier = _s(row.get("Fournisseur"))
            lot_number = _parse_lot(row.get("Lot"))
            year, year_label = _parse_year(row.get("Année / prix"))
            internal_label = _s(row.get("Libellé document"))
            comment = _s(row.get("Commentaires extraction"))
            pages = _s(row.get("Pages"))

            if not (pdf_filename and supplier and lot_number and year):
                logger.warning("Document ignoré (clés manquantes) : %s", pdf_filename)
                counters["errors"] += 1
                continue

            ms = _extract_ms_from_label(internal_label)
            avenant = _extract_amendment_from_filename(pdf_filename)
            amendment_label = year_label or internal_label

            # Gestion des doublons de clé unique (ex : LOT3 prix ferme V2 + Annexe 2 AE)
            key = (supplier, year, ms, lot_number, avenant)
            if key in seen_keys:
                # Distinguer en bumpant amendment_number artificiel
                fallback_avenant = (avenant or 0) + 1
                while (supplier, year, ms, lot_number, fallback_avenant) in seen_keys:
                    fallback_avenant += 1
                logger.warning(
                    "Doublon de clé pour %s : %s (collision avec %s). "
                    "Attribution amendment_number=%d pour différencier.",
                    pdf_filename, key, seen_keys[key], fallback_avenant,
                )
                avenant = fallback_avenant
                key = (supplier, year, ms, lot_number, avenant)
            seen_keys[key] = pdf_filename

            # Upsert
            existing = (
                session.query(BpuDocument)
                .filter(
                    BpuDocument.supplier == supplier,
                    BpuDocument.valid_year == year,
                    BpuDocument.market_subsequent == ms,
                    BpuDocument.lot_number == lot_number,
                    BpuDocument.amendment_number == avenant,
                )
                .one_or_none()
            )
            if existing is not None and not force:
                # MAJ légère sans toucher aux enfants
                doc = existing
                doc.amendment_label = amendment_label or doc.amendment_label
                doc.extraction_status = EXTRACTION_MANUAL
                doc.extraction_method = "xlsx_manual"
                doc.extraction_confidence = 1.0
                if comment:
                    doc.extraction_notes = comment
            else:
                if existing is not None:
                    session.delete(existing)
                    session.flush()
                notes_parts = []
                if internal_label and internal_label != year_label:
                    notes_parts.append(f"interne: {internal_label}")
                if pages:
                    notes_parts.append(f"pages: {pages}")
                if comment:
                    notes_parts.append(comment)
                doc = BpuDocument(
                    supplier=supplier,
                    valid_year=year,
                    market_subsequent=ms,
                    lot_number=lot_number,
                    amendment_number=avenant,
                    amendment_label=amendment_label,
                    pdf_filename=pdf_filename,
                    pdf_relative_path=f"HERAULT ENERGIE/HISTORIQUE BPU/{pdf_filename}",
                    extraction_status=EXTRACTION_MANUAL,
                    extraction_method="xlsx_manual",
                    extraction_confidence=1.0,
                    extraction_notes=" | ".join(notes_parts) or None,
                )
                session.add(doc)
                session.flush()

            docs_by_filename[pdf_filename] = doc
            counters["documents"] += 1

        # --- 2. Prix (depuis Prix_detailles) ---
        # Cache des segments et postes par document
        segments_cache: dict[tuple[int, str], BpuSegment] = {}
        periods_cache: dict[tuple[int, str], BpuTimePeriod] = {}
        # Set des composantes déjà créées dans cette session pour éviter les
        # doublons (la relation period.components peut ne pas refléter les
        # ajouts pas encore flushés)
        seen_components: set[tuple[int, str]] = set()

        for _, row in prices_df.iterrows():
            pdf_filename = _s(row.get("Source fichier"))
            doc = docs_by_filename.get(pdf_filename)
            if doc is None:
                counters["skipped_prices"] += 1
                continue

            site = _s(row.get("Site / typologie"))
            turpe = _s(row.get("Tarif TURPE / référence"))
            tension = _s(row.get("Tension / alimentation"))
            period_raw = _s(row.get("Poste horosaisonnier"))
            notes = _s(row.get("Notes / observations"))

            segment_code, segment_type = _normalize_segment(site, turpe, tension)
            period_code = _normalize_period(period_raw)

            # turpe_tariff est limité à VARCHAR(10) → on n'y met que les codes
            # courts standards. Les libellés métier longs (ex: "Assimilé
            # Eclairage Public") vont dans `segment_label`.
            turpe_short = None
            if turpe:
                m_turpe = re.match(r"^(C[1-5]|BT|HTA|EP|CU4|CU|MU4|MUDT|LU)$", turpe.strip(), re.IGNORECASE)
                if m_turpe:
                    turpe_short = m_turpe.group(1).upper()

            # tension_category aussi en VARCHAR(10) → BT ou HTA uniquement
            tension_short = None
            if tension:
                if "HTA" in tension.upper():
                    tension_short = "HTA"
                elif "BT" in tension.upper():
                    tension_short = "BT"

            # segment_label = libellé site complet, sinon turpe long, sinon tension
            segment_label_parts = []
            if site:
                segment_label_parts.append(site)
            if turpe and turpe_short is None:
                segment_label_parts.append(f"TURPE: {turpe}")
            segment_label = " | ".join(segment_label_parts)[:200] if segment_label_parts else (site or turpe or tension)

            # Trouver/créer segment
            seg_key = (doc.id, segment_code)
            segment = segments_cache.get(seg_key)
            if segment is None:
                segment = BpuSegment(
                    document_id=doc.id,
                    segment_type=segment_type,
                    segment_code=segment_code[:50],  # safety on VARCHAR(50)
                    segment_label=segment_label,
                    tension_category=tension_short,
                    turpe_tariff=turpe_short,
                    usage_label=(site[:100] if site and segment_type == SEGMENT_TYPE_USAGE else None),
                )
                session.add(segment)
                session.flush()
                segments_cache[seg_key] = segment
                counters["segments"] += 1

            # Trouver/créer période
            per_key = (segment.id, period_code)
            period = periods_cache.get(per_key)
            if period is None:
                period = BpuTimePeriod(
                    segment_id=segment.id,
                    period_code=period_code,
                    period_label=period_raw,
                )
                session.add(period)
                session.flush()
                periods_cache[per_key] = period
                counters["periods"] += 1

            # Composantes : créer 1 par valeur non-null
            composantes = [
                ("Prix fourniture", "Unité fourniture", COMPONENT_FOURNITURE),
                ("CEE", "Unité CEE", COMPONENT_CEE),
                ("Option ENR / GO", "Unité option", COMPONENT_GO),
                ("Mécanisme / prix capacité", "Unité capacité", COMPONENT_CAPACITE),
            ]
            for value_col, unit_col, comp_type in composantes:
                price_value = _f(row.get(value_col))
                if price_value is None:
                    continue
                # Éviter doublons sur (period, component_type) — via set local
                # robuste au batching SQLAlchemy (period.components peut ne pas
                # voir les inserts pas encore flushés)
                dup_key = (period.id, comp_type)
                if dup_key in seen_components:
                    logger.warning(
                        "Composante deja vue, ignoree : period_id=%s comp=%s "
                        "(PDF=%s site=%s poste=%s)",
                        period.id, comp_type, pdf_filename, site, period_raw,
                    )
                    counters["skipped_prices"] += 1
                    continue
                seen_components.add(dup_key)
                unit = _s(row.get(unit_col)) or "EUR/MWh"
                comp = BpuPriceComponent(
                    period_id=period.id,
                    component_type=comp_type,
                    component_label=value_col,
                    price_value=price_value,
                    price_unit=unit,
                    is_negative=price_value < 0,
                    notes=notes,
                )
                # price_value_eur_per_mwh : laisse None pour l'instant, on peut
                # le calculer plus tard via colonnes c€/kWh normalisées du xlsx
                u = unit.lower().replace(" ", "")
                if "c€/kwh" in u or "ce/kwh" in u or "ct€/kwh" in u:
                    comp.price_value_eur_per_mwh = price_value * 10.0
                elif "€/mwh" in u or "eur/mwh" in u:
                    comp.price_value_eur_per_mwh = price_value
                session.add(comp)
                counters["components"] += 1

            # Abonnement mensuel sur la même ligne → BpuFixedCharge lié au segment
            abo_value = _f(row.get("Abonnement mensuel"))
            if abo_value is not None and abo_value > 0:
                charge = BpuFixedCharge(
                    document_id=doc.id,
                    segment_id=segment.id,
                    charge_type="abonnement",
                    charge_label=f"Abonnement {segment_code}",
                    charge_value=abo_value,
                    charge_unit=_s(row.get("Unité abonnement")) or "€HT/mois",
                    charge_value_eur_per_month=abo_value,
                    notes=notes,
                )
                session.add(charge)
                counters["charges"] += 1

        session.commit()

        # --- 3. Surcouts fixes (depuis Surcouts_fixes) ---
        for _, row in charges_df.iterrows():
            pdf_filename = _s(row.get("Source fichier"))
            doc = docs_by_filename.get(pdf_filename)
            if doc is None:
                counters["skipped_charges"] += 1
                continue
            libelle = _s(row.get("Libellé"))
            montant = _f(row.get("Montant"))
            if montant is None:
                counters["skipped_charges"] += 1
                continue
            applicable_from, applicable_to = _parse_applicable_period(_s(row.get("Période concernée")))
            charge = BpuFixedCharge(
                document_id=doc.id,
                segment_id=None,
                charge_type=_map_charge_type(libelle),
                charge_label=libelle,
                charge_value=montant,
                charge_unit=_s(row.get("Unité")) or "€HT/mois",
                charge_value_eur_per_month=montant,
                applicable_from=applicable_from,
                applicable_to=applicable_to,
                notes=_s(row.get("Notes")),
            )
            session.add(charge)
            counters["charges"] += 1

        # Tag Controle_qualite sur tous les docs
        if controle_notes:
            for doc in docs_by_filename.values():
                doc.extraction_notes = (
                    (doc.extraction_notes or "") + "\n\n--- Controle qualite global ---\n" + controle_notes
                )[:2000]

        session.commit()

    # Reporting
    print()
    print("=" * 60)
    print("RÉSUMÉ IMPORT BPU XLSX")
    print("=" * 60)
    for k, v in counters.items():
        print(f"  {k:<20} : {v}")
    print()
    return counters


def main() -> int:
    parser = argparse.ArgumentParser(description="Import BPU depuis xlsx canonique")
    parser.add_argument("--xlsx", default=str(DEFAULT_XLSX), help=f"Chemin du xlsx (défaut : {DEFAULT_XLSX})")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Supprime les BpuDocument déjà en BDD pour les PDFs listés avant de ré-importer.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        counters = import_xlsx(Path(args.xlsx), force=args.force)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Import BPU xlsx échoué")
        print(f"Erreur : {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    return 0 if counters["errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
