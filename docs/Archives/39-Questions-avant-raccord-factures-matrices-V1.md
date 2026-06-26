# Questions avant raccord complet Factures & matrices V1

Date : 2026-06-25  
Objet : arbitrer le comportement utilisateur avant de brancher l'application, la validation et l'export finance des matrices comptables dans `/refonte-v1/factures`.

À lire avant réponse : `docs/40-Analyse-factures-reelles-pour-matrice-comptable.md`, qui analyse les factures réelles DALKIA, ENGIE, EDF et TotalEnergies.

## Ce que tu dois faire maintenant

Répondre uniquement aux questions marquées `À trancher`.  
Les autres points sont proposés par défaut : tu peux les corriger si tu n'es pas d'accord.

Objectif : éviter de raccorder une action sensible, comme appliquer une matrice comptable à une facture, sans avoir validé le workflow métier.

---

## 1. Choix de la matrice à appliquer

### Question 1 — À trancher

Quand l'utilisateur ouvre une facture et clique sur `Proposer l'imputation`, comment choisit-on la matrice comptable ?

Options possibles :

1. La plateforme sélectionne automatiquement la matrice active la plus probable selon le fournisseur / contrat / source.
2. La plateforme propose une matrice préselectionnée, mais l'utilisateur doit confirmer.
3. L'utilisateur choisit toujours manuellement la matrice.

Recommandation Codex : option 2.  
Cela garde une UX fluide tout en évitant une imputation silencieuse sur le mauvais contrat.

Réponse Pascal :

> Alors c'est une question importante, selon moi lorsque l'utilisateur ouvre une facture c'est que le fichier de facture au format xlsx a déjà été importé/analysé et la matrice comptable a à appliquer est déjà fait automatiquement puis suit le workflow de contrôle et de validation qu'on a déjà mis en place. Donc ce que je veux dire c'est que pour chaque tiers facturant on doit trouver une section matrice comptable qui permet d'importer un fichier xlsx -> détecte toutes les données de facturations qui seront récurrentes (Parsing? je sais pas si c'est le bon terme) -> Affiche alors dans un tableau toutes les données comptables récurrente et propose une saisie manuelle dans le tableau mai sil a aussi la possibilité d'exporter le tableau au fromat xlsx pour la saisir sur excel pour ensuite lui permettre de la réimporter -> vérification par la plateforme que toutes les données fournies reprennent bien celles identifiées des données comptables récurrentes -> puis enregistré/refuser (+motif).  Ainsi dès qu'une facture va arriver avec la donnée comptable récurrente identifié (c'est à toi de l'identifier dans les factures que je t'ai transmises) la matrice comptable sera automatiquement appliquée

---

## 2. Niveau de confiance requis avant validation

### Question 2 — À trancher

Une facture peut-elle être validée si la matrice produit des exceptions ?

Options possibles :

1. Non, aucune validation possible tant qu'il reste une exception.
2. Oui, mais seulement via une correction manuelle motivée.
3. Oui, avec simple avertissement.

Recommandation Codex : option 2.  
Le moteur bloque la validation standard si exceptions, mais la comptabilité peut forcer avec motif.

Réponse Pascal :

> option 1 - Justement cela doit être remonté en cas d'incohérence par rapport aux données comptables récurrentes

---

## 3. Rôle autorisé à valider / exporter

### Question 3 — À trancher

Qui doit pouvoir valider une imputation comptable et exporter finance ?

Rôles actuellement autorisés côté backend : `ADMIN`, `SUPERADMIN`, `FINANCE`, `COMPTA`, `COMPTABILITE`.

Est-ce suffisant ?

Réponse Pascal :

> TOUS LES ROLES sauf fluides et technicien CVC

---

## 4. Facture déjà traitée puis réimportée

### Question 4 — À trancher

Si tu réimportes un export annuel complet contenant des factures déjà traitées, quel comportement souhaites-tu ?

Proposition Codex :

- facture identique déjà validée/exportée : affichée comme historique, non retraitée ;
- facture déjà connue mais modifiée : alerte `facture réimportée différente`, analyse manuelle ;
- facture nouvelle : intégrée dans la file à traiter.

Valides-tu cette logique ?

Réponse Pascal :

> facture identique déjà validée/exportée : affichée comme historique, non retraitée ;

---

## 5. Export finance

### Question 5 — À trancher

Quand une facture est marquée `exportée finance`, faut-il aussi mettre à jour la facture source ?

Exemples :

- `EnergyInvoiceImport.finance_exported_at`
- `GasInvoice.finance_exported_at`
- `CpeFinanceInvoice.finance_exported_at`

Recommandation Codex : oui.  
Le snapshot comptable est la preuve, mais la facture source doit aussi porter le marqueur pour l'historique et les filtres.

Réponse Pascal :

> Oui

---

## 6. Réclamation fournisseur

### Question 6 — À trancher

Pour une facture avec anomalie, quelle action veux-tu en V1 ?

Options possibles :

1. Générer uniquement un brouillon de mail avec destinataire, objet et contenu à copier.
2. Ouvrir le client mail local via `mailto:`.
3. Envoyer directement depuis la plateforme.

Recommandation Codex : option 1 maintenant, option 2 ensuite si confortable.  
L'envoi direct demande une vraie configuration mail / domaine / SMTP, donc plus sensible.

Réponse Pascal :

> Générer uniquement un brouillon de mail avec destinataire, objet et contenu à copier.

---

## 7. Contacts fournisseurs par contrat

### Question 7 — À trancher

Pour chaque marché/contrat, veux-tu gérer un seul contact entreprise ou plusieurs contacts ?

Exemples :

- contact facturation ;
- contact technique ;
- contact commercial / marché ;
- contact réclamation.

Recommandation Codex : plusieurs contacts à terme, mais un contact principal `facturation/réclamation` suffit en V1.

Réponse Pascal :

> plusieurs contacts possibles

---

## 8. Périmètre du mot `Fluides`

### Question 8 — À trancher

Confirmes-tu que le domaine `Énergie` doit devenir `Fluides` dans la refonte, pour intégrer ensuite l'eau ?

Proposition Codex :

- navigation et UX : `Fluides` ;
- sous-domaines : électricité, gaz, eau ;
- compatibilité technique temporaire : certains noms backend peuvent rester `energy` tant que la migration n'est pas complète.

Réponse Pascal :

> navigation et UX : `Fluides` ;
- sous-domaines : électricité, gaz, eau ;
- Tout doit passer en fluide lorsqu'il était question de parler des ces trois fluides ou ancienne éléctricité gaz

---

## 9. Ordre de priorité UX dans Factures V1

### Question 9 — À trancher

Quel écran est prioritaire dans `/refonte-v1/factures` ?

Options possibles :

1. File de factures à traiter, très opérationnelle.
2. Vue par contrat/marché puis factures associées.
3. Vue par anomalies / décisions urgentes.

Recommandation Codex : option 1 en page principale, avec filtres contrat/anomalies.  
C'est le plus naturel pour traiter un flux d'import et décider facture par facture.

Réponse Pascal :

> option 1 en page principale, avec filtres contrat/anomalies.  
C'est le plus naturel pour traiter un flux d'import et décider facture par facture.

---

## 10. Niveau de détail dans le drawer facture

### Question 10 — À trancher

Dans la fiche facture, veux-tu voir par défaut :

1. une synthèse courte, puis détail dépliable ;
2. tout le détail immédiatement ;
3. une vue très compacte avec accès à une page détail séparée.

Recommandation Codex : option 1.  
Synthèse lisible d'abord, détail ligne par ligne ensuite.

Réponse Pascal :

> une synthèse courte, puis détail dépliable

---

## 11. Seuil pour considérer l'imputation comme complète

### Question 11 — À trancher

Une facture est-elle `imputation complète` uniquement si 100 % des lignes sont imputées sans exception ?

Recommandation Codex : oui.

Tolérance proposée : écart maximal de 0,01 % ou 0,01 € selon le cas.

Réponse Pascal :

> Oui

---

## 12. Ce que Codex peut faire après tes réponses

Une fois les réponses saisies, je pourrai :

1. raccorder le bouton `Proposer l'imputation` avec choix/confirmation de matrice ;
2. afficher les exceptions comptables de manière compréhensible ;
3. raccorder `Valider` et `Exporter finance` ;
4. ajouter le statut historique des factures déjà traitées ;
5. préparer le brouillon de mail fournisseur en cas d'anomalie.

---

## 13. Lecture de la matrice bêta DALKIA

Fichier consulté : `saas/energie/DALKIA/COMPTABILITE/analyse_codification_dalkia_enrichie_par_code_contrat (1).xlsx`

Constats rapides :

- 4 feuilles : `Sites vers codes`, `Poste facturé vers Nature ctpab`, `Signification poste facturés`, `Codes contrat - marchés`.
- 75 sites codifiés avec axes : service, fonction, antenne, opération.
- 43 règles DALKIA par code contrat / poste facturé.
- 7 codes contrats identifiés.
- 31 postes facturés distincts.
- 8 natures comptables proposées.
- Aucun calcul/formule : c'est une matrice déclarative, donc adaptée à un import XLSX en base.

Répartition des statuts :

- `Cohérent` : 34 règles ;
- `À valider compta` : 4 règles ;
- `À ventiler` : 3 règles ;
- `À arbitrer comptabilité` : 1 règle ;
- `En attente DALKIA – fournir n° facture` : 1 règle.

Conséquence importante : cette matrice confirme qu'il ne faut pas seulement faire une règle `poste facturé -> nature`. Il faut aussi gérer le code contrat, le marché/périmètre, le service vendu, les périodes anciennes/nouvelles, les cas à ventiler, les cas à arbitrer et les cas en attente fournisseur.

---

## 14. DALKIA — froid réseau et nature 60613

### Question 12 — À trancher

Dans les contrats thalassothermie `C00107051V` et `C00157795L`, les postes froid réseau `R1f` et `R2f` sont proposés en `60613`, mais marqués `À valider compta`.

Confirmes-tu que le froid / rafraîchissement réseau doit bien être codé en `60613` comme le chaud réseau ?

Réponse Pascal :

> A terme c'est un contrat qu'il conviendra de contrôler mais il ne fait pas partie du même marché que DALKIA ville donc ne pas le traiter pour l'instant et rester sur cette règle d'ignorance. D'aillerus dans le code actuel normalement il est déjà fait référence à ce tri par identifiant contrat

---

## 15. DALKIA — règles à ventiler

### Question 13 — À trancher

La matrice contient des postes `À ventiler`, notamment :

- `C00032657J / P1` : selon service vendu ;
- `C00032657J / P2` : isoler ce qui n'est pas strictement maintenance ;
- `C00190116O / P2` : maintenance + sensibilisation amélioration énergétique.

Souhaites-tu que la plateforme :

1. bloque la validation tant que ces lignes ne sont pas ventilées ;
2. propose une ventilation automatique basée sur `service vendu`, puis demande confirmation ;
3. laisse passer avec avertissement.

Recommandation Codex : option 2 quand le service vendu est exploitable, sinon blocage.

Réponse Pascal :

La matrice comptable doit pouvoir l'identifier précisément, c'est justement l'un de ses objectifs et reste sous la validation de la comptable lors de la saisi de ces données durant létape de configuration de la matrice comptable.La matrice comptable doit pouvoir l'identifier précisément, c'est justement l'un de ses objectifs et reste sous la validation de la comptable lors de la saisi de ces données durant létape de configuration de la matrice comptable.

---

## 16. DALKIA — P3.4 travaux programmés

### Question 14 — À trancher

Le poste `C00190116O / P3.4 / WORKS` est proposé comme `615221 / investissement`, avec statut `À arbitrer comptabilité`.

Comment veux-tu traiter ce cas ?

Options possibles :

1. Toujours bloquer et demander arbitrage comptable.
2. Autoriser une nature par défaut `615221`, mais avec validation obligatoire.
3. Distinguer fonctionnement / investissement selon le détail de la ligne ou un seuil.

Recommandation Codex : option 1 au départ, car c'est le type de ligne qui peut poser problème au mandatement.

Réponse Pascal :

La matrice comptable doit pouvoir l'identifier précisément, c'est justement l'un de ses objectifs et reste sous la validation de la comptable lors de la saisi de ces données durant létape de configuration de la matrice comptable.

---

## 17. DALKIA — prestations ponctuelles

### Question 15 — À trancher

Le poste `C00190116O / PREST PONC` est proposé en `611`, mais le statut indique `En attente DALKIA – fournir n° facture`.

Souhaites-tu :

1. bloquer ces lignes tant qu'une clarification DALKIA n'est pas attachée ;
2. accepter provisoirement `611` avec alerte ;
3. créer une action automatique `demande fournisseur` avec brouillon de mail.

Recommandation Codex : option 3, avec blocage de validation tant que la réponse n'est pas documentée.

Réponse Pascal :

> La matrice comptable doit pouvoir l'identifier précisément, c'est justement l'un de ses objectifs et reste sous la validation de la comptable lors de la saisi de ces données durant létape de configuration de la matrice comptable.

---

## 18. DALKIA — périodes anciennes / nouveau marché

### Question 16 — À trancher

De nombreuses alertes indiquent : `Factures 2026 liées à échéances/périodes antérieures` ou `lignes antérieures à 2026 à isoler`.

Souhaites-tu que la plateforme t'alerte quand une facture importée en 2026 concerne une période antérieure ou un ancien marché ?

Recommandation Codex : oui. Cela doit devenir un contrôle de cohérence `période facturée vs marché actif`.

Réponse Pascal :

> Pertinent, nous avons signé un nouveau marché qui est devenu opérationnel à partir du 11 octobre 2025 (ou pas loin de cette date, ainsi tout ce qui est facturé avant ne nous concerne plus car ici on travail sur le nouveau marché (assez complexe comme ca))

---

## 19. DALKIA — validation comptable dans le XLSX

### Question 17 — À trancher

La colonne `Validation comptable` est vide dans la bêta.

Souhaites-tu que l'import XLSX considère :

1. `Statut = Cohérent` comme utilisable même sans validation comptable ;
2. toutes les règles comme brouillon tant que `Validation comptable` n'est pas remplie ;
3. uniquement les règles explicitement validées par la comptabilité comme activables.

Recommandation Codex : option 2 pour l'import initial, puis activation explicite d'une version validée.

Réponse Pascal :

> La matrice comptable doit pouvoir l'identifier précisément, c'est justement l'un de ses objectifs et reste sous la validation de la comptable lors de la saisi de ces données durant létape de configuration de la matrice comptable.
> 

