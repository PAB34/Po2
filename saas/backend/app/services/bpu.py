"""
Service couche métier pour l'ingestion des BPU (Bordereaux de Prix Unitaires).

Pipeline d'import (3 étages) :

1. Identification : parser le nom de fichier → {supplier, year, MS, lot, avenant}
2. Extraction texte : pdftotext (rapide, exact pour PDFs textuels) → fallback OCR
   (tesseract + pdf2image) pour les scans
3. Parsing : extraire les triplets (segment, période, composante) + frais fixes
   à partir du texte. Tolérant aux variations de format. Si la confiance est
   trop faible, on enregistre quand même le doc avec status=`ocr_review` pour
   permettre une saisie corrective côté UI plus tard.

Ce service est utilisé par `app.scripts.import_bpu_documents` et par
l'endpoint admin POST /api/bpu/import.
"""
from __future__ import annotations

import hashlib
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.bpu import (
    BpuDocument,
    BpuFixedCharge,
    BpuPriceComponent,
    BpuSegment,
    BpuTimePeriod,
    CHARGE_ABONNEMENT,
    CHARGE_AUTRE,
    CHARGE_BRANCHEMENT_PROVISOIRE,
    CHARGE_CONTRAT_TEMPORAIRE,
    COMPONENT_CAPACITE,
    COMPONENT_CEE,
    COMPONENT_FOURNITURE,
    COMPONENT_GO,
    COMPONENT_RENOUVELABLE,
    EXTRACTION_ERROR,
    EXTRACTION_OCR_OK,
    EXTRACTION_OCR_REVIEW,
    EXTRACTION_OK,
    EXTRACTION_PENDING,
    PERIOD_BASE,
    PERIOD_HC,
    PERIOD_HCE,
    PERIOD_HCH,
    PERIOD_HP,
    PERIOD_HPE,
    PERIOD_HPH,
    PERIOD_POINTE,
    SEGMENT_TYPE_SITE,
    SEGMENT_TYPE_TENSION,
    SEGMENT_TYPE_USAGE,
)

logger = logging.getLogger(__name__)


# Répertoire par défaut côté conteneur.
# En prod, le dépôt complet est monté en read-only sur /workspace via le compose,
# donc les PDFs des BPU sont accessibles à ce chemin.
DEFAULT_BPU_SOURCE_DIR = Path(
    "/workspace/saas/energie/HERAULT ENERGIE/HISTORIQUE BPU"
)


# ---------------------------------------------------------------------------
# Dataclasses internes pour la phase de parsing
# ---------------------------------------------------------------------------


@dataclass
class ParsedComponent:
    component_type: str
    price_value: float
    price_unit: str
    component_label: str | None = None
    price_value_eur_per_mwh: float | None = None
    is_negative: bool = False
    notes: str | None = None


@dataclass
class ParsedPeriod:
    period_code: str
    period_label: str | None = None
    components: list[ParsedComponent] = field(default_factory=list)


@dataclass
class ParsedSegment:
    segment_type: str
    segment_code: str
    segment_label: str | None = None
    tension_category: str | None = None
    turpe_tariff: str | None = None
    usage_label: str | None = None
    notes: str | None = None
    periods: list[ParsedPeriod] = field(default_factory=list)


@dataclass
class ParsedFixedCharge:
    charge_type: str
    charge_value: float
    charge_unit: str
    charge_label: str | None = None
    charge_value_eur_per_month: float | None = None
    notes: str | None = None


@dataclass
class ParsedBpu:
    supplier: str
    valid_year: int
    lot_number: int
    market_subsequent: int | None = None
    amendment_number: int | None = None
    amendment_label: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    signature_date: date | None = None
    segments: list[ParsedSegment] = field(default_factory=list)
    fixed_charges: list[ParsedFixedCharge] = field(default_factory=list)
    extraction_method: str = "pdftotext"
    extraction_confidence: float | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Identification du fichier
# ---------------------------------------------------------------------------

# Regex modulaires pour extraire les composants du nom de fichier.
# On évite \b autour des séparateurs car `_` est un caractère "word" en regex
# et bloquerait les matchs sur "EDF_MS1" ou "LOT_1".
_RX_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_RX_LOT = re.compile(r"LOT[\s_-]*n?[°]?[\s_-]*(\d)(?!\d)", re.IGNORECASE)
_RX_MS = re.compile(r"MS[\s_-]*n?[°]?[\s_-]*(\d)(?!\d)", re.IGNORECASE)
_RX_AVENANT = re.compile(r"AVENANT[\s_-]*(\d{1,2})", re.IGNORECASE)
_RX_SUPPLIER_EDF = re.compile(r"(?<![A-Za-z])EDF(?![A-Za-z])", re.IGNORECASE)
_RX_SUPPLIER_ENGIE = re.compile(r"(?<![A-Za-z])ENGIE(?![A-Za-z])", re.IGNORECASE)


def parse_filename_metadata(filename: str) -> dict[str, int | str | None]:
    """Extrait du nom de fichier : supplier / valid_year / lot / MS / avenant.

    Tolérant aux variations de format (espaces, underscores, casse,
    présence/absence de chaque champ). Renvoie un dict avec des valeurs
    `None` quand un champ n'est pas trouvable — l'appelant décidera si
    c'est acceptable ou si on doit marquer le fichier en erreur.

    Exemples :
      - "EDF_MS1_LOT_1_AVENANT_6_BPU_2025.pdf" → EDF/2025/1/MS1/avenant6
      - "2025_18_MS1_BPU_ENGIE_LOT_1.pdf"      → ENGIE/2025/1/MS1
      - "BPU MS n°1 lot n°1 EDF 2023 signé.pdf" → EDF/2023/1/MS1
      - "LOT3 BPU_MS3_N°20-28_EDF_2021-2022 prix ferme.pdf" → EDF/2021/3/MS3/label=prix ferme
    """
    name = filename.rsplit(".", 1)[0]

    # Supplier
    supplier: str | None = None
    if _RX_SUPPLIER_ENGIE.search(name):
        supplier = "ENGIE"
    elif _RX_SUPPLIER_EDF.search(name):
        supplier = "EDF"

    # Year (prend la première année 20xx trouvée — pour "2021-2022", on garde 2021)
    year: int | None = None
    m = _RX_YEAR.search(name)
    if m:
        year = int(m.group(1))

    # Lot
    lot: int | None = None
    m = _RX_LOT.search(name)
    if m:
        lot = int(m.group(1))

    # MS (Marché Subséquent)
    ms: int | None = None
    m = _RX_MS.search(name)
    if m:
        ms = int(m.group(1))

    # Avenant
    avenant: int | None = None
    m = _RX_AVENANT.search(name)
    if m:
        avenant = int(m.group(1))

    # Label libre (V2, achat clic, prix ferme, ...)
    label: str | None = None
    for marker in ("achat clic", "prix ferme", "V2", "signé"):
        if marker.lower() in name.lower():
            label = marker
            break

    return {
        "supplier": supplier,
        "valid_year": year,
        "lot_number": lot,
        "market_subsequent": ms,
        "amendment_number": avenant,
        "amendment_label": label,
    }


# ---------------------------------------------------------------------------
# Extraction de texte
# ---------------------------------------------------------------------------


def _which_pdftotext() -> str | None:
    """Trouve la commande pdftotext (poppler-utils)."""
    return shutil.which("pdftotext")


def extract_text_pdftotext(pdf_path: Path, *, layout: bool = True) -> str:
    """Lance `pdftotext -layout` sur le PDF et retourne le texte concaténé.

    Lève FileNotFoundError si pdftotext n'est pas installé.
    Retourne "" si l'extraction échoue silencieusement.
    """
    binary = _which_pdftotext()
    if not binary:
        raise FileNotFoundError(
            "pdftotext (poppler-utils) n'est pas installé. Ajouter au Dockerfile."
        )

    cmd = [binary]
    if layout:
        cmd.append("-layout")
    cmd.extend(["-enc", "UTF-8", str(pdf_path), "-"])
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        logger.warning("pdftotext timeout sur %s", pdf_path)
        return ""
    if result.returncode != 0:
        logger.warning(
            "pdftotext rc=%s sur %s : %s",
            result.returncode, pdf_path, result.stderr.decode(errors="replace")[:200],
        )
    try:
        return result.stdout.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def extract_text_ocr(pdf_path: Path, *, lang: str = "fra", dpi: int = 300) -> str:
    """Convertit le PDF en images puis lance tesseract page par page.

    Nécessite `pdf2image` (Python) + `poppler-utils` (système) + `tesseract-ocr`.
    Renvoie le texte concaténé de toutes les pages. Retourne "" si échec.
    """
    try:
        from pdf2image import convert_from_path  # type: ignore
        import pytesseract  # type: ignore
    except ImportError as exc:
        logger.error("OCR indisponible : %s", exc)
        return ""

    try:
        images = convert_from_path(str(pdf_path), dpi=dpi)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Conversion PDF→image échouée pour %s : %s", pdf_path, exc)
        return ""

    pages = []
    for idx, img in enumerate(images, start=1):
        try:
            text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
            pages.append(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tesseract page %d échouée pour %s : %s", idx, pdf_path, exc)
            pages.append("")
    return "\n\n--- PAGE ---\n\n".join(pages)


def _looks_textual(text: str, *, min_chars: int = 200, min_alpha_ratio: float = 0.5) -> bool:
    """Heuristique : décide si la sortie pdftotext est exploitable.

    Si pdftotext renvoie un texte court ou principalement composé de bruit
    (peu de caractères alphabétiques), on bascule en OCR.
    """
    if len(text) < min_chars:
        return False
    alpha = sum(1 for c in text if c.isalpha())
    if alpha / max(1, len(text)) < min_alpha_ratio:
        return False
    # Indices de texte de BPU : au moins une mention de € ou MWh ou kWh
    lowered = text.lower()
    return any(marker in lowered for marker in ("€", "mwh", "kwh", "tarif", "fourniture"))


# ---------------------------------------------------------------------------
# Parsing du texte → ParsedBpu
# ---------------------------------------------------------------------------

# Normalisation des codes de poste (gère les variantes)
_PERIOD_NORMALIZATION: dict[str, str] = {
    "BASE": PERIOD_BASE,
    "POINTE": PERIOD_POINTE,
    "HPH": PERIOD_HPH,
    "HCH": PERIOD_HCH,
    "HPE": PERIOD_HPE,
    "HCE": PERIOD_HCE,
    "HPB": PERIOD_HPE,  # heures pleines basse saison = HPE
    "HCB": PERIOD_HCE,  # heures creuses basse saison = HCE
    "HP": PERIOD_HP,
    "HC": PERIOD_HC,
    "HEURES PLEINES HIVER": PERIOD_HPH,
    "HEURES CREUSES HIVER": PERIOD_HCH,
    "HEURES PLEINES ETE": PERIOD_HPE,
    "HEURES CREUSES ETE": PERIOD_HCE,
    "HEURES PLEINES": PERIOD_HP,
    "HEURES CREUSES": PERIOD_HC,
    "HEURES DE POINTE": PERIOD_POINTE,
}

_COMPONENT_KEYWORDS: dict[str, str] = {
    "fourniture": COMPONENT_FOURNITURE,
    "capacité": COMPONENT_CAPACITE,
    "capacite": COMPONENT_CAPACITE,
    "cee": COMPONENT_CEE,
    "garanties": COMPONENT_GO,
    "garantie d'origine": COMPONENT_GO,
    "garantie origine": COMPONENT_GO,
    "go": COMPONENT_GO,
    "renouvelable": COMPONENT_RENOUVELABLE,
}

# Repérage de blocs segment (TURPE / site / usage)
_RX_TURPE = re.compile(
    r"\b(CU4|MU4|MUDT|MUDTD|CUD|CU|LU|C[1-5]|EP|BT\s*≤?\s*36\s*kVA|BT\s*>\s*36\s*kVA|HTA)\b",
    re.IGNORECASE,
)
_RX_USAGE = re.compile(
    r"\b(éclairage public|eclairage public|bâtiment|batiment|bornes)\b",
    re.IGNORECASE,
)

# Détection prix : nombre avec , ou . décimal — tolère les espaces dans les milliers
_RX_PRICE = re.compile(r"[-+]?\d{1,4}(?:[  ]\d{3})*(?:[.,]\d{1,4})?")

_COMPONENT_HEADER_ALIASES: tuple[tuple[str, str], ...] = (
    ("fourniture", COMPONENT_FOURNITURE),
    ("energie", COMPONENT_FOURNITURE),
    ("capac", COMPONENT_CAPACITE),
    ("cee", COMPONENT_CEE),
    ("garantie", COMPONENT_GO),
    ("origine", COMPONENT_GO),
    ("go", COMPONENT_GO),
    ("renouvelable", COMPONENT_RENOUVELABLE),
)


def _to_float(token: str) -> float | None:
    """Convertit '12,3', '12.34', '1 234,56' → float ou None."""
    token = token.replace(" ", " ").strip()
    token = token.replace(" ", "").replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return None


def _normalize_unit_to_eur_per_mwh(value: float, unit: str) -> float | None:
    """Convertit en EUR/MWh selon l'unité d'origine.

    Conventions :
      - c€/kWh HTT ou c€/kWh → EUR/MWh × 10  (1 c€/kWh = 10 €/MWh)
      - €/MWh ou €HTT/MWh    → identique
      - €/kWh                 → × 1000
    Renvoie None si l'unité n'est pas reconnue.
    """
    u = unit.lower().replace(" ", "")
    if "c€/kwh" in u or "ce/kwh" in u or "centime/kwh" in u or "ct€/kwh" in u:
        return value * 10.0
    if "€/kwh" in u or "eur/kwh" in u:
        return value * 1000.0
    if "€/mwh" in u or "€htt/mwh" in u or "eur/mwh" in u or "ehtt/mwh" in u:
        return value
    return None


def _detect_default_unit(text: str) -> str:
    text_lower = text.lower()
    if "câ‚¬/kwh" in text_lower or "centime" in text_lower:
        return "câ‚¬/kWh HTT"
    if "â‚¬htt/mwh" in text_lower or "â‚¬/mwh" in text_lower:
        return "â‚¬HTT/MWh"
    return "â‚¬/MWh"


def _estimate_extraction_confidence(segments: list[ParsedSegment]) -> float:
    n_components = sum(len(p.components) for s in segments for p in s.periods)
    n_segments = len(segments)
    if n_segments == 0:
        return 0.0
    if n_components < 5:
        return 0.25
    if n_components < 20:
        return 0.55
    if n_components < 50:
        return 0.75
    return 0.9


def parse_bpu_text(text: str, metadata: dict, *, extraction_method: str) -> ParsedBpu:
    """Parse le texte brut d'un BPU en une structure normalisée.

    Approche tolérante : on identifie les blocs (segment, période, composante)
    par des heuristiques regex et on enregistre les triplets reconnus. Tout
    ce qui n'est pas reconnu reste dans `raw_text` côté BpuDocument.

    Une confiance est estimée d'après la couverture (nb segments × nb postes
    extraits vs attendu typique). Si la confiance < 0.4, l'appelant marque le
    document comme `ocr_review`.
    """
    parsed = ParsedBpu(
        supplier=str(metadata.get("supplier") or "INCONNU"),
        valid_year=int(metadata.get("valid_year") or 0),
        lot_number=int(metadata.get("lot_number") or 0),
        market_subsequent=metadata.get("market_subsequent"),
        amendment_number=metadata.get("amendment_number"),
        amendment_label=metadata.get("amendment_label"),
        extraction_method=extraction_method,
    )

    # Pas de texte → impossible de parser
    if not text or not text.strip():
        parsed.extraction_confidence = 0.0
        parsed.notes = "Texte source vide"
        return parsed

    # Détection unité globale par texte (heuristique simple)
    text_lower = text.lower()
    if "c€/kwh" in text_lower or "centime" in text_lower:
        default_unit = "c€/kWh HTT"
    elif "€htt/mwh" in text_lower or "€/mwh" in text_lower:
        default_unit = "€HTT/MWh"
    else:
        default_unit = "€/MWh"

    # 1. Extraire les frais fixes (abonnements et branchements) par patterns
    parsed.fixed_charges.extend(_extract_fixed_charges(text))

    # 2. Extraire les segments + postes + composantes
    parsed.segments.extend(_extract_segments(text, default_unit=default_unit))

    # 3. Date de signature (best-effort)
    parsed.signature_date = _extract_signature_date(text)

    # 4. Confiance : combien de segments et combien de prix extraits
    n_components = sum(
        len(p.components) for s in parsed.segments for p in s.periods
    )
    n_segments = len(parsed.segments)
    # Heuristique : 5 segments × 4 postes × 4 composantes ≈ 80 prix attendus
    # On considère 30 prix = forte confiance
    if n_segments == 0:
        parsed.extraction_confidence = 0.0
    elif n_components < 5:
        parsed.extraction_confidence = 0.25
    elif n_components < 20:
        parsed.extraction_confidence = 0.55
    elif n_components < 50:
        parsed.extraction_confidence = 0.75
    else:
        parsed.extraction_confidence = 0.9

    return parsed


def _extract_signature_date(text: str) -> date | None:
    """Repère une date au format DD/MM/YYYY ou DD-MM-YYYY."""
    m = re.search(r"\b(0?[1-9]|[12]\d|3[01])[/\-](0?[1-9]|1[0-2])[/\-](20\d{2})\b", text)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _extract_fixed_charges(text: str) -> list[ParsedFixedCharge]:
    """Recherche : abonnement mensuel, branchement provisoire, contrat temporaire."""
    charges: list[ParsedFixedCharge] = []

    # Patterns approximatifs — on cherche le mot-clé sur une ligne et un nombre proche
    patterns: list[tuple[str, str]] = [
        (r"abonnement\s+mensuel", CHARGE_ABONNEMENT),
        (r"branchement\s+provisoire", CHARGE_BRANCHEMENT_PROVISOIRE),
        (r"contrat\s+temporaire", CHARGE_CONTRAT_TEMPORAIRE),
    ]
    for pattern, ctype in patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            # Cherche un nombre dans la ligne suivante (jusqu'à 200 caractères)
            window = text[m.end(): m.end() + 200]
            price_m = _RX_PRICE.search(window)
            if not price_m:
                continue
            val = _to_float(price_m.group(0))
            if val is None or val <= 0:
                continue
            charges.append(
                ParsedFixedCharge(
                    charge_type=ctype,
                    charge_value=val,
                    charge_unit="€HT/mois",
                    charge_label=m.group(0),
                    charge_value_eur_per_month=val,
                )
            )
    return charges


def _detect_segment_code(line: str) -> str | None:
    """Detect the most useful BPU segment code on a line."""
    up = line.upper()
    for code in ("MUDTD", "MUDT", "CU4", "MU4", "CUD", "CU", "LU", "C1", "C2", "C3", "C4", "C5", "EP"):
        if re.search(rf"\b{code}\b", up):
            return code
    if re.search(r"\bBT\s*(?:<=|≤)?\s*36\s*KVA\b", up):
        return "BT <= 36 KVA"
    if re.search(r"\bBT\s*>\s*36\s*KVA\b", up):
        return "BT > 36 KVA"
    if re.search(r"\bHTA\b", up):
        return "HTA"
    return None


def _extract_segments(text: str, *, default_unit: str) -> list[ParsedSegment]:
    """Découpe le texte en blocs par segment tarifaire et en tire les postes.

    Stratégie minimaliste mais robuste : on traite le texte ligne par ligne,
    on repère les en-têtes de segment (TURPE / usage), puis pour chaque ligne
    suivante on essaie d'extraire (poste, prix). On laisse les composantes
    sur un poste par défaut "fourniture" tant qu'on n'a pas mieux pour le MVP.

    Suivi avec validation visuelle par l'utilisateur → on enrichira après.
    """
    segments: list[ParsedSegment] = []
    current_segment: ParsedSegment | None = None
    current_period: ParsedPeriod | None = None
    current_table_components: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # En-tête de segment
        segment_code = _detect_segment_code(line)
        m_usage = _RX_USAGE.search(line) if not segment_code else None

        if segment_code:
            code = segment_code
            # Si on a déjà un segment avec ce code, ne pas dupliquer
            existing = next((s for s in segments if s.segment_code == code), None)
            if existing is not None:
                current_segment = existing
            else:
                current_segment = ParsedSegment(
                    segment_type=SEGMENT_TYPE_SITE if code.startswith("C") else SEGMENT_TYPE_TENSION,
                    segment_code=code,
                    segment_label=line[:200],
                    tension_category="HTA" if code in ("C1", "C2", "C3") or "HTA" in line.upper() else "BT",
                    turpe_tariff=code if code.startswith("C") else None,
                )
                segments.append(current_segment)
            current_period = None
            header_components = _detect_component_header(line)
            if header_components:
                current_table_components = header_components
            continue

        if m_usage:
            usage = m_usage.group(1).lower()
            code = "ECLAIRAGE" if "éclairage" in usage or "eclairage" in usage else "USAGE"
            if "bornes" in usage:
                code = "BORNES"
            elif "bâtiment" in usage or "batiment" in usage:
                code = "BATIMENT"
            existing = next((s for s in segments if s.segment_code == code), None)
            if existing is not None:
                current_segment = existing
            else:
                current_segment = ParsedSegment(
                    segment_type=SEGMENT_TYPE_USAGE,
                    segment_code=code,
                    segment_label=line[:200],
                    usage_label=usage,
                )
                segments.append(current_segment)
            current_period = None
            header_components = _detect_component_header(line)
            if header_components:
                current_table_components = header_components
            continue

        # Pas dans un segment encore → ignorer
        if current_segment is None:
            continue

        header_components = _detect_component_header(line)
        if header_components:
            current_table_components = header_components

        # Détection d'un code de poste sur la ligne (avec ou sans prix)
        period_match = _detect_period(line)
        if period_match is not None:
            current_period = next(
                (p for p in current_segment.periods if p.period_code == period_match),
                None,
            )
            if current_period is None:
                current_period = ParsedPeriod(period_code=period_match, period_label=line[:80])
                current_segment.periods.append(current_period)

        # Extraction des prix sur la ligne (peu importe le poste : on les rattache au courant)
        if current_period is not None:
            components = list(_extract_components_from_line(line))
            if not components and current_table_components:
                components = _extract_components_from_table_line(line, current_table_components)
            for component_type, value in components:
                # Évite de pousser plusieurs fois la même composante
                if any(c.component_type == component_type for c in current_period.components):
                    continue
                current_period.components.append(
                    ParsedComponent(
                        component_type=component_type,
                        price_value=value,
                        price_unit=default_unit,
                        price_value_eur_per_mwh=_normalize_unit_to_eur_per_mwh(value, default_unit),
                    )
                )

    return segments


def _detect_component_header(line: str) -> list[str]:
    """Detect a table header containing ordered price components."""
    lower = line.lower()
    hits: list[tuple[int, str]] = []
    for alias, component in _COMPONENT_HEADER_ALIASES:
        idx = lower.find(alias)
        if idx >= 0:
            hits.append((idx, component))
    if len(hits) < 2:
        return []

    ordered: list[str] = []
    seen: set[str] = set()
    for _, component in sorted(hits, key=lambda item: item[0]):
        if component not in seen:
            ordered.append(component)
            seen.add(component)
    return ordered


def _extract_components_from_table_line(line: str, component_order: list[str]) -> list[tuple[str, float]]:
    """Map numeric cells in a table row to a previously detected component order."""
    period_code = _detect_period(line)
    if period_code:
        m = re.search(rf"\b{period_code}\b", line, flags=re.IGNORECASE)
        if m:
            line = line[m.end():]

    values: list[float] = []
    for m in _RX_PRICE.finditer(line):
        value = _to_float(m.group(0))
        if value is None:
            continue
        # Avoid mapping years or page numbers to prices.
        if abs(value) >= 2000:
            continue
        values.append(value)

    if not values:
        return []

    if len(values) > len(component_order):
        values = values[:len(component_order)]

    return list(zip(component_order[: len(values)], values, strict=False))


def _clean_table_cell(value: object) -> str:
    return str(value or "").replace("\n", " ").strip()


def _extract_components_from_table_cells(cells: list[str], component_order: list[str]) -> list[tuple[str, float]]:
    return _extract_components_from_table_line(" ".join(cells), component_order)


def extract_segments_pdfplumber(pdf_path: Path, *, default_unit: str) -> list[ParsedSegment]:
    """Extract BPU price tables with pdfplumber when available.

    This is intentionally optional: the backend image installs pdfplumber, but
    the parser can still run through pdftotext/OCR in environments where the
    dependency is absent.
    """
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return []

    segments: list[ParsedSegment] = []
    current_segment: ParsedSegment | None = None
    current_table_components: list[str] = []

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    for raw_cells in table:
                        cells = [_clean_table_cell(cell) for cell in raw_cells]
                        cells = [cell for cell in cells if cell]
                        if not cells:
                            continue
                        line = " ".join(cells)

                        segment_code = _detect_segment_code(line)
                        if segment_code:
                            existing = next((s for s in segments if s.segment_code == segment_code), None)
                            if existing is None:
                                existing = ParsedSegment(
                                    segment_type=SEGMENT_TYPE_SITE if segment_code.startswith("C") else SEGMENT_TYPE_TENSION,
                                    segment_code=segment_code,
                                    segment_label=line[:200],
                                    tension_category="HTA" if segment_code in ("C1", "C2", "C3", "HTA") else "BT",
                                    turpe_tariff=segment_code if segment_code.startswith("C") else None,
                                )
                                segments.append(existing)
                            current_segment = existing

                        header_components = _detect_component_header(line)
                        if header_components:
                            current_table_components = header_components
                            continue

                        if current_segment is None or not current_table_components:
                            continue

                        period_code = _detect_period(line)
                        if period_code is None:
                            continue

                        period = next((p for p in current_segment.periods if p.period_code == period_code), None)
                        if period is None:
                            period = ParsedPeriod(period_code=period_code, period_label=line[:80])
                            current_segment.periods.append(period)

                        for component_type, value in _extract_components_from_table_cells(cells, current_table_components):
                            if any(c.component_type == component_type for c in period.components):
                                continue
                            period.components.append(
                                ParsedComponent(
                                    component_type=component_type,
                                    price_value=value,
                                    price_unit=default_unit,
                                    price_value_eur_per_mwh=_normalize_unit_to_eur_per_mwh(value, default_unit),
                                )
                            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Extraction pdfplumber échouée pour %s : %s", pdf_path, exc)
        return []

    return segments


def _merge_segments(base: list[ParsedSegment], extra: list[ParsedSegment]) -> list[ParsedSegment]:
    for extra_segment in extra:
        segment = next((s for s in base if s.segment_code == extra_segment.segment_code), None)
        if segment is None:
            base.append(extra_segment)
            continue
        for extra_period in extra_segment.periods:
            period = next((p for p in segment.periods if p.period_code == extra_period.period_code), None)
            if period is None:
                segment.periods.append(extra_period)
                continue
            for extra_component in extra_period.components:
                if any(c.component_type == extra_component.component_type for c in period.components):
                    continue
                period.components.append(extra_component)
    return base


def _detect_period(line: str) -> str | None:
    """Repère un code de poste horosaisonnier dans la ligne."""
    up = line.upper()
    # Codes courts (cherché en mot entier)
    for code in ("HPH", "HCH", "HPE", "HCE", "HPB", "HCB", "BASE", "POINTE", "HP", "HC"):
        if re.search(rf"\b{code}\b", up):
            return _PERIOD_NORMALIZATION.get(code, code)
    # Codes verbeux
    for verbose, mapped in _PERIOD_NORMALIZATION.items():
        if len(verbose) > 3 and verbose in up:
            return mapped
    return None


def _extract_components_from_line(line: str) -> Iterable[tuple[str, float]]:
    """Repère des couples (composante, prix) sur une ligne.

    Patterns supportés (best-effort) :
      - "Fourniture : 75,29"
      - "Capacité 0,52"
      - "CEE 10,59"
      - "GO / Renouvelable 1,67"
      - Une ligne avec 1 seul prix → considéré comme fourniture (fallback)
    """
    found: list[tuple[str, float]] = []
    line_lower = line.lower()

    for keyword, component in _COMPONENT_KEYWORDS.items():
        if keyword in line_lower:
            # Cherche un nombre proche de ce mot-clé (après ou avant)
            idx = line_lower.find(keyword)
            window = line[max(0, idx - 5): idx + len(keyword) + 80]
            m = _RX_PRICE.search(window[len(keyword) + 5:]) or _RX_PRICE.search(window)
            if not m:
                continue
            val = _to_float(m.group(0))
            if val is not None:
                found.append((component, val))

    if found:
        return found

    # Fallback : 1 ou 2 prix sur la ligne sans label clair → ne rien deviner
    return []


# ---------------------------------------------------------------------------
# Hash + helpers
# ---------------------------------------------------------------------------


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Persistance
# ---------------------------------------------------------------------------


def find_existing_document(
    session: Session,
    *,
    supplier: str,
    valid_year: int,
    market_subsequent: int | None,
    lot_number: int,
    amendment_number: int | None,
) -> BpuDocument | None:
    return (
        session.query(BpuDocument)
        .filter(
            BpuDocument.supplier == supplier,
            BpuDocument.valid_year == valid_year,
            BpuDocument.market_subsequent == market_subsequent,
            BpuDocument.lot_number == lot_number,
            BpuDocument.amendment_number == amendment_number,
        )
        .one_or_none()
    )


def persist_parsed_bpu(
    session: Session,
    parsed: ParsedBpu,
    *,
    raw_text: str,
    pdf_filename: str,
    pdf_relative_path: str | None,
    pdf_sha256: str,
    extraction_status: str,
    extraction_notes: str | None,
    imported_by_user_id: int | None = None,
    force: bool = False,
) -> BpuDocument:
    """Crée (ou met à jour si force=True) le BpuDocument et ses enfants.

    Si le doc existe déjà :
      - sans `force` → on lève un appel à update-existing qui actualise raw_text
        et le status mais NE TOUCHE PAS les segments/composantes (préserve les
        corrections manuelles).
      - avec `force` → on remplace tout (delete cascade puis re-insert).
    """
    existing = find_existing_document(
        session,
        supplier=parsed.supplier,
        valid_year=parsed.valid_year,
        market_subsequent=parsed.market_subsequent,
        lot_number=parsed.lot_number,
        amendment_number=parsed.amendment_number,
    )

    if existing is not None and not force:
        # On rafraîchit raw_text + meta extraction sans toucher aux relations
        existing.raw_text = raw_text
        existing.extraction_status = extraction_status
        existing.extraction_method = parsed.extraction_method
        existing.extraction_confidence = parsed.extraction_confidence
        existing.extraction_notes = extraction_notes
        existing.pdf_sha256 = pdf_sha256
        session.flush()
        return existing

    if existing is not None and force:
        # Supprime les segments (cascade vers periods + components) et fixed charges
        session.delete(existing)
        session.flush()

    doc = BpuDocument(
        supplier=parsed.supplier,
        valid_year=parsed.valid_year,
        valid_from=parsed.valid_from,
        valid_to=parsed.valid_to,
        market_subsequent=parsed.market_subsequent,
        lot_number=parsed.lot_number,
        amendment_number=parsed.amendment_number,
        amendment_label=parsed.amendment_label,
        pdf_filename=pdf_filename,
        pdf_relative_path=pdf_relative_path,
        pdf_sha256=pdf_sha256,
        signature_date=parsed.signature_date,
        extraction_status=extraction_status,
        extraction_method=parsed.extraction_method,
        extraction_confidence=parsed.extraction_confidence,
        extraction_notes=extraction_notes,
        raw_text=raw_text,
        imported_by_user_id=imported_by_user_id,
    )
    session.add(doc)
    session.flush()  # pour obtenir doc.id

    for ps in parsed.segments:
        seg = BpuSegment(
            document_id=doc.id,
            segment_type=ps.segment_type,
            segment_code=ps.segment_code,
            segment_label=ps.segment_label,
            tension_category=ps.tension_category,
            turpe_tariff=ps.turpe_tariff,
            usage_label=ps.usage_label,
            notes=ps.notes,
        )
        session.add(seg)
        session.flush()
        for pp in ps.periods:
            period = BpuTimePeriod(
                segment_id=seg.id,
                period_code=pp.period_code,
                period_label=pp.period_label,
            )
            session.add(period)
            session.flush()
            for pc in pp.components:
                comp = BpuPriceComponent(
                    period_id=period.id,
                    component_type=pc.component_type,
                    component_label=pc.component_label,
                    price_value=pc.price_value,
                    price_unit=pc.price_unit,
                    price_value_eur_per_mwh=pc.price_value_eur_per_mwh,
                    is_negative=pc.is_negative,
                    notes=pc.notes,
                )
                session.add(comp)

    for fc in parsed.fixed_charges:
        charge = BpuFixedCharge(
            document_id=doc.id,
            charge_type=fc.charge_type,
            charge_label=fc.charge_label,
            charge_value=fc.charge_value,
            charge_unit=fc.charge_unit,
            charge_value_eur_per_month=fc.charge_value_eur_per_month,
            notes=fc.notes,
        )
        session.add(charge)

    session.flush()
    return doc


# ---------------------------------------------------------------------------
# Pipeline orchestrant
# ---------------------------------------------------------------------------


@dataclass
class FileImportResult:
    filename: str
    status: str  # ok | ocr_ok | ocr_review | error | skipped
    document_id: int | None = None
    segments_count: int = 0
    components_count: int = 0
    fixed_charges_count: int = 0
    extraction_method: str | None = None
    extraction_confidence: float | None = None
    error: str | None = None


def import_pdf(
    session: Session,
    pdf_path: Path,
    *,
    source_root: Path | None = None,
    enable_ocr: bool = True,
    force: bool = False,
    imported_by_user_id: int | None = None,
) -> FileImportResult:
    """Importe un seul PDF. Renvoie un résultat structuré."""
    filename = pdf_path.name
    rel_path: str | None = None
    if source_root is not None:
        try:
            rel_path = str(pdf_path.relative_to(source_root))
        except ValueError:
            rel_path = str(pdf_path)

    try:
        metadata = parse_filename_metadata(filename)

        # 1. Tentative pdftotext
        text = extract_text_pdftotext(pdf_path)
        method = "pdftotext"

        # 2. Fallback OCR si texte trop pauvre
        if not _looks_textual(text):
            if not enable_ocr:
                return FileImportResult(
                    filename=filename,
                    status="skipped",
                    error="PDF non textuel, OCR désactivé",
                )
            text = extract_text_ocr(pdf_path)
            method = "tesseract"

        if not text.strip():
            return FileImportResult(
                filename=filename,
                status="error",
                error="Aucun texte extrait (ni pdftotext ni OCR)",
                extraction_method=method,
            )

        # 3. Fallback de métadonnées : si supplier manque dans le nom, regarder
        #    dans le texte extrait. Idem pour year (rare en pratique).
        if not metadata.get("supplier"):
            up = text.upper()
            if "ENGIE" in up:
                metadata["supplier"] = "ENGIE"
            elif "EDF" in up:
                metadata["supplier"] = "EDF"

        if not metadata.get("supplier") or not metadata.get("valid_year") or not metadata.get("lot_number"):
            return FileImportResult(
                filename=filename,
                status="error",
                error=f"Métadonnées incomplètes : {metadata}",
                extraction_method=method,
            )

        # 3. Parsing
        parsed = parse_bpu_text(text, metadata, extraction_method=method)
        table_segments = extract_segments_pdfplumber(
            pdf_path,
            default_unit=_detect_default_unit(text),
        )
        if table_segments:
            parsed.segments = _merge_segments(parsed.segments, table_segments)
            parsed.extraction_confidence = _estimate_extraction_confidence(parsed.segments)
            parsed.extraction_method = f"{method}+pdfplumber"

        # 4. Statut final
        conf = parsed.extraction_confidence or 0.0
        if method == "pdftotext":
            extraction_status = EXTRACTION_OK if conf >= 0.55 else EXTRACTION_OCR_REVIEW
        else:
            extraction_status = EXTRACTION_OCR_OK if conf >= 0.55 else EXTRACTION_OCR_REVIEW

        # 5. Persistance
        pdf_sha = compute_sha256(pdf_path)
        doc = persist_parsed_bpu(
            session,
            parsed,
            raw_text=text,
            pdf_filename=filename,
            pdf_relative_path=rel_path,
            pdf_sha256=pdf_sha,
            extraction_status=extraction_status,
            extraction_notes=parsed.notes,
            imported_by_user_id=imported_by_user_id,
            force=force,
        )
        session.commit()

        return FileImportResult(
            filename=filename,
            status=extraction_status,
            document_id=doc.id,
            segments_count=len(parsed.segments),
            components_count=sum(len(p.components) for s in parsed.segments for p in s.periods),
            fixed_charges_count=len(parsed.fixed_charges),
            extraction_method=method,
            extraction_confidence=float(conf),
        )

    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("Erreur import BPU %s", filename)
        return FileImportResult(
            filename=filename,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def import_directory(
    session: Session,
    *,
    source_dir: Path | None = None,
    only_filename: str | None = None,
    enable_ocr: bool = True,
    force: bool = False,
    imported_by_user_id: int | None = None,
) -> list[FileImportResult]:
    """Importe tous les PDFs d'un répertoire (récursif, .pdf only)."""
    base = source_dir or DEFAULT_BPU_SOURCE_DIR
    if not base.exists():
        raise FileNotFoundError(f"Répertoire BPU introuvable : {base}")

    pdfs = sorted(p for p in base.glob("*.pdf") if p.is_file())
    if only_filename:
        pdfs = [p for p in pdfs if p.name == only_filename]
        if not pdfs:
            raise FileNotFoundError(f"Fichier {only_filename} introuvable dans {base}")

    results: list[FileImportResult] = []
    for pdf in pdfs:
        logger.info("Import BPU : %s", pdf.name)
        result = import_pdf(
            session,
            pdf,
            source_root=base,
            enable_ocr=enable_ocr,
            force=force,
            imported_by_user_id=imported_by_user_id,
        )
        logger.info("  → %s (segments=%d, prix=%d, conf=%.2f)",
                    result.status, result.segments_count,
                    result.components_count, result.extraction_confidence or 0.0)
        results.append(result)
    return results
