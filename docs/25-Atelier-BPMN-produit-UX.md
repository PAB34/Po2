# 25 - Atelier BPMN Produit & UX

> Date : 2026-06-22
> Livrable : `docs/atelier-bpmn-produit/index.html`

## Objectif

Cartographier visuellement les workflows metier et l'experience utilisateur, sous une forme proche de BPMN mais enrichie avec les capacites developpees, les ecrans cibles, les preuves, les phases AS-IS/TO-BE et les commentaires produit.

## Diagrammes precharges

- `L0` : carte generale des cinq axes et des fondations ;
- `L1` : factures de fourniture ENGIE, EDF et TotalEnergies ;
- `L2` : controle detaille ENGIE ;
- `L2` : controle gaz TotalEnergies, avec la fiche livree et les deux increments UX restants en TO-BE.

## Fonctions

- entrée intégrée `Légende & fonctionnement` : niveaux, couloirs, symboles, statuts, relations, AS-IS/TO-BE et mode opératoire ;
- couloirs par acteurs ;
- evenements, taches humaines, taches systeme, decisions, ecrans, donnees et capacites ;
- deplacement libre des cadres ;
- duplication des cadres avec conservation des propriétés et nouvel identifiant ;
- zoom centre sous le pointeur avec la molette et panoramique au clic gauche maintenu sur le fond ;
- relations typees : sequence, message, dependance, alimentation, preuve, navigation ;
- fiches dynamiques specialisees selon le type de cadre ;
- preremplissage expert non destructif sur les 155 cadres et 171 relations de l etat actuel ;
- boite d'edition/commentaire sur les cadres et relations ;
- profil, capacite, ecran cible, description, donnees et preuves ;
- statuts developpe, partiel, a construire, bloque et futur ;
- filtres AS-IS, TO-BE, acteur, arbitrages et recherche ;
- vue Registre ;
- vue Couverture UX avec detection des capacites/ecrans manquants et arbitrages requis ;
- sauvegarde automatique dans `localStorage` ;
- import/export JSON.
- marqueurs ◆ structurants, ◇ conception et ✓ valides, avec question et proposition modifiables dans chaque fiche.

## Utilisation

Double-cliquer sur :

```text
docs/atelier-bpmn-produit/ouvrir-atelier.cmd
```

Ou servir le dossier `docs/` avec un serveur local. Double-cliquer un cadre ou une relation pour ouvrir sa fiche. Pour une relation, activer `+ Liaison`, cliquer la source puis la cible.

## Regle de travail

1. Cartographier l'AS-IS avec les capacites reellement developpees.
2. Dupliquer/completer en TO-BE avec les ecrans cibles.
3. Commenter les ecarts et arbitrages.
4. Utiliser Couverture UX pour traiter les orphelins.
5. Exporter le JSON lorsque la carte est validee et le versionner dans le depot.
6. Alimenter les contrats d'ecran de [[24-Cockpit-canonique-reconstruction-produit-frontend]].
7. Apres une livraison fonctionnelle, demander une synchronisation assistee de l'atelier ; elle complete la carte sans ecraser les choix utilisateur.

## Validation effectuee

Validation dans le navigateur integre :

- chargement et parcours des 11 diagrammes ;
- rendu des 5 couloirs et du workflow multi-fournisseurs ;
- déplacement d'un cadre avec persistance de la position ;
- ouverture de la fiche d'un cadre ;
- saisie et persistance d'un commentaire ;
- filtres AS-IS et TO-BE ;
- vue Couverture UX ;
- creation d'une liaison et ouverture de sa fiche ;
- aucune erreur console detectee.


## Couverture differentielle

L'audit [[26-Audit-couverture-atelier-BPMN-2026-06-22]] confirme 55 capacites sur 55 dans l etat actuel et 66 sur 66 dans la V1.

## Versions du modele

Le selecteur d'en-tete propose `Etat actuel - AS-IS` et `V1 - Plateforme operationnelle cible`. La V1 est decrite dans [[27-Modele-V1-plateforme-operationnelle]] et comprend 16 diagrammes, 230 cadres et 259 relations. Les deux versions sont editees et sauvegardees independamment.

## Registre des arbitrages

Les 26 questions liees a la V1 sont detaillees dans [[28-Questions-arbitrage-avant-refonte-V1]]. Treize sont structurantes avant de figer les workflows et treize peuvent etre fermees pendant les ateliers UX. Dix-sept decisions sont consolidees ; neuf restent a completer. Les reponses saisies dans l atelier sont preservees lors des mises a jour et exportees en JSON.
