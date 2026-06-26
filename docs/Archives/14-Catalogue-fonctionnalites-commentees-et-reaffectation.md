# 14 - Catalogue des fonctionnalites commentees et reaffectation

> Date : 2026-06-15.
> Objectif : comprendre l'utilite de chaque fonctionnalite deja developpee avant de decider sa reaffectation
> dans la plateforme cible.

Ce document complete :

- [[08-Inventaire-fonctionnalites-developpees-2026-06-02]] : inventaire general du code reel ;
- [[12-Plan-plateforme-cible-et-tri-endpoints]] : vision cible produit et navigation ;
- [[13-Matrice-routes-fonctionnalites-refonte-api]] : matrice technique generee endpoint par endpoint.

La matrice `13` dit **ou est le code**. Ce document dit **a quoi sert la fonctionnalite**.

## 1. Methode de lecture

Une fonctionnalite n'est pas seulement une route API. C'est une capacite utile pour un utilisateur.

Exemple :

```text
Importer une facture fournisseur
= plusieurs endpoints + parser + modeles de donnees + controle + decision + export finance
```

Pour chaque bloc, on documente :

| Champ | Sens |
|---|---|
| Utilite metier | Pourquoi la fonctionnalite existe |
| Decision aidee | Quelle decision ou action elle facilite |
| Utilisateurs | Qui doit pouvoir l'utiliser ou la lire |
| Code actuel | Routeurs, services, pages principales |
| Reaffectation cible | Ou placer la fonctionnalite dans la navigation cible |
| Statut | Ce que l'on peut dire aujourd'hui sans survendre |
| Commentaire | Point de vigilance avant refonte |

## 2. Lecture synthetique

| Bloc developpe | Utilite principale | Domaine cible | Priorite refonte |
|---|---|---|---|
| Authentification et commune | securiser l'acces et filtrer par ville | Administration / socle | Garder discret |
| Patrimoine Site -> Batiment -> Local | base maitre pour rattacher tout le reste | Patrimoine | P0 |
| Rattachement compteurs | relier PRM, PCE et eau au bon niveau patrimonial | Patrimoine + Energie | P0 |
| ENEDIS | lire les consommations electriques et la couverture des donnees | Energie | P1 |
| GRDF | lire les consommations gaz et preparer le controle P1/fourniture gaz | Energie | P1 |
| BPU / TURPE | verifier les prix contractuels et reseau | Energie / referentiels | P0 |
| Factures fournisseurs | controler, decider, exporter vers finance | Energie / finance | P0 |
| CPE DALKIA | piloter P1/P2/P3, factures, cibles, atterrissage | Marches & contrats | P0 |
| Referentiel DALKIA XLSX | transformer l'acte d'engagement en base de controle | Marches / Administration | P0 |
| CVC / equipements | suivre les equipements, controles, F-Gaz, ESP | Technique | P1 |
| Connecteur ENGIE API | potentiel connecteur, non prouve comme usage produit actif | Administration / connecteurs | A arbitrer |
| Pronostics | hors produit | Hors plateforme | Ne pas integrer |

## 3. Socle et administration

### 3.1 Authentification, profil, mot de passe

| Element | Detail |
|---|---|
| Utilite metier | Permettre a chaque utilisateur d'entrer dans la plateforme avec son compte et ses droits. |
| Decision aidee | Aucune decision metier directe : c'est le socle de securite. |
| Utilisateurs | Tous. |
| Code actuel | `routes/auth.py`, `services/auth.py`, `core/security.py`, pages `LoginPage`, `RegisterPage`, `AccountPage`. |
| Routes actuelles | `/api/auth/*`. |
| Reaffectation cible | Garder `/api/auth` ou ranger visuellement dans `Administration > Utilisateurs`. |
| Statut | Coeur utile. |
| Commentaire | Ne pas melanger avec les fonctions metier. L'utilisateur doit rarement voir ce socle sauf pour son profil. |

### 3.2 Commune / tenant

| Element | Detail |
|---|---|
| Utilite metier | Garantir qu'un utilisateur ne voit que les donnees de sa commune. |
| Decision aidee | Evite les erreurs de perimetre et de donnees melangees. |
| Utilisateurs | Administrateur, indirectement tous les utilisateurs. |
| Code actuel | `routes/cities.py`, `services/cities.py`, filtrage `city_id` dans les services. |
| Routes actuelles | `/api/cities`. |
| Reaffectation cible | `Administration > Ville / contexte`, API cible `/api/admin/villes`. |
| Statut | Coeur utile mais discret. |
| Commentaire | A conserver comme regle transversale. La refonte ne doit pas casser le filtrage `city_id`. |

### 3.3 Diagnostics techniques

| Element | Detail |
|---|---|
| Utilite metier | Verifier que l'application repond et aider au diagnostic de production. |
| Decision aidee | Savoir si le probleme vient de l'application ou d'un usage metier. |
| Utilisateurs | Administrateur, support, IA/developpeur. |
| Code actuel | `routes/health.py`, `routes/internal_auth.py`. |
| Routes actuelles | `/api/health`, `/api/internal/*`. |
| Reaffectation cible | `Administration > Diagnostics`, ou rester cache. |
| Statut | Utile, non produit. |
| Commentaire | Ne pas exposer comme une fonctionnalite principale. C'est de l'outillage. |

## 4. Patrimoine

### 4.1 Referentiel Site -> Batiment -> Local

| Element | Detail |
|---|---|
| Utilite metier | Construire la base maitre de la plateforme : tout contrat, facture, equipement ou compteur doit pouvoir remonter au patrimoine. |
| Decision aidee | Savoir quel site/batiment/local est concerne par une facture, une consommation, un equipement ou une action. |
| Utilisateurs | Responsable energie, service energie, technique, direction. |
| Code actuel | `routes/buildings.py`, `services/buildings.py`, modeles `Site`, `Building`, `Local`. |
| Pages actuelles | `BuildingsLandingPage`, `BuildingsPage`, `BuildingsListPage`, `BuildingDetailPage`, `BuildingCreateEditPage`. |
| Routes actuelles | `/api/buildings`, `/api/buildings/sites`, `/api/buildings/{id}/locals`. |
| Reaffectation cible | `Patrimoine`, API cible `/api/patrimoine/sites`, `/api/patrimoine/batiments`, `/api/patrimoine/locaux`. |
| Statut | Coeur produit. |
| Commentaire | C'est la colonne vertebrale. La refonte doit respecter la regle utilisateur : `Site -> Batiment -> Local -> Contrats/Factures/Equipements -> Compteurs`. |

### 4.2 Import et rapprochement DGFiP / IGN / OSM

| Element | Detail |
|---|---|
| Utilite metier | Creer et fiabiliser l'inventaire a partir des donnees fiscales et geographiques. |
| Decision aidee | Eviter les doublons, corriger les noms, rattacher a la bonne geometrie. |
| Utilisateurs | Administrateur, responsable patrimoine/energie. |
| Code actuel | `services/building_naming.py`, endpoints d'import dans `routes/buildings.py`. |
| Pages actuelles | `BuildingCreateEditPage`. |
| Reaffectation cible | `Administration > Imports > Patrimoine`, avec resultat visible dans `Patrimoine`. |
| Statut | Coeur utile. |
| Commentaire | L'import est une action experte. Le resultat doit etre simple : une base patrimoine propre et exploitable. |

### 4.3 Rattachement des compteurs PRM/PCE/eau

| Element | Detail |
|---|---|
| Utilite metier | Relier les compteurs au bon niveau patrimonial pour lire les consommations par site, batiment ou local. |
| Decision aidee | Dire quelle consommation appartient a quel patrimoine et corriger les compteurs non rattaches. |
| Utilisateurs | Service energie, responsable energie. |
| Code actuel | `BuildingMeterLink`, `services/meter_matching.py`, endpoints `routes/buildings.py`. |
| Pages actuelles | `MeterMatchingPage`, fiche batiment. |
| Routes actuelles | `/api/buildings/{building_id}/meters`, routes de matching. |
| Reaffectation cible | `Patrimoine > Rattachements` et `Energie > Compteurs`, API cible `/api/patrimoine/rattachements/compteurs`. |
| Statut | Utile a consolider. |
| Commentaire | Point clef pour la refonte : un compteur doit etre rattachable et modifiable au niveau site, batiment ou local, pas seulement au batiment. |

### 4.4 Fiche patrimoine

| Element | Detail |
|---|---|
| Utilite metier | Donner une vue centrale d'un batiment/local : infos, rattachements, equipements, compteurs, pieces d'identification. |
| Decision aidee | Comprendre rapidement ce qui existe et ce qui manque pour exploiter le site. |
| Utilisateurs | Tous les profils metier. |
| Code actuel | `BuildingDetailPage`, endpoints `routes/buildings.py`, `routes/equipment.py`. |
| Reaffectation cible | `Patrimoine > Fiche site/batiment/local`. |
| Statut | Coeur utile mais UX a clarifier. |
| Commentaire | La fiche doit devenir le point de retour commun : depuis une facture, une consommation ou un equipement, on doit pouvoir revenir au patrimoine. |

## 5. Energie - consommations et distributeurs

### 5.1 Portefeuille PRM et detail electricite

| Element | Detail |
|---|---|
| Utilite metier | Lister les points de livraison electriques et lire les consommations, puissances et donnees associees. |
| Decision aidee | Identifier les derivees de consommation, les puissances inadaptees, les donnees manquantes. |
| Utilisateurs | Service energie, responsable energie, direction en synthese. |
| Code actuel | `routes/energie.py`, `services/energie.py`, services `power_*`, `dju_*`. |
| Pages actuelles | `EnergiePage`, `EnergieDetailPage`, `EnergieRecommendationsPage`. |
| Routes actuelles | `/api/energie/*`. |
| Reaffectation cible | `Energie > Consommations > Electricite`, API cible `/api/energie/consommations/electricite`. |
| Statut | Coeur utile. |
| Commentaire | Les sigles PRM, DJU, puissance doivent rester visibles, avec une courte explication utilisateur. |

### 5.2 Acquisition ENEDIS synchrone

| Element | Detail |
|---|---|
| Utilite metier | Recuperer des donnees ENEDIS de secours ou lancer une reprise controlee sur un petit perimetre. |
| Decision aidee | Savoir si les donnees electriques sont a jour ou si une relance est necessaire. |
| Utilisateurs | Administrateur donnees, service energie avance. |
| Code actuel | `routes/enedis_sync.py`, `services/enedis_sync.py`, `enedis_customer_sync.py`. |
| Routes actuelles | `/api/energie/sync/*`. |
| Reaffectation cible | `Administration > Connecteurs > ENEDIS`, avec resume dans `Energie`. |
| Statut | Utile mais a ne pas mettre trop en avant. |
| Commentaire | C'est de l'exploitation de donnees. L'utilisateur final doit surtout voir la fraicheur et les trous de couverture. |

### 5.3 Acquisition ENEDIS asynchrone FTP/AES

| Element | Detail |
|---|---|
| Utilite metier | Suivre les demandes et fichiers asynchrones ENEDIS. |
| Decision aidee | Savoir quelles donnees sont en attente, recues ou en erreur. |
| Utilisateurs | Administrateur donnees, service energie avance. |
| Code actuel | `routes/enedis_async.py`, `services/enedis_async.py`, scheduler. |
| Routes actuelles | `/api/energie/sync/async/*`. |
| Reaffectation cible | `Administration > Connecteurs > ENEDIS async`. |
| Statut | Coeur technique, depend d'un connecteur externe. |
| Commentaire | Ne pas confondre avec l'analyse energie. C'est la plomberie de collecte. |

### 5.4 Audit de couverture ENEDIS

| Element | Detail |
|---|---|
| Utilite metier | Mesurer les PRM couverts, les donnees absentes et la qualite de la base. |
| Decision aidee | Prioriser les relances et expliquer pourquoi une analyse est incomplete. |
| Utilisateurs | Service energie, responsable energie. |
| Code actuel | `routes/energie.py`, services energie. |
| Page actuelle | `EnergiePage`. |
| Reaffectation cible | `Energie > Qualite des donnees`. |
| Statut | Coeur utile. |
| Commentaire | A faire remonter dans le tableau de bord sous forme de carte "donnees a completer". |

### 5.5 DJU et performance climatique

| Element | Detail |
|---|---|
| Utilite metier | Comparer les consommations au climat pour eviter de juger une annee froide comme une simple derive. |
| Decision aidee | Comprendre si une hausse vient de la meteo, de l'usage, d'un reglage ou d'un contrat. |
| Utilisateurs | Service energie, direction en synthese. |
| Code actuel | `services/dju_sync.py`, routes energie et CPE. |
| Reaffectation cible | `Energie > Performance`, partage avec `Marches & contrats > CPE DALKIA`. |
| Statut | Utile mais attention : les tests locaux signalent des donnees DJU a corriger sur certains parcours CPE. |
| Commentaire | DJU doit etre explique simplement : correction meteo pour comparer deux periodes. |

### 5.6 GRDF, PCE et gaz

| Element | Detail |
|---|---|
| Utilite metier | Lire les points de livraison gaz, consommations et donnees contractuelles GRDF. |
| Decision aidee | Controler le gaz fournisseur et alimenter les analyses P1 CPE DALKIA. |
| Utilisateurs | Service energie, responsable energie. |
| Code actuel | `routes/grdf.py`, `services/grdf_conso.py`, `gas_analytics.py`. |
| Page actuelle | `EnergieGazPage`. |
| Routes actuelles | `/api/grdf/*`. |
| Reaffectation cible | `Energie > Consommations > Gaz`, API cible `/api/energie/distributeurs/grdf`. |
| Statut | Utile, en consolidation. |
| Commentaire | Le gaz doit etre separe entre fourniture gaz hors CPE et P1 gaz CPE DALKIA, car les controles ne sont pas les memes. |

### 5.7 Eau

| Element | Detail |
|---|---|
| Utilite metier | Lire les consommations eau et les factures eau a terme. |
| Decision aidee | Completer la vision multi-fluides et controler les factures eau. |
| Utilisateurs | Service energie, direction. |
| Code actuel | Pas de moteur eau complet identifie ; l'eau apparait dans certains imports CPE multi-fluides. |
| Reaffectation cible | `Energie > Consommations > Eau`, puis `Energie > Factures > Eau`. |
| Statut | A cadrer. |
| Commentaire | Ne pas inventer une API eau sans connaitre fournisseur, format facture, identifiant compteur et logique comptable. |

## 6. Energie - prix, BPU, TURPE

### 6.1 BPU historique

| Element | Detail |
|---|---|
| Utilite metier | Stocker les prix contractuels dans le temps pour verifier les factures au bon tarif. |
| Decision aidee | Dire si le prix facture correspond au prix du marche. |
| Utilisateurs | Responsable energie, comptabilite indirectement, direction en cas d'ecart. |
| Code actuel | `routes/bpu.py`, `services/bpu.py`, tables `bpu_*`, scripts d'import XLSX. |
| Page actuelle | `EnergieBpuPage`. |
| Routes actuelles | `/api/bpu/*`. |
| Reaffectation cible | `Energie > Prix contractuels`, API cible `/api/energie/prix`. |
| Statut | Coeur P0 pour controle facture. |
| Commentaire | BPU doit rester visible comme terme technique, avec explication : bordereau des prix du marche. |

### 6.2 Configuration tarifaire courante

| Element | Detail |
|---|---|
| Utilite metier | Parametrer un fournisseur, ses postes de prix, les plages HP/HC et lignes BPU de repli. |
| Decision aidee | Permettre au controle facture de fonctionner quand le referentiel historique ne suffit pas. |
| Utilisateurs | Administrateur energie, responsable energie. |
| Code actuel | `routes/billing.py`, modeles `BillingConfig`, `BillingPriceEntry`, `BillingHphcSlot`, `BillingBpuLine`. |
| Page actuelle | `EnergieBillingPage`. |
| Reaffectation cible | `Administration > Referentiels > Prix fournisseurs`, avec consultation dans `Energie`. |
| Statut | Utile mais recouvrement a arbitrer avec `bpu_*`. |
| Commentaire | Ne pas supprimer : c'est un repli utile. Mais il faut clarifier la source de verite. |

### 6.3 TURPE

| Element | Detail |
|---|---|
| Utilite metier | Controler la part reglementee reseau de l'electricite. |
| Decision aidee | Distinguer un ecart fournisseur d'un ecart d'acheminement reglemente. |
| Utilisateurs | Responsable energie, comptabilite si ecart. |
| Code actuel | `services/turpe.py`, routes dans `billing.py` et `bpu.py`. |
| Routes actuelles | `/api/billing/turpe/versions`, `/api/bpu/turpe-evolution`. |
| Reaffectation cible | `Energie > Prix > TURPE`. |
| Statut | Coeur utile. |
| Commentaire | A expliquer courtement : tarif reseau electricite, distinct du prix fournisseur. |

## 7. Factures fournisseurs energie

### 7.1 Import factures fournisseurs

| Element | Detail |
|---|---|
| Utilite metier | Charger les factures a controler sans ressaisie manuelle. |
| Decision aidee | Lancer le controle et preparer la transmission finance. |
| Utilisateurs | Responsable energie, service energie. |
| Code actuel | `routes/billing.py`, `services/engie_xlsx_import.py`, `edf_csv_import.py`, parsers facture. |
| Pages actuelles | `EnergieInvoicesPage`, `EnergieInvoiceDetailPage`. |
| Routes actuelles | `/api/billing/invoices/imports/*`. |
| Reaffectation cible | `Energie > Factures fournisseurs > Imports`, API cible `/api/energie/factures/imports`. |
| Statut | Coeur P0. |
| Commentaire | Les fournisseurs ont des specificites. Ne pas faire un controle generique trop pauvre : electricite, gaz, eau et P1 CPE n'ont pas les memes regles. |

### 7.2 Controle facture fournisseur

| Element | Detail |
|---|---|
| Utilite metier | Comparer la facture aux prix, BPU, TURPE, consommations et informations attendues. |
| Decision aidee | Valider, bloquer, demander correction ou transmettre a la comptabilite. |
| Utilisateurs | Responsable energie, comptabilite, direction en synthese. |
| Code actuel | `services/invoice_analysis.py`, `invoice_bpu.py`, `energie_accounting.py`. |
| Routes actuelles | `/api/billing/invoices/imports/{id}/analyze`, routes detail facture. |
| Reaffectation cible | `Energie > Factures fournisseurs > Controle`. |
| Statut | Coeur P0, mais validation fonctionnelle complete non certifiee endpoint par endpoint. |
| Commentaire | C'est le premier parcours a rendre parfait : facture -> controle -> decision -> liaison XLSX. |

### 7.3 Decision facture

| Element | Detail |
|---|---|
| Utilite metier | Garder la trace de la decision prise sur une facture. |
| Decision aidee | Savoir ce qui est a payer, bloque, transmis ou a revoir. |
| Utilisateurs | Responsable energie, comptabilite. |
| Code actuel | `PATCH /api/billing/invoices/imports/{id}/decision`, modeles facture. |
| Reaffectation cible | `Energie > Factures fournisseurs > Decisions`. |
| Statut | Coeur P0. |
| Commentaire | Il faudra probablement historiser les changements et clarifier qui a le dernier mot. |

### 7.4 Matrice comptable et export liaison XLSX

| Element | Detail |
|---|---|
| Utilite metier | Transformer une facture controlee en fichier exploitable par le service finance. |
| Decision aidee | Transmettre une facture avec codification, montant, justification et statut. |
| Utilisateurs | Comptabilite, responsable energie. |
| Code actuel | `services/energie_accounting.py`, routes `/accounting/*`, `/liaison.xlsx`. |
| Routes actuelles | `/api/billing/accounting/*`, `/api/billing/invoices/imports/{id}/liaison.xlsx`. |
| Reaffectation cible | `Energie > Finance`, et `Administration > Matrices comptables` pour le parametrage. |
| Statut | P0, mais test local signale une regression de codification dans une suite CPE/billing selon contexte. |
| Commentaire | "Matrice comptable parfaite" = objectif prioritaire. Ne pas refondre les routes avant de verrouiller le format attendu par la comptabilite. |

### 7.5 Synthese mensuelle et historique

| Element | Detail |
|---|---|
| Utilite metier | Voir les imports, les lots, les consommations et l'historique de traitement. |
| Decision aidee | Savoir ce qui a deja ete importe, controle et transmis. |
| Utilisateurs | Responsable energie, direction en synthese. |
| Code actuel | routes `/api/billing/invoices/batches`, `/consumption-monthly`, `/imports`. |
| Reaffectation cible | `Energie > Factures fournisseurs > Historique`. |
| Statut | Utile. |
| Commentaire | A faire remonter au tableau de bord avec des cartes simples : a controler, transmis, bloque, ecart. |

## 8. Marches & contrats - CPE DALKIA

### 8.1 Sites et consommations CPE

| Element | Detail |
|---|---|
| Utilite metier | Piloter les sites du CPE et leurs consommations multi-fluides. |
| Decision aidee | Comparer reel, cibles, DJU, performance et perimetre contractuel. |
| Utilisateurs | Responsable energie, service energie, direction. |
| Code actuel | `routes/cpe.py`, `services/cpe.py`, `cpe_import.py`, modeles `CpeSite`, `CpeConsoReleve`. |
| Pages actuelles | `CpeDalkiaPage`, `CpeSiteDetailPage`. |
| Routes actuelles | `/api/cpe/sites`, `/api/cpe/consommations/synthese/{annee}`. |
| Reaffectation cible | `Marches & contrats > CPE DALKIA > Performance et consommations`. |
| Statut | Coeur utile, mais certains rattachements sites restent a consolider. |
| Commentaire | Les sites CPE doivent etre relies au patrimoine, sans les fusionner brutalement avec les sites patrimoniaux. |

### 8.2 Factures DALKIA et finances

| Element | Detail |
|---|---|
| Utilite metier | Importer, lire, controler et transmettre les factures DALKIA. |
| Decision aidee | Valider ou bloquer une facture, produire la liaison finance, suivre l'exercice. |
| Utilisateurs | Responsable energie, comptabilite, direction. |
| Code actuel | `services/cpe_finance_preview.py`, `cpe_accounting.py`, routes `/api/cpe/finances/*`. |
| Page actuelle | `CpeDalkiaPage`. |
| Reaffectation cible | `Marches & contrats > CPE DALKIA > Factures et controle`. |
| Statut | Coeur P0, avec quelques tests locaux CPE en echec autour DJU/codification/atterrissage. |
| Commentaire | DALKIA ne doit pas etre traite comme une facture fournisseur simple : P1/P2/P3, revisions, cibles et interesses sont specifiques. |

### 8.3 Controle global factures CPE

| Element | Detail |
|---|---|
| Utilite metier | Recalculer et lire les controles sur l'ensemble des factures CPE. |
| Decision aidee | Identifier les ecarts reels, blocages et factures transmissibles. |
| Utilisateurs | Responsable energie, comptabilite. |
| Code actuel | `build_finance_control_report`, routes `/api/cpe/finances/controls/*`. |
| Reaffectation cible | `Marches & contrats > CPE DALKIA > Controle factures`. |
| Statut | Coeur P0. |
| Commentaire | A exposer comme une file priorisee, pas comme une table technique. |

### 8.4 Matrice comptable CPE

| Element | Detail |
|---|---|
| Utilite metier | Affecter les lignes DALKIA aux natures comptables et sites attendus. |
| Decision aidee | Produire un fichier finance exact. |
| Utilisateurs | Comptabilite, responsable energie. |
| Code actuel | `CpeAccountingNatureRule`, `CpeAccountingSiteMapping`, routes `/api/cpe/accounting/*`. |
| Reaffectation cible | `Administration > Matrices comptables > CPE DALKIA`, avec usage dans `Marches & contrats`. |
| Statut | Coeur P0, mais une suite de test locale a signale un cas de lignes sans nature comptable rattachee. |
| Commentaire | A verrouiller avant toute livraison finance : c'est un point de confiance majeur. |

### 8.5 Atterrissage financier CPE

| Element | Detail |
|---|---|
| Utilite metier | Estimer la fin d'annee : factures deja recues, reste a venir, interesses/penalites, P3. |
| Decision aidee | Anticiper le budget et expliquer la trajectoire a la direction. |
| Utilisateurs | Direction, responsable energie. |
| Code actuel | `services/cpe_atterrissage.py`, `cpe_market_tracking.py`, `cpe_p3_devis.py`. |
| Routes actuelles | `/api/cpe/bilan/{annee}/atterrissage`, `/api/cpe/finances/market-tracking`, `/p3-devis/atterrissage`. |
| Reaffectation cible | `Marches & contrats > CPE DALKIA > Atterrissage`. |
| Statut | Utile mais a corriger : tests locaux signalent des erreurs DJU/interessement. |
| Commentaire | A rendre tres lisible, car c'est une information directionnelle. |

### 8.6 Formules, indices, preuves PDF

| Element | Detail |
|---|---|
| Utilite metier | Justifier les revisions de prix et conserver les preuves. |
| Decision aidee | Accepter ou contester les coefficients appliques. |
| Utilisateurs | Responsable energie, comptabilite en controle. |
| Code actuel | routes `/api/cpe/revision-*`, preuves PDF, application des indices declares. |
| Reaffectation cible | `Marches & contrats > CPE DALKIA > Referentiel finance`. |
| Statut | Coeur utile. |
| Commentaire | Doit rester comprehensible : formule, valeur DALKIA, valeur verifiee, preuve. |

### 8.7 Referentiel DALKIA acte d'engagement XLSX

| Element | Detail |
|---|---|
| Utilite metier | Transformer les fichiers contractuels DALKIA en reference exploitable par les controles. |
| Decision aidee | Verifier P2/P3, cibles, P1 gaz, recap marche, APE, BPU travaux. |
| Utilisateurs | Responsable energie, administrateur donnees. |
| Code actuel | `routes/cpe_dalkia.py`, `services/cpe_dalkia_import.py`, `cpe_dpgf_p1.py`, tables `cpe_dalkia_ref_*`. |
| Page actuelle | `CpeDalkiaImportPage`. |
| Routes actuelles | `/api/cpe/dalkia-ref/*`. |
| Reaffectation cible | `Administration > Imports > DALKIA` pour l'import, puis `Marches & contrats > CPE DALKIA > Referentiel` pour la consultation. |
| Statut | Coeur P0. |
| Commentaire | L'import est expert, mais ses resultats doivent etre consultables sans re-uploader le fichier. |

### 8.8 P3 devis et BPU travaux

| Element | Detail |
|---|---|
| Utilite metier | Suivre les devis et travaux P3, avec prix de reference. |
| Decision aidee | Controler un devis, suivre l'enveloppe, anticiper le reste a charge. |
| Utilisateurs | Responsable energie/maintenance, direction. |
| Code actuel | `services/cpe_p3_devis.py`, BPU DALKIA ref. |
| Routes actuelles | `/api/cpe/finances/p3-devis/*`, `/api/cpe/dalkia-ref/imports/{id}/bpu`. |
| Reaffectation cible | `Marches & contrats > CPE DALKIA > P3 travaux`. |
| Statut | Utile, socle de controle. |
| Commentaire | A ne pas melanger avec SPIE P2 : P3 est propre au CPE DALKIA. |

## 9. Marches & contrats - SPIE P2

| Element | Detail |
|---|---|
| Utilite metier | Suivre un contrat de maintenance preventive P2. |
| Decision aidee | Verifier prestations attendues, equipements couverts, planning, factures P2. |
| Utilisateurs | Responsable maintenance/energie, comptabilite. |
| Code actuel | Pas de moteur SPIE P2 complet identifie dans les routes principales. Les briques CVC/equipements peuvent servir de base. |
| Reaffectation cible | `Marches & contrats > SPIE P2`. |
| Statut | A construire, sans copier le moteur DALKIA. |
| Commentaire | Correction metier importante : SPIE = contrat P2 uniquement. Pas de P1, pas d'interessement energie, pas de logique CPE complete. |

## 10. Technique

### 10.1 Referentiel SYPEMI et equipements

| Element | Detail |
|---|---|
| Utilite metier | Structurer les familles d'equipements techniques et leur rattachement au patrimoine. |
| Decision aidee | Savoir quels equipements existent, ou ils sont, et quels sujets de maintenance ils portent. |
| Utilisateurs | Service technique, responsable energie. |
| Code actuel | `routes/equipment.py`, `services/equipment.py`, modeles `EquipmentReference`, `BuildingEquipment`. |
| Page actuelle | `BuildingTechniquePage`. |
| Routes actuelles | `/api/equipment/*`. |
| Reaffectation cible | `Technique > Equipements`, API cible `/api/technique/equipements`. |
| Statut | Coeur utile. |
| Commentaire | A relier clairement a la fiche patrimoine et aux contrats de maintenance. |

### 10.2 Inventaire terrain CVC

| Element | Detail |
|---|---|
| Utilite metier | Importer et nettoyer les releves terrain CVC. |
| Decision aidee | Identifier les equipements, rattacher les sites, preparer le suivi technique. |
| Utilisateurs | Service technique, responsable energie. |
| Code actuel | `routes/cvc.py`, `services/cvc.py`, modeles `CvcInventoryItem`. |
| Pages actuelles | `CvcImportPage`, `CvcSiteMappingPage`. |
| Routes actuelles | `/api/cvc/imports`, `/api/cvc/items`, `/api/cvc/site-mappings`. |
| Reaffectation cible | `Technique > CVC > Inventaire terrain`. |
| Statut | Coeur utile, matching a surveiller. |
| Commentaire | Garder la difference entre inventaire terrain detaille et synthese SYPEMI. |

### 10.3 Fluides F-Gaz et ESP/DESP

| Element | Detail |
|---|---|
| Utilite metier | Suivre les controles reglementaires et echeances des equipements frigorifiques/pression. |
| Decision aidee | Planifier les controles, reperer les echeances proches, eviter les oublis reglementaires. |
| Utilisateurs | Service technique, responsable energie. |
| Code actuel | `routes/cvc.py`, endpoints refrigerants/dashboard, modeles `cvc_refrigerant_items`. |
| Page actuelle | `CvcRefrigerantsPage`. |
| Reaffectation cible | `Technique > Fluides et controles`. |
| Statut | Coeur utile. |
| Commentaire | A faire apparaitre dans le tableau de bord comme file "echeances techniques". |

### 10.4 Rapport technique CVC

| Element | Detail |
|---|---|
| Utilite metier | Produire une lecture consolidee de l'etat technique. |
| Decision aidee | Prioriser les actions techniques et expliquer les besoins. |
| Utilisateurs | Service technique, direction. |
| Code actuel | `CvcTechnicalReportPage`, routes CVC associees. |
| Reaffectation cible | `Technique > Rapport`. |
| Statut | Utile. |
| Commentaire | Doit rester une synthese decisionnelle, pas seulement un export technique. |

## 11. Connecteurs et surfaces a arbitrer

### 11.1 Proxy API ENGIE

| Element | Detail |
|---|---|
| Utilite metier possible | Recuperer profils, sites, contrats, consommations, factures ou demandes via API ENGIE si le contrat d'acces est reel. |
| Decision aidee | Automatiser une partie des donnees fournisseur. |
| Utilisateurs | Administrateur donnees, service energie. |
| Code actuel | `routes/engie.py`, `services/engie_client.py`. |
| Routes actuelles | `/api/engie/*`. |
| Reaffectation cible | `Administration > Connecteurs > ENGIE`. |
| Statut | Disponible mais non cable comme parcours principal. |
| Commentaire | A ne pas supprimer brutalement. Il faut d'abord confirmer s'il existe un acces API ENGIE utile. Aujourd'hui le flux actif semble etre l'import XLSX. |

### 11.2 Pronostics

| Element | Detail |
|---|---|
| Utilite metier plateforme | Aucune pour PatrimoineAuCarre. |
| Code actuel | `routes/pronostics.py`, services football. |
| Reaffectation cible | Hors plateforme. |
| Statut | Ne pas integrer, ne pas toucher sans demande explicite. |
| Commentaire | Le sortir du produit ne signifie pas le supprimer maintenant. Il faut simplement l'exclure de la navigation et de la refonte metier. |

## 12. Reaffectation cible par navigation

### Tableau de bord

Doit consommer les fonctionnalites sans porter toute la complexite.

Fonctionnalites a y remonter :

- factures energie a controler ;
- factures DALKIA bloquees ;
- fiches de liaison finance a transmettre ;
- atterrissage financier annuel ;
- consommations vs DJU/cibles ;
- compteurs non rattaches ;
- sites marche non relies ;
- echeances F-Gaz/ESP.

### Patrimoine

Fonctionnalites a y ranger :

- sites, batiments, locaux ;
- fiche patrimoine ;
- rattachement compteurs ;
- rattachement contrats/factures/equipements ;
- qualite de referentiel ;
- rapprochements non resolus.

### Energie

Fonctionnalites a y ranger :

- consommations electricite, gaz, eau ;
- PRM/PCE et compteurs ;
- ENEDIS et GRDF en lecture metier ;
- factures fournisseurs ;
- controle BPU/TURPE ;
- matrice comptable energie ;
- preconisations puissance ;
- performance DJU.

### Marches & contrats

Fonctionnalites a y ranger :

- CPE DALKIA ;
- SPIE P2 ;
- contrats de fourniture/maintenance ;
- factures marche ;
- atterrissages financiers ;
- P1/P2/P3 quand le contrat le justifie ;
- references contractuelles.

### Technique

Fonctionnalites a y ranger :

- equipements ;
- inventaire CVC ;
- fluides F-Gaz ;
- ESP/DESP ;
- rapports techniques ;
- lien vers contrats de maintenance.

### Administration

Fonctionnalites a y ranger :

- imports experts ;
- connecteurs ENEDIS/ENGIE/GRDF ;
- matrices comptables ;
- referentiels prix/BPU/TURPE ;
- diagnostics ;
- gestion utilisateurs/ville.

## 13. Ce qui ne doit pas etre fait tout de suite

1. Ne pas renommer massivement les endpoints.
2. Ne pas fusionner brutalement `Site`, `CpeSite` et `CpeDalkiaRefSite`.
3. Ne pas traiter SPIE comme un clone DALKIA.
4. Ne pas cacher les sigles techniques, mais les expliquer.
5. Ne pas supprimer le proxy ENGIE sans confirmation.
6. Ne pas lancer la refonte UX sans avoir verrouille le parcours facture -> decision -> export finance.

## 14. Statut de confiance actuel

Ce document est un **commentaire fonctionnel**, pas une certification que chaque endpoint fonctionne en production.

Verifications locales deja faites le 2026-06-15 :

| Verification | Resultat |
|---|---|
| Compilation backend `python -m compileall app` | OK |
| Generation catalogue API | OK, 279 endpoints detectes |
| Test boot application | OK |
| Suite backend complete SQLite in-memory | 206 passes, 4 echecs, 1 erreur locale de repertoire temporaire |

Echecs fonctionnels a garder en tete avant de refondre :

- codification comptable CPE/factures : cas avec lignes sans nature comptable rattachee ;
- atterrissage CPE : DJU reel a 0 dans certains tests ;
- interessement/penalite CPE : resultat attendu non calcule dans un test ;
- suivi marche CPE : bloc DJU sans donnees dans un test ;
- test ENEDIS async bloque localement par permission de repertoire temporaire, donc non concluant fonctionnellement.

Conclusion :

```text
On peut utiliser cette cartographie pour organiser la refonte.
On ne doit pas encore l'utiliser comme preuve que toutes les APIs sont operationnelles.
```

## 15. Prochaine etape recommandee

Le prochain travail utile est de prendre le parcours P0 et de le detailler de bout en bout :

```text
Facture fournisseur energie
-> import
-> controle BPU/TURPE/conso
-> decision
-> matrice comptable
-> export XLSX finance
-> historique de transmission
-> carte tableau de bord
```

Pour chaque endpoint concerne, on doit ensuite ajouter :

- statut de validation ;
- page front qui l'utilise ;
- service appele ;
- donnees lues/ecrites ;
- route cible ;
- test existant ou test a creer ;
- risque de migration.
