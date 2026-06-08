"""
Synchronisation des prix de facturation (`BillingBpuLine`) depuis le BPU audité.

Contexte (cf. docs/energie/BPU-Audit-PDF-vs-Excel-2026-06-08.md) :
- `/energie/bpu` est alimenté par le xlsx canonique `extraction_tarifs_electricite_BPU.xlsx`,
  qui est la **source de vérité** (extraction manuelle validée).
- `/energie/facturation` stocke `BillingBpuLine` (prix par tarif TURPE × poste), consommé
  par le moteur de vérification de factures (`invoice_analysis.py`).
- Historiquement, ces prix étaient saisis 2 fois : une fois dans le xlsx, une fois en dur
  dans `bpu_templates.py`. Ce module **branche** les deux : il dérive les `BillingBpuLine`
  directement du xlsx, par **lot** (le document de référence = l'année la plus récente du lot).

⚠️ Pourquoi le xlsx et pas les tables `bpu_*` : le parseur BPU segmente par *typologie de
site* (ex. ENGIE → tout sous le segment « BATIMENT »), ce qui **écrase la dimension tarifaire**
(CU/CU4/MU4/MUDT/C4/C2). Le xlsx, lui, garde la colonne Tension/TURPE → seule source à la bonne
granularité.

La sortie de `build_lines_for_lot()` reproduit, sur les lots couverts, le contenu de
`bpu_templates.BPU_TEMPLATES_BY_LOT` (vérifié par tests).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.scripts.import_bpu_xlsx import DEFAULT_XLSX, _normalize_period

# Mapping période BPU normalisée (HPH/HCH/…) → poste billing (minuscule)
_PERIOD_TO_POSTE = {
    "BASE": "base",
    "POINTE": "pointe",
    "HPH": "hph",
    "HCH": "hch",
    "HPE": "hpe",
    "HCE": "hce",
    "HP": "hp",
    "HC": "hc",
}


def _col(df: pd.DataFrame, prefix: str) -> str | None:
    """Retrouve le nom exact d'une colonne par son préfixe ASCII (le xlsx a des accents)."""
    for c in df.columns:
        if c.encode("ascii", "ignore").decode().startswith(prefix):
            return c
    return None


def _num(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_last_year(value) -> int | None:
    """'2026' → 2026 ; '2021-2022' → 2022 ; '2022 / signé 2023' → 2023."""
    if value is None:
        return None
    years = re.findall(r"(20\d{2})", str(value))
    return max(int(y) for y in years) if years else None


def _to_eur_per_mwh(value: float | None, unit: str | None) -> float | None:
    """Normalise en €/MWh : les BPU en c€/kWh sont multipliés par 10."""
    if value is None:
        return None
    u = (unit or "").lower().replace(" ", "")
    if "c€/kwh" in u or "ce/kwh" in u or "ct€/kwh" in u:
        return round(value * 10.0, 4)
    return value


def tariff_codes_for_row(tension: str | None, turpe: str | None, site: str | None) -> list[str]:
    """Dérive le(s) code(s) tarifaire(s) billing depuis Tension/TURPE/Site du xlsx.

    Une ligne « CU4 / MU4 » alimente **deux** tarifs (CU4 et MU4), comme le template.
    Retourne [] si non mappable (la ligne est alors signalée, jamais écrite en silence).
    """
    # Priorité aux tokens de la colonne TENSION : le TURPE peut valoir « Assimilé
    # Eclairage Public » sur toutes les lignes d'un lot EP et polluerait la détection.
    t = (tension or "").upper()
    s = f"{tension or ''} {turpe or ''}".upper()  # C2/C4 ENGIE sont portés par le TURPE
    site_u = (site or "").upper()
    if "HTA" in t or re.search(r"\bC2\b", s):
        return ["C2"]
    if re.search(r"\bC4\b", s) or "BT>36" in t or "BT > 36" in t:
        return ["C4"]
    if "MUDT" in t:
        return ["MUDT"]
    if "CU4" in t and "MU4" in t:
        return ["CU4", "MU4"]
    if "CU4" in t:
        return ["CU4"]
    if "MU4" in t:
        return ["MU4"]
    if re.search(r"\bLU\b", t):
        return ["LU"]
    if re.search(r"\bCU\b", t):
        return ["CU"]
    # Pas de tarif reconnu dans la Tension → Éclairage Public (ligne sans SDT/Cx)
    if "ECLAIRAGE" in s or "ÉCLAIRAGE" in s or "ECLAIRAGE" in site_u or "ÉCLAIRAGE" in site_u:
        return ["EP"]
    return []


@dataclass
class LotSyncResult:
    lot_number: int
    source_filename: str | None = None
    source_year: int | None = None
    source_supplier: str | None = None
    lines: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def build_lines_for_lot(lot_number: int, xlsx_path: Path | None = None) -> LotSyncResult:
    """Construit les `BillingBpuLine` (year=None) d'un lot depuis le xlsx canonique.

    Document de référence = la ligne `Source fichier` de l'année **la plus récente**
    pour ce lot (tous fournisseurs confondus) — reproduit le choix du template.
    """
    path = Path(xlsx_path) if xlsx_path else DEFAULT_XLSX
    res = LotSyncResult(lot_number=lot_number)
    if not path.exists():
        res.warnings.append(f"xlsx introuvable : {path}")
        return res

    df = pd.read_excel(path, sheet_name="Prix_detailles")
    c_lot = _col(df, "Lot")
    c_year = _col(df, "Ann")
    c_src = _col(df, "Source fichier")
    c_supplier = _col(df, "Fournisseur")
    c_tension = _col(df, "Tension")
    c_turpe = _col(df, "Tarif TURPE")
    c_site = _col(df, "Site")
    c_poste = _col(df, "Poste")
    c_unit = _col(df, "Unit")  # Unité fourniture (unité des composantes €/MWh)
    c_fourn = _col(df, "Prix fourniture")
    c_cee = _col(df, "CEE")
    c_go = _col(df, "Option ENR")
    c_cap = _col(df, "M")  # Mécanisme / prix capacité

    # Filtre lot (la colonne 'Lot' vaut 'Lot 1', 'Lot 2'…)
    lot_mask = df[c_lot].astype(str).str.contains(rf"\b{lot_number}\b", regex=True, na=False)
    sub = df[lot_mask].copy()
    if sub.empty:
        res.warnings.append(f"Aucune ligne pour le lot {lot_number} dans le xlsx.")
        return res

    # Document de référence = année max
    sub["_year"] = sub[c_year].map(_parse_last_year)
    best_year = sub["_year"].max()
    ref = sub[sub["_year"] == best_year]
    # S'il reste plusieurs docs sur la même année, préférer celui en €/MWh, puis le plus fourni
    if ref[c_src].nunique() > 1:
        scored = []
        for fn, grp in ref.groupby(c_src):
            unit = str(grp[c_unit].iloc[0] or "").lower()
            scored.append((("c€/kwh" not in unit and "ce/kwh" not in unit), len(grp), fn))
        scored.sort(reverse=True)
        ref = ref[ref[c_src] == scored[0][2]]

    res.source_year = int(best_year) if best_year is not None else None
    res.source_filename = str(ref[c_src].iloc[0])
    res.source_supplier = str(ref[c_supplier].iloc[0]) if c_supplier else None

    for _, row in ref.iterrows():
        tension = row.get(c_tension)
        turpe = row.get(c_turpe)
        site = row.get(c_site)
        codes = tariff_codes_for_row(tension, turpe, site)
        poste_norm = _normalize_period(str(row.get(c_poste) or "") or None)
        poste = _PERIOD_TO_POSTE.get(poste_norm)
        if not codes:
            res.warnings.append(f"Tarif non mappé : tension={tension!r} turpe={turpe!r} site={site!r}")
            continue
        if poste is None:
            res.warnings.append(f"Poste non mappé : {row.get(c_poste)!r}")
            continue

        unit = row.get(c_unit)
        pu_fourniture = _to_eur_per_mwh(_num(row.get(c_fourn)), unit)
        pu_capacite = _to_eur_per_mwh(_num(row.get(c_cap)), unit)
        pu_cee = _to_eur_per_mwh(_num(row.get(c_cee)), unit)
        pu_go = _to_eur_per_mwh(_num(row.get(c_go)), unit)
        if pu_fourniture is None:
            pu_total = None
        else:
            pu_total = round(sum(v for v in (pu_fourniture, pu_capacite, pu_cee, pu_go) if v is not None), 4)

        for code in codes:
            res.lines.append(
                {
                    "year": None,
                    "tariff_code": code,
                    "poste": poste,
                    "pu_fourniture": pu_fourniture,
                    "pu_capacite": pu_capacite,
                    "pu_cee": pu_cee,
                    "pu_go": pu_go,
                    "pu_total": pu_total,
                    "observation": f"Synchronisé du BPU {res.source_filename} ({res.source_year})",
                }
            )
    return res


def _lot_number_from_config_lot(lot: str | None) -> int | None:
    """'lot1' / 'Lot 2' / '3' → numéro de lot entier."""
    if not lot:
        return None
    m = re.search(r"(\d+)", str(lot))
    return int(m.group(1)) if m else None


def preview_config_sync(db, cfg, xlsx_path: Path | None = None) -> LotSyncResult:
    """Construit (sans écrire) les lignes que la sync poserait pour ce config."""
    lot_number = _lot_number_from_config_lot(cfg.lot)
    if lot_number is None:
        res = LotSyncResult(lot_number=0)
        res.warnings.append("Aucun lot sélectionné pour ce fournisseur — sync impossible.")
        return res
    return build_lines_for_lot(lot_number, xlsx_path=xlsx_path)


def apply_config_sync(db, cfg, xlsx_path: Path | None = None) -> LotSyncResult:
    """Remplace les `BillingBpuLine` courantes (year IS NULL) du config par celles du BPU.

    Les éventuelles lignes datées (year non nul) sont conservées. Ne commit pas si
    aucune ligne n'a pu être construite (évite d'effacer une config sur une erreur de mapping).
    """
    from app.models.billing import BillingBpuLine

    res = preview_config_sync(db, cfg, xlsx_path=xlsx_path)
    if not res.lines:
        return res  # rien construit → on ne touche pas à l'existant

    db.query(BillingBpuLine).filter(
        BillingBpuLine.config_id == cfg.id, BillingBpuLine.year.is_(None)
    ).delete(synchronize_session=False)
    db.add_all(
        BillingBpuLine(config_id=cfg.id, **line) for line in res.lines
    )
    db.commit()
    return res
