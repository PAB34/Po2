from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class EtatVetuste(str, Enum):
    OBSOLETE = "obsolete"
    DEGRADE = "degrade"
    MOYEN = "moyen"
    NEUF = "neuf"


class QuantiteEstimee(str, Enum):
    FAIBLE = "faible"
    MOYENNE = "moyenne"
    ELEVEE = "elevee"


ETAT_COEFFICIENTS: dict[str, float] = {
    EtatVetuste.OBSOLETE: 0.0,
    EtatVetuste.DEGRADE: 0.25,
    EtatVetuste.MOYEN: 0.5,
    EtatVetuste.NEUF: 1.0,
}


class EquipmentReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_ligne: int
    code_niveau_1: str
    libelle_niveau_1: str
    code_niveau_2: str
    libelle_niveau_2: str
    niveau_3: str | None = None
    niveau_4: str | None = None
    niveau_5: str | None = None
    equipement: str
    sypemi_mini_annees: float | None = None
    sypemi_reference_annees: float | None = None
    sypemi_maxi_annees: float | None = None
    fiche_cee: str | None = None


class BuildingEquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    equipment_ref_id: int
    etat: str
    quantite: str
    commentaire: str | None = None
    duree_vie_restante: float
    created_at: datetime
    updated_at: datetime
    equipment_ref: EquipmentReferenceRead | None = None


class BuildingEquipmentCreate(BaseModel):
    equipment_ref_id: int
    etat: EtatVetuste
    quantite: QuantiteEstimee
    commentaire: str | None = None


class BuildingEquipmentUpdate(BaseModel):
    etat: EtatVetuste | None = None
    quantite: QuantiteEstimee | None = None
    commentaire: str | None = None


class BuildingEquipmentBulkItem(BaseModel):
    equipment_ref_id: int
    etat: EtatVetuste
    quantite: QuantiteEstimee
    commentaire: str | None = None


class BuildingEquipmentBulkCreate(BaseModel):
    items: list[BuildingEquipmentBulkItem]


class EquipmentStateCounts(BaseModel):
    obsolete: int = 0
    degrade: int = 0
    moyen: int = 0
    neuf: int = 0
    total: int = 0
    score_sante: float | None = None


class BuildingEquipmentSummary(BaseModel):
    building_id: int
    counts: EquipmentStateCounts
