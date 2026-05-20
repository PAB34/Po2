# Module — Conformité OPERAT / décret éco tertiaire

> Suivi des bâtiments tertiaires assujettis au dispositif Éco Énergie Tertiaire, préparation des déclarations annuelles OPERAT et, à terme, interconnexion API.

## Contexte

OPERAT est la plateforme ADEME de recueil et de suivi des consommations d'énergie du secteur tertiaire. Le dispositif concerne propriétaires et preneurs à bail de bâtiments, parties de bâtiments ou ensembles de bâtiments soumis aux obligations de réduction de consommation.

Sources consultées le 2026-05-20 :
- ADEME open data : https://data.ademe.fr/datasets/consommation-tertiaire-vecteur-energetique
- Justice.fr / Entreprendre Service Public : https://www.justice.fr/fiche/declaration-suivi-consommations-energie-batiments-secteur-tertiaire-plateforme-operat

## Périmètre fonctionnel

| Fonctionnalité | Statut |
|---|---|
| Référentiel EFA / assujettissement | 🔴 Todo |
| Suivi surfaces tertiaires et activités | 🔴 Todo |
| Consolidation consommations annuelles | 🔴 Todo |
| Tableau trajectoire réglementaire | 🔴 Todo |
| Export annuel pour déclaration | 🔴 Todo |
| Connexion API OPERAT | 🔴 À cadrer avec ADEME/OPERAT |

## Données à modéliser

### EFA / entité fonctionnelle assujettie

Une EFA peut correspondre à un bâtiment complet, une partie de bâtiment, ou un ensemble de bâtiments. Il ne faut donc pas supposer un simple `Building -> EFA` 1-1.

Modèle cible probable :

```python
class OperatEfa(Base):
    __tablename__ = "operat_efas"
    id, city_id
    name: str
    operat_external_id: str | None
    siret: str | None
    activity_category: str | None
    tertiary_surface_m2: float | None
    reference_year: int | None
    reference_consumption_kwh: float | None
    target_2030_kwh: float | None
    target_2040_kwh: float | None
    target_2050_kwh: float | None
```

Relation :
- `OperatEfaBuildingLink` : EFA N-N Building, avec `surface_m2` et `usage_share` si nécessaire.

### Consommations déclarables

Sources Po2 disponibles :
- ENEDIS pour électricité ;
- futur GRDF pour gaz ;
- futur SUEZ/eau si utile ;
- import manuel pour les vecteurs non connectés.

Modèle cible probable :

```python
class OperatAnnualConsumption(Base):
    __tablename__ = "operat_annual_consumptions"
    id, efa_id
    year: int
    energy_vector: str  # electricity, gas, heat, fuel...
    consumption_kwh: float
    source: str  # enedis, invoice, manual, operat_api
    declared_at: datetime | None
    declaration_status: str
```

## API OPERAT — point d'attention

La documentation API détaillée n'est pas à supposer publiquement disponible. Avant développement d'une écriture API :

1. vérifier l'accès OPERAT de l'utilisateur ;
2. récupérer la documentation API officielle ou l'espace développeur associé ;
3. confirmer le mode d'authentification, les endpoints, l'environnement de test, et les responsabilités de déclaration ;
4. implémenter d'abord un mode lecture/export si l'écriture directe n'est pas ouverte.

## MVP conseillé

1. Créer le modèle EFA et lier aux bâtiments.
2. Saisir surfaces, activité, année de référence.
3. Calculer la consommation annuelle à partir des données Po2 disponibles.
4. Afficher un tableau conformité : année, conso, écart à référence, trajectoire 2030/2040/2050.
5. Générer un export CSV/XLSX réutilisable pour OPERAT.
6. Ajouter l'API OPERAT seulement après validation des accès.

## Dépendances

- `Building` / surfaces fiables ;
- ENEDIS stabilisé pour électricité ;
- GRDF futur pour gaz ;
- Baux locataires si certaines EFA concernent des locaux loués ;
- contrats de maintenance et gestion technique pour relier conformité et plan d'actions.
