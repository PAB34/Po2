# 32 - Consolidation des réponses et audit de la matrice DALKIA

> Date : 2026-06-24  
> Source : réponses au document 30 et audit du classeur `saas/energie/DALKIA/COMPTABILITE/analyse_codification_dalkia_enrichie_par_code_contrat (1).xlsx`.

## Conclusion

Les arbitrages utilisateur atteignent **95/100**. Les 5 points non acquis dépendent de preuves ou de revalidations, pas d'une indécision générale sur le produit.

Le développement du socle visuel et des contrats d'écran peut avancer. La mise en production raccordée reste conditionnée par les contrats d'écran, la cartographie API, les jeux de recette et une spécification détaillée du domaine Fluides.

## Décisions V1 consolidées

### Profils et responsabilités

- `Responsable de service maintenance` : lecture transverse de la plateforme, validation des devis P3 au-dessus du seuil et visibilité sur les accords automatiques.
- `Technique/CVC` : DALKIA P2/P3, SPIE, analyse technique, criticité CVC et propositions PPT.
- `Fluides` : Hérault Énergie, eau, DALKIA P1, consommations ENEDIS/GRDF, DJU et atterrissages.
- `Finances/Comptabilité` : traitement comptable dans la plateforme, préparation de la transmission aux finances et mise à jour manuelle dans CIRIL.
- `Patrimoine` : bâtiments, sites, rattachements et qualité du référentiel.
- `Administrateur général` : utilisateurs, rôles, paramètres et référentiels transversaux.
- Le portail tiers DALKIA est reporté en phase 2.

Tous les profils internes V1 peuvent réouvrir une facture. La réouverture exige un motif, une trace horodatée et la conservation de la décision précédente. L'accès tiers futur n'est pas compris dans cette règle.

### Cycle facture

Le parcours cible devient :

`importée → contrôlée → décision métier → transmise aux finances → traitée`.

- CIRIL n'est ni synchronisé ni importé dans la V1.
- La plateforme ne prétend pas connaître le paiement ou le mandatement CIRIL.
- Le statut `transmise aux finances` appartient à la plateforme ; la comptable met ensuite CIRIL à jour manuellement.
- Une facture réimportée ne perd jamais son historique : doublon ignoré, nouvelle version liée, avoir rattaché ou réouverture motivée.
- Dans le frontend, l'ancien libellé `Transmises CIRIL` doit devenir `Transmises aux finances`, avec une lecture mensuelle.

### Budget et axes d'analyse

Le **numéro d'opération** est le seul niveau d'écriture budgétaire faisant foi dans Po². Les autres dimensions servent au drill-down et à l'analyse :

- exercice ;
- marché, lot et code contrat ;
- fournisseur ;
- service et fonction ;
- nature comptable ;
- antenne, site et bâtiment ;
- fluide ;
- facture et ligne de facture.

L'antenne est une dimension importante pour lire les bâtiments ou sites consommateurs de budget.

### Devis P3

Parcours : `dépôt/import → contrôle BPU → instruction Technique/CVC → accord ou validation → émission et archivage`.

- devis inférieur à 1 000 € et conforme au BPU : bon pour accord automatique, envoi au titulaire et notification au Responsable de service maintenance ;
- devis à partir de 1 000 €, ou non conforme : validation du Responsable de service maintenance ;
- toute décision conserve le devis, la version du BPU, le résultat du contrôle, le décideur et l'horodatage.

### Expérience utilisateur

- la direction graphique du prototype Po² est validée ;
- la priorité est l'ordinateur ;
- le cockpit reste aéré, les tableaux métier peuvent être plus denses ;
- toutes les entrées principales devront être prototypées avant extraction définitive du design system ;
- `Sites 360°` s'ouvre d'abord sur une vue portefeuille des sites et bâtiments, puis sur la fiche détaillée d'un site ;
- la première tranche cible `Facturation`, `Cockpit`, `Sites 360°` et `Fluides`.

## Audit du classeur comptable DALKIA

### Couverture observée

| Élément | Résultat |
|---|---:|
| Sites codifiés | 75 |
| Codes site uniques | 75 |
| Contrats recensés | 7 |
| Couples contrat / poste facturé | 43 |
| Services | 15 |
| Fonctions | 26 |
| Antennes | 39 |
| Numéros d'opération renseignés | 75/75 |
| Natures ou règles proposées | 9 familles |
| Validations comptables renseignées | 0/43 |

La structure est exploitable pour construire une matrice versionnée. Elle ne constitue pas encore une doctrine comptable validée.

### Clés cibles de rapprochement

| Objet | Clé fonctionnelle recommandée | Remarque |
|---|---|---|
| Marché / version | collectivité + code contrat + lot + dates d'effet | Le seul code contrat ne suffit pas pour distinguer ancien et nouveau marché dans le temps. |
| Site | collectivité + code site | Conserver l'identifiant bâtiment interne après rapprochement. |
| Facture | fournisseur + type de pièce + numéro de facture | Ajouter date, marché/lot et montant comme contrôles de cohérence, pas comme clé principale. |
| Ligne facture | facture interne + numéro ou rang de ligne | Porter aussi le poste facturé et le service vendu. |
| Règle comptable | version de matrice + code contrat + poste facturé + service vendu éventuel | Dates d'effet et statut de validation obligatoires. |
| Ventilation analytique | ligne facture + opération + nature + service + fonction + antenne/site | L'opération porte le budget ; les autres axes documentent l'analyse. |

Aucune clé de mandat ou de paiement CIRIL n'est requise dans la V1, puisque ce périmètre est explicitement hors plateforme.

### Règles encore incertaines

Neuf couples ne peuvent pas être transformés en règle automatique définitive sans arbitrage :

- P1 multi-services de la piscine Fonquerne : ventilation selon le service vendu ;
- P2 de Fonquerne et du nouveau marché lot 1 : isoler les lignes qui ne relèvent pas strictement de la maintenance ;
- R1f et R2f des deux lots de thalassothermie : confirmer l'emploi de la nature 60613 pour le froid ;
- P3.4 : distinguer fonctionnement, maintenance lourde et immobilisation ligne par ligne ;
- PREST PONC : obtenir un exemple de facture et confirmer la nature.

Quatre libellés de marché comportent encore `à confirmer`. Les 43 cellules de validation comptable sont vides. La future interface d'administration doit donc gérer au minimum : `proposée`, `à valider`, `validée`, `refusée`, dates d'effet, auteur et justification.

## Ce qui reste réellement à l'utilisateur

1. Répondre aux six choix Fluides du document 33.
2. Fournir le corpus SPIE lorsqu'il souhaitera ouvrir ce module ; ce corpus ne bloque pas le premier lot frontend.
3. Relire et valider les conclusions de la revalidation DALKIA P1/P2/P3 et, si nécessaire, faire arbitrer les règles comptables par la comptabilité.

Codex constitue d'abord la recette avec les fichiers déjà présents. L'utilisateur ne sera sollicité que pour un exemple réellement absent.

## Ce que Codex doit maintenant produire

1. Revalider les matrices DALKIA P1, P2 et P3 séparément.
2. Écrire les contrats d'écran du premier lot, en commençant par Facturation puis Fluides.
3. Cartographier chaque donnée affichée vers une API, un calcul ou un manque identifié.
4. Étendre le prototype à toutes les entrées principales, avec une vue portefeuille pour Sites 360°.
5. Constituer la recette UX et la stratégie de migration par route.

## Garde-fou Fluides

La carte actuelle n'oublie pas ENEDIS, GRDF, les DJU ni les atterrissages. En revanche, elle ne définit pas encore assez précisément l'expérience raccordée : granularités temporelles, comparaisons, couverture, données manquantes, formules kWh/euros et drill-down compteur/site. Le domaine Fluides est donc **inventorié mais pas encore suffisamment contractualisé** pour la première mise en production.
