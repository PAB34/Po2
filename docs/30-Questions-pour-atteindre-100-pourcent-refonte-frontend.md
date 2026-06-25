# 30 - Questions pour atteindre 100 % de préparation à la refonte frontend

> Date : 2026-06-24  
> Point de départ : **57/100** pour construire et raccorder le frontend définitif.  
> Objectif : rendre la première tranche de refonte suffisamment décidée, documentée et vérifiée pour être développée puis déployée sans improvisation.
## Consolidation après réponses — 2026-06-24

Le questionnaire est traité. Les réponses portent la **couverture des arbitrages à 95/100**.

Ce score mesure les décisions prises et les preuves disponibles. Il ne signifie pas encore que le frontend raccordé est prêt à 95 % : les contrats d'écran, le raccordement API, la recette réelle et les états d'interface restent à produire par Codex.

| Bloc | Obtenu | Lecture |
|---|---:|---|
| A — Gouvernance et profils | 10/10 | Profils et responsabilités V1 suffisamment définis. |
| B — Factures et comptabilité | 13/13 | CIRIL est explicitement hors intégration ; la plateforme prépare la transmission aux finances. Audit de la matrice DALKIA réalisé. |
| C — Contrats et technique | 4/7 | Circuit P3 fixé ; revalidation P1/P2/P3 et pièces SPIE encore attendues. |
| D — Expérience utilisateur | 6/6 | Direction visuelle, navigation, densité et priorité ordinateur validées. |
| E — Recette et migration | 5/7 | Périmètre et stratégie validés ; jeux de recette réels non encore constitués. |
| **Total avec socle** | **95/100** | **5 points restent liés à des preuves ou revalidations.** |

### Points restant ouverts

- `R13 · 2 pts` : revalider séparément les contrôles contractuels DALKIA P1, P2 et P3 à partir des pièces et des données réelles ;
- `R14 · 1 pt` : recevoir et analyser le corpus SPIE faisant foi ;
- `R27 · 2 pts` : constituer et localiser les jeux de recette réels.

### Garde-fou Fluides — obligatoire mais non prévu dans le barème initial

Le premier périmètre de production inclut désormais `Fluides`. La carte fonctionnelle couvre déjà ENEDIS, GRDF, DJU, projections de consommation et conversion en euros, mais cela ne suffit pas à raccorder le frontend définitif. Avant de déclarer la préparation complète, Codex doit produire un contrat d'écran Fluides précisant :

- les vues globales et les accès au détail compteur/site ;
- les séries, pas de temps, périodes comparées et règles de couverture ;
- le rôle interfonctionnel des DJU ;
- les formules d'atterrissage kWh puis euros ;
- les sources ENEDIS, GRDF et facturation utilisées par chaque calcul ;
- les états incomplet, périmé, non rattaché et non calculable.

Tant que ce contrat n'est pas validé, le score documentaire peut être élevé mais la mise en production de `Fluides` reste bloquée.

Les six questions Fluides du document 33 sont répondues. Le contrat d'écran est livré dans le document 34 et sa maquette est intégrée au prototype.


## Ce que signifie 100 %

`100 %` ne signifie pas que l'eau, OPERAT, BACS, tous les marchés et toutes les fonctions futures seront terminés. Cela signifie que :

- le périmètre de la première version est fermé ;
- les profils, droits et workflows sont décidés ;
- les données et API nécessaires sont connues ;
- le design et les contrats d'écran sont validés ;
- des cas réels permettent de tester ;
- la migration de l'ancien frontend vers le nouveau possède une stratégie sûre.

Le développement des fonctionnalités encore absentes continuera ensuite par tranches verticales.

## Mode d'emploi

- `👤 Métier` : ta décision ou celle d'un utilisateur de la collectivité est nécessaire.
- `📎 Preuve` : un fichier, un export ou un cas réel doit être fourni et analysé.
- `🤖 Codex` : je dois auditer, proposer ou réaliser le travail technique ; tu valides seulement le résultat.
- Tu peux écrire `Proposition validée` lorsque ma recommandation te convient.
- Les points sont acquis uniquement lorsque la réponse est validée **et**, si demandé, la preuve disponible.

## Barème de progression

| Score | Signification |
|---:|---|
| 57 | Situation actuelle : prototype convaincant, raccordement encore insuffisamment cadré. |
| 70 | Socle visuel et composants communs peuvent être développés sereinement. |
| 80 | Première tranche verticale raccordée peut commencer. |
| 90 | Parcours testable sur staging avec des données représentatives. |
| 100 | Première tranche prête pour une mise en production progressive et mesurable. |

---

## Bloc A — Gouvernance, profils et responsabilités · 10 points

| ID  | Pts | Responsable | Question à fermer                                                                                     | Recommandation de départ                                                                                                                                                                   | Ta réponse / décision                                                                                                                                                                                                                                                              |
| --- | --: | ----------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R01 |   2 | 👤 Métier   | Le profil `Maintenance` est-il autonome ou intégré au profil `Technique/CVC` ?                        | Intégrer Maintenance dans Technique/CVC en V1, avec une vue dédiée, sauf si deux personnes différentes portent réellement ces responsabilités.                                             | **Réponse :** `Proposition En fait ce profil serait plutot celui de mon responsable de service qui à la charge de valider les devis P3. Ca seul fonction est donc pour l'instant celle-ci. En tant que responsable de service il a un accès tout ce qui se passe sur la plateforme |
| R02 |   2 | 👤 Métier   | Le portail tiers DALKIA pour déposer les devis P3 appartient-il à la première version de la refonte ? | Le placer en phase 2. Commencer par un dépôt interne/import contrôlé afin de ne pas bloquer la refonte sur l'authentification d'un tiers.                                                  | **Réponse :** `Proposition validée`                                                                                                                                                                                                                                                |
| R03 |   2 | 👤 Métier   | Quelles modifications peuvent être déléguées sans validation de l'Administrateur général ?            | Déléguer au responsable de domaine les contacts, rattachements, commentaires et décisions de son périmètre ; réserver utilisateurs, rôles et référentiels transversaux à l'administrateur. | **Réponse :** `Proposition validée`                                                                                                                                                                                                                                                |
| R04 |   2 | 👤 Métier   | Quelles données doivent être invisibles ou limitées selon le profil ?                                 | Lecture large pour patrimoine, consommations et contrôles ; restriction des données personnelles, paramètres, brouillons sensibles et actions financières.                                 | **Réponse :**`Proposition validée`                                                                                                                                                                                                                                                 |
| R05 |   2 | 👤 Métier   | Qui gère les contacts entreprise DALKIA P2/P3 et SPIE ?                                               | Profil Technique/CVC pour P2/P3 et SPIE ; profil Fluides pour Hérault Énergie, eau et DALKIA P1.                                                                                           | **Réponse :**`Proposition validée`                                                                                                                                                                                                                                                 |

**Sous-total validé :** `10/10`

---

## Bloc B — Factures, CIRIL et matrice comptable · 13 points

| ID  | Pts | Responsable | Question ou preuve attendue                                                                                                     | Recommandation de départ                                                                                                                                                         | Ta réponse / décision                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| --- | --: | ----------- | ------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R06 |   2 | 👤 Métier   | À quelle étape exacte une facture devient-elle définitivement `traitée` ?                                                       | Décision consolidée : après décision métier et transmission au service finances. Conserver séparément `importée`, `contrôlée`, `décidée`, `transmise aux finances`, `traitée`, `rejetée` et `réouverte` ; aucun statut CIRIL n’est synchronisé. | **Réponse :**`Proposition validée`                                                                                                                                                                                                                                                                                                                                                                                                                            |
| R07 |   2 | 👤 Métier   | Qui peut réouvrir une facture et pour quels motifs ?                                                                            | Comptable responsable, responsable de marché et administrateur ; motif obligatoire parmi rectificatif, avoir, nouvelle preuve, erreur de rattachement ou décision corrigée.      | **Réponse consolidée :** tous les profils internes V1, avec motif obligatoire, horodatage et conservation de la décision précédente                                                                                                                                                                                                                                                                                                                                                                                                                                |
| R08 |   2 | 📎 Preuve   | Peux-tu obtenir un export CIRIL réel et anonymisé comportant budget, engagements, services faits, mandats et paiements ?        | Décision consolidée : aucun export CIRIL n'est requis en V1 ; la plateforme prépare une transmission libre au service finances.                                                   | **Réponse / emplacement du fichier :** En fait on en a pas besoin de traiter cela car la fiche navette que la comptable envoi au service finance ne respecte aucun gabarit, dictionnaire ou autre. C'est ce seul cas ou un import sur ciril est réalisé.                                                                                                                                                                                                      |
| R09 |   2 | 👤 + 📎     | Quelle granularité budgétaire fait foi : numéro d'opération seulement, ou également service, fonction, nature, marché et site ? | Conserver le numéro d'opération comme pivot budgétaire, puis permettre le drill-down analytique sur service, fonction, nature, marché, antenne et site.                                 | **Réponse :** L'écriture budgétaire se fait uniquement sur le numéro d'opération, le reste ; service, fonction, nature, marché ; c'est pour un analyse plus fine des dépenses ce qui est intéressant aussi mais le budget n'est pas écrit à ces niveaux là. Donc intéressant pour une lecture informative par exemple des antennes les plus consommatrices de budget, oui parce qu'il y a aussi le champs "Antenne" qui définit le site/bâtiment consommateur |
| R10 |   2 | 🤖 Codex    | Quelles clés permettent de rapprocher sans ambiguïté budget, engagement, facture, mandat, fournisseur et site ?                 | Auditer le fichier comptable DALKIA ; produire une table de correspondance versionnée et signaler tout rapprochement incertain. CIRIL est hors périmètre V1.                             | **Validation attendue :** audit Codex réalisé le 2026-06-24 ; conclusions dans le document 32.                                                                                                                                                                                                                                                                  |
| R11 |   2 | 👤 Métier   | À quelle fréquence les données CIRIL doivent-elles être actualisées ?                                                           | Décision consolidée : aucune donnée CIRIL n’est importée ou actualisée dans la plateforme en V1.                                                  | **Réponse :** Ici on ne doit pas se poser la question, seul la comptable reçoit les notifications des factures sur CIRIL, nous n'avons pas à lui rappeler ou à agir sur CIRIL                                                                                                                                                                                                                                                                                 |
| R12 |   1 | 👤 Métier   | En cas d'écart entre facture importée, décision plateforme et statut CIRIL, quelle source fait foi ?                            | Décision consolidée : la plateforme fait foi pour le contrôle métier et la transmission aux finances ; elle ne représente ni le paiement ni le statut CIRIL.                                                         | **Réponse :** Une fois que la comptable à traiter la facture sur notre plateforme elle aura juste à modifier le statut dans CIRIL à lamain, il ne peut y avoir de différences.                                                                                                                                                                                                                                                                                |

**Sous-total validé :** `13/13`

---

## Bloc C — Contrats, maintenance et technique · 7 points

| ID  | Pts | Responsable   | Question ou preuve attendue                                                                                                                    | Recommandation de départ                                                                                                                                                | Ta réponse / décision                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| --- | --: | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R13 |   2 | 🤖 Codex + 📎 | Quelles règles, tolérances et preuves contrôlent réellement DALKIA P1, P2 et P3 ?                                                              | Construire trois matrices distinctes à partir des pièces contractuelles et de `export_maintenance_20260624.csv`, sans appliquer une règle générique aux trois familles. | **Validation attendue :** `À analyser par Codex` Oui mais ce travail avait déjà été réalisé mais à revalider                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| R14 |   1 | 📎 Preuve     | Où se trouve la liste contractuelle SPIE faisant foi pour les bâtiments et équipements couverts ?                                              | Utiliser la pièce de marché ou l'annexe la plus récente, versionnée avec date d'effet ; ne pas déduire la couverture du seul inventaire CVC.                            | **Réponse / emplacement :** Alors pour l'instant j'ai rien fourni mais je devrai fournir à CODEX le CCTP + CCAP + Acte d'engagement pour valider le périmètre et les modalités de facturation. Je fournirai ensuite le listing des sites actés, le listing des sites mis à jour par ordre de service ainsi que la liste des équipements associés. Au niveau des pièces marché il y a une DPGF comme pour DALKIA qui est modifié selon les ordres de services ou avenant. Mais à ce stade on ne prévoit rien car cela nécessite un travail de profondeur par codex |
| R15 |   1 | 👤 Métier     | Le niveau `local` doit-il influencer la couverture contractuelle ou seulement documenter l'emplacement d'un équipement ?                       | Calculer d'abord au bâtiment et à la famille d'équipement ; utiliser le local comme précision, sauf clause contractuelle contraire.                                     | **Réponse :** `Proposition validée`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| R16 |   2 | 👤 Métier     | Quel est le circuit exact d'un devis P3 ou d'un ordre de service : dépôt, contrôle BPU, validation technique, validation Direction, émission ? | Dépôt/import → contrôle automatique BPU → instruction Technique/CVC → validation Direction si impact budgétaire → émission et archivage.                                | **Réponse :** Dépôt/import → contrôle automatique BPU → instruction Technique/CVC → validation responsable de service maintenance si impact budgétaire → émission et archivage. règle : Si le devis P3 est inférieur à 1000 € et s'il respecte le BPU alors il est automatiquement bon pour accord auprès du titulaire du marché + notification au responsable de service maintenance. Pour tout devis supérieur alors besoin de validation du responsable de service maintenance                                                                                 |
| R17 |   1 | 👤 Métier     | Qui peut modifier la criticité CVC et le coût prévisionnel d'une action du PPT ?                                                               | Technique/CVC propose et justifie ; Direction arbitre l'année et l'enveloppe ; l'historique des valeurs est conservé.                                                   | **Réponse :** Technique/CVC  + Responsable de service maintenance propose et justifie                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |

**Sous-total validé :** `4/7`

---

## Bloc D — Validation de l'expérience utilisateur · 6 points

| ID  | Pts | Responsable | Question à fermer                                                                                                                                                                                               | Recommandation de départ                                                                                                                                   | Ta réponse / décision                                                                                                                                                                                                                                                                |
| --- | --: | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| R18 |   1 | 👤 Métier   | Le langage visuel du prototype, réaligné sur la charte PO², devient-il la direction officielle de la refonte ?                                                                                                  | Conserver sa structure puis appliquer le bleu nuit `#1D3150`, le vert accent `#74B44A`, les gris techniques et la typographie définis dans le document 31. | **Réponse :** J'ai pris connaissance du prototype et je le trouve très bien pour l'instant, donc validé. Mais j'aurais aimé voir ce que donnerait toutes les pages et pas uniquement Cockpit, site 360 et factures et décisions.                                                     |
| R19 |   1 | 👤 Métier   | Les entrées `Mon cockpit`, `Factures & décisions`, `Sites 360°`, `Fluides`, `Marchés & contrats`, `Maintenance`, `Technique & PPT`, `Budget & finances`, `Patrimoine` correspondent-elles au vocabulaire réel ? | Conserver cette architecture et renommer seulement les termes qui ne sont pas compris sans explication par les futurs testeurs.                            | **Réponse / renommages :** `Proposition validée`                                                                                                                                                                                                                                     |
| R20 |   1 | 👤 Métier   | La densité du prototype est-elle trop faible, correcte ou trop forte ?                                                                                                                                          | Garder le cockpit aéré et les tableaux métier plus denses ; proposer un mode compact uniquement si les comptables le demandent.                            | **Réponse :** `Proposition validée`                                                                                                                                                                                                                                                  |
| R21 |   1 | 👤 Métier   | Sur quels appareils la plateforme sera-t-elle réellement utilisée ?                                                                                                                                             | Priorité ordinateur 1280 px et plus ; tablette pour consultation ; mobile limité aux alertes, recherches et validations simples.                           | **Réponse :** Pour l'instant uniquement ordinateur                                                                                                                                                                                                                                   |
| R22 |   1 | 👤 Métier   | Le panneau latéral facture présente-t-il les preuves dans le bon ordre ?                                                                                                                                        | Verdict → montant/échéance → contrôles → références/preuves → décision → réclamation.                                                                      | **Réponse / ordre souhaité :** `Proposition validée`<br><br>J'ai juste une correction dans l'entrée Factures & décisions, le cadre "Transmises CIRIL" pré voir plutot une visualisation au mois et pas à la semaine, maisbon c'est du chipotage tout ca pourra être fignolé plustard |
| R23 |   1 | 👤 Métier   | La fiche Site 360° doit-elle rester la porte d'entrée transversale ?                                                                                                                                            | Oui : elle évite les silos et permet le global-vers-détail sans dupliquer les données.                                                                     | **Réponse :** Selon moi cette page doit être retravaillé pour ne pas avoir comme vue celle d'un site directement. Une vue générale des sites/bâtiments et oui avoir la possibilité de cliquer sur un site précis pour en avoir les informations précises                             |

**Sous-total validé :** `6/6`

---

## Bloc E — Données réelles, recette et migration · 7 points

| ID  | Pts | Responsable | Question ou preuve attendue                                                                                    | Recommandation de départ                                                                                                                                    | Ta réponse / décision                                                                                                           |
| --- | --: | ----------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| R24 |   1 | 👤 Métier   | Qui représentera chaque profil pendant les tests ?                                                             | Identifier au minimum : Direction, comptable Hérault Énergie/DALKIA, comptable EDF, Fluides, Technique/CVC et Patrimoine.                                   | **Réponse / personnes ou fonctions :** `Proposition validée` mais avec en + responsable de service maintenance                  |
| R25 |   1 | 👤 Métier   | Quelles trois tâches doivent être réussies sans aide pour accepter la première tranche ?                       | Trouver une facture prioritaire, comprendre son verdict, décider ou préparer une réclamation ; retrouver ensuite le site et la preuve associée.             | **Réponse :** Cela me semble être cohérent                                                                                      |
| R26 |   1 | 👤 Métier   | Valides-tu les seuils de qualité proposés : fiable ≥95 %, dégradé 70–95 %, inutilisable <70 % ou sans source ? | Les utiliser comme défaut, puis les adapter par source lorsque la fréquence normale diffère.                                                                | **Réponse :** `Proposition validée`                                                                                             |
| R27 |   2 | 📎 Preuve   | Quels jeux de données constitueront la recette : factures, contrats, consommations, équipements et budget ?    | Constituer un lot anonymisé contenant au moins un cas conforme, une anomalie, un doublon, un avoir, un site non couvert et un équipement critique.          | **Réponse / emplacements :** `Proposition validée`                                                                              |
| R28 |   1 | 👤 Métier   | Combien de temps l'ancien et le nouveau frontend doivent-ils coexister ?                                       | Déploiement progressif par route avec drapeau de fonctionnalité ; conserver l'ancien parcours jusqu'à validation de la tranche sur staging puis production. | **Réponse :** J'ai stoppé le développement pour nous consacrer au frontend pour l'instant, donc oui progressif mais rapidement. |
| R29 |   1 | 👤 Métier   | Quel est le premier périmètre réellement mis en production ?                                                   | Dossier facture commun et file de décisions, d'abord sur ENGIE/TotalEnergies, puis EDF et DALKIA ; cockpit et Site 360° raccordés ensuite.                  | **Réponse :** Facturation, cockpit, site 360, Fluides.                                                                          |

**Sous-total validé :** `5/7`

**Consolidation Codex :** le domaine Fluides est inventorié dans la carte, mais son expérience raccordée n’est pas encore suffisamment contractualisée. Le garde-fou ajouté en tête de document devient obligatoire pour le premier lot.
---

## Ce que Codex devra produire après tes réponses · sans points supplémentaires

Ces travaux ne nécessitent pas que tu choisisses la solution technique, mais ils sont obligatoires pour que le score déclaré soit réel :

- [x] transformer les réponses en décisions consolidées et mettre à jour la carte V1 ;
- [ ] produire les contrats d'écran de la première tranche ;
- [ ] cartographier chaque donnée visible vers l'endpoint ou le calcul existant ;
- [ ] identifier les endpoints manquants et les fonctionnalités encore simulées ;
- [ ] extraire du prototype les tokens et composants React réutilisables ;
- [ ] implémenter chargement, absence de données, erreur, permission refusée et données périmées ;
- [ ] vérifier clavier, contraste, lecteurs d'écran et responsive ;
- [ ] définir les tests unitaires, intégration, parcours et non-régression ;
- [ ] déployer par drapeau de fonctionnalité sur staging ;
- [ ] mesurer les scénarios utilisateurs avant bascule de production.

## Calcul final

| Bloc | Maximum | Obtenu |
|---|---:|---:|
| Socle déjà acquis | 57 | 57 |
| A — Gouvernance et profils | 10 | 10 |
| B — Factures, CIRIL et comptabilité | 13 | 13 |
| C — Contrats, maintenance et technique | 7 | 4 |
| D — Expérience utilisateur | 6 | 6 |
| E — Données, recette et migration | 7 | 5 |
| **Total** | **100** | **95** |

## Ordre conseillé pour répondre

1. Commencer par R18 à R23 pendant que le prototype est frais en mémoire.
2. Répondre ensuite à R01 à R07, qui ferment profils, droits et cycle facture.
3. Organiser avec la comptabilité R08 à R12 : c'est le principal verrou du raccordement.
4. Fermer R13 à R17 avec les pièces DALKIA/SPIE.
5. Terminer par R24 à R29 pour préparer la recette et la migration.