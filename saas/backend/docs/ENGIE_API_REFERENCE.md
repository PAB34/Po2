# ENGIE Entreprises & Collectivités — API Reference

> Source : Swagger `api.entreprises-collectivites.engie.fr/ec/v1`
> Analysé le 2026-05-18 à partir du fichier `saas/energie/ENGIE/SWAGGER/Swagger complet.txt`

## Base URL

```
https://api.entreprises-collectivites.engie.fr/ec/v1
```

## Authentification

**Azure API Management (APIM)** — Clé d'abonnement dans le header.

```
Ocp-Apim-Subscription-Key: <votre_clé>
Content-Type: application/json
Cache-Control: no-cache
```

Variable d'environnement : `ENGIE_SUBSCRIPTION_KEY`

Les endpoints retournent **401 Unauthorized** si la clé est absente/invalide
et **403 Forbidden** si les droits sont insuffisants.

---

## Domaines fonctionnels

| Domaine | Endpoints | Énergie |
|---|---|---|
| **Sites** | 5 endpoints | GAZ + ELECTRICITE |
| **Groupes** | 2 endpoints | — |
| **Contrats** | 2 endpoints | GAZ + ELECTRICITE |
| **Consommations** | 6 endpoints | GAZ + ELECTRICITE |
| **Factures** | 5 endpoints | GAZ + ELECTRICITE |
| **Demandes** | 4 endpoints | GAZ + ELECTRICITE |
| **Profil** | 2 endpoints | — |

---

## 1. Sites

### `GET /sites`
Liste paginée de tous les sites.

| Param | In | Type | Description |
|---|---|---|---|
| offset | query | integer | Décalage (0-indexed) |
| limit | query | integer | Nombre max d'éléments |
| codePostal | query | string | Filtre par code postal |
| referenceClient | query | string | Filtre par référence client |
| groupeId | query | string | Filtre par groupe |

**Response** : `SiteListe` (paginée) → `Site[]`

```json
{
    "paging": { "offset": 0, "currentItems": 0, "total": 0 },
    "liste": [{
        "uid": "string",
        "nom": "string",
        "codePostal": "string",       // DEPRECATED → adresse.codePostal
        "commune": "string",           // DEPRECATED → adresse.ville
        "adresse": { "codePostal": "string", "ville": "string" },
        "referenceClient": "string",
        "dateFinAcces": "string",      // format yyyymmjj
        "groupes": [{ "uid": "string", "nom": "string" }]
    }]
}
```

### `GET /sites/{uid}`
Détail d'un site (inclut la liste de ses groupes).

### `GET /sites/{uid}/details` (V1)
Point de consommation détaillé : puissances souscrites, type compteur, FTA, segment, profil, etc.

```json
{
    "uid": "string",
    "nom": "string",
    "typeEnergie": "GAZ",            // GAZ | ELECTRICITE
    "adresse": { "numeroEtVoie": "…", "codePostal": "…", "ville": "…", "pays": "…" },
    "puissances": {
        "HCD": 0, "HCE": 0, "HCH": 0, "HPD": 0, "HPE": 0, "HPH": 0,
        "JIA": 0, "pointe": 0, "simple": "string"
    },
    "puissancesARENH": [{ "annee": 0, "puissance": 0 }],
    "tarifTransportComptage": "string",
    "FTA": "string",
    "telereleve": true,
    "typeCompteur": "string",
    "compteurCommunicant": "oui/non",
    "frequenceReleve": "SEMESTRIELLE | MENSUELLE | JOURNALIERE | COURBE_DE_CHARGE",
    "branchementProvisoire": false,
    "modeAlimentation": "monophasé | triphasé",
    "segmentElec": "string",          // C1, C2, C3, C4, C5
    "profil": "ADMINISTRATEUR | AVANCE | STANDARD",
    "profilEnNombre": 3,
    "groupes": [{ "uid": "string", "nom": "string" }]
}
```

### `GET /sites/details?uid={uid}` (V2)
Même structure que V1 + champs additionnels :
- `refContratClient`, `refComptaClient`, `refMarche`
- `codeInseeCommuneUtilisatrice`, `codeInseeCommuneContractante`, `codeInseeCommunePayeuse`
- `adresse.codeInseeCommune`

### `GET /sites/{uid}/programmationHoraire`
Programmation horaire actuelle et future.

---

## 2. Groupes

### `GET /groupes`
Liste tous les groupements de sites.

### `GET /groupes/{uid}`
Détail d'un groupe avec ses sites.

---

## 3. Contrats

### `GET /contrats[?siteId]`
Liste des contrats. Filtrable par `siteId`.

```json
{
    "contrats": [{
        "energie": "string",
        "flexibilite": { "basse": 0, "haute": 0, "situation": 0, "type": "string" },
        "nbSites": 0,
        "nbSitesInitial": 0,
        "periode": { "dateDebut": "YYYY-MM-DD", "dateFin": "YYYY-MM-DD", "duree": "string" },
        "reference": "string",
        "typePrix": "string"
    }]
}
```

### `GET /contrats/{uid}/sites`
Sites liés à une proposition commerciale. Inclut `entiteContractante` (raison sociale + adresse).

---

## 4. Consommations

### `GET /consommations`
Liste paginée des consommations par site/groupe/période.

| Param | In | Type | Description |
|---|---|---|---|
| offset | query | integer | Décalage |
| limit | query | integer | Limite |
| groupeId | query | string | Filtre groupe |
| siteId | query | string | Filtre site |
| dateDebut | query | string | YYYY-MM-JJ |
| dateFin | query | string | YYYY-MM-JJ |
| agregationTemporelle | query | string | Agrégation |

**Response** détaillée avec index HP/HC/HPH/HCH/HPD/HCD/HPE/HCE/pointe/JA + relevés + PCE.

### `GET /consommations/foisonne`
Consommation foisonnée (agrégée multi-sites). Même paramètres.

```json
{
    "paging": { "offset": 0, "currentItems": 0, "total": 0 },
    "agregationTemporelle": "string",
    "liste": [{
        "date": "YYYY-MM-DD",
        "unite": "M3 | KWH",
        "facturee": 0,
        "volume": 0,
        "corrigeeDJU": 0,
        "kwhCorrige": 0
    }]
}
```

### `GET /consommations/site/{uid}/courbeDeCharge`
Courbe de charge (énergie active) d'un site.

| Param | Type | Description |
|---|---|---|
| uid | string | **Required** — identifiant site |
| dateDebut | string | YYYY-MM-JJ |
| dateFin | string | YYYY-MM-JJ |
| pasTemporel | string | 10MINUTES, 30MINUTES, HORAIRE, JOURNALIER, MENSUEL |
| unite | string | Unité souhaitée |

```json
{
    "periode": { "debut": "datetime", "fin": "datetime" },
    "pce": "string",
    "liste": [{ "date": "datetime", "valeur": 0.0, "statut": "VALIDE" }],
    "conditionsAtmospherique": {
        "combustion": { "temperature": { "valeur": 0, "unite": "…" }, "pression": { … } },
        "releve": { … }
    }
}
```

### `GET /consommations/site/{uid}/energieReactive`
Courbe d'énergie réactive. Mêmes params que courbeDeCharge (sans `unite`).

### `GET /consommations/site/{uid}/puissanceSouscrite`
Courbe de puissance souscrite. Mêmes params.

### `GET /consommations/site/{uid}/index?dateDebut={}&dateFin={}`
Index mensuels par calendrier distributeur/fournisseur.

```json
[{
    "id": "string",
    "releve": [{
        "index": {
            "energieActive": { "cadran": [{ "indexDebut": "…", "indexFin": "…", "libelle": "…" }], "unite": "…" },
            "energieReactive": { … },
            "puissanceMax": { "cadran": [{ "libelle": "…", "valeur": "…" }], "unite": "…" },
            "depassementQuadratique": { … }
        },
        "periode": { "dateDebut": "…", "dateFin": "…" },
        "typeCalendrier": "DISTRIBUTEUR | FOURNISSEUR",
        "natureIndex": "string",
        "statut": "string"
    }]
}]
```

---

## 5. Factures

### `GET /factures`
Liste paginée des factures.

| Param | In | Type | Description |
|---|---|---|---|
| offset | query | integer | |
| limit | query | integer | |
| groupeId | query | string | |
| siteId | query | string | |
| dateDebut | query | string | Période conso ou édition |
| dateFin | query | string | |
| typePeriode | query | string | consommation ou facturation |

### `GET /factures/{uid}`
Facture ou facture multi-sites par uid.

### `GET /factures/{uid}/details`
Détail complet d'une facture : montants (fourniture, acheminement, taxes, régularisation), consommations par poste tarifaire, puissances, relevés, engagement, dépassement, etc.

```json
{
    "montants": {
        "fourniture": { "pointe": 0, "base": 0, "HPH": 0, "HCH": 0, "HPE": 0, "HCE": 0, "HP": 0, "HC": 0, "Total": 0 },
        "totaux": { "HTVA": 0, "TTC": 0, "HTT": 0 },
        "taxes": { "tva": { "Total": 0 }, "CSPE": 0, "TICFE": 0, "CTA": 0, "TICGN": 0, "CBM": 0, "CTSSG": 0 },
        "acheminement": { "Total": 0, "depassement": 0, "energieReactive": 0,
            "composantes": { "gestion": 0, "comptage": 0, "soutirage": { "partFixe": 0, "partVariable": 0, … } } },
        "regularisation": { "energie": 0, "HP": 0, "HC": 0, "fraisSoutirage": 0 },
        "autre": { "prestationsTechniquesDistributeur": 0, "services": 0, "fraisGestion": 0, "abonnement": 0 },
        "partFixe": 0,
        "partVariable": 0
    }
}
```

### `GET /factures/{uid}/fichier`
Téléchargement du PDF de la facture.

---

## 6. Demandes

### `GET /demandes[?dateDebut&dateFin]`
Liste des demandes/réclamations.

### `GET /demandes/{uid}`
Détail d'une demande.

### `GET /demandes/categories`
Catégories de demandes disponibles (avec éligibilité énergie/profil).

### `POST /demandes`
Création d'une demande.

---

## 7. Profil

### `GET /profil[?sessionId&userId]`
Profil de l'utilisateur connecté (email, nom, prénom, société, marché, segmentMarketing).

### `GET /profils`
Liste des profils rattachés au compte API (contactId + société).

---

## Enums de référence

| Enum | Valeurs |
|---|---|
| **TypeEnergie** | `GAZ`, `ELECTRICITE` |
| **Unite** | `M3`, `KWH` |
| **FrequenceReleve** | `JOURNALIERE`, `MENSUELLE`, `SEMESTRIELLE` |
| **TypeReleve** | `RELEVE`, `AUTO_RELEVE`, `ESTIME` |
| **TypeDocumentFacture** | `FACTURE`, `FACTURE_REGULARISATION`, `FACTURE_RESILIATION`, `AVOIR`, `FIC`, `FUM`, `FMC`, `BORDEREAU` |
| **DemandeStatut** | `OUVERTE`, `EN_COURS`, `TRAITEE`, `ANNULEE` |
| **DemandeCanal** | `ESPACE_CLIENT`, `COURRIER`, `EMAIL`, `TELEPHONE`, `VISITE` |
| **Profil** | `ADMINISTRATEUR`, `AVANCE`, `STANDARD` |
| **ProfilEnNombre** | `3` (admin), `2` (avancé), `1` (standard) |

## Postes tarifaires (consommations & factures)

| Code | Signification |
|---|---|
| base / simple | Tarif unique |
| HP / HC | Heures pleines / creuses |
| HPH / HCH | Heures pleines/creuses hiver |
| HPD / HCD | Heures pleines/creuses demi-saison |
| HPE / HCE | Heures pleines/creuses été |
| pointe | Pointe |
| JA | Juillet-Août |
| PAH | — |

## Pagination

Toutes les listes paginées utilisent `PagingAttributes` :
```json
{ "offset": 0, "currentItems": 0, "total": 0 }
```
Paramètres query : `offset` (décalage 0-indexed) + `limit` (nombre max).

## Points d'attention

1. **Bi-énergie** — ENGIE couvre GAZ et ELECTRICITE dans la même API (contrairement à ENEDIS qui est élec uniquement).
2. **PCE vs PRM** — Le champ `pce` est utilisé pour les deux énergies (PCE gaz / PRM électricité).
3. **Champs DEPRECATED** — Plusieurs champs racine sont dépréciés au profit de sous-objets (`site.pce` remplace `pce`, `adresse.codePostal` remplace `codePostal`, etc.).
4. **V2 Site Details** — Ajoute les codes INSEE et les références contrat/compta/marché. Privilégier V2.
5. **Auth APIM** — Header `Ocp-Apim-Subscription-Key` obligatoire sur chaque requête.
6. **Courbe de charge** — Pas temporels : 10MIN, 30MIN, HORAIRE, JOURNALIER, MENSUEL.
7. **Conditions atmosphériques** — La courbe de charge gaz inclut les conditions de combustion et de relève.
