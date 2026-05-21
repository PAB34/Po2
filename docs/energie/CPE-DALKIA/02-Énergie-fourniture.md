# Énergie — Fourniture et rôles

tags: #énergie #gaz #électricité #ENEDIS #GRDF #HéraultÉnergie

---

## Cartographie des responsabilités

| Énergie | Fournisseur | Gestionnaire réseau | Qui contracte | Données conso |
|---------|-------------|---------------------|---------------|---------------|
| **Gaz** | Choisi par DALKIA via consultation | GRDF (réseau distribution) | **DALKIA** (mandaté) | API GRDF ADICT |
| **Électricité** | EDF / ENGIE via Hérault Énergie | ENEDIS | **Ville de Sète** | API ENEDIS |

> **Point critique** : La PSE (Prestation Supplémentaire Éventuelle) qui aurait confié la gestion de l'électricité à DALKIA **n'a pas été retenue** par la collectivité (décision acte OUV11). La Ville reste maître de ses contrats électricité.

---

## Gaz — Rôle de DALKIA (P1)

### Achat
- DALKIA lance une consultation auprès des fournisseurs de gaz
- Première consultation **avant le 30 septembre 2025** (pour démarrage 13/10/2025)
- Durée contrat gaz initial : **13/10/2025 → 31/12/2027** (indexé PEG)
- Option SWAP en prix fixe possible à la prise d'effet (décision concertée PA + DALKIA)
- Renouvellement tous les 2 ans minimum (avant l'échéance du contrat fournisseur)

### Transparence contractuelle
- DALKIA remet copies des factures fournisseurs **chaque trimestre**
- Bilan mensuel des achats d'énergie transmis en **format EXCEL + CSV**
- Veille tarifaire permanente : tableau comparatif des fournisseurs, rapport semestriel minimum
- Tout nouveau contrat de fourniture formalisé par **Ordre de Service** du PA

### Indexation prix gaz
```
Pugaz = Pugaz0 × (a + b×PEG/PEG0 + c×TVD/TVD0 + d×CEE/CEE0 + e×TICGN/TICGN0)
```
- Coefficients calculés en fonction de la quote-part réelle de chaque composante
- Une formule par typolog tarifaire (T1, T2, T3, T4)
- TVD, TICGN, CEE : évoluent à l'euro/l'euro des factures fournisseur

### Facturation P1 chauffage
```
P1 = QT × Pugaz
```
- QT = consommation théorique contractuelle (en MWhPCI) définie en Annexe 6 de l'AE
- 3 acomptes aux 31/03, 30/06, 30/09 (chacun = ¼ du P10)
- Décompte définitif avant le **15 février** de l'année N+1

---

## Électricité — Rôle de la Ville

### Contrat cadre
- Contrat cadre **Hérault Énergie** (syndicat d'énergie de l'Hérault)
- Fournisseurs : **EDF** et **ENGIE** selon les sites
- La Ville reste maître d'ouvrage des contrats électricité

### Données de consommation pour le CPE
- Accès aux index via l'**API ENEDIS** (déjà opérationnelle côté Po2)
- DALKIA vérifie ses engagements électricité via protocole **IPMVP option B**
- DALKIA fournit un rapport IPMVP avant le **31 janvier** de chaque année
- Objectif : vérification de la réduction des consommations électricité liées aux APE

---

## GRDF ADICT — Accès API gaz

> **Statut (mai 2026)** : En attente de formation et fourniture des droits d'accès par GRDF

### Ce que permet l'API GRDF ADICT
- Relevés de consommation gaz par point de comptage (PCE)
- Données journalières et horodatées
- Indices compteurs
- Courbes de charge (selon abonnement)

### Architecture d'intégration prévue dans Po2
- Authentification OAuth2 (spécifique GRDF)
- Stockage des PCE par site dans le modèle `Building`
- Synchronisation journalière via tâche cron
- Lien avec calcul intéressement DALKIA (calcul NC mensuel/annuel)

---

## ENEDIS — Accès API électricité

- API déjà intégrée dans Po2 (module énergie MVP)
- Données de consommation électrique par PDL (Point de Livraison)
- Utilisé pour suivi cibles électricité (IPMVP option B)
- Également utile pour détecter les dérives de consommation électrique des équipements CVC (auxiliaires gérés par DALKIA)

---

## Liens
- [[01-Structure-du-marché]] — rôle P1 dans la structure financière
- [[03-Cibles-et-intéressement]] — utilisation des données gaz dans le calcul NC/N'B
- [[07-GTC-et-données]] — intégration des données énergie avec la GTC/GTB
