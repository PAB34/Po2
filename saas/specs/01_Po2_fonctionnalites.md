# Spécifications Fonctionnelles — PatrimoineOp v0.2

## 1. Finalité du produit

PatrimoineOp est une plateforme SaaS multi-collectivités destinée à constituer, fiabiliser et exploiter un **référentiel patrimonial** à partir de sources hétérogènes, en priorité :

* fichiers DGFiP / foncier / locaux des personnes morales,
* géocodage et cartographie,
* données énergétiques ENEDIS, GRDF
* référentiel de durées de vie des équipements et matériaux,
* documents patrimoniaux et, à terme, baux / conventions d’occupation.

La mission première de la plateforme n’est pas uniquement de suivre l’énergie ou les équipements, mais de transformer une donnée patrimoniale brute, absente, dispersée et incomplète en un **patrimoine métier clair, validé et exploitable**.

---

## 2. Principes directeurs

### 2.1 Le bâtiment métier est l’objet central

Un bâtiment dans la plateforme n’est pas créé automatiquement depuis une ligne DGFiP.
Il résulte d’un travail de consolidation métier à partir de plusieurs objets sources :

* lignes DGFiP,
* adresses,
* parcelles,
* objets cartographiques,
* compteurs,
* documents.

### 2.2 La donnée source n’est jamais écrasée

La plateforme distingue :

* **donnée source**
* **donnée consolidée**
* **donnée validée métier**

### 2.3 Le produit doit rester pragmatique

L’objectif du prototype n’est pas de couvrir tous les cas patrimoniaux dès le départ, mais de permettre à une collectivité de :

* voir ses actifs probables,
* les corriger,
* les regrouper,
* les nommer,
* les enrichir,
* les relier ensuite à l’énergie et aux équipements.

### 2.4 Le prototype doit rester déployable à faible coût

Le prototype doit pouvoir être développé et exploité avec un niveau de complexité réduit.

Cela implique :

* un usage possible depuis un poste d’entreprise sans installation locale spécifique,
* un environnement de développement accessible depuis le navigateur,
* une petite production possible sur une infrastructure simple et économique,
* une architecture qui reste portable vers Azure à terme.

---

## 3. Périmètre fonctionnel v0.2

Le prototype est structuré en 4 blocs :

### 3.1 Référentiel de données

* import des sources patrimoniales DGFiP,
* création de candidats bâtiments,
* validation et consolidation en bâtiments métiers,
* rattachement des adresses, parcelles et locaux sources,
* gestion des statuts de validation et niveaux de confiance.

### 3.2 Ingestion

* import fichier DGFiP,
* géocodage et cartographie,
* import du référentiel de durées de vie,
* intégration des données ENEDIS via le socle Fabric existant,
* import manuel CSV/XLSX pour compléments patrimoniaux.

### 3.3 Saisie métier

* correction / fusion / exclusion des bâtiments candidats,
* enrichissement des fiches bâtiments,
* saisie des surfaces de référence,
* inventaire simplifié des équipements et matériaux,
* création d’actions de travaux.

### 3.4 Restitution

* carte patrimoniale,
* liste des bâtiments par statut,
* fiche bâtiment,
* vue énergie,
* vue équipements,
* vue plan pluriannuel de travaux,
* indicateurs qualité des données.

### 3.5 Contraintes de mise en œuvre du prototype

Le prototype doit être conçu pour être exploitable avec une petite charge et un budget d’hébergement limité.

En conséquence :

* le frontend, le backend et la base doivent pouvoir être déployés simplement,
* la solution cible de petite production peut reposer sur un VPS Linux unique,
* le socle technique doit éviter les dépendances bloquantes à un cloud provider unique,
* la migration future vers Azure doit rester possible sans refonte fonctionnelle.

---

## 4. Module 1 — Référentiel patrimonial

## 4.1 Objectif

Permettre à la collectivité de passer d’un fichier DGFiP brut à un référentiel métier exploitable.

## 4.2 Référentiel de données

### Objet `source_dgfip_local`

Table de staging issue du fichier DGFiP.

Champs minimum :

* id
* fichier_source
* date_import
* departement
* code_commune
* nom_commune
* section
* numero_plan
* batiment_source
* entree
* niveau
* porte
* numero_voirie
* indice_repetition
* nature_voie
* nom_voie
* code_droit
* numero_majic
* numero_siren
* groupe_personne
* forme_juridique
* forme_juridique_abregee
* denomination
* adresse_reconstituee
* statut_import

### Objet `batiment_candidat`

Objet intermédiaire créé après géocodage / rapprochement.

Champs minimum :

* id
* collectivite_id
* libelle_propose
* adresse_proposee
* latitude
* longitude
* source_principale
* score_confiance
* statut
* commentaire

### Objet `batiment`

Objet métier validé.

Champs minimum :

* id
* collectivite_id
* code_interne
* nom_metier
* adresse_reference
* latitude
* longitude
* typologie
* statut_juridique
* surface_totale_m2
* surface_chauffee_m2
* surface_reference_energie_m2
* annee_construction
* statut_validation
* created_at
* updated_at

### Objet `batiment_source_link`

Table de relation entre un bâtiment métier et ses sources.

Champs minimum :

* id
* batiment_id
* source_type
* source_object_id
* type_lien
* score_confiance
* valide_par
* valide_le

## 4.3 Ingestion

Étapes fonctionnelles :

1. import du fichier DGFiP départemental,
2. filtrage par SIREN,
3. normalisation de l’adresse,
4. géocodage,
5. création de candidats bâtiments,
6. proposition de regroupements,
7. validation par l’utilisateur.

## 4.4 Saisie métier

L’utilisateur doit pouvoir :

* fusionner plusieurs lignes sources en un bâtiment,
* dissocier un regroupement proposé,
* exclure une ligne non pertinente,
* renommer le bâtiment,
* compléter les champs obligatoires,
* définir un statut :

  * à traiter
  * en cours de qualification
  * validé
  * exclu

## 4.5 Restitution

* carte des candidats bâtiments,
* liste des bâtiments validés / non validés,
* taux de complétude du référentiel,
* vue des sources rattachées par bâtiment,
* alertes sur incohérences d’adresse ou doublons.

---

## 5. Module 2 — Fiche bâtiment

## 5.1 Objectif

Disposer d’une fiche bâtiment métier unique, servant de pivot pour les modules énergie, technique et travaux.

## 5.2 Référentiel de données

La fiche bâtiment doit contenir :

### Identification

* nom métier
* adresse de référence
* commune
* code postal
* latitude / longitude
* statut de validation
* source principale

### Qualification

* typologie
* usage principal
* sous-usage éventuel
* statut juridique
* année de construction
* commentaire général

### Surfaces

* surface totale
* surface chauffée
* surface de référence énergie
* surface tertiaire soumise OPERAT

### Liens

* lignes DGFiP rattachées
* parcelles associées
* compteurs associés
* équipements associés
* documents associés

## 5.3 Saisie métier

* édition simple de la fiche,
* saisie rapide des surfaces,
* gestion de plusieurs adresses ou références rattachées,
* upload photo et documents.

## 5.4 Restitution

* onglet identité,
* onglet sources,
* onglet énergie,
* onglet équipements,
* onglet travaux,
* onglet documents.

---

## 6. Module 3 — Référentiel durées de vie

## 6.1 Objectif

Structurer un référentiel technique commun pour l’inventaire bâtiment et la projection des renouvellements.

## 6.2 Référentiel de données

Le fichier de durées de vie fourni est hiérarchisé et doit être repris comme référentiel métier.

### Objet `ref_duree_vie_equipement`

Champs minimum :

* id_ligne
* source_fichier
* page_source_pdf
* ordre_dans_page
* code_niveau_1
* libelle_niveau_1
* code_niveau_2
* libelle_niveau_2
* niveau_3
* niveau_4
* niveau_5
* equipement
* sypemi_mini_annees
* sypemi_reference_annees
* sypemi_maxi_annees
* votre_proposition_mini_annees
* votre_proposition_reference_annees
* votre_proposition_maxi_annees
* fiche_cee
* actif

## 6.3 Ingestion

* import CSV du référentiel,
* contrôle de structure,
* versionnage,
* activation d’une version de référence.

## 6.4 Saisie métier

Le référentiel doit être utilisable dans les formulaires d’inventaire via :

* listes hiérarchiques,
* recherche par texte,
* proposition automatique de durée de vie de référence.

## 6.5 Restitution

* consultation du référentiel,
* filtrage par niveaux,
* affichage de la durée mini / référence / maxi.

---

## 7. Module 4 — Inventaire technique simplifié

## 7.1 Objectif

Permettre un premier inventaire utile à la gestion patrimoniale et à la priorisation des renouvellements, sans viser l’exhaustivité dès le prototype.

## 7.2 Référentiel de données

### Objet `equipement`

* id
* batiment_id
* ref_duree_vie_id
* categorie
* sous_categorie
* designation
* localisation
* quantite
* marque
* modele
* numero_serie
* annee_installation
* puissance_kw
* debit_m3h
* fluide_frigorigene
* performance
* longueur_m
* epaisseur_mm
* dernier_entretien
* prochain_entretien
* duree_vie_conventionnelle
* date_fin_vie_estimee
* etat
* criticite
* commentaire

## 7.3 Ingestion

* saisie manuelle,
* import CSV/XLSX futur,
* préremplissage via référentiel durées de vie.

## 7.4 Saisie métier

L’utilisateur doit pouvoir :

* ajouter un équipement,
* choisir une catégorie et une désignation,
* renseigner les attributs utiles,
* corriger la durée de vie proposée,
* attribuer un niveau d’état.

## 7.5 Restitution

* liste des équipements par bâtiment,
* filtres par catégorie,
* échéances de fin de vie,
* vue synthétique des équipements critiques.

---

## 8. Module 5 — Plan pluriannuel de travaux

## 8.1 Objectif

Produire une première vision de renouvellement patrimonial à partir des données bâtiment + équipements.

## 8.2 Référentiel de données

### Objet `action_travaux`

* id
* batiment_id
* equipement_id nullable
* type_action
* description
* motif
* urgence
* annee_cible
* statut
* commentaire

### Objet `ppi_ligne`

* id
* collectivite_id
* batiment_id
* action_travaux_id
* exercice
* priorite
* statut_arbitrage
* commentaire

## 8.3 Ingestion

Aucune ingestion externe obligatoire en v0.2.

## 8.4 Saisie métier

* création manuelle d’une action,
* proposition automatique d’actions à partir des équipements en fin de vie,
* priorisation par l’utilisateur.

## 8.5 Restitution

* timeline simple,
* vue annuelle des actions,
* vue bâtiment,
* vue consolidée patrimoine.

> Le chiffrage automatique par coût unitaire est retiré du prototype à ce stade.

---

## 9. Module 6 — Énergie (ENEDIS)

## 9.1 Objectif

Relier les bâtiments validés aux données de comptage et restituer les consommations utiles à l’analyse patrimoniale.

## 9.2 Référentiel de données

### Objet `compteur`

* id
* collectivite_id
* identifiant_externe
* type_energie
* gestionnaire
* statut

### Objet `batiment_compteur`

* id
* batiment_id
* compteur_id
* type_rattachement
* principal
* score_confiance
* statut_validation

### Données de mesure

Les consommations journalières et courbes de charge sont issues du socle Fabric existant.

## 9.3 Ingestion

* les flux ENEDIS sont gérés dans Fabric,
* l’application consomme des tables consolidées,
* le prototype ne refait pas la logique brute d’acquisition dans le backend.

## 9.4 Saisie métier

* rattachement manuel ou assisté PRM ↔ bâtiment,
* validation du rattachement,
* exclusion des faux rattachements.

## 9.5 Restitution

* consommation annuelle,
* comparaison N / N-1,
* courbe de charge,
* ratio kWh/m²,
* classement inter-bâtiments.

---

## 10. Module 7 — Qualité des données

## 10.1 Objectif

Rendre visible l’état réel du référentiel et guider la collectivité dans sa fiabilisation.

## 10.2 Référentiel de données

### Objet `anomalie_donnee`

* id
* objet_type
* objet_id
* type_anomalie
* severite
* description
* statut
* cree_le
* traite_le
* traite_par

## 10.3 Saisie métier

* marquer une anomalie comme traitée,
* commenter,
* requalifier un objet.

## 10.4 Restitution

* bâtiments sans surface,
* bâtiments sans compteur,
* candidats non validés,
* doublons probables,
* équipements sans année d’installation,
* rattachements à faible confiance.

---

## 11. Module 8 — Baux / occupations (phase suivante)

## 11.1 Objectif

Rattacher les contrats d’occupation au référentiel bâtiment.

## 11.2 Périmètre futur

* dépôt de documents,
* extraction IA,
* revue humaine,
* rattachement au bâtiment / lot / local,
* suivi des échéances et montants.

> Ce module est préparé dès la conception, mais n’est pas inclus dans le prototype v0.2.

---

## 12. Onboarding collectivité

### Étapes

1. création du compte collectivité,
2. saisie du SIREN,
3. import des données sources DGFiP,
4. affichage carte des candidats bâtiments,
5. qualification et validation,
6. enrichissement des fiches bâtiments,
7. rattachement des compteurs,
8. démarrage inventaire technique.

---

## 13. Écrans du prototype

### Inclus

* connexion / gestion utilisateurs
* tableau de bord d’accueil
* carte patrimoniale
* liste des bâtiments
* fiche bâtiment
* écran de consolidation des candidats bâtiments
* liste des équipements
* fiche équipement
* vue PPI
* vue énergie bâtiment
* vue qualité des données

### Non inclus

* OPERAT
* import d’audit énergétique
* GTB EN 52120
* analyse IA des baux
* chiffrage automatique détaillé

---

## 14. Indicateurs du prototype

* nombre de lignes sources DGFiP importées
* nombre de candidats bâtiments
* nombre de bâtiments validés
* taux de complétude des fiches bâtiments
* nombre de bâtiments avec compteur rattaché
* nombre de bâtiments avec inventaire technique
* nombre d’actions travaux créées
* consommation totale
* ratio kWh/m²

---

## 15. Critères d’acceptation du prototype

Le prototype est valide si une collectivité pilote peut :

1. importer et visualiser ses données sources patrimoniales,
2. consolider ses bâtiments métiers,
3. compléter les informations essentielles de chaque bâtiment,
4. rattacher au moins une partie des compteurs ENEDIS à ses bâtiments,
5. saisir des équipements majeurs,
6. voir les équipements en fin de vie,
7. produire une première vue de plan pluriannuel de travaux,
8. suivre un niveau minimal de qualité des données.

---

## 16. Priorités de développement

### Priorité 1

Référentiel patrimonial et consolidation des bâtiments

### Priorité 2

Inventaire technique simplifié et durées de vie

### Priorité 3

Rattachement énergie et restitution bâtiment

### Priorité 4

Plan pluriannuel de travaux

### Priorité 5

Baux / occupations et documents avancés