from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class GasInvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    num_facture: str
    type_detail: str | None = None
    date_comptable: date | None = None
    date_echeance: date | None = None
    pce: str
    nom_site: str | None = None
    lib_regroupement: str | None = None
    adresse: str | None = None
    ville: str | None = None
    classe_conso: str | None = None
    tarif_acheminement: str | None = None
    debut_conso: date | None = None
    fin_conso: date | None = None
    prix_conso_gaz: float | None = None
    montant_conso_gaz: float | None = None
    total_hors_tva: float | None = None
    total_ttc: float | None = None
    total_conso_kwh: int | None = None
    total_conso_m3: int | None = None
    building_id: int | None = None
    control_status: str
    control_issues_json: str | None = None
    control_detail_json: str | None = None
    decision_status: str
    decision_comment: str | None = None


class GasInvoiceDecisionIn(BaseModel):
    decision_status: str
    comment: str | None = None


class GasBpuPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    annee: int
    profil: str
    fourniture_ht_mwh: float | None = None
    cee_ht_mwh: float | None = None
    cee_precarite_ht_mwh: float | None = None
    cpb_ht_mwh: float | None = None
    go_ht_mwh: float | None = None
    source: str | None = None


class GasBpuPriceUpdateIn(BaseModel):
    fourniture_ht_mwh: float | None = None
    cee_ht_mwh: float | None = None
    cee_precarite_ht_mwh: float | None = None
    cpb_ht_mwh: float | None = None
    go_ht_mwh: float | None = None


class GasNetworkTariffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    annee: int
    option: str
    atrd_terme_variable_eur_mwh: float | None = None
    atrd_abonnement_annuel_eur: float | None = None
    source: str | None = None
    source_url: str | None = None


class GasNetworkTariffUpdateIn(BaseModel):
    atrd_terme_variable_eur_mwh: float | None = None
    atrd_abonnement_annuel_eur: float | None = None
    source: str | None = None


class GasTaxRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    valid_from: date
    valid_to: date | None = None
    ticgn_eur_mwh: float | None = None
    cta_coeff_atrd_fixe: float | None = None
    source: str | None = None
    source_url: str | None = None


class GasTaxRateUpdateIn(BaseModel):
    ticgn_eur_mwh: float | None = None
    cta_coeff_atrd_fixe: float | None = None
    source: str | None = None


class GasRevisablePriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    annee: int
    mois: int
    fourniture_eur_mwh: float | None = None
    source: str | None = None


class GasRevisablePriceIn(BaseModel):
    annee: int
    mois: int
    fourniture_eur_mwh: float
    source: str | None = None
