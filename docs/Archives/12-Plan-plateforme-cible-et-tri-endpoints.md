# 12 - Plan plateforme cible et tri des endpoints

> Date : 2026-06-15.
> Objectif : transformer l'analyse backend ([[11-Analyse-backend-et-socle-refonte-UX]]) en plan produit clair,
> comprehensible pour un debutant, et directement exploitable pour developper une plateforme fonctionnelle,
> pratique et jolie.

## 1. Intention produit

PatrimoineAuCarre doit devenir un **cockpit moderne de pilotage patrimoine, energie, maintenance et finance**.

La plateforme ne doit pas seulement afficher des donnees. Elle doit aider a prendre les decisions frequentes :

- controler les factures et produire les fichiers XLSX de liaison finance ;
- verifier les consommations par rapport au climat (DJU), aux cibles et aux trajectoires ;
- anticiper l'atterrissage financier annuel des tiers facturants ;
- fiabiliser les rattachements entre patrimoine, contrats, factures, equipements et compteurs ;
- rendre les termes techniques visibles, mais comprehensibles par la direction et la comptabilite.

La plateforme doit servir plusieurs profils :

| Profil | Besoin principal |
|---|---|
| Responsable energie / maintenance | piloter les controles, arbitrer, comprendre les ecarts |
| Service energie | analyser consommations, compteurs, DJU, contrats, anomalies |
| Direction | lire une synthese claire, priorisee, financiere |
| Comptabilite | recevoir une fiche de liaison fiable, justifiee, exportable |

## 2. Colonne vertebrale metier

Correction structurante apportee par l'utilisateur :

```text
Site -> Batiment -> Local -> Contrats / Factures / Equipements -> Compteurs
```

Les compteurs ne sont donc pas le niveau intermediaire entre patrimoine et contrats. Ils sont des objets techniques
rattachables au bon niveau patrimonial, et modifiables.

### Regles de rattachement

| Objet | Niveau cible possible | Regle |
|---|---|---|
| Contrat | Site, batiment ou lot de patrimoine selon le marche | doit toujours etre relie au patrimoine |
| Facture | via contrat, site facture ou compteur selon la source | doit pouvoir remonter au patrimoine |
| Equipement | site, batiment ou local | doit servir au pilotage technique et maintenance |
| Compteur PRM/PCE/eau | site, batiment ou local | rattachement manuel ou assiste, modifiable |
| Site marche DALKIA/SPIE | site patrimoine obligatoire | aucun site marche ne doit rester durablement isole |

## 3. Navigation cible

Navigation validee par domaine metier :

```text
Tableau de bord
Patrimoine
Energie
Marches & contrats
Technique
Administration
```

### Principe

- **Tableau de bord** : cockpit principal, a la fois indicateurs et files a traiter.
- **Patrimoine** : referentiel Site -> Batiment -> Local, rattachements, qualite de la base.
- **Energie** : consommations, distributeurs, factures de fourniture, BPU/TURPE, DJU, preconisations.
- **Marches & contrats** : CPE DALKIA, SPIE P2, contrats de maintenance/fourniture, atterrissages financiers.
- **Technique** : equipements, CVC, fluides F-Gaz, ESP/DESP, rapports techniques.
- **Administration** : imports experts, referentiels, matrices comptables, diagnostics, donnees sources.

Les imports doivent etre regroupes dans Administration, sauf lorsqu'une action quotidienne impose de les exposer
dans le parcours metier.

## 4. Tableau de bord cible

L'image fournie est une bonne ebauche, mais elle doit etre rendue plus lisible, plus actionnable et plus elegante.

### Ce qu'il faut garder de l'ebauche

- un cockpit sombre, moderne, avec cartes et priorites ;
- des domaines visibles ;
- des KPI rapides ;
- des files a traiter avec bouton d'action ;
- une lecture mixte : indicateurs + travail concret a effectuer.

### Ce qu'il faut ameliorer

1. **Clarifier l'en-tete**
   - titre : `Tableau de bord`
   - sous-titre : `Factures, consommations, atterrissages financiers et rapprochements`
   - periode visible : mois / trimestre / annee budgetaire.

2. **Separer les indicateurs et les decisions**
   - ligne 1 : sante globale ;
   - ligne 2 : files a traiter ;
   - ligne 3 : trajectoires et finances.

3. **Faire ressortir les priorites**
   - `Urgent` : bloque paiement / ecart reel / echeance proche ;
   - `A traiter` : controle ou rapprochement necessaire ;
   - `A surveiller` : tendance ou derive.

4. **Rendre les cartes plus explicites**
   Chaque carte doit dire :
   - le domaine ;
   - l'objet ;
   - le chiffre ;
   - le risque ;
   - l'action attendue.

### Proposition de structure

```text
Tableau de bord

Filtres globaux :
Annee budgetaire · Periode · Domaine · Tiers facturant · Fluide · Statut

Synthese rapide :
- Factures a controler
- Montant en attente de transmission finance
- Consommations vs DJU / cibles
- Atterrissage financier annuel
- Rattachements patrimoine incomplets

Files prioritaires :
1. Factures energie a controler
2. Factures CPE / maintenance bloquees
3. Fiches de liaison finance a produire
4. Compteurs non rattaches
5. Sites marche non relies
6. Echeances techniques / F-Gaz

Trajectoires :
- Electricite : conso vs DJU / puissance / budget
- Gaz : GRDF + P1 CPE DALKIA + fourniture Herault Energie
- Eau : a cadrer, mais prevue comme fluide de pilotage
- Atterrissage financier par tiers
```

### Cartes recommandees

| Carte | Domaine | Action |
|---|---|---|
| Factures energie a controler | Energie | ouvrir controle factures fournisseurs |
| Fiches finance a transmettre | Energie / Marches | generer XLSX finance |
| Factures DALKIA bloquees | Marches & contrats | ouvrir controle CPE |
| Atterrissage annuel | Marches & contrats | lire previsionnel par tiers |
| Electricite vs DJU | Energie | analyser derive |
| Gaz vs cibles | Energie / CPE | analyser GRDF, P1, DALKIA |
| Eau - couverture a construire | Energie | cadrer source et donnees |
| Compteurs non rattaches | Patrimoine | rapprocher PRM/PCE/eau |
| Sites marche non relies | Patrimoine / Marches | relier DALKIA/SPIE au patrimoine |
| Echeances F-Gaz | Technique | planifier controle |

## 5. Priorite fonctionnelle numero 1

Priorite utilisateur :

> Controle des factures d'energie et de maintenance/fourniture, avec export XLSX fiable vers la comptabilite.

Le controle facture doit couvrir en priorite :

| Perimetre | Specificites |
|---|---|
| Electricite | factures fournisseurs, PRM, ENEDIS, BPU, TURPE, puissance, matrice comptable |
| Gaz Herault Energie | contrat de fourniture, PCE, GRDF, BPU gaz si disponible, matrice comptable |
| Gaz P1 CPE DALKIA | logique CPE specifique, P1, DJU, cibles, atterrissage, factures DALKIA |
| Eau | a cadrer : fournisseur, donnees distributeur, formats facture, matrice comptable |
| Maintenance | contrats de maintenance, SPIE P2, DALKIA P2/P3, controles propres au contrat |

Le livrable finance doit etre parfait :

- matrice comptable fiable ;
- montant controle ;
- statut decision ;
- justification ;
- export XLSX ;
- historique de transmission ;
- separation claire entre les types de contrats.

## 6. Marches et contrats

### CPE DALKIA

DALKIA reste un moteur specifique, parce que le CPE porte :

- P1 energie ;
- P2 maintenance ;
- P3 travaux / gros entretien ;
- cibles de performance ;
- interesses / penalites ;
- revisions contractuelles ;
- atterrissage financier.

### SPIE

Correction importante :

> SPIE n'est pas un clone de DALKIA.

SPIE correspond a un contrat **P2 uniquement**, donc maintenance preventive. Le moteur SPIE doit etre pense comme :

- contrat de maintenance preventive ;
- prestations attendues ;
- equipements couverts ;
- planning / interventions ;
- factures et controles P2 ;
- matrice comptable ;
- rattachement obligatoire au patrimoine.

Il peut partager des composants d'interface avec DALKIA (contrat, factures, matrice, export finance), mais pas le
moteur CPE complet : pas de P1, pas d'interessement energie, pas de cibles CPE, pas de logique P3 DALKIA sauf si
le contrat le prevoit explicitement.

## 7. Sigles techniques : les garder, mais mieux les expliquer

Les sigles doivent rester visibles pour la precision metier, mais ils doivent etre accompagnes d'une explication
courte et orientee communication.

| Sigle | Role dans la plateforme | Explication utilisateur |
|---|---|---|
| PRM | compteur electrique ENEDIS | identifiant du point de livraison electrique |
| PCE | compteur gaz GRDF | identifiant du point de livraison gaz |
| DJU | correction climatique | permet de comparer les consommations en tenant compte de la rigueur meteo |
| BPU | prix contractuels | bordereau des prix du marche, base du controle facture |
| TURPE | tarif reseau electricite | part reglementee d'acheminement de l'electricite |
| P1 | energie dans le CPE | fourniture / cout energie porte par le contrat CPE |
| P2 | maintenance | maintenance preventive et corrective courante |
| P3 | gros entretien / renouvellement | travaux, renouvellements ou provisions selon contrat |
| DPGF | decomposition du prix | reference contractuelle pour verifier les prix factures |
| F-Gaz | fluides frigorigenes | obligations de controle sur les equipements frigorifiques |

Regle UX :

```text
Sigle visible + libelle court + infobulle metier + impact concret.
```

Exemple :

```text
TURPE
Tarif reseau electricite. Part reglementee de la facture, controlee a part des prix fournisseur.
```

## 8. Analyse Routeur -> Prefixe -> Endpoints

Cette analyse doit maintenant servir a trier la plateforme.

| Routeur | Prefixe | Role cible | Decision |
|---|---|---|---|
| `auth` | `/auth` | socle connexion/utilisateurs | garder |
| `cities` | `/cities` | socle ville / tenant | garder discret |
| `health` | `/health` | supervision technique | Administration / diagnostic |
| `internal` | `/internal` | usage technique | cacher produit |
| `buildings` | `/buildings` | patrimoine, sites, batiments, locaux, rattachements | coeur produit |
| `equipment` | `/equipment` | referentiel technique SYPEMI | Technique / Administration |
| `cvc` | `/cvc` | inventaires terrain, fluides, matching technique | Technique |
| `energie` | `/energie` | conso, PRM, preconisations, DJU | Energie |
| `enedis_sync` | `/energie/sync` | acquisition ENEDIS | Administration + Energie donnees |
| `enedis_async` | `/energie/sync/async` | acquisition ENEDIS async | Administration / diagnostic |
| `grdf` | `/grdf` | gaz distributeur, PCE, conso | Energie gaz |
| `billing` | `/billing` | factures fournisseurs, controles, matrices, exports | priorite P0 |
| `bpu` | `/bpu` | prix contractuels, TURPE | Energie + Administration referentiels |
| `engie` | `/engie` | proxy API ENGIE non compris / non cable front | a expliquer, puis mettre en attente |
| `cpe` | `/cpe` | CPE DALKIA, finances, conso, controles, P3 | Marches & contrats |
| `cpe_dalkia` | `/cpe/dalkia-ref` | referentiel contractuel expert DALKIA | Administration + CPE expert |
| `pronostics` | `/pronostics` | hors produit | sortir du recit produit, ne pas toucher |

### Ce que signifie "proxy ENGIE API"

Le proxy ENGIE API est un ensemble d'endpoints backend `/api/engie/*` qui semblent faits pour appeler directement
l'API ENGIE Entreprises : profils, sites, contrats, consommations, factures.

Aujourd'hui, d'apres l'analyse precedente :

- il n'est pas cable dans le front ;
- il etait bloque par un probleme d'abonnement / acces 403 ;
- le controle facture utilise surtout les fichiers importes, pas cette API.

Decision provisoire :

```text
Ne pas supprimer maintenant.
Le ranger comme "connecteur API potentiel", hors parcours utilisateur, jusqu'a decision sur l'acces ENGIE.
```

## 9. Regle de tri des endpoints

Chaque endpoint doit recevoir une des decisions suivantes :

| Decision | Definition | Action |
|---|---|---|
| Garder coeur | indispensable a un parcours utilisateur quotidien | rendre visible et clair |
| Garder support | utile mais technique | cacher dans Administration ou sous-parcours expert |
| Fusionner / simplifier | recouvre un autre endpoint ou une autre notion | documenter puis refactor progressif |
| Mettre en attente | depend d'un acces, fournisseur ou decision | cacher du produit, garder code |
| Supprimer progressivement | sans usage produit confirme | retirer par petits lots testes |
| Hors produit - ne pas toucher | hors plateforme mais a conserver pour l'instant | exclure de la navigation et de l'analyse produit |

Application immediate :

- `pronostics` : hors produit, ne pas toucher ;
- `/engie` : mettre en attente, expliquer ;
- endpoints jamais utilises cote front : supprimer progressivement apres confirmation ;
- imports experts : deplacer vers Administration ;
- endpoints finance/factures : priorite P0.

## 10. Plan d'avancement recommande

### Etape 1 - Cadrer le tableau de bord

Produire une maquette cible plus propre que l'ebauche :

- version desktop ;
- version mobile ;
- cartes prioritaires ;
- vocabulary / infobulles ;
- etats urgent / a traiter / a surveiller.

### Etape 2 - Trier les endpoints par parcours

Ne pas trier par fichier technique. Trier par parcours :

1. Controle facture -> decision -> export XLSX finance.
2. Consommations -> DJU/cibles -> analyse ecart.
3. Atterrissage financier -> prevision fin d'annee.
4. Patrimoine -> rattachement contrats/factures/equipements/compteurs.
5. Technique -> obligations et maintenance.
6. Administration -> imports et referentiels.

Livrable attendu : une matrice exhaustive `fonctionnalite actuelle -> routes/prefixes/endpoints -> code ->
fonctionnalite cible`.

Cette matrice doit repondre a quatre questions :

1. **Ou est le code aujourd'hui ?** routeur, prefixe, endpoint, fichier route, services, schemas, modeles.
2. **A quelle fonctionnalite deja developpee appartient-il vraiment ?**
3. **Dans quelle experience cible doit-il vivre ?** Tableau de bord, Patrimoine, Energie, Marches & contrats,
   Technique, Administration.
4. **Que fait-on de l'endpoint ?** garder, deplacer, fusionner, masquer, mettre en attente, supprimer progressivement.

### Etape 3 - Refaire l'experience utilisateur

Ordre conseille :

1. Tableau de bord cockpit.
2. Navigation a 6 domaines.
3. Page Controle factures unifiee par type de contrat.
4. Matrice comptable et export finance.
5. Rattachement compteurs/site/batiment/local.
6. Atterrissage financier.
7. Administration imports/referentiels.

### Etape 4 - Supprimer progressivement

On ne supprime pas en bloc. On marque, on confirme, on retire par petits lots :

- endpoints sans front ;
- code obsolete ;
- imports historiques inutiles ;
- recouvrements confirmes.

## 11. Refonte proposee des routes, prefixes et endpoints

Oui : il faut attacher toutes les routes aux fonctionnalites developpees, puis proposer une reorganisation cible.
Ce travail doit etre fait avant de refondre massivement l'interface, sinon on risque de repeindre une architecture
encore eparpillee.

### 11.1 Inventaire a produire

Pour chaque endpoint existant :

| Champ | Exemple | Pourquoi |
|---|---|---|
| Routeur actuel | `billing` | localiser l'existant |
| Prefixe actuel | `/api/billing` | comprendre l'organisation technique historique |
| Endpoint | `POST /api/billing/invoices/imports/xlsx` | identifier l'action exacte |
| Fichier route | `api/routes/billing.py` | retrouver le code HTTP |
| Services appeles | `engie_xlsx_import.py`, `invoice_analysis.py` | rattacher la logique metier |
| Modeles / schemas | `EnergyInvoice`, `EnergyInvoiceImportOut` | connaitre les donnees touchees |
| Fonctionnalite actuelle | import factures ENGIE XLSX | parler metier |
| Parcours cible | Controle facture -> decision -> export finance | rattacher a l'UX |
| Domaine cible | `Energie` ou `Marches & contrats` | rattacher a la navigation |
| Decision | garder / deplacer / fusionner / cacher / supprimer | preparer le plan de refonte |

### 11.2 Proposition de grammaire API cible

La future API devrait raconter les domaines metier plutot que l'historique du code.

```text
/api/dashboard
/api/patrimoine
/api/patrimoine/sites
/api/patrimoine/batiments
/api/patrimoine/locaux
/api/patrimoine/rattachements

/api/energie
/api/energie/consommations
/api/energie/compteurs
/api/energie/distributeurs/enedis
/api/energie/distributeurs/grdf
/api/energie/factures
/api/energie/prix
/api/energie/turpe
/api/energie/preconisations

/api/marches
/api/marches/contrats
/api/marches/cpe-dalkia
/api/marches/spie-p2
/api/marches/factures
/api/marches/atterrissages
/api/marches/finance

/api/technique
/api/technique/equipements
/api/technique/cvc
/api/technique/fluides
/api/technique/controles

/api/admin
/api/admin/imports
/api/admin/referentiels
/api/admin/matrices-comptables
/api/admin/connecteurs
/api/admin/diagnostics
```

Ce n'est pas une consigne de renommage immediat. C'est une **cible de lecture**. Les routes existantes peuvent
rester en place pendant la transition, avec des alias ou des facades, pour eviter de casser le front et les tests.

### 11.3 Reattribution proposee des routeurs actuels

| Routeur actuel | Code principal | Fonctionnalites developpees | Domaine cible | Prefixe cible probable |
|---|---|---|---|---|
| `auth` | `routes/auth.py`, `services/auth.py` | connexion, profil, mot de passe | Administration / socle | `/api/admin/auth` ou garder `/api/auth` |
| `cities` | `routes/cities.py`, `services/cities.py` | ville / tenant | Administration / socle | `/api/admin/villes` |
| `buildings` | `routes/buildings.py`, `services/buildings.py`, `building_naming.py`, `meter_matching.py` | sites, batiments, locaux, imports, matching compteurs | Patrimoine | `/api/patrimoine/*` |
| `equipment` | `routes/equipment.py`, `services/equipment.py` | referentiel SYPEMI, equipements batiment | Technique | `/api/technique/equipements` |
| `cvc` | `routes/cvc.py`, `services/cvc.py` | inventaires CVC, matching sites, F-Gaz, ESP, rapport technique | Technique | `/api/technique/cvc`, `/api/technique/fluides` |
| `energie` | `routes/energie.py`, `services/energie.py`, `power_*`, `dju_*` | portefeuille PRM, conso, DJU, preconisations | Energie | `/api/energie/consommations`, `/api/energie/preconisations` |
| `enedis_sync` | `routes/enedis_sync.py`, `services/enedis_*` | acquisition ENEDIS synchrone, DJU | Energie / Administration | `/api/energie/distributeurs/enedis`, `/api/admin/connecteurs/enedis` |
| `enedis_async` | `routes/enedis_async.py`, `services/enedis_async.py` | jobs async ENEDIS FTP/AES | Administration / connecteurs | `/api/admin/connecteurs/enedis/async` |
| `grdf` | `routes/grdf.py`, `services/grdf_*`, `gas_analytics.py` | PCE, conso gaz, contractuel GRDF, rapprochement P1 | Energie gaz | `/api/energie/distributeurs/grdf` |
| `billing` | `routes/billing.py`, `invoice_*`, `energie_accounting.py`, `supplier_registry.py` | factures fournisseurs, controles, decisions, matrice, export finance | Energie + Finance | `/api/energie/factures`, `/api/energie/finance` |
| `bpu` | `routes/bpu.py`, `services/bpu.py`, `turpe.py` | BPU, TURPE, prix contractuels | Energie / referentiels | `/api/energie/prix`, `/api/admin/referentiels/prix` |
| `cpe` | `routes/cpe.py`, `services/cpe_*` | CPE DALKIA, factures, controles, conso, atterrissage, P3 | Marches & contrats | `/api/marches/cpe-dalkia/*` |
| `cpe_dalkia` | `routes/cpe_dalkia.py`, `services/cpe_dalkia_*`, `cpe_dpgf_p1.py` | referentiel contractuel DALKIA, actes, DPGF, diff | Marches / Admin expert | `/api/marches/cpe-dalkia/referentiel`, `/api/admin/imports/dalkia` |
| `engie` | `routes/engie.py`, `services/engie_client.py` | proxy API ENGIE potentiel | Connecteur en attente | `/api/admin/connecteurs/engie` |
| `pronostics` | `routes/pronostics.py`, `services/pronostics.py`, `football_data.py` | jeu hors produit | hors plateforme | ne pas integrer, ne pas toucher |
| `health`, `internal` | `routes/health.py`, `internal_auth.py` | sante technique, auth interne | Administration / technique | `/api/admin/diagnostics` ou garder discret |

### 11.4 Regles de migration

1. **Ne pas renommer brutalement les 279 endpoints.**
   On cree d'abord la matrice et la cible, puis on migre par parcours.

2. **Prioriser les parcours visibles.**
   Le premier lot doit couvrir `controle facture -> decision -> export XLSX finance`, car c'est le besoin P0.

3. **Creer des facades cible si necessaire.**
   Exemple : une future route `/api/energie/factures/a-controler` peut reutiliser le service actuel `billing`
   sans deplacer tout le code immediatement.

4. **Mettre les imports experts sous Administration.**
   Les endpoints peuvent rester dans leur fichier au debut, mais l'UX doit les exposer dans Administration.

5. **Documenter les alias.**
   Pendant la transition, chaque route cible doit indiquer si elle remplace une route historique.

6. **Supprimer seulement apres preuve.**
   Un endpoint est supprimable si :
   - aucun appel front ;
   - pas utilise par script/import ;
   - pas utile pour une fonctionnalite cible ;
   - test ou verification CI OK.

### 11.5 Premier livrable technique recommande

Enrichir `docs/api-cartographie/api_catalog.js` et/ou generer un fichier Markdown avec :

```text
endpoint
route_file
route_line
function_name
router_current
prefix_current
services_detected
schemas_detected
feature_current
domain_target
prefix_target
decision
```

Puis produire :

```text
docs/13-Matrice-routes-fonctionnalites-refonte-api.md
```

Ce document deviendra la table de correspondance entre :

- ce qui existe ;
- le code qui le porte ;
- la fonctionnalite metier ;
- la place cible dans la plateforme ;
- la decision de refonte.

## 12. Questions restantes pour verrouiller le prochain sprint

Repondre a ces questions permettra de passer du cadrage a l'implementation.

### Tableau de bord

1. Sur le tableau de bord, veux-tu voir les montants en `TTC`, `HT`, ou les deux ?
2. La periode principale est-elle l'annee civile, l'exercice budgetaire, ou le trimestre ?
3. Les cartes doivent-elles afficher les montants par fournisseur/titulaire, par fluide, ou par site ?

### Controle factures

4. Pour la comptabilite, quel est le format exact attendu du fichier XLSX final ?
5. Une facture validee doit-elle etre verrouillee, ou modifiable avec historique ?
6. Qui a le dernier mot : service energie, comptabilite, direction ?

### Eau

7. Le fournisseur eau est-il SUEZ uniquement ?
8. As-tu des factures eau PDF/XLSX/CSV exploitables ?
9. Existe-t-il un identifiant compteur eau equivalent PRM/PCE ?

### Patrimoine et rattachements

10. Un compteur peut-il alimenter plusieurs batiments ou locaux ?
11. Un contrat peut-il couvrir plusieurs sites avec une repartition comptable differente ?
12. Veux-tu une boite "objets non rattaches" commune, ou une file separee par domaine ?

### Design

13. Faut-il garder le theme sombre comme experience principale ?
14. La direction doit-elle avoir une vue simplifiee, sans details techniques ?
15. Veux-tu que l'interface soit orientee "cartes cockpit" ou "tableaux denses avec filtres" selon les pages ?

## 13. Definition du succes

La refonte sera reussie si :

- l'utilisateur sait quoi traiter en ouvrant la plateforme ;
- une facture peut etre controlee, decidee et transmise finance sans manipulation externe ;
- les consommations sont lisibles par fluide, par site et par meteo ;
- les contrats/factures/equipements/compteurs sont rattaches au patrimoine ;
- les sigles techniques restent exacts mais deviennent communicables ;
- les imports experts ne parasitent plus l'usage quotidien ;
- chaque endpoint a une raison claire d'exister.
