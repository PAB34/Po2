# Module GRDF — API ADICT

> **Source** : `saas/energie/GRDF/GRDFADICT_PROD_v1.12/`
> **Versions documentées** : MODOP Client Connect v1.4 · Swagger B2B v1.9 · Postman B2B v1.9 · Données v1.9 · Erreurs v1.10
> **Synthèse réalisée** : 2026-05-21 par IA (Claude Sonnet 4.6)
> **Ticket** : PO2-GRDF-001 (à créer dans le Backlog)

---

## 1. Vue d'ensemble

**GRDF ADICT** (Accès aux Données Individuelles des Clients par des Tiers) est l'API officielle de GRDF permettant à un **Tiers** (Po2) d'accéder aux données de consommation gaz d'un **Titulaire** (la mairie/collectivité propriétaire du PCE), sous réserve de son **consentement explicite**.

### Acteurs

| Acteur | Rôle |
|--------|------|
| **Titulaire** | Propriétaire du PCE (Point de Comptage et d'Estimation). Donne son consentement. |
| **Tiers** | Po2 — la plateforme qui accède aux données. Peut être `AUTORISE_CONTRAT_FOURNITURE` (avec consentement) ou `DETENTEUR_CONTRAT_FOURNITURE` (si le Tiers est lui-même titulaire). |
| **GRDF** | Fournisseur de données. Gère les droits d'accès, valide les consentements et expose les API. |

### PCE — Point de Comptage et d'Estimation

Le PCE est l'identifiant fondamental de l'API GRDF. Format : `GI + 6 chiffres` ou `14 chiffres`. Équivalent gazier du PRM ENEDIS. Chaque bâtiment avec une alimentation gaz a un PCE.

### Types de compteurs (fréquences de relevé)

| Code | Fréquence | Historique dispo |
|------|-----------|-----------------|
| `6M` | Semestriel | 5 ans (publiées) |
| `1M` | Mensuel | 5 ans (publiées), 3 ans (informatives) |
| `MM` | Mensuel communicant (Gazpar) | 5 ans (publiées), 3 ans (informatives) |
| `JJ` | Journalier | 5 ans (publiées), 3 ans (informatives) |

---

## 2. Authentification — Deux tokens distincts

> **Point critique** : Il existe **deux tokens complètement différents** qui ne sont PAS interchangeables.

### Token 1 — API Data (client_credentials)

Utilisé pour tous les appels API (GDA, CONSO, C&T). Valide **4 heures**.

#### Endpoint SOFIT (recommandé)
```
POST https://sofit-sso-oidc.grdf.fr/openam/oauth2/realms/externeGrdf/access_token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
client_id=<CLIENT_ID_RECU_PAR_MAIL>
client_secret=<CLIENT_SECRET_RECU_PAR_SMS>
scope=/adict/v2
```

#### Endpoint OKTA (alternatif)
```
POST https://adict-connexion.grdf.fr/oauth2/aus5y2ta2uEHjCWIR417/v1/token
(mêmes paramètres)
```

#### Réponse
```json
{
  "access_token": "eyJ...",
  "scope": "/adict/v2 <user_id> <raison_sociale>",
  "token_type": "Bearer",
  "expires_in": 14399
}
```

Usage : `Authorization: Bearer <access_token>` dans tous les appels API.

### Token 2 — Client Connect / Consentement (authorization_code)

Utilisé **uniquement** pour décoder le consentement exprimé par le titulaire via Client Connect. **Ce token ne sert PAS à appeler les API de données.**

```
POST https://adict-connexion.grdf.fr/oauth2/aus5y2ta2uEHjCWIR417/v1/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
client_id=<CLIENT_ID>
client_secret=<CLIENT_SECRET>
code=<CODE_RECU_EN_CALLBACK>
redirect_uri=<URL_CALLBACK_DECLAREE_CHEZ_GRDF>
```

#### Réponse
```json
{
  "access_token": "...",
  "id_token": "<JWT_HS256_contenant_les_consentements>",
  "token_type": "Bearer",
  "expires_in": 14399
}
```

L'`id_token` est un JWT HS256 décodable sur [jwt.io](https://jwt.io). Il contient le détail des consentements accordés par le titulaire.

---

## 3. Flux Consentement — Client Connect (MODOP v1.4)

Le parcours de consentement est une implémentation OAuth2 Authorization Code Flow.

### Étape 1 — Redirection vers GRDF

Po2 redirige le titulaire vers :
```
https://sofit-sso-oidc.grdf.fr/openam/oauth2/realms/externeGrdf/authorize
  ?client_id=<CLIENT_ID>
  &response_type=code
  &scope=openid
  &redirect_uri=<URL_CALLBACK_DECLAREE_CHEZ_GRDF>
  &state=<PARAMETRE_CSRF_OPTIONNEL>
  &login_hint=<prenom>;<nom>;<email>;<NOM_TIERS>
```

> **v1.4** : le séparateur dans `login_hint` est `;` (et non `|` comme dans les versions précédentes).

Le titulaire s'authentifie sur le portail GRDF, sélectionne son PCE, choisit les périmètres de consentement et valide.

### Étape 2 — Callback

GRDF redirige vers :
```
<redirect_uri>?code=XXXXXXXXXXXXXX&iss=https://sofit-sso-oidc.grdf.fr...&client_id=<CLIENT_ID>&state=<STATE>
```

### Étape 3 — Échange du code (optionnel)

Pour décoder les consentements accordés, Po2 échange le `code` contre un `id_token` (voir Token 2 ci-dessus).

### Périmètres de consentement

Le titulaire peut accorder ou refuser :
- `perim_donnees_publiees` — Consommations publiées (définitives, facturées)
- `perim_donnees_informatives` — Consommations informatives (journalières plus récentes)
- `perim_donnees_contractuelles` — Données du contrat (tarif, CAR, profil)
- `perim_donnees_techniques` — Données compteur (adresse, fréquence, calibre)
- `perim_donnees_conso_debut` / `perim_donnees_conso_fin` — Fenêtre temporelle des données
- `date_debut_droit_acces` / `date_fin_droit_acces` — Durée de validité du droit

---

## 4. API GDA — Gestion des Droits d'Accès

Base URL : `https://api.grdf.fr/adict/v2`

### PUT /pce/{id_pce}/droit_acces — Déclarer un droit d'accès

À appeler **après** obtention du consentement. Corps JSON :

```json
{
  "role_tiers": "AUTORISE_CONTRAT_FOURNITURE",
  "nom_titulaire": "Mairie de Sète",
  "code_postal": "34200",
  "courriel_titulaire": "contact@ville-sete.fr",
  "numero_telephone_mobile_titulaire": "0600000000",
  "date_debut_droit_acces": "2026-05-21",
  "date_fin_droit_acces": "2027-05-21",
  "perim_donnees_conso_debut": "2021-01-01",
  "perim_donnees_conso_fin": "2027-05-21",
  "perim_donnees_contractuelles": "Vrai",
  "perim_donnees_techniques": "Vrai",
  "perim_donnees_informatives": "Vrai",
  "perim_donnees_publiees": "Vrai"
}
```

Codes retour :
- `201 / "0000000000"` — Succès, droit actif
- `201 / "0000000002"` — En attente validation titulaire
- `409 / "1000000003"` — Droit déjà existant
- `404 / "1000000006"` — PCE inconnu

`role_tiers` peut aussi être `DETENTEUR_CONTRAT_FOURNITURE` (pas besoin de consentement), `AUTORISE_CONTRAT_INJECTION` ou `DETENTEUR_CONTRAT_INJECTION` (biométhane).

### GET /droits_acces — Consulter tous mes droits

Retourne la liste de tous les droits d'accès du Tiers. Format : `application/x-ndjson` (streaming).

Paramètres optionnels : `?object=<string>&statut_controle=<integer>`

Réponse clé : `liste_acces[]` avec pour chaque droit :
- `id_droit_acces`, `id_pce`, `etat_droit_acces`
- `date_debut_autorisation`, `date_fin_autorisation`
- `perim_donnees_publiees`, `perim_donnees_informatives`, `perim_donnees_contractuelles`, `perim_donnees_techniques`

### POST /droits_acces — Consulter des droits spécifiques

Filtres cumulatifs :
```json
{
  "role_tiers": ["AUTORISE_CONTRAT_FOURNITURE"],
  "etat_droit_acces": ["Active", "A valider"],
  "statut_controle_preuve": ["Preuve Vérifiée OK"],
  "id_pce": ["GI123456", "GI789012"]
}
```

Max 1000 PCE par requête (code `"2000000009"` sinon).

### PATCH /droit_acces/{id_accreditation} — Révoquer un droit

Corps vide `{}`. Réponse `200 / "0000000000"` si succès.

### PUT /droit_acces/{id_droit_acces}/preuves — Transmettre preuves

Upload multipart de 1 à 3 fichiers justificatifs (si GRDF demande validation de preuve). Formats autorisés définis par GRDF.

---

## 5. API CONSO — Données de Consommation

### GET /pce/{id_pce}/donnees_consos_publiees — Consommations Publiées

Données **facturées** (définitives). Historique max : **5 ans**.

```
GET https://api.grdf.fr/adict/v2/pce/{id_pce}/donnees_consos_publiees
  ?periode=2025-01                  # OU
  ?date_debut=2024-01-01&date_fin=2025-01-01
```

Formats calendaires supportés pour `periode` :
- `YYYY` → année entière (ex. `2024`)
- `YYYY-NN` → mois (ex. `2024-01` = janvier 2024)
- `YYYY-WNN` → semaine ISO (ex. `2024-W01`)
- `YYYY-NNN` → jour julien (ex. `2024-001`)

**Réponse JSON (structure complète)** :
```json
{
  "pce": { "id_pce": "GI123456" },
  "periode": {
    "valeur": "2025-01",
    "date_debut": "2025-01-01",
    "date_fin": "2025-01-31"
  },
  "releve_debut": {
    "date_releve": "2025-01-01T06:00:00+01:00",
    "raison_releve": "RNO",
    "qualite_releve": "Mesure",
    "statut_releve": "Normal",
    "index_brut_debut": { "valeur_index": 12345, "horodate_Index": "..." },
    "index_converti_debut": { "valeur_index": 12400, "horodate_Index": "..." }
  },
  "releve_fin": { "... même structure ..." },
  "consommation": {
    "date_debut_consommation": "2025-01-01T06:00:00+01:00",
    "date_fin_consommation": "2025-02-01T06:00:00+01:00",
    "volume_brut": 1234,
    "coeff_calcul": {
      "coeff_pta": 1.012,
      "valeur_pcs": 11.234,
      "coeff_conversion": 11.37
    },
    "volume_converti": 1248,
    "energie": 14189,
    "type_qualif_conso": "Mesuré",
    "sens_flux_gaz": "Consommation",
    "statut_conso": "Définitive",
    "type_conso": "Publiée",
    "journee_gaziere": null
  },
  "statut_restitution": null
}
```

Champs clés pour Po2 :
- `energie` en **kWh** — c'est la valeur principale à stocker
- `volume_brut` en **m³** — index physique du compteur
- `statut_conso` : `"Provisoire"` ou `"Définitive"` — ne stocker que les définitives
- `raison_releve` : codes `RNO`, `NSI`, `CHF1`, `CFR`, `CCP`, `FSI`, `CHF2`, `CHT`, `COM`, `RSP`, `EXP`

### GET /pce/{id_pce}/donnees_consos_informatives — Consommations Informatives

Données **quasi-temps réel** (journalières ou horaires). Historique max : **3 ans**.

Même structure que les publiées, avec :
- `type_conso` : `"Informative Journalier"` ou `"Informative horaire"`
- Plus fraîches mais provisoires (non facturées)

---

## 6. API Injections Biométhane

### GET /pce/{id_pce}/donnees_injections_publiees

Même structure que les consommations publiées, mais pour les **producteurs de biométhane**. Rôle requis : `AUTORISE_CONTRAT_INJECTION` ou `DETENTEUR_CONTRAT_INJECTION`.

`sens_flux_gaz` = `"Production"` (au lieu de `"Consommation"`).

> **Pertinence Po2** : non applicable pour l'instant (Sète = consommateur, pas producteur de biométhane).

---

## 7. API Données Contractuelles

### GET /pce/{id_pce}/donnees_contractuelles

Données du contrat GRDF. Filtres optionnels via `?filtre=car`, `?filtre=cja`, `?filtre=profil_type_actuel`, `?filtre=tarif_acheminement`, `?filtre=date_mes`.

**Réponse** :
```json
{
  "pce": { "id_pce": "..." },
  "donnees_contractuelles": {
    "date_mes": "2010-03-15",
    "tarif_acheminement": "T2",
    "date_publication": "2025-01-15",
    "consommation_journaliere_plafond": 500,
    "car": {
      "car_actuelle": 45000,
      "car_future": 46000
    },
    "cja": {
      "cja": 200,
      "cja_journaliere": 50,
      "cja_mensuelle": 100
    },
    "profil": {
      "profil_type_actuel": "P013",
      "date_debut_profil_type_actuel": "2025-04-01",
      "date_fin_profil_type_actuel": "2026-03-31",
      "profil_type_futur": "P013"
    },
    "modulation": {
      "modulation_n_1": 1200,
      "modulation_n_2": 980,
      "modulation_n_3": 1050,
      "assiette": 1015
    }
  }
}
```

Champs clés :
- **`tarif_acheminement`** : T1 (<6 MWh/an), T2 (6 MWh–300 MWh), T3 (300 MWh–5 GWh), T4 (>5 GWh), TP (proximité), TB (biométhane)
- **`car_actuelle`** (kWh) : Consommation Annuelle de Référence — estimation GRDF de la conso annuelle
- **`profil_type_actuel`** (P000–P019) : profil de répartition saisonnière — P013 à P019 = usage chauffage fort
- **`cja`** : Capacité Journalière d'Acheminement — seulement pour T4/TP/JJ

---

## 8. API Données Techniques

### GET /pce/{id_pce}/donnees_techniques

```json
{
  "pce": { "id_pce": "..." },
  "donnees_techniques": {
    "situation_compteur": {
      "numero_rue": "12",
      "nom_rue": "Rue de la République",
      "complement_adresse": null,
      "code_postal": "34200",
      "commune": "Sète"
    },
    "caracteristiques_compteur": {
      "frequence": "MM",
      "client_sensible_mig": "Non",
      "code_calibre": "G16",
      "code_debit": "25",
      "code_debit_normalise": 25.312,
      "pression_livraison": "21",
      "matricule_compteur": "ABC123456"
    },
    "pitd": {
      "identifiant_pitd": "XYZ001",
      "libelle_pitd": "Réseau Sète Sud"
    },
    "regime_propriete": {
      "regime_propriete_compteur": "GRDF",
      "regime_propriete_convertisseur": null,
      "regime_propriete_poste": null,
      "regime_propriete_enregistreur": null
    }
  }
}
```

---

## 9. Codes d'erreur principaux

### Codes HTTP génériques

| HTTP | Cause typique |
|------|--------------|
| 400 | Absence d'espace entre "Bearer " et le token, ou Bearer mal orthographié |
| 401 | Token absent ou expiré |
| 403 | Paramètre `id_pce` obligatoire manquant |
| 409 | Droit déjà existant, PCE échu, code postal erroné |
| 429 | Quota dépassé — voir portail ADICT pour les limites |
| 503 | Indisponibilité GRDF — consulter [indisponibilités](https://sites.grdf.fr/web/portail-api-grdf-adict/indisponibilites) |
| 504 | Timeout — retenter l'appel |

### Codes métier GDA (Déclarer droit)

| code_statut | HTTP | Signification |
|------------|------|---------------|
| `0000000000` | 201 | Succès |
| `0000000002` | 201 | En attente validation titulaire |
| `1000000003` | 409 | Droit déjà existant |
| `1000000004` | 409 | Contrat gaz échu |
| `1000000005` | 409 | Code postal ne correspond pas |
| `1000000006` | 404 | PCE inconnu |
| `1000000022` | 409 | Périmètre incohérent |
| `2000000007` | 500 | Erreur technique |

### Codes métier CONSO

| code | HTTP | Signification |
|------|------|---------------|
| `1000000` | 200 | Client déménagé, PCE non-accessible |
| `1000001` | 200 | Droit expiré, renouveler le consentement |
| `1000002` | 200/403 | Aucun droit d'accès |
| `1000008` | 200 | Pas de données sur la période demandée |
| `1000009` | 200 | Périmètre ne couvre pas les publiées |
| `1000010` | 200 | Périmètre ne couvre pas les informatives |
| `1000011` | 200 | Preuve de consentement invalide |
| `1000014` | 200 | Titulaire a révoqué son consentement |
| `2000100` | 200 | Erreur partielle — retenter sur la période |

---

## 10. Plan d'intégration Po2

### Schéma de données à créer (migration alembic)

```python
# 0018_add_gas_pce
class GasPce(Base):
    __tablename__ = "gas_pces"
    id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey("cities.id"))
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)
    id_pce = Column(String, unique=True, nullable=False)   # ex. "GI123456"
    role_tiers = Column(String)                            # AUTORISE_CONTRAT_FOURNITURE
    id_droit_acces = Column(String, nullable=True)
    etat_droit_acces = Column(String, nullable=True)       # Active / A valider / Révoquée
    date_debut_droit_acces = Column(Date, nullable=True)
    date_fin_droit_acces = Column(Date, nullable=True)
    # Périmètres accordés
    perim_publiees = Column(Boolean, default=False)
    perim_informatives = Column(Boolean, default=False)
    perim_contractuelles = Column(Boolean, default=False)
    perim_techniques = Column(Boolean, default=False)
    # Données contractuelles cachées
    tarif_acheminement = Column(String, nullable=True)
    car_actuelle = Column(Integer, nullable=True)          # kWh/an
    profil_type = Column(String, nullable=True)            # P013
    frequence_releve = Column(String, nullable=True)       # MM, JJ, 1M, 6M
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class GasConsumption(Base):
    __tablename__ = "gas_consumptions"
    id = Column(Integer, primary_key=True)
    pce_id = Column(Integer, ForeignKey("gas_pces.id"))
    date_debut = Column(Date, nullable=False)
    date_fin = Column(Date, nullable=False)
    energie_kwh = Column(Integer, nullable=True)           # valeur principale
    volume_brut_m3 = Column(Integer, nullable=True)
    statut_conso = Column(String)                          # Provisoire / Définitive
    type_conso = Column(String)                            # Publiée / Informative Journalier
    type_qualif = Column(String)                           # Mesuré / Estimé / Corrigé
    coeff_conversion = Column(Numeric(6, 2), nullable=True)
    journee_gaziere = Column(Date, nullable=True)          # Pour JJ uniquement
    synced_at = Column(DateTime, default=datetime.utcnow)
```

### Flux d'intégration recommandé

#### Phase 1 — Référencer les PCE (manuel)

1. Importer la liste des PCE depuis un fichier fourni par la mairie (analogue à l'import PRM ENEDIS)
2. Créer la table `gas_pces` avec `etat_droit_acces = null` initialement

#### Phase 2 — Consentement batch

Pour chaque PCE :
1. Appeler `PUT /pce/{id_pce}/droit_acces` avec `role_tiers = "AUTORISE_CONTRAT_FOURNITURE"`, email et code postal du titulaire
2. Si `201 / "0000000002"` → le titulaire doit valider via son espace GRDF (email envoyé automatiquement)
3. Requêter `GET /droits_acces` pour surveiller les `etat_droit_acces` qui passent à `"Active"`

#### Phase 3 — Collecte initiale

Une fois les droits actifs :
1. Backfill historique `?date_debut=<aujourd'hui-5ans>&date_fin=<aujourd'hui>` pour chaque PCE
2. Insérer en BDD uniquement les lignes `statut_conso = "Définitive"`

#### Phase 4 — Sync quotidienne

Scheduler journalier :
1. Pour chaque PCE actif, appeler `/donnees_consos_publiees?date_debut=<j-7>&date_fin=<j>` (fenêtre glissante pour rattraper les retards)
2. Upsert sur `(pce_id, date_debut, type_conso)`

### Services backend à créer

```
saas/backend/app/
  services/
    grdf_auth.py          # get_access_token() → cache 4h, refresh auto
    grdf_gda.py           # declare_droit(), list_droits(), revoke_droit()
    grdf_conso.py         # fetch_consos_publiees(), fetch_consos_informatives()
    grdf_contractuel.py   # fetch_donnees_contractuelles(), fetch_donnees_techniques()
  routes/
    gas_pce.py            # CRUD PCE + déclenchement sync
```

### Credentials à obtenir

1. S'inscrire sur [Portail ADICT](https://sites.grdf.fr/web/portail-api-grdf-adict) (inscription Tiers)
2. Recevoir `client_id` par mail et `client_secret` par SMS
3. Déclarer l'URL callback `https://patrimoineaucarre.com/api/grdf/callback` auprès de GRDF
4. Stocker `GRDF_CLIENT_ID` et `GRDF_CLIENT_SECRET` dans `.env` prod **SANS JAMAIS LES COMMITTER**

### Quotas et limites

Les quotas sont définis dans la documentation des Ateliers Fonctionnels disponible sur le portail GRDF ADICT :
- `https://sites.grdf.fr/web/portail-api-grdf-adict/documentation_fonctionnelle`
- Code 429 = quota dépassé → implémenter backoff exponentiel

---

## 11. Différences clés vs ENEDIS

| Aspect | ENEDIS (PRM) | GRDF (PCE) |
|--------|-------------|------------|
| Identifiant | PRM (14 chiffres) | PCE (`GI+6` ou 14 chiffres) |
| Consentement | Via portail ENEDIS | Via Client Connect (OAuth2 web) |
| Token API | client_credentials | client_credentials (idem) |
| Granularité max | 30 min (CDC) | Journalier (JJ) |
| Historique | 3 ans (CDC), 2 ans (index) | 5 ans (publiées) |
| Données contractuelles | Séparées (API C2) | Intégrées (`/donnees_contractuelles`) |
| Async / FTP | Oui (jobs async ENEDIS) | **Non** — API synchrone uniquement |

---

## 12. Ressources

- **Portail GRDF ADICT** : https://sites.grdf.fr/web/portail-api-grdf-adict
- **Documentation fonctionnelle** : https://sites.grdf.fr/web/portail-api-grdf-adict/documentation_fonctionnelle
- **Support utilisateurs** : https://sites.grdf.fr/web/portail-api-grdf-adict/support-utilisateurs
- **Indisponibilités planifiées** : https://sites.grdf.fr/web/portail-api-grdf-adict/indisponibilites
- **Décodeur JWT** : https://jwt.io
- Fichiers source : `saas/energie/GRDF/GRDFADICT_PROD_v1.12/`

---

## 13. État opérationnel & préparation visio GRDF (2026-06-09)

> Analyse de mise en production. Intrants déjà présents dans `saas/energie/GRDF/` :
> contrat signé (`CONTRAT D ACCES AU SERVICE GRDF ADICT.pdf`), spec v1.9 (swagger vérifié
> conforme à ce module), et surtout `modele-donnees.xlsx` = **fichier de déclaration de
> droits en masse rempli** (~50 PCE Commune de Sète, consentement 01/05/2026→01/05/2029,
> accès données depuis 01/01/2024, périmètres conso/contractuel/technique = OUI).

### Le verrou central : modèle de consentement

Deux voies pour déclarer un droit d'accès. Pour les ~50 PCE de Sète, la voie cible est la
**déclaration en masse** (`PUT /pce/{id_pce}/droit_acces`, rôle `AUTORISE_CONTRAT_FOURNITURE`,
email + code postal du titulaire → GRDF envoie un mail de validation → état `Active`), pas le
parcours Client Connect web (lourd à 50 PCE). C'est exactement ce que prépare `modele-donnees.xlsx`.

⚠️ Deux points à clarifier sur le fichier :
- PCE de **formats mixtes** : 14 chiffres (`24355282138581`) ET `GI+6` (`GI091919`).
- Email de validation = adresse **`@dalkia`** → qui est juridiquement titulaire (mairie) vs
  mandataire (DALKIA) ? Point RGPD/acceptation le plus sensible.

### Checklist questions GRDF (visio)

1. `client_id`/`client_secret` actifs en **PROD** ? scope `/adict/v2` ?
2. URL callback à déclarer même en voie « déclaration en masse » ?
3. Déclaration batch confirmée vs Client Connect ? 1 appel/PCE ou endpoint batch ?
4. Validation titulaire par PCE ou globale ? délai ?
5. Adresse de validation DALKIA (mandataire) acceptée ou mairie obligatoire ?
6. Formats PCE mixtes (14 chiffres / `GI+6`) tous valides ?
7. Profondeur réelle : 5 ans publiées + données dispo depuis 01/01/2024 ?
8. **Quotas précis** (429) : req/s, req/h, req/jour ?
9. Fraîcheur des données informatives journalières (J+1 ? J+2 ?) → calage scheduler.
10. Révocation (`1000014`) : push ou polling `GET /droits_acces` ?
11. Flux indisponibilités planifiées à surveiller ?

### Scaffolding livré (Phases 0-1) — 2026-06-09

| Élément | Fichier | État |
|---|---|---|
| Config `grdf_*` (auth, base url, quotas, sync) | `app/core/config.py` | ✅ |
| Auth `GrdfTokenManager` + `RateLimiter` (réutilise `enedis_common`) | `app/services/grdf_auth.py` | ✅ compile + instanciable |
| Modèles `GasPce` / `GasConsumption` | `app/models/gas.py` (+ `__init__.py`) | ✅ enregistrés (SQLite OK) |
| Migration `0049_add_gas_pce_consumption` | `alembic/versions/` | ✅ écrite (down_revision `0048`) |

> Validation locale : `compileall` OK ; import modèles + settings OK via `DATABASE_URL=sqlite:///:memory:`.
> Build frontend non lancé (npm absent du poste). `alembic upgrade head` à passer en CI/prod.

### Reste à faire (post-visio, selon réponses Q3-Q6)

- **Phase 2** : script import `modele-donnees.xlsx` → `gas_pces` ; `grdf_gda.py`
  (`declare_droit`/`list_droits`/`revoke_droit`) ; endpoint `POST /api/grdf/droits/declare-batch`.
- **Phase 3** : `grdf_conso.py` (publiées/informatives) + backfill depuis 2024-01-01 ;
  `grdf_contractuel.py` (CAR, tarif, profil, technique) → enrichit `gas_pces`.
- **Phase 4** : job `_grdf_conso_sync_job` dans `core/scheduler.py` (interval 24h, no-op si
  credentials vides, fenêtre glissante J-7→J, upsert `(pce_id, date_debut, type_conso)`).
- **Phase 5 (valeur métier)** : rapprochement conso GRDF ↔ factures **P1 GAZ DALKIA**
  (jointure `gas_pces.id_pce` ↔ `cpe_dalkia_ref_p1_gaz.pce`) + suivi temporel par bâtiment via
  `BuildingMeterLink`. ⚠️ Conversion kWh (GRDF) ↔ MWh PCI (CPE) à tracer (cf. écart PCS/PCI /1,1068).
