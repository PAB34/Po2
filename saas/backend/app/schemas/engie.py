"""
Schémas Pydantic pour l'API ENGIE Entreprises & Collectivités.

Modèles générés à partir du Swagger ENGIE (ec/v1).
Tous les champs sont optionnels sauf mention contraire, car l'API ENGIE
ne garantit pas leur présence systématique.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TypeEnergie(str, Enum):
    GAZ = "GAZ"
    ELECTRICITE = "ELECTRICITE"


class Unite(str, Enum):
    M3 = "M3"
    KWH = "KWH"


class FrequenceReleve(str, Enum):
    JOURNALIERE = "JOURNALIERE"
    MENSUELLE = "MENSUELLE"
    SEMESTRIELLE = "SEMESTRIELLE"


class TypeReleve(str, Enum):
    RELEVE = "RELEVE"
    AUTO_RELEVE = "AUTO_RELEVE"
    ESTIME = "ESTIME"


class TypeDocumentFacture(str, Enum):
    FACTURE = "FACTURE"
    FACTURE_REGULARISATION = "FACTURE_REGULARISATION"
    FACTURE_RESILIATION = "FACTURE_RESILIATION"
    AVOIR = "AVOIR"
    FIC = "FIC"
    FUM = "FUM"
    FMC = "FMC"
    BORDEREAU = "BORDEREAU"


class DemandeStatut(str, Enum):
    OUVERTE = "OUVERTE"
    EN_COURS = "EN_COURS"
    TRAITEE = "TRAITEE"
    ANNULEE = "ANNULEE"


class DemandeCanal(str, Enum):
    ESPACE_CLIENT = "ESPACE_CLIENT"
    COURRIER = "COURRIER"
    EMAIL = "EMAIL"
    TELEPHONE = "TELEPHONE"
    VISITE = "VISITE"


class Profil(str, Enum):
    ADMINISTRATEUR = "ADMINISTRATEUR"
    AVANCE = "AVANCE"
    STANDARD = "STANDARD"


# ---------------------------------------------------------------------------
# Shared / reusable models
# ---------------------------------------------------------------------------


class PagingAttributes(BaseModel):
    offset: int = 0
    currentItems: int = 0
    total: int = 0


class AdressePartielle(BaseModel):
    codePostal: Optional[str] = None
    ville: Optional[str] = None


class Adresse(AdressePartielle):
    numeroEtVoie: Optional[str] = None
    pays: Optional[str] = None
    codeInseeCommune: Optional[str] = None  # V2 only


class PeriodeDate(BaseModel):
    dateDebut: Optional[date] = None
    dateFin: Optional[date] = None


class PeriodeDatetime(BaseModel):
    debut: Optional[datetime] = None
    fin: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------


class GroupeBase(BaseModel):
    uid: Optional[str] = None
    nom: Optional[str] = None


class SiteBase(BaseModel):
    uid: Optional[str] = None
    nom: Optional[str] = None
    codePostal: Optional[str] = None  # DEPRECATED
    commune: Optional[str] = None  # DEPRECATED
    adresse: Optional[AdressePartielle] = None
    referenceClient: Optional[str] = None
    dateFinAcces: Optional[str] = None


class Site(SiteBase):
    groupes: Optional[list[GroupeBase]] = None


class Groupe(GroupeBase):
    sites: Optional[list[SiteBase]] = None


class PuissancesSouscrites(BaseModel):
    HCD: Optional[float] = None
    HCE: Optional[float] = None
    HCH: Optional[float] = None
    HPD: Optional[float] = None
    HPE: Optional[float] = None
    HPH: Optional[float] = None
    JIA: Optional[float] = None
    pointe: Optional[float] = None
    simple: Optional[str] = None


class PuissanceARENH(BaseModel):
    annee: Optional[int] = None
    puissance: Optional[float] = None


class SiteDetail(BaseModel):
    uid: Optional[str] = None
    nom: Optional[str] = None
    dateFinAcces: Optional[str] = None
    typeEnergie: Optional[TypeEnergie] = None
    adresse: Optional[Adresse] = None
    referenceClient: Optional[str] = None
    puissances: Optional[PuissancesSouscrites] = None
    puissancesARENH: Optional[list[PuissanceARENH]] = None
    tarifTransportComptage: Optional[str] = None
    FTA: Optional[str] = None
    versionsUtilisation: Optional[str] = None
    telereleve: Optional[bool] = None
    typeCompteur: Optional[str] = None
    compteurCommunicant: Optional[str] = None
    frequenceReleve: Optional[str] = None
    branchementProvisoire: Optional[bool] = None
    modeAlimentation: Optional[str] = None
    segmentElec: Optional[str] = None
    profil: Optional[Profil] = None
    profilEnNombre: Optional[int] = None
    groupes: Optional[list[GroupeBase]] = None


class SiteDetailV2(SiteDetail):
    refContratClient: Optional[str] = None
    refComptaClient: Optional[str] = None
    refMarche: Optional[str] = None
    codeInseeCommuneUtilisatrice: Optional[str] = None
    codeInseeCommuneContractante: Optional[str] = None
    codeInseeCommunePayeuse: Optional[str] = None


class ProgrammationHoraire(BaseModel):
    programmationHoraireActuelleHeurePointe: Optional[str] = None
    programmationHoraireActuelleHeureCreuse: Optional[str] = None
    programmationHoraireActuelle: Optional[str] = None
    programmationHoraireFutureHeurePointe: Optional[str] = None
    programmationHoraireFutureHeureCreuse: Optional[str] = None
    programmationHoraireFuture: Optional[str] = None


# ---------------------------------------------------------------------------
# Contrats
# ---------------------------------------------------------------------------


class FlexibiliteContrat(BaseModel):
    basse: Optional[float] = None
    haute: Optional[float] = None
    situation: Optional[float] = None
    type: Optional[str] = None


class PeriodeContrat(BaseModel):
    dateDebut: Optional[str] = None
    dateFin: Optional[str] = None
    duree: Optional[str] = None


class Contrat(BaseModel):
    energie: Optional[str] = None
    flexibilite: Optional[FlexibiliteContrat] = None
    nbSites: Optional[int] = None
    nbSitesInitial: Optional[int] = None
    periode: Optional[PeriodeContrat] = None
    reference: Optional[str] = None
    typePrix: Optional[str] = None


class ContratsResponse(BaseModel):
    contrats: Optional[list[Contrat]] = None


class EntiteContractanteAdresse(BaseModel):
    boitePostale: Optional[str] = None
    codePostal: Optional[str] = None
    commune: Optional[str] = None
    noVoie: Optional[str] = None
    voie: Optional[str] = None


class EntiteContractante(BaseModel):
    adresse: Optional[EntiteContractanteAdresse] = None
    raisonSociale: Optional[str] = None


class ContratSite(BaseModel):
    dateDebut: Optional[str] = None
    entiteContractante: Optional[EntiteContractante] = None
    reference: Optional[str] = None


class ContratSitesResponse(BaseModel):
    sites: Optional[list[ContratSite]] = None


# ---------------------------------------------------------------------------
# Consommations
# ---------------------------------------------------------------------------


class ConsommationBase(BaseModel):
    date: Optional[str] = None
    unite: Optional[Unite] = None
    facturee: Optional[float] = None
    volume: Optional[float] = None
    corrigeeDJU: Optional[float] = None
    kwhCorrige: Optional[float] = None


class ConsoPosteSimple(BaseModel):
    debut: Optional[float] = None
    fin: Optional[float] = None


class ConsoPosteTarifaire(ConsoPosteSimple):
    energieReactive: Optional[float] = None
    puissanceSouscrite: Optional[float] = None
    puissanceAtteinte: Optional[float] = None


class IndexConso(ConsoPosteSimple):
    simple: Optional[ConsoPosteTarifaire] = None
    HP: Optional[ConsoPosteTarifaire] = None
    HC: Optional[ConsoPosteTarifaire] = None
    pointe: Optional[ConsoPosteTarifaire] = None
    HPH: Optional[ConsoPosteTarifaire] = None
    HPD: Optional[ConsoPosteTarifaire] = None
    HCH: Optional[ConsoPosteTarifaire] = None
    HCD: Optional[ConsoPosteTarifaire] = None
    HPE: Optional[ConsoPosteTarifaire] = None
    HCE: Optional[ConsoPosteTarifaire] = None
    JA: Optional[ConsoPosteTarifaire] = None
    PAH: Optional[ConsoPosteTarifaire] = None


class ReleveInfo(BaseModel):
    type: Optional[TypeReleve] = None
    typePrecedent: Optional[TypeReleve] = None
    rythme: Optional[FrequenceReleve] = None
    date: Optional[str] = None


class Consommation(ConsommationBase):
    periode: Optional[PeriodeDate] = None
    releve: Optional[ReleveInfo] = None
    index: Optional[IndexConso] = None
    pce: Optional[str] = None
    tarifTransport: Optional[float] = None


class ConsommationFoisonnee(ConsommationBase):
    pass


class EnergieItem(BaseModel):
    date: Optional[datetime] = None
    valeur: Optional[float] = None
    statut: Optional[str] = None


class ConditionsAtmospherique(BaseModel):
    temperature_valeur: Optional[float] = Field(None, alias="temperature.valeur")
    temperature_unite: Optional[str] = Field(None, alias="temperature.unite")
    pression_valeur: Optional[float] = Field(None, alias="pression.valeur")
    pression_unite: Optional[str] = Field(None, alias="pression.unite")

    model_config = {"populate_by_name": True}


class ConsommationsSiteBase(BaseModel):
    periode: Optional[PeriodeDatetime] = None
    pce: Optional[str] = None
    liste: Optional[list[EnergieItem]] = None


class ConsommationsCourbeDeCharge(ConsommationsSiteBase):
    conditionsAtmospherique: Optional[dict] = None


# ---------------------------------------------------------------------------
# Factures
# ---------------------------------------------------------------------------


class StatutsFacture(BaseModel):
    soldee: Optional[bool] = None
    retard: Optional[bool] = None
    prelevementAVenir: Optional[bool] = None
    annulee: Optional[bool] = None
    transmissionDematerialisee: Optional[str] = None


class FactureSite(BaseModel):
    pce: Optional[str] = None
    nom: Optional[str] = None
    adresse: Optional[Adresse] = None
    installation: Optional[str] = None
    typeComptage: Optional[str] = None
    versionUtilisation: Optional[str] = None


class MontantsTotaux(BaseModel):
    TTC: Optional[float] = None
    HTVA: Optional[float] = None
    HTT: Optional[float] = None


class MontantsTVA(BaseModel):
    Total: Optional[float] = None
    tauxReduit: Optional[float] = None
    tauxNormal: Optional[float] = None


class MontantsTaxes(BaseModel):
    tva: Optional[MontantsTVA] = None
    CSPE: Optional[float] = None
    taxeLocale: Optional[float] = None
    TICFE: Optional[float] = None
    CTA: Optional[float] = None
    TICGN: Optional[float] = None
    CBM: Optional[float] = None
    CTSSG: Optional[float] = None


class MontantsFourniture(BaseModel):
    pointe: Optional[float] = None
    base: Optional[float] = None
    HPH: Optional[float] = None
    HCH: Optional[float] = None
    HPE: Optional[float] = None
    HCE: Optional[float] = None
    HP: Optional[float] = None
    HC: Optional[float] = None
    HPD: Optional[float] = None
    HCD: Optional[float] = None
    JA: Optional[float] = None
    autre: Optional[float] = None
    Total: Optional[float] = None


class MontantsFacture(BaseModel):
    fourniture: Optional[MontantsFourniture] = None
    totaux: Optional[MontantsTotaux] = None
    taxes: Optional[MontantsTaxes] = None
    acheminement: Optional[dict] = None  # structure complexe imbriquée
    regularisation: Optional[dict] = None
    autre: Optional[dict] = None
    partFixe: Optional[float] = None
    partVariable: Optional[float] = None


class Facture(BaseModel):
    uid: Optional[str] = None
    typeDoc: Optional[str] = None  # DEPRECATED
    typeDocument: Optional[TypeDocumentFacture] = None
    pce: Optional[str] = None  # DEPRECATED
    site: Optional[FactureSite] = None
    energie: Optional[TypeEnergie] = None
    segment: Optional[str] = None
    dateEdition: Optional[str] = None
    libelleCCC: Optional[str] = None
    consommations: Optional[dict] = None
    statuts: Optional[StatutsFacture] = None
    periodeConsommation: Optional[PeriodeDate] = None
    montants: Optional[MontantsTotaux] = None


class FactureData(Facture):
    """Facture détaillée (endpoint /factures/{uid}/details)."""
    numeroFacture: Optional[str] = None  # DEPRECATED
    libelleOffre: Optional[str] = None
    bordereauFumFmc: Optional[str] = None
    compteContrat: Optional[str] = None
    compteContratCollectif: Optional[str] = None
    societePayeuse: Optional[dict] = None
    referencesClient: Optional[dict] = None
    numeroMarche: Optional[str] = None
    paquet: Optional[dict] = None
    montants: Optional[MontantsFacture] = None  # type: ignore[assignment]
    releve: Optional[dict] = None
    engagement: Optional[dict] = None
    puissances: Optional[dict] = None
    depassement: Optional[dict] = None
    gestionnaireReseauDistribution: Optional[dict] = None
    capaciteJournaliere: Optional[dict] = None
    rattrapageTarifaire: Optional[dict] = None


# ---------------------------------------------------------------------------
# Demandes
# ---------------------------------------------------------------------------


class Demande(BaseModel):
    uid: Optional[str] = None
    statut: Optional[DemandeStatut] = None
    dateCreation: Optional[date] = None
    libelle: Optional[str] = None
    canal: Optional[DemandeCanal] = None
    dateDerniereMAJ: Optional[date] = None
    dernierCommentaire: Optional[str] = None
    suiviEmail: Optional[bool] = None


class CategorieDemandeEligibilite(BaseModel):
    energie: Optional[list[TypeEnergie]] = None
    profil: Optional[Profil] = None
    profilEnNombre: Optional[int] = None


class CategorieDemande(BaseModel):
    uid: Optional[str] = None
    eligibilite: Optional[CategorieDemandeEligibilite] = None
    groupe: Optional[str] = None
    libelle: Optional[str] = None
    description: Optional[str] = None
    cgu: Optional[str] = None
    perimetreMultiple: Optional[bool] = None
    instructions: Optional[str] = None


# ---------------------------------------------------------------------------
# Profil / Contact
# ---------------------------------------------------------------------------


class Contact(BaseModel):
    uid: Optional[str] = None
    email: Optional[str] = None
    fixe: Optional[str] = None
    mobile: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    civilite: Optional[str] = None
    societe: Optional[str] = None
    contactId: Optional[str] = None
    marche: Optional[str] = None
    segmentMarketing: Optional[str] = None
    ref: Optional[str] = None


class ContactListItem(BaseModel):
    contactId: Optional[str] = None
    societe: Optional[str] = None


# ---------------------------------------------------------------------------
# Paginated list wrappers
# ---------------------------------------------------------------------------


class SiteListe(BaseModel):
    paging: Optional[PagingAttributes] = None
    liste: Optional[list[Site]] = None


class GroupeListe(BaseModel):
    liste: Optional[list[Groupe]] = None


class ConsommationListe(BaseModel):
    paging: Optional[PagingAttributes] = None
    liste: Optional[list[Consommation]] = None


class ConsommationFoisonneeListe(BaseModel):
    paging: Optional[PagingAttributes] = None
    agregationTemporelle: Optional[str] = None
    liste: Optional[list[ConsommationFoisonnee]] = None


class FactureListe(BaseModel):
    paging: Optional[PagingAttributes] = None
    liste: Optional[list[Facture]] = None


class FactureDataListe(BaseModel):
    paging: Optional[PagingAttributes] = None
    liste: Optional[list[FactureData]] = None


class CategorieDemandeList(BaseModel):
    liste: Optional[list[CategorieDemande]] = None


class ContactsListe(BaseModel):
    liste: Optional[list[ContactListItem]] = None
