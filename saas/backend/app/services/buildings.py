from fastapi import HTTPException, status
import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.building_meter import BuildingMeterLink
from app.models.city import City
from app.models.cvc import CvcInventoryItem, CvcRefrigerantItem, CvcSourceBuildingMapping
from app.models.local import Local
from app.models.patrimoine_legacy import PatrimoineLegacyAsset
from app.models.site import Site
from app.models.user import User
from app.schemas.building import BuildingCreate, BuildingIgnAttachmentPayload, BuildingMeterLinkCreate, BuildingNamingSelectionPayload, BuildingUpdate, LocalCreate, LocalUpdate, PatrimonyReclassifyPayload, PatrimonyReclassifyResult, SiteCreate, SiteUpdate
from app.services.building_naming import _dedupe_candidate_dicts, build_building_payload
from app.services.building_naming import reverse_geocode_point
from app.services.cities import get_city_by_id


def list_buildings(db: Session, current_user: User) -> list[Building]:
    statement = select(Building).order_by(Building.created_at.desc())
    if current_user.city_id is not None:
        statement = statement.where(Building.city_id == current_user.city_id)
    return list(db.scalars(statement))


def _normalize_lookup(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def list_sites(db: Session, current_user: User) -> list[Site]:
    statement = select(Site).order_by(Site.nom_site.asc())
    if current_user.city_id is not None:
        statement = statement.where(Site.city_id == current_user.city_id)
    return list(db.scalars(statement))


def get_site_or_404(db: Session, site_id: int, current_user: User) -> Site:
    statement = select(Site).where(Site.id == site_id)
    site = db.scalar(statement)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site introuvable.")
    if current_user.city_id is not None and site.city_id != current_user.city_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces au site refuse.")
    return site


def create_site(db: Session, payload: SiteCreate, current_user: User) -> Site:
    city_id = current_user.city_id if current_user.city_id is not None else payload.city_id
    if city_id is not None and get_city_by_id(db, city_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ville inconnue.")
    nom_site = payload.nom_site.strip()
    for site in list_sites(db, current_user):
        if site.city_id == city_id and _normalize_lookup(site.nom_site) == _normalize_lookup(nom_site):
            if payload.adresse and not site.adresse:
                site.adresse = payload.adresse.strip()
            if payload.source_file and not site.source_file:
                site.source_file = payload.source_file.strip()
            if payload.source_rows_json and not site.source_rows_json:
                site.source_rows_json = payload.source_rows_json.strip()
            db.add(site)
            db.commit()
            db.refresh(site)
            return site
    site = Site(
        city_id=city_id,
        nom_site=nom_site,
        adresse=payload.adresse.strip() if payload.adresse else None,
        source_file=payload.source_file.strip() if payload.source_file else None,
        source_rows_json=payload.source_rows_json.strip() if payload.source_rows_json else None,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def update_site(db: Session, site: Site, payload: SiteUpdate) -> Site:
    if payload.nom_site is not None:
        site.nom_site = payload.nom_site.strip()
    if payload.adresse is not None:
        site.adresse = payload.adresse.strip() if payload.adresse else None
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def get_building_or_404(db: Session, building_id: int, current_user: User) -> Building:
    statement = select(Building).where(Building.id == building_id)
    building = db.scalar(statement)
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bâtiment introuvable.")
    if current_user.city_id is not None and building.city_id != current_user.city_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès au bâtiment refusé.")
    return building


def _resolve_city(db: Session, payload: BuildingCreate, current_user: User) -> City | None:
    city_id = current_user.city_id if current_user.city_id is not None else payload.city_id
    if city_id is None:
        return None
    city = get_city_by_id(db, city_id)
    if city is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ville inconnue.")
    return city


def _build_default_local_name(building: Building) -> str:
    return building.nom_batiment or "Local principal"


def _apply_building_payload(building: Building, payload: BuildingCreate, nom_commune: str) -> Building:
    building.site_id = payload.site_id
    building.dgfip_unique_key = payload.dgfip_unique_key.strip() if payload.dgfip_unique_key else None
    building.dgfip_source_file = payload.dgfip_source_file.strip() if payload.dgfip_source_file else None
    building.dgfip_source_rows_json = payload.dgfip_source_rows_json.strip() if payload.dgfip_source_rows_json else None
    building.dgfip_reference_norm = payload.dgfip_reference_norm.strip() if payload.dgfip_reference_norm else None
    building.nom_batiment = payload.nom_batiment.strip() if payload.nom_batiment else None
    building.nom_commune = nom_commune
    building.numero_voirie = payload.numero_voirie.strip() if payload.numero_voirie else None
    building.indice_repetition = payload.indice_repetition.strip() if payload.indice_repetition else None
    building.nature_voie = payload.nature_voie.strip() if payload.nature_voie else None
    building.nom_voie = payload.nom_voie.strip() if payload.nom_voie else None
    building.prefixe = payload.prefixe.strip() if payload.prefixe else None
    building.section = payload.section.strip() if payload.section else None
    building.numero_plan = payload.numero_plan.strip() if payload.numero_plan else None
    building.adresse_reconstituee = payload.adresse_reconstituee.strip() if payload.adresse_reconstituee else None
    building.latitude = payload.latitude
    building.longitude = payload.longitude
    building.ign_layer = payload.ign_layer.strip() if payload.ign_layer else None
    building.ign_typename = payload.ign_typename.strip() if payload.ign_typename else None
    building.ign_id = payload.ign_id.strip() if payload.ign_id else None
    building.ign_name = payload.ign_name.strip() if payload.ign_name else None
    building.ign_label = payload.ign_label.strip() if payload.ign_label else None
    building.ign_name_proposed = payload.ign_name_proposed.strip() if payload.ign_name_proposed else None
    building.ign_name_source = payload.ign_name_source.strip() if payload.ign_name_source else None
    building.ign_name_distance_m = payload.ign_name_distance_m
    building.ign_attributes_json = payload.ign_attributes_json.strip() if payload.ign_attributes_json else None
    building.ign_features_json = payload.ign_features_json.strip() if payload.ign_features_json else None
    building.ign_toponym_candidates_json = (
        payload.ign_toponym_candidates_json.strip() if payload.ign_toponym_candidates_json else None
    )
    building.parcel_labels_json = payload.parcel_labels_json.strip() if payload.parcel_labels_json else None
    building.majic_building_values_json = payload.majic_building_values_json.strip() if payload.majic_building_values_json else None
    building.majic_entry_values_json = payload.majic_entry_values_json.strip() if payload.majic_entry_values_json else None
    building.majic_level_values_json = payload.majic_level_values_json.strip() if payload.majic_level_values_json else None
    building.majic_door_values_json = payload.majic_door_values_json.strip() if payload.majic_door_values_json else None
    building.source_creation = payload.source_creation or building.source_creation or "MANUEL"
    building.statut_geocodage = payload.statut_geocodage or building.statut_geocodage or "NON_FAIT"
    return building


def create_building(db: Session, payload: BuildingCreate, current_user: User) -> Building:
    city = _resolve_city(db, payload, current_user)
    nom_commune = city.nom_commune if city else (payload.nom_commune.strip() if payload.nom_commune else None)
    if nom_commune is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La commune est obligatoire.")
    if payload.site_id is not None:
        site = get_site_or_404(db, payload.site_id, current_user)
        if city is not None and site.city_id is not None and site.city_id != city.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le site n'appartient pas a la ville du batiment.")

    building = _apply_building_payload(Building(city_id=city.id if city else None), payload, nom_commune)
    db.add(building)
    db.flush()

    if payload.create_default_local:
        default_local = Local(
            building_id=building.id,
            nom_local=_build_default_local_name(building),
            type_local="PRINCIPAL",
        )
        db.add(default_local)
    db.commit()
    db.refresh(building)
    return building


def create_building_from_naming_selection(
    db: Session,
    payload: BuildingNamingSelectionPayload,
    current_user: User,
) -> Building:
    target_city_id = current_user.city_id if current_user.city_id is not None else payload.city_id
    target_city = get_city_by_id(db, target_city_id) if target_city_id is not None else None
    target_city_name = target_city.nom_commune if target_city is not None else None
    generated_payload = build_building_payload(
        unique_key=payload.unique_key,
        selected_feature=dict(payload.selected_feature) if payload.selected_feature else None,
        selected_features=[dict(f) for f in (payload.selected_features or []) if isinstance(f, dict)] or None,
        validated_name=payload.validated_name,
        city_name=target_city_name,
    )
    existing_statement = select(Building).where(Building.dgfip_unique_key == generated_payload["unique_key"])
    if target_city_id is not None:
        existing_statement = existing_statement.where(Building.city_id == target_city_id)
    existing_building = db.scalar(existing_statement)
    if existing_building is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse DGFIP a déjà été transformée en bâtiment dans votre périmètre.",
        )

    building_payload = BuildingCreate(
        city_id=target_city_id,
        dgfip_unique_key=generated_payload["unique_key"],
        dgfip_source_file=generated_payload["source_file"],
        dgfip_source_rows_json=json.dumps(generated_payload["source_rows"], ensure_ascii=False),
        dgfip_reference_norm=generated_payload["reference_norm"],
        nom_batiment=generated_payload["nom_batiment"],
        nom_commune=generated_payload["nom_commune"],
        numero_voirie=generated_payload["numero_voirie"],
        indice_repetition=generated_payload["indice_repetition"],
        nature_voie=generated_payload["nature_voie"],
        nom_voie=generated_payload["nom_voie"],
        prefixe=generated_payload["prefixe"],
        section=generated_payload["section"],
        numero_plan=generated_payload["numero_plan"],
        adresse_reconstituee=generated_payload["adresse_reconstituee"],
        latitude=generated_payload["latitude"],
        longitude=generated_payload["longitude"],
        ign_layer=generated_payload["ign_layer"],
        ign_typename=generated_payload["ign_typename"],
        ign_id=generated_payload["ign_id"],
        ign_name=generated_payload["ign_name"],
        ign_label=generated_payload["ign_label"],
        ign_name_proposed=generated_payload["ign_name_proposed"],
        ign_name_source=generated_payload["ign_name_source"],
        ign_name_distance_m=generated_payload["ign_name_distance_m"],
        ign_attributes_json=generated_payload["ign_attributes_json"],
        ign_features_json=generated_payload.get("ign_features_json"),
        ign_toponym_candidates_json=generated_payload["ign_toponym_candidates_json"],
        parcel_labels_json=generated_payload["parcel_labels_json"],
        majic_building_values_json=generated_payload["majic_building_values_json"],
        majic_entry_values_json=generated_payload["majic_entry_values_json"],
        majic_level_values_json=generated_payload["majic_level_values_json"],
        majic_door_values_json=generated_payload["majic_door_values_json"],
        source_creation=generated_payload["source_creation"],
        statut_geocodage=generated_payload["statut_geocodage"],
    )
    return create_building(db, building_payload, current_user)


def attach_building_geo(
    db: Session,
    building: Building,
    payload: BuildingNamingSelectionPayload,
    current_user: User,
) -> Building:
    target_city_id = building.city_id or current_user.city_id or payload.city_id
    target_city = get_city_by_id(db, target_city_id) if target_city_id is not None else None
    target_city_name = target_city.nom_commune if target_city is not None else building.nom_commune
    generated_payload = build_building_payload(
        unique_key=payload.unique_key,
        selected_feature=dict(payload.selected_feature) if payload.selected_feature else None,
        selected_features=[dict(f) for f in (payload.selected_features or []) if isinstance(f, dict)] or None,
        validated_name=payload.validated_name,
        city_name=target_city_name,
    )
    existing_statement = select(Building).where(
        Building.dgfip_unique_key == generated_payload["unique_key"],
        Building.id != building.id,
    )
    if target_city_id is not None:
        existing_statement = existing_statement.where(Building.city_id == target_city_id)
    existing_building = db.scalar(existing_statement)
    if existing_building is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse DGFIP est déjà rattachée à un autre bâtiment dans votre périmètre.",
        )

    building_payload = BuildingCreate(
        city_id=target_city_id,
        dgfip_unique_key=generated_payload["unique_key"],
        dgfip_source_file=generated_payload["source_file"],
        dgfip_source_rows_json=json.dumps(generated_payload["source_rows"], ensure_ascii=False),
        dgfip_reference_norm=generated_payload["reference_norm"],
        nom_batiment=generated_payload["nom_batiment"] or building.nom_batiment,
        nom_commune=generated_payload["nom_commune"] or building.nom_commune,
        numero_voirie=generated_payload["numero_voirie"],
        indice_repetition=generated_payload["indice_repetition"],
        nature_voie=generated_payload["nature_voie"],
        nom_voie=generated_payload["nom_voie"],
        prefixe=generated_payload["prefixe"],
        section=generated_payload["section"],
        numero_plan=generated_payload["numero_plan"],
        adresse_reconstituee=generated_payload["adresse_reconstituee"],
        latitude=generated_payload["latitude"],
        longitude=generated_payload["longitude"],
        ign_layer=generated_payload["ign_layer"],
        ign_typename=generated_payload["ign_typename"],
        ign_id=generated_payload["ign_id"],
        ign_name=generated_payload["ign_name"],
        ign_label=generated_payload["ign_label"],
        ign_name_proposed=generated_payload["ign_name_proposed"],
        ign_name_source=generated_payload["ign_name_source"],
        ign_name_distance_m=generated_payload["ign_name_distance_m"],
        ign_attributes_json=generated_payload["ign_attributes_json"],
        ign_features_json=generated_payload.get("ign_features_json"),
        ign_toponym_candidates_json=generated_payload["ign_toponym_candidates_json"],
        parcel_labels_json=generated_payload["parcel_labels_json"],
        majic_building_values_json=generated_payload["majic_building_values_json"],
        majic_entry_values_json=generated_payload["majic_entry_values_json"],
        majic_level_values_json=generated_payload["majic_level_values_json"],
        majic_door_values_json=generated_payload["majic_door_values_json"],
        source_creation=building.source_creation,
        statut_geocodage=generated_payload["statut_geocodage"],
    )
    updated_building = _apply_building_payload(building, building_payload, target_city_name or building.nom_commune)
    updated_building.city_id = target_city_id
    db.add(updated_building)
    db.commit()
    db.refresh(updated_building)
    return updated_building


def attach_building_ign(
    db: Session,
    building: Building,
    payload: BuildingIgnAttachmentPayload,
) -> Building:
    # Resolution multi-features :
    # - payload.selected_features (liste, nouvelle API) si fourni
    # - sinon retro-compat avec payload.selected_feature (singulier)
    features_list: list[dict[str, object]] = []
    if payload.selected_features:
        features_list = [f for f in payload.selected_features if isinstance(f, dict)]
    elif payload.selected_feature:
        features_list = [payload.selected_feature]

    # 1er feature = principal (alimente les champs ign_* legacy)
    primary_feature = features_list[0] if features_list else None
    feature_properties = (primary_feature or {}).get("properties", {}) or {}
    attributes = feature_properties.get("attributes", {}) or {}
    resolved_candidates = _dedupe_candidate_dicts(feature_properties.get("resolved_name_candidates") or [])

    proposed_name = str(
        payload.validated_name
        or feature_properties.get("resolved_name")
        or feature_properties.get("name")
        or building.nom_batiment
        or ""
    ).strip()

    # Le nom resolu ne vient pas toujours du batiment IGN lui-meme : quand celui-ci est
    # anonyme, `_resolve_building_name` retombe sur le toponyme de la ZONE qui l'englobe
    # (`zone_d_activite_ou_d_interet`, `zone_d_habitation`, `erp`, toponymie). Ce nom
    # designe alors le groupe entier, pas le batiment. L'ecrire renomme donc a l'identique
    # tous les batiments d'un meme ensemble.
    # Constate en prod sur le groupe scolaire Anatole France : 3 batiments renommes
    # « Ecole Elementaire Anatole France », dont 2 accroches au meme batiment IGN. Le
    # rapprochement ASTECH ne pouvait plus les departager (garde-fou « plusieurs batiments
    # proches ») et la referente n'avait plus aucun moyen de les distinguer a l'ecran.
    # On n'ecrase donc un nom existant que si l'utilisateur a explicitement valide le nom,
    # ou si le nom vient du batiment lui-meme. Sinon la proposition reste disponible dans
    # `ign_name_proposed`, que l'ecran peut offrir sans l'imposer.
    name_from_building_itself = (
        str(feature_properties.get("resolved_name_source") or "") == "batiment"
    )
    name_validated_by_user = bool(str(payload.validated_name or "").strip())
    if proposed_name and (
        name_validated_by_user or name_from_building_itself or not (building.nom_batiment or "").strip()
    ):
        building.nom_batiment = proposed_name
    if primary_feature:
        building.ign_layer = feature_properties.get("ign_layer")
        building.ign_typename = feature_properties.get("ign_typename")
        building.ign_id = feature_properties.get("ign_id")
        building.ign_name = feature_properties.get("name")
        building.ign_label = feature_properties.get("label")
        building.ign_name_proposed = feature_properties.get("resolved_name")
        building.ign_name_source = feature_properties.get("resolved_name_source")
        building.ign_name_distance_m = feature_properties.get("resolved_name_distance_m")
        building.ign_attributes_json = json.dumps(attributes, ensure_ascii=False) if attributes else None
        building.ign_toponym_candidates_json = json.dumps(resolved_candidates, ensure_ascii=False) if resolved_candidates else None
        building.statut_geocodage = "IGN_VALIDE"
        # Stockage de la liste complete des batiments IGN (incluant le principal)
        building.ign_features_json = json.dumps(features_list, ensure_ascii=False) if features_list else None
    if payload.lat is not None:
        building.latitude = payload.lat
    if payload.lon is not None:
        building.longitude = payload.lon

    db.add(building)
    db.commit()
    db.refresh(building)
    # Le cadastre et l'adresse que l'IGN vient de donner au batiment doivent DESCENDRE
    # jusqu'aux biens ASTECH qui le visent, sinon ils n'atteindront jamais le fichier
    # de retour : l'attribution enrichissait Po2 et le bien gardait ses anciennes
    # valeurs. Import local pour ne pas creer de dependance au chargement du module.
    from app.services.patrimoine_legacy import refresh_assets_of_building

    refresh_assets_of_building(db, building.id)
    return building


def move_building(
    db: Session, building: Building, lat: float, lon: float, resolve_address: bool = True
) -> Building:
    """Repositionne un batiment sur la carte et rafraichit son adresse.

    Endpoint dedie plutot que `update_building` : ce dernier remplace l'ensemble des
    champs a partir du payload, donc un appel partiel effacerait le nom, la commune et
    le reste. Ici on ne touche qu'a la position et a l'adresse resolue.
    """
    building.latitude = lat
    building.longitude = lon
    if resolve_address:
        found = reverse_geocode_point(lat, lon)
        if found.get("found"):
            if found.get("label"):
                building.adresse_reconstituee = str(found["label"])[:255]
            if found.get("city"):
                building.nom_commune = str(found["city"])[:255]
            if found.get("postcode"):
                building.code_postal = str(found["postcode"])[:10]
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


# Champs texte de `BuildingUpdate` appliques tels quels, apres `.strip()`.
_BUILDING_TEXT_FIELDS = (
    "nom_batiment", "code_postal", "numero_voirie", "indice_repetition", "nature_voie",
    "nom_voie", "prefixe", "section", "numero_plan", "adresse_reconstituee",
)


def update_building(db: Session, building: Building, payload: BuildingUpdate) -> Building:
    """Mise a jour PARTIELLE : seuls les champs presents dans le payload sont touches.

    Cette fonction remettait a plat TOUT le batiment : chaque champ absent du payload
    etait ecrase par `None`. Un appel qui n'envoyait que `nom_batiment` — renommer un
    batiment depuis l'ecran de rapprochement — effacait donc sa position, son adresse,
    son code postal et son cadastre.

    Constate en prod le 2026-08-21 : le batiment 1316 « STADE FRANCOIS MAILLOL », cree
    avec ses coordonnees a 07:57, les avait perdues a 08:00 apres un simple renommage.
    Il n'apparaissait plus sur la carte, et le bien ASTECH qui le visait semblait
    disparaitre avec lui.

    Les ecrans qui envoient le formulaire complet ne changent pas de comportement :
    leurs champs sont, eux, bien presents dans le payload.
    """
    fields_set = payload.model_fields_set
    for field in _BUILDING_TEXT_FIELDS:
        if field not in fields_set:
            continue
        value = getattr(payload, field)
        setattr(building, field, value.strip() if value else None)
    if "nom_commune" in fields_set and payload.nom_commune:
        building.nom_commune = payload.nom_commune.strip()
    if "latitude" in fields_set:
        building.latitude = payload.latitude
    if "longitude" in fields_set:
        building.longitude = payload.longitude
    # site_id : patch semantic. Si le frontend envoie site_id explicitement (meme None),
    # on l'applique. Sinon (champ absent du payload), on ne touche pas. Sert au drag&drop
    # Site>Batiment dans la vue cascade ET evite que les autres updates (rename, etc.)
    # ecrasent le rattachement existant.
    if "site_id" in fields_set:
        if payload.site_id is not None:
            # Valide que le site existe et appartient a la meme ville.
            site = db.scalar(select(Site).where(Site.id == payload.site_id))
            if site is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site cible introuvable.")
            if building.city_id is not None and site.city_id is not None and site.city_id != building.city_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le site cible n'appartient pas a la meme ville.")
        building.site_id = payload.site_id
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


def list_building_locals(db: Session, building: Building) -> list[Local]:
    statement = select(Local).where(Local.building_id == building.id).order_by(Local.created_at.asc())
    return list(db.scalars(statement))


def list_all_locals(db: Session, current_user: User) -> list[Local]:
    """Liste tous les locaux visibles par l'utilisateur (filtres par city_id via building.city_id)."""
    statement = select(Local).join(Building, Local.building_id == Building.id).order_by(Local.created_at.asc())
    if current_user.city_id is not None:
        statement = statement.where(Building.city_id == current_user.city_id)
    return list(db.scalars(statement))


def get_local_or_404(db: Session, building: Building, local_id: int) -> Local:
    statement = select(Local).where(Local.id == local_id, Local.building_id == building.id)
    local = db.scalar(statement)
    if local is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local introuvable.")
    return local


def create_local(db: Session, building: Building, payload: LocalCreate) -> Local:
    local = Local(
        building_id=building.id,
        nom_local=payload.nom_local.strip(),
        type_local=payload.type_local.strip(),
        niveau=payload.niveau.strip() if payload.niveau else None,
        surface_m2=payload.surface_m2,
        usage=payload.usage.strip() if payload.usage else None,
        statut_occupation=payload.statut_occupation.strip() if payload.statut_occupation else None,
        commentaire=payload.commentaire.strip() if payload.commentaire else None,
        # Adresse propre du local : le fichier d'inventaire en porte une sur chaque
        # ligne, y compris pour les locaux. Elle etait perdue jusqu'ici.
        adresse_reconstituee=payload.adresse_reconstituee.strip() if payload.adresse_reconstituee else None,
        code_postal=payload.code_postal.strip() if payload.code_postal else None,
        nom_commune=payload.nom_commune.strip() if payload.nom_commune else None,
        latitude=payload.latitude,
        longitude=payload.longitude,
        dgfip_reference_norm=payload.dgfip_reference_norm.strip() if payload.dgfip_reference_norm else None,
    )
    db.add(local)
    db.commit()
    db.refresh(local)
    return local


def update_local(db: Session, local: Local, payload: LocalUpdate) -> Local:
    fields_set = payload.model_fields_set
    if payload.nom_local is not None:
        local.nom_local = payload.nom_local.strip()
    if payload.type_local is not None:
        local.type_local = payload.type_local.strip()
    local.niveau = payload.niveau.strip() if payload.niveau else None
    local.surface_m2 = payload.surface_m2
    local.usage = payload.usage.strip() if payload.usage else None
    local.statut_occupation = payload.statut_occupation.strip() if payload.statut_occupation else None
    local.commentaire = payload.commentaire.strip() if payload.commentaire else None
    # building_id : drag&drop d'un local vers un autre batiment dans la vue cascade.
    # Champ absent du payload = ne touche pas ; entier fourni = deplace (apres validation ville).
    if "building_id" in fields_set and payload.building_id is not None:
        target = db.scalar(select(Building).where(Building.id == payload.building_id))
        if target is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batiment cible introuvable.")
        current_building = db.scalar(select(Building).where(Building.id == local.building_id))
        if (
            current_building is not None
            and current_building.city_id is not None
            and target.city_id is not None
            and target.city_id != current_building.city_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le batiment cible n'appartient pas a la meme ville.",
            )
        local.building_id = payload.building_id
    db.add(local)
    db.commit()
    db.refresh(local)
    return local


def delete_all_buildings(
    db: Session, current_user: User, *, include_sites: bool = False
) -> dict[str, int]:
    """Purge le patrimoine du périmètre de l'utilisateur.

    Les locaux partent en cascade avec leur bâtiment. Les **sites** ne sont pas des
    enfants des bâtiments (c'est l'inverse : `Building.site_id`), donc supprimer les
    bâtiments les laissait en place et l'arborescence restait peuplée de sites vides.
    `include_sites=True` vide aussi les sites, pour repartir d'une base réellement propre.
    """
    statement = select(Building)
    if current_user.city_id is not None:
        statement = statement.where(Building.city_id == current_user.city_id)
    buildings = list(db.scalars(statement))
    for building in buildings:
        db.delete(building)
    db.commit()

    deleted_sites = 0
    if include_sites:
        site_statement = select(Site)
        if current_user.city_id is not None:
            site_statement = site_statement.where(Site.city_id == current_user.city_id)
        sites = list(db.scalars(site_statement))
        for site in sites:
            db.delete(site)
        db.commit()
        deleted_sites = len(sites)

    return {"deleted": len(buildings), "deleted_sites": deleted_sites}


def delete_local(db: Session, local: Local) -> None:
    db.delete(local)
    db.commit()


def delete_building(db: Session, building: Building) -> None:
    """Supprime un batiment et ses locaux (CASCADE DB)."""
    db.delete(building)
    db.commit()


def delete_site(db: Session, site: Site) -> None:
    """Supprime un site. Les batiments rattaches sont detaches (SET NULL, pas supprimes)."""
    db.delete(site)
    db.commit()


def _default_city_name(db: Session, current_user: User) -> str:
    if current_user.city_id is None:
        return "Commune"
    city = get_city_by_id(db, current_user.city_id)
    return city.nom_commune if city else "Commune"


def _assert_building_can_be_removed(db: Session, building: Building) -> None:
    if db.scalar(select(Local.id).where(Local.building_id == building.id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce batiment contient des locaux. Deplace ou supprime les locaux avant de le reclasser.",
        )
    if db.scalar(select(BuildingMeterLink.id).where(BuildingMeterLink.building_id == building.id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce batiment a des compteurs rattaches. Le reclassement est bloque pour eviter de perdre les rattachements.",
        )
    if db.scalar(select(CvcInventoryItem.id).where(CvcInventoryItem.building_id == building.id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce batiment a des equipements CVC rattaches. Retire ou deplace ces rattachements avant de le reclasser.",
        )
    if db.scalar(select(CvcRefrigerantItem.id).where(CvcRefrigerantItem.building_id == building.id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce batiment a des fluides CVC rattaches. Retire ou deplace ces rattachements avant de le reclasser.",
        )
    if db.scalar(select(CvcSourceBuildingMapping.id).where(CvcSourceBuildingMapping.building_id == building.id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce batiment est utilise dans le matching CVC. Retire ou deplace ce rattachement avant de le reclasser.",
        )
    cvc_mappings = db.scalars(select(CvcSourceBuildingMapping).where(CvcSourceBuildingMapping.building_ids_json.is_not(None)))
    for mapping in cvc_mappings:
        try:
            building_ids = json.loads(mapping.building_ids_json or "[]")
        except json.JSONDecodeError:
            building_ids = []
        if building.id in building_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce batiment est utilise dans un matching CVC multi-batiments. Retire ou deplace ce rattachement avant de le reclasser.",
            )


def _move_astech_assets(
    db: Session,
    *,
    from_building_id: int | None = None,
    from_local_id: int | None = None,
    to_building_id: int | None = None,
    to_local_id: int | None = None,
) -> int:
    """Reporte les biens ASTECH sur l'entite nee du reclassement.

    Un reclassement SUPPRIME l'entite et en recree une avec un nouvel identifiant. Les
    biens du referentiel historique qui la visaient seraient donc orphelins : la cle
    etrangere est en `ON DELETE SET NULL`, le rattachement disparaitrait en silence.

    Le garde-fou `_assert_building_can_be_removed` verifie les compteurs et le CVC mais
    ignorait les biens ASTECH. Plutot que de bloquer le reclassement, on transporte le
    rattachement : c'est la meme realite qui change de niveau, pas un lien a rompre.
    """
    statement = select(PatrimoineLegacyAsset)
    if from_local_id is not None:
        statement = statement.where(PatrimoineLegacyAsset.local_id == from_local_id)
    else:
        statement = statement.where(
            PatrimoineLegacyAsset.building_id == from_building_id,
            PatrimoineLegacyAsset.local_id.is_(None),
        )
    moved = 0
    for asset in db.scalars(statement):
        asset.building_id = to_building_id
        asset.local_id = to_local_id
        asset.target_type = "local" if to_local_id is not None else "building"
        db.add(asset)
        moved += 1
    return moved


def reclassify_site(
    db: Session, site: Site, payload: PatrimonyReclassifyPayload, current_user: User
) -> PatrimonyReclassifyResult:
    if payload.target_type == "site":
        return PatrimonyReclassifyResult(entity_type="site", entity_id=site.id)
    if db.scalar(select(Building.id).where(Building.site_id == site.id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce site contient des batiments. Detache ou deplace les batiments avant de le reclasser.",
        )
    name = (payload.name or site.nom_site).strip()
    if payload.target_type == "building":
        if payload.target_site_id is not None:
            target_site = db.get(Site, payload.target_site_id)
            if target_site is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site parent introuvable.")
            if current_user.city_id is not None and target_site.city_id != current_user.city_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site parent hors perimetre.")
        building = Building(
            city_id=site.city_id,
            site_id=payload.target_site_id,
            nom_batiment=name,
            nom_commune=_default_city_name(db, current_user),
            adresse_reconstituee=site.adresse,
            source_creation="RECLASSEMENT",
            statut_geocodage="NON_FAIT",
        )
        db.add(building)
        db.delete(site)
        db.commit()
        db.refresh(building)
        return PatrimonyReclassifyResult(entity_type="building", entity_id=building.id)
    if payload.target_type == "local":
        if payload.target_building_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choisis un batiment parent.")
        parent = db.get(Building, payload.target_building_id)
        if parent is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batiment parent introuvable.")
        if current_user.city_id is not None and parent.city_id != current_user.city_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batiment parent hors perimetre.")
        local = Local(building_id=parent.id, nom_local=name, type_local="RECLASSEMENT")
        db.add(local)
        db.delete(site)
        db.commit()
        db.refresh(local)
        return PatrimonyReclassifyResult(entity_type="local", entity_id=local.id)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categorie cible invalide.")


def reclassify_building(
    db: Session, building: Building, payload: PatrimonyReclassifyPayload, current_user: User
) -> PatrimonyReclassifyResult:
    if payload.target_type == "building":
        return PatrimonyReclassifyResult(entity_type="building", entity_id=building.id)
    _assert_building_can_be_removed(db, building)
    name = (payload.name or building.nom_batiment or f"Batiment #{building.id}").strip()
    if payload.target_type == "site":
        site = Site(
            city_id=building.city_id,
            nom_site=name,
            adresse=building.adresse_reconstituee,
            source_file="RECLASSEMENT",
        )
        db.add(site)
        db.delete(building)
        db.commit()
        db.refresh(site)
        return PatrimonyReclassifyResult(entity_type="site", entity_id=site.id)
    if payload.target_type == "local":
        if payload.target_building_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choisis un batiment parent.")
        parent = db.get(Building, payload.target_building_id)
        if parent is None or parent.id == building.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batiment parent invalide.")
        if current_user.city_id is not None and parent.city_id != current_user.city_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batiment parent hors perimetre.")
        local = Local(
            building_id=parent.id,
            nom_local=name,
            type_local="RECLASSEMENT",
            # Le batiment emporte tout ce qui le situait : un local sait porter adresse,
            # position et cadastre depuis la migration 0074.
            adresse_reconstituee=building.adresse_reconstituee,
            code_postal=building.code_postal,
            nom_commune=building.nom_commune,
            latitude=building.latitude,
            longitude=building.longitude,
            dgfip_reference_norm=building.dgfip_reference_norm,
        )
        db.add(local)
        db.flush()
        _move_astech_assets(
            db, from_building_id=building.id, to_building_id=parent.id, to_local_id=local.id
        )
        db.delete(building)
        db.commit()
        db.refresh(local)
        return PatrimonyReclassifyResult(entity_type="local", entity_id=local.id)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categorie cible invalide.")


def reclassify_local(
    db: Session, local: Local, payload: PatrimonyReclassifyPayload, current_user: User
) -> PatrimonyReclassifyResult:
    if payload.target_type == "local":
        return PatrimonyReclassifyResult(entity_type="local", entity_id=local.id)
    parent = db.get(Building, local.building_id)
    name = (payload.name or local.nom_local).strip()
    if payload.target_type == "site":
        site = Site(
            city_id=parent.city_id if parent else current_user.city_id,
            nom_site=name,
            source_file="RECLASSEMENT",
        )
        db.add(site)
        db.delete(local)
        db.commit()
        db.refresh(site)
        return PatrimonyReclassifyResult(entity_type="site", entity_id=site.id)
    if payload.target_type == "building":
        target_site_id = payload.target_site_id if payload.target_site_id is not None else (parent.site_id if parent else None)
        if target_site_id is not None:
            target_site = db.get(Site, target_site_id)
            if target_site is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site parent introuvable.")
            if current_user.city_id is not None and target_site.city_id != current_user.city_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site parent hors perimetre.")
        # Le local emporte son adresse, sa position et son cadastre — a defaut ceux de
        # son batiment porteur. Sans ce transport, promouvoir un local le depouillait
        # de tout ce qui permettait de le situer.
        latitude = local.latitude if local.latitude is not None else (parent.latitude if parent else None)
        longitude = local.longitude if local.longitude is not None else (parent.longitude if parent else None)
        building = Building(
            city_id=parent.city_id if parent else current_user.city_id,
            site_id=target_site_id,
            nom_batiment=name,
            nom_commune=local.nom_commune or (parent.nom_commune if parent else _default_city_name(db, current_user)),
            adresse_reconstituee=local.adresse_reconstituee or (parent.adresse_reconstituee if parent else None),
            code_postal=local.code_postal or (parent.code_postal if parent else None),
            latitude=latitude,
            longitude=longitude,
            dgfip_reference_norm=local.dgfip_reference_norm or (parent.dgfip_reference_norm if parent else None),
            source_creation="RECLASSEMENT",
            statut_geocodage="A_VERIFIER" if latitude is not None else "NON_FAIT",
        )
        db.add(building)
        db.flush()
        _move_astech_assets(db, from_local_id=local.id, to_building_id=building.id)
        db.delete(local)
        db.commit()
        db.refresh(building)
        return PatrimonyReclassifyResult(entity_type="building", entity_id=building.id)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categorie cible invalide.")


def list_building_meter_links(db: Session, building: Building) -> list[BuildingMeterLink]:
    statement = (
        select(BuildingMeterLink)
        .where(BuildingMeterLink.building_id == building.id)
        .order_by(BuildingMeterLink.fluid.asc(), BuildingMeterLink.meter_identifier.asc())
    )
    return list(db.scalars(statement))


def get_building_meter_link_or_404(db: Session, building: Building, meter_link_id: int) -> BuildingMeterLink:
    statement = select(BuildingMeterLink).where(
        BuildingMeterLink.id == meter_link_id,
        BuildingMeterLink.building_id == building.id,
    )
    meter_link = db.scalar(statement)
    if meter_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rattachement compteur introuvable.")
    return meter_link


def _clean_meter_link_text(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def create_building_meter_link(
    db: Session,
    building: Building,
    payload: BuildingMeterLinkCreate,
) -> BuildingMeterLink:
    valid_from = payload.valid_from
    valid_to = payload.valid_to
    if valid_from and valid_to and valid_to < valid_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fin de validite du rattachement doit suivre son debut.",
        )

    fluid = payload.fluid.strip().upper()
    meter_identifier = payload.meter_identifier.strip()
    duplicate = db.scalar(
        select(BuildingMeterLink).where(
            BuildingMeterLink.building_id == building.id,
            BuildingMeterLink.fluid == fluid,
            BuildingMeterLink.meter_identifier == meter_identifier,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce compteur est deja rattache a ce batiment pour ce fluide.",
        )

    meter_link = BuildingMeterLink(
        building_id=building.id,
        fluid=fluid,
        meter_identifier=meter_identifier,
        meter_label=_clean_meter_link_text(payload.meter_label),
        usage_label=_clean_meter_link_text(payload.usage_label),
        share_ratio=payload.share_ratio,
        valid_from=valid_from,
        valid_to=valid_to,
        confidence=payload.confidence.strip().upper(),
        validation_status=payload.validation_status.strip().upper(),
        source=payload.source.strip(),
        contract_context=_clean_meter_link_text(payload.contract_context),
        supplier_name=_clean_meter_link_text(payload.supplier_name),
        notes=_clean_meter_link_text(payload.notes),
    )
    db.add(meter_link)
    db.commit()
    db.refresh(meter_link)
    return meter_link


def delete_building_meter_link(db: Session, meter_link: BuildingMeterLink) -> None:
    db.delete(meter_link)
    db.commit()
