"""Service des matrices comptables versionnées (doc 38).

Cette couche concentre les invariants métier du référentiel versionné :

- une seule version ``active`` par contrat matrice ;
- une version active n'est jamais modifiée en place : on crée une nouvelle
  version (éventuellement clonée) puis on l'active explicitement ;
- une version déjà appliquée à une facture (snapshot) ne peut pas être
  supprimée ;
- les règles ne sont modifiables que tant que leur version n'est pas active.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.accounting_matrix import (
    AccountingMatrixContract,
    AccountingMatrixRule,
    AccountingMatrixVersion,
    InvoiceAccountingSnapshot,
)
from app.models.cpe import CpeAccountingNatureRule, CpeAccountingSiteMapping, CpeFinanceLine
from app.models.invoice import (
    EnergyAccountingNatureRule,
    EnergyAccountingSiteMapping,
    EnergyInvoice,
    EnergyInvoiceImport,
    EnergyInvoiceLine,
    EnergyInvoicePeriod,
    EnergyInvoiceSite,
)
from app.services.prm_scope import in_scope_clause

# Mots vides retirés lors de la dérivation d'un nom court d'antenne depuis la
# désignation de site (ENGIE/EDF), pour rester lisible (cf. antenna_code DALKIA).
_ANTENNA_STOPWORDS = {
    "ESPACE", "LOCAL", "LOCAUX", "APPART", "APPARTEMENT", "MINUTERIE", "SITE",
    "BATIMENT", "BAT", "DE", "DES", "DU", "LA", "LE", "LES", "ET", "A", "AU", "AUX",
    "RDC", "ETAGE", "SOUS", "SOL",
    # Toponymes/génériques trop courants qui provoquent de faux rapprochements.
    "SETE", "COMMUNE", "VILLE", "GENERAL", "GENERALE", "POSTE",
}


def _short_antenna(designation: str | None) -> str | None:
    """Nom court d'antenne dérivé d'une désignation de site (v1, modifiable ensuite)."""
    if not designation:
        return None
    tokens = re.split(r"[^A-Za-z0-9]+", designation.upper())
    kept = [t for t in tokens if t and t not in _ANTENNA_STOPWORDS]
    if not kept:
        kept = [t for t in tokens if t]
    short = " ".join(kept)[:16].strip()
    return short or None


_INDEX_COMPTA_PATH = Path(__file__).resolve().parents[1] / "data" / "index_compta.json"
_MATCH_STOPWORDS = _ANTENNA_STOPWORDS | {"EX", "ANCIEN", "ANCIENNE", "DIV", "PLACE", "RUE", "AVENUE"}


@lru_cache(maxsize=1)
def _index_compta() -> dict:
    try:
        return json.loads(_INDEX_COMPTA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _referential(axis: str) -> list[tuple[str, str]]:
    """Entrées (code, libellé) d'un axe du référentiel CIRIL. Vide si absent."""
    entries = _index_compta().get("referentiels", {}).get(axis, {}).get("entries", [])
    return [(e.get("code") or "", e.get("label") or "") for e in entries if e.get("code")]


def _antenna_referential() -> list[tuple[str, str]]:  # rétrocompat
    return _referential("antenne")


def _match_tokens(text: str) -> set[str]:
    ascii_text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    cleaned = re.sub(r"[^A-Z0-9 ]", " ", ascii_text.upper())
    # singularisation grossière (ECOLES -> ECOLE) pour rapprocher libellés pluriels
    return {t.rstrip("S") for t in cleaned.split() if len(t) > 2 and t not in _MATCH_STOPWORDS}


def _suggest_from_referential(designation: str | None, axis: str) -> str | None:
    """Meilleur code du référentiel `axis` par recouvrement de mots avec la désignation."""
    if not designation:
        return None
    hay = _match_tokens(designation)
    if not hay:
        return None
    best: tuple[int, str] | None = None
    for code, label in _referential(axis):
        ref = _match_tokens(label)
        if not ref:
            continue
        overlap = len(hay & ref)
        if overlap and (best is None or overlap > best[0]):
            best = (overlap, code)
    return best[1] if best else None


def _suggest_antenna(designation: str | None) -> str | None:
    """Antenne suggérée : rapprochement au référentiel CIRIL (code = nom court
    officiel du bâtiment), sinon nom court dérivé. Toujours corrigeable."""
    return _suggest_from_referential(designation, "antenne") or _short_antenna(designation)


def _resolve_site_designations(
    db: Session, city_id: int | None, contract: AccountingMatrixContract, rules: list[AccountingMatrixRule]
) -> dict[tuple[str, str], str]:
    """Désignation de site extraite des factures, par (type, clé) :
    DALKIA -> ('site', site_code) via cpe_finance_lines.detail ;
    énergie -> ('meter', prm) via energy_invoice_sites.site_name."""
    out: dict[tuple[str, str], str] = {}
    site_codes = {r.site_code for r in rules if r.site_code}
    meter_ids = {r.meter_id for r in rules if r.meter_id}

    if contract.domain == "cpe" and site_codes:
        # Priorité au nom curé « Sites vers codes » (nom_du_site) : propre et lisible
        # (ex. « Maternelle AGNES VARDA »). Le « LIEU OU DÉTAIL DE LA PRESTATION » brut
        # de la facture (avec préfixe code + « REFAC €/€ ») ne sert que de repli.
        for code, name in db.execute(
            select(CpeAccountingSiteMapping.code_site, CpeAccountingSiteMapping.site_name).where(
                CpeAccountingSiteMapping.city_id == city_id,
                CpeAccountingSiteMapping.code_site.in_(site_codes),
                CpeAccountingSiteMapping.site_name.isnot(None),
            )
        ).all():
            if code and name and ("site", code) not in out:
                out[("site", code)] = name
        for code, detail in db.execute(
            select(CpeFinanceLine.site_code_detected, CpeFinanceLine.detail).where(
                CpeFinanceLine.city_id == city_id,
                CpeFinanceLine.site_code_detected.in_(site_codes),
                CpeFinanceLine.detail.isnot(None),
            )
        ).all():
            if code and detail:
                out.setdefault(("site", code), detail)

    if meter_ids:
        for prm, name in db.execute(
            select(EnergyInvoiceSite.prm_id, EnergyInvoiceSite.site_name)
            .join(EnergyInvoice, EnergyInvoiceSite.invoice_id == EnergyInvoice.id)
            .where(EnergyInvoice.city_id == city_id, EnergyInvoiceSite.prm_id.in_(meter_ids))
        ).all():
            if prm and name and ("meter", prm) not in out:
                out[("meter", prm)] = name

    return out

_RULE_COPY_FIELDS = (
    "stable_rule_key",
    "scope",
    "site_code",
    "building_id",
    "meter_id",
    "billed_item_pattern",
    "supplier_item_code",
    "accounting_service",
    "accounting_function",
    "accounting_antenna",
    "operation_number",
    "accounting_nature",
    "accounting_label",
    "allocation_percent",
    "priority",
    "is_active",
    "comment",
)


# ---------------------------------------------------------------------------
# Contrats matrice
# ---------------------------------------------------------------------------
def list_contracts(
    db: Session,
    city_id: int | None,
    *,
    domain: str | None = None,
    supplier: str | None = None,
) -> list[dict]:
    stmt = (
        select(AccountingMatrixContract)
        .where(AccountingMatrixContract.city_id == city_id)
        .options(selectinload(AccountingMatrixContract.versions))
        .order_by(AccountingMatrixContract.supplier, AccountingMatrixContract.contract_code)
    )
    if domain:
        stmt = stmt.where(AccountingMatrixContract.domain == domain)
    if supplier:
        stmt = stmt.where(AccountingMatrixContract.supplier == supplier)
    contracts = db.execute(stmt).scalars().all()
    return [_contract_summary(c) for c in contracts]


def get_contract(db: Session, city_id: int | None, contract_id: int) -> dict:
    contract = _require_contract(db, city_id, contract_id)
    summary = _contract_summary(contract)
    summary["versions"] = [_version_out(v) for v in contract.versions]
    return summary


def create_contract(db: Session, city_id: int | None, payload) -> dict:
    contract = AccountingMatrixContract(
        city_id=city_id,
        domain=payload.domain,
        supplier=payload.supplier,
        contract_code=payload.contract_code,
        contract_label=payload.contract_label,
        lot_label=payload.lot_label,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        status=payload.status,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return _contract_summary(contract)


def update_contract(db: Session, city_id: int | None, contract_id: int, payload) -> dict:
    contract = _require_contract(db, city_id, contract_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(contract, field, value)
    db.commit()
    db.refresh(contract)
    return _contract_summary(contract)


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------
def create_version(
    db: Session, city_id: int | None, contract_id: int, payload, *, user_id: int | None
) -> dict:
    contract = _require_contract(db, city_id, contract_id)

    if payload.status == "active":
        raise ValueError("Une version est créée en brouillon/candidate puis activée explicitement.")

    version = AccountingMatrixVersion(
        matrix_contract_id=contract.id,
        version_label=payload.version_label,
        status=payload.status or "draft",
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        source=payload.source or "manuel",
        created_by_user_id=user_id,
    )
    db.add(version)
    db.flush()

    if payload.clone_from_version_id is not None:
        source_version = _require_version(db, city_id, payload.clone_from_version_id)
        if source_version.matrix_contract_id != contract.id:
            raise ValueError("La version source n'appartient pas à ce contrat matrice.")
        for rule in source_version.rules:
            db.add(_clone_rule(rule, version.id))

    db.commit()
    db.refresh(version)
    return _version_out(version)


def activate_version(db: Session, city_id: int | None, version_id: int, *, user_id: int | None) -> dict:
    version = _require_version(db, city_id, version_id)
    if version.status == "archived":
        raise ValueError("Une version archivée ne peut pas être activée.")

    # Désactiver l'ancienne version active sans la supprimer (archivage).
    current_active = db.execute(
        select(AccountingMatrixVersion).where(
            AccountingMatrixVersion.matrix_contract_id == version.matrix_contract_id,
            AccountingMatrixVersion.status == "active",
            AccountingMatrixVersion.id != version.id,
        )
    ).scalars().all()
    for previous in current_active:
        previous.status = "archived"

    version.status = "active"
    version.validated_by_user_id = user_id
    version.validated_at = func.now()
    db.commit()
    db.refresh(version)
    return _version_out(version)


def archive_version(db: Session, city_id: int | None, version_id: int) -> dict:
    version = _require_version(db, city_id, version_id)
    if version.status == "active":
        raise ValueError("Activez d'abord une autre version : une version active ne s'archive pas directement.")
    version.status = "archived"
    db.commit()
    db.refresh(version)
    return _version_out(version)


def list_version_rules(db: Session, city_id: int | None, version_id: int) -> list[AccountingMatrixRule]:
    version = _require_version(db, city_id, version_id)
    rules = list(version.rules)
    # Enrichissement (transient, non persisté) : désignation de site extraite des
    # factures + antenne suggérée (référentiel CIRIL ou nom court) pour l'éditeur.
    designations = _resolve_site_designations(db, city_id, version.contract, rules)
    for rule in rules:
        designation = None
        if rule.site_code:
            designation = designations.get(("site", rule.site_code))
        if designation is None and rule.meter_id:
            designation = designations.get(("meter", rule.meter_id))
        rule.site_designation = designation
        rule.suggested_antenna = (
            _suggest_antenna(designation) if designation and not rule.accounting_antenna else None
        )
    return rules


# ---------------------------------------------------------------------------
# Règles
# ---------------------------------------------------------------------------
def create_rule(db: Session, city_id: int | None, version_id: int, payload) -> AccountingMatrixRule:
    version = _require_version(db, city_id, version_id)
    if version.status == "archived":
        raise ValueError(
            "Une version archivée est figée (historique des factures) : elle ne peut plus être éditée. "
            "Activez ou créez une autre version pour faire évoluer la matrice."
        )
    rule = AccountingMatrixRule(matrix_version_id=version.id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, city_id: int | None, rule_id: int, payload) -> AccountingMatrixRule:
    rule = db.get(AccountingMatrixRule, rule_id)
    if rule is None:
        raise ValueError("Règle introuvable.")
    version = _require_version(db, city_id, rule.matrix_version_id)
    if version.status == "archived":
        raise ValueError(
            "Une règle d'une version archivée (historique figé) ne peut pas être modifiée. "
            "Éditez la version active ou créez une nouvelle version."
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, city_id: int | None, rule_id: int) -> None:
    rule = db.get(AccountingMatrixRule, rule_id)
    if rule is None:
        raise ValueError("Règle introuvable.")
    version = _require_version(db, city_id, rule.matrix_version_id)
    if version.status == "archived":
        raise ValueError("Une version archivée (historique figé) ne peut pas être modifiée.")
    db.delete(rule)
    db.commit()


# ---------------------------------------------------------------------------
# Snapshot facture (lecture seule pour la tranche minimale)
# ---------------------------------------------------------------------------
def get_invoice_snapshot(
    db: Session, city_id: int | None, source: str, invoice_id: str
) -> InvoiceAccountingSnapshot | None:
    return db.execute(
        select(InvoiceAccountingSnapshot).where(
            InvoiceAccountingSnapshot.city_id == city_id,
            InvoiceAccountingSnapshot.invoice_source == source,
            InvoiceAccountingSnapshot.invoice_id == invoice_id,
        )
    ).scalars().first()


# ---------------------------------------------------------------------------
# Seed depuis les codifications existantes (doc 38, étape 3)
# ---------------------------------------------------------------------------
SEED_VERSION_LABEL = "V0 - migration existant"


def seed_from_existing(db: Session, city_id: int | None, *, user_id: int | None) -> dict:
    """Crée des matrices versionnées en `draft` depuis les tables à plat.

    Choix de regroupement (validé avec l'utilisateur le 2026-06-25) :

    - Énergie : une matrice par fournisseur (`domain=fluides`). Les règles de
      nature suivent leur `supplier` ; les mappings PRM->axes (non rattachés à
      un fournisseur dans l'existant) sont dupliqués dans chaque matrice énergie.
    - CPE DALKIA : une matrice par `contract_code` (`domain=cpe`). Les mappings
      site->axes (sans `contract_code`) sont dupliqués dans chaque matrice CPE.

    Idempotent : une matrice déjà présente (même clé contrat) est ignorée.
    Aucune version n'est activée : la validation reste un acte explicite.
    """
    energy = _seed_energy(db, city_id, user_id=user_id)
    cpe = _seed_cpe(db, city_id, user_id=user_id)
    db.commit()
    return {
        "energy": energy,
        "cpe": cpe,
        "versions_created": energy["contracts_created"] + cpe["contracts_created"],
    }


def _seed_energy(db: Session, city_id: int | None, *, user_id: int | None) -> dict:
    nature_rules = db.execute(
        select(EnergyAccountingNatureRule).where(EnergyAccountingNatureRule.city_id == city_id)
    ).scalars().all()
    site_mappings = db.execute(
        select(EnergyAccountingSiteMapping).where(EnergyAccountingSiteMapping.city_id == city_id)
    ).scalars().all()

    suppliers = sorted({(r.supplier or "INCONNU").strip() for r in nature_rules})
    created = skipped = rules_count = 0

    for supplier in suppliers:
        if _contract_exists(db, city_id, domain="fluides", supplier=supplier, contract_code=None, lot_label=None):
            skipped += 1
            continue
        version = _new_seed_contract_version(
            db, city_id, domain="fluides", supplier=supplier,
            contract_label=f"Fourniture {supplier} (migration codification énergie)", user_id=user_id,
        )
        # Règles de nature pour ce fournisseur.
        for r in (x for x in nature_rules if (x.supplier or "INCONNU").strip() == supplier):
            db.add(AccountingMatrixRule(
                matrix_version_id=version.id,
                stable_rule_key=_key("energy", "nature", r.market, r.billed_item, r.frequency),
                scope="billed_item",
                billed_item_pattern=r.billed_item,
                accounting_nature=r.accounting_nature,
                accounting_label=r.accounting_label,
                is_active=r.active,
                comment=r.notes,
            ))
            rules_count += 1
        # Mappings PRM -> axes (dupliqués dans chaque matrice énergie).
        for m in site_mappings:
            db.add(AccountingMatrixRule(
                matrix_version_id=version.id,
                stable_rule_key=_key("energy", "site", m.prm_id),
                scope="meter",
                meter_id=m.prm_id,
                accounting_service=m.service_label or m.service_code,
                accounting_function=m.function_label or m.function_code,
                accounting_antenna=m.antenna_code or m.antenna_label,
                operation_number=m.operation_code,
                is_active=m.active,
                comment=_join(m.site_name, m.regroupement, m.family, m.notes),
            ))
            rules_count += 1
        created += 1

    return {"contracts_created": created, "contracts_skipped": skipped, "rules": rules_count}


def _seed_cpe(db: Session, city_id: int | None, *, user_id: int | None) -> dict:
    nature_rules = db.execute(
        select(CpeAccountingNatureRule).where(CpeAccountingNatureRule.city_id == city_id)
    ).scalars().all()
    site_mappings = db.execute(
        select(CpeAccountingSiteMapping).where(CpeAccountingSiteMapping.city_id == city_id)
    ).scalars().all()

    contract_codes = sorted({(r.contract_code or "").strip() for r in nature_rules})
    created = skipped = rules_count = 0

    for code in contract_codes:
        code_value = code or None
        if _contract_exists(db, city_id, domain="cpe", supplier="DALKIA", contract_code=code_value, lot_label=None):
            skipped += 1
            continue
        label = f"DALKIA {code}" if code else "DALKIA - non rattaché"
        version = _new_seed_contract_version(
            db, city_id, domain="cpe", supplier="DALKIA",
            contract_code=code_value, contract_label=label, user_id=user_id,
        )
        for r in (x for x in nature_rules if (x.contract_code or "").strip() == code):
            db.add(AccountingMatrixRule(
                matrix_version_id=version.id,
                stable_rule_key=_key("cpe", "nature", r.market, r.service_sold, r.billed_item, r.frequency),
                scope="billed_item",
                billed_item_pattern=r.billed_item,
                supplier_item_code=r.service_sold,
                accounting_nature=r.accounting_nature,
                accounting_label=r.accounting_label,
                is_active=r.active,
                comment=r.notes,
            ))
            rules_count += 1
        for m in site_mappings:
            db.add(AccountingMatrixRule(
                matrix_version_id=version.id,
                stable_rule_key=_key("cpe", "site", m.code_site),
                scope="site",
                site_code=m.code_site,
                accounting_service=m.service_label or m.service_code,
                accounting_function=m.function_label or m.function_code,
                accounting_antenna=m.antenna_code or m.antenna_label,
                operation_number=m.operation_code,
                is_active=m.active,
                comment=_join(m.site_name, m.family, m.manager, m.notes),
            ))
            rules_count += 1
        created += 1

    return {"contracts_created": created, "contracts_skipped": skipped, "rules": rules_count}


def prefill_energy_matrices(db: Session, city_id: int | None) -> dict:
    """Pré-remplit la codification énergie (ENGIE/EDF) pour un premier jet corrigeable :

    - règles poste→nature : tous les postes élec vus dans les factures → 60612, par
      fournisseur présent (ENGIE, EDF) ;
    - axes des sites (PRM) déduits de la désignation facture via le référentiel CIRIL :
      antenne (nom court du bâtiment), service, fonction ; opération laissée **vide**
      (électricité = fonctionnement, cf. arbitrage comptable).

    N'active aucune version : `seed_from_existing` est appelé ensuite pour (re)construire
    les matrices versionnées. Reconstruit intégralement les règles de nature énergie.
    """
    postes = sorted({
        (code or "").upper()
        for (code,) in db.execute(
            select(EnergyInvoiceLine.normalized_code)
            .join(EnergyInvoicePeriod, EnergyInvoiceLine.invoice_period_id == EnergyInvoicePeriod.id)
            .join(EnergyInvoiceSite, EnergyInvoicePeriod.invoice_site_id == EnergyInvoiceSite.id)
            .join(EnergyInvoice, EnergyInvoiceSite.invoice_id == EnergyInvoice.id)
            .where(
                EnergyInvoice.city_id == city_id,
                EnergyInvoiceLine.normalized_code.isnot(None),
                in_scope_clause(city_id),
            )
            .distinct()
        ).all()
        if code and code.strip()
    })
    suppliers = [
        s for s in (
            (val or "").upper()
            for (val,) in db.execute(
                select(EnergyInvoiceImport.supplier_guess)
                .where(EnergyInvoiceImport.city_id == city_id, EnergyInvoiceImport.supplier_guess.isnot(None))
                .distinct()
            ).all()
        )
        if s in ("ENGIE", "EDF")
    ] or ["ENGIE"]

    # 1. Règles poste -> nature (reconstruction complète).
    db.execute(delete(EnergyAccountingNatureRule).where(EnergyAccountingNatureRule.city_id == city_id))
    rules_created = 0
    for supplier in suppliers:
        for poste in postes:
            db.add(EnergyAccountingNatureRule(
                city_id=city_id, supplier=supplier, market=None, billed_item=poste,
                accounting_nature="60612", accounting_label="Energie - Electricite",
            ))
            rules_created += 1

    # 2. Axes des sites (PRM) déduits de la désignation facture.
    designations = {
        prm: name
        for prm, name in db.execute(
            select(EnergyInvoiceSite.prm_id, EnergyInvoiceSite.site_name)
            .join(EnergyInvoice, EnergyInvoiceSite.invoice_id == EnergyInvoice.id)
            .where(
                EnergyInvoice.city_id == city_id,
                EnergyInvoiceSite.prm_id.isnot(None),
                EnergyInvoiceSite.site_name.isnot(None),
                in_scope_clause(city_id),
            )
        ).all()
        if prm and name
    }
    service_labels = dict(_referential("service"))
    function_labels = dict(_referential("fonction"))
    antenna_labels = dict(_referential("antenne"))

    filled = 0
    mappings = db.execute(
        select(EnergyAccountingSiteMapping).where(EnergyAccountingSiteMapping.city_id == city_id)
    ).scalars().all()
    for m in mappings:
        designation = designations.get(m.prm_id)
        if not designation:
            continue
        antenna = _suggest_antenna(designation)
        service = _suggest_from_referential(designation, "service")
        function = _suggest_from_referential(designation, "fonction")
        m.antenna_code = antenna
        m.antenna_label = antenna_labels.get(antenna or "")
        m.service_code = service
        m.service_label = service_labels.get(service or "")
        m.function_code = function
        m.function_label = function_labels.get(function or "")
        m.operation_code = None
        m.operation_label = None
        filled += 1

    db.commit()
    return {
        "suppliers": suppliers,
        "postes": len(postes),
        "nature_rules_created": rules_created,
        "sites_prefilled": filled,
        "sites_total": len(mappings),
    }


def _contract_exists(
    db: Session, city_id: int | None, *, domain: str, supplier: str,
    contract_code: str | None, lot_label: str | None,
) -> bool:
    return db.execute(
        select(AccountingMatrixContract.id).where(
            AccountingMatrixContract.city_id == city_id,
            AccountingMatrixContract.domain == domain,
            AccountingMatrixContract.supplier == supplier,
            AccountingMatrixContract.contract_code.is_(None) if contract_code is None
            else AccountingMatrixContract.contract_code == contract_code,
            AccountingMatrixContract.lot_label.is_(None) if lot_label is None
            else AccountingMatrixContract.lot_label == lot_label,
        )
    ).first() is not None


def _new_seed_contract_version(
    db: Session, city_id: int | None, *, domain: str, supplier: str,
    contract_label: str, user_id: int | None, contract_code: str | None = None,
) -> AccountingMatrixVersion:
    contract = AccountingMatrixContract(
        city_id=city_id, domain=domain, supplier=supplier,
        contract_code=contract_code, contract_label=contract_label, status="active",
    )
    db.add(contract)
    db.flush()
    source = "migration_cpe" if domain == "cpe" else "migration_energie"
    version = AccountingMatrixVersion(
        matrix_contract_id=contract.id,
        version_label=SEED_VERSION_LABEL,
        status="draft",
        source=source,
        created_by_user_id=user_id,
    )
    db.add(version)
    db.flush()
    return version


def _key(*parts: str | None) -> str:
    return ":".join((p or "-").strip() for p in parts)


def _join(*parts: str | None) -> str | None:
    values = [p.strip() for p in parts if p and p.strip()]
    return " · ".join(values) if values else None


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------
def _require_contract(db: Session, city_id: int | None, contract_id: int) -> AccountingMatrixContract:
    contract = db.get(AccountingMatrixContract, contract_id)
    if contract is None or contract.city_id != city_id:
        raise ValueError("Contrat matrice introuvable.")
    return contract


def _require_version(db: Session, city_id: int | None, version_id: int) -> AccountingMatrixVersion:
    version = db.get(AccountingMatrixVersion, version_id)
    if version is None:
        raise ValueError("Version de matrice introuvable.")
    # Vérifie l'isolation multi-tenant via le contrat parent.
    if version.contract is None or version.contract.city_id != city_id:
        raise ValueError("Version de matrice introuvable.")
    return version


def _clone_rule(rule: AccountingMatrixRule, version_id: int) -> AccountingMatrixRule:
    data = {field: getattr(rule, field) for field in _RULE_COPY_FIELDS}
    return AccountingMatrixRule(matrix_version_id=version_id, **data)


def _active_version(contract: AccountingMatrixContract) -> AccountingMatrixVersion | None:
    for version in contract.versions:
        if version.status == "active":
            return version
    return None


def _contract_summary(contract: AccountingMatrixContract) -> dict:
    active = _active_version(contract)
    return {
        "id": contract.id,
        "domain": contract.domain,
        "supplier": contract.supplier,
        "contract_code": contract.contract_code,
        "contract_label": contract.contract_label,
        "lot_label": contract.lot_label,
        "starts_on": contract.starts_on,
        "ends_on": contract.ends_on,
        "contact_name": contract.contact_name,
        "contact_email": contract.contact_email,
        "status": contract.status,
        "active_version_id": active.id if active else None,
        "active_version_label": active.version_label if active else None,
        "versions_count": len(contract.versions),
        "created_at": contract.created_at,
        "updated_at": contract.updated_at,
    }


def _version_out(version: AccountingMatrixVersion) -> dict:
    return {
        "id": version.id,
        "matrix_contract_id": version.matrix_contract_id,
        "version_label": version.version_label,
        "status": version.status,
        "effective_from": version.effective_from,
        "effective_to": version.effective_to,
        "source": version.source,
        "source_filename": version.source_filename,
        "source_sha256": version.source_sha256,
        "created_by_user_id": version.created_by_user_id,
        "validated_by_user_id": version.validated_by_user_id,
        "validated_at": version.validated_at,
        "rules_count": len(version.rules),
        "created_at": version.created_at,
        "updated_at": version.updated_at,
    }
