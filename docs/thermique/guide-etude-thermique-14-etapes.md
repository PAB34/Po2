---
read_policy: toujours, avant tout travail sur la plateforme thermique ; GUIDE DE RÉFÉRENCE (thermicien, 2026-10-02)
statut: référence — à garder précieusement, ne pas modifier sans accord du thermicien
source: « Étude thermique sur plans : guide des prompts étape par étape », Pierre-André, 2026-10-02
---

> **Document de référence voulu par le thermicien** : il sert de guide pour reprendre toute la plateforme.
> Objectif : un assistant IA à la réalisation d'études thermiques, dans un environnement local avec Claude.
> Copie fidèle du fichier reçu. Correspondance avec la plateforme : `refondation-assistant-ia-local-decisions.md`.

# Étude thermique sur plans : guide des prompts étape par étape

Oct 2, 2026 · @Pierre-André

## Principe général

L'étude se déroule en 14 étapes : vous envoyez tous les plans une seule fois au début, puis un prompt par étape et par plan analysé. Chaque étape produit un livrable que vous validez avant la suivante.

Trois règles s'appliquent à tous les prompts :

- **Un prompt = une étape + un plan principal.** Les autres plans restent joints pour les recoupements, mais je ne trace finement qu'un plan à la fois.
- **Chaque prompt rappelle trois choses** : le plan visé (par son nom de fichier), l'étape, et les conventions déjà validées.
- **Chaque prompt se termine par** : « liste tes hypothèses et tes doutes ». Vous corrigez, puis nous passons à la suite.

Nommez les fichiers de façon stable, par exemple `PLAN-N0`, `PLAN-N1`, `COUPE-AA`, `FACADE-SUD`, `TOITURE`, `MASSE`. Je reprends ces noms dans tous les livrables.

## Avant de commencer : ce qu'il faut réunir

Plus la liste ci-dessous est complète, moins je ferai d'hypothèses. Ce qui manque ne bloque pas l'étude : je le signale et je travaille avec une valeur par défaut que vous validez.

**Pièces graphiques**

- [ ] Plans de tous les niveaux, y compris sous-sol et combles
- [ ] Plan de toiture
- [ ] Toutes les coupes
- [ ] Toutes les façades
- [ ] Plan masse avec le nord et les bâtiments voisins
- [ ] Carnet de détails (acrotères, appuis de baie, liaisons plancher / façade), s'il existe
- [ ] Plans de structure, s'ils existent
- [ ] Plans fluides (chauffage, ventilation, plomberie), s'ils existent

**Pièces écrites**

- [ ] CCTP ou notice descriptive : composition des parois, isolants, épaisseurs
- [ ] Carnet ou tableau de menuiseries : dimensions, vitrages, cadres, Uw, Sw, TLw
- [ ] Étude thermique antérieure ou notice thermique, s'il y en a une

**Informations à me donner par écrit**

- [ ] Réglementation ou méthode visée (RE2020, RT existant, audit, autre) et logiciel de calcul utilisé
- [ ] Usage du bâtiment et de chaque zone
- [ ] Locaux chauffés, non chauffés, et bâtiments mitoyens
- [ ] Localisation : commune, altitude, zone climatique
- [ ] Vos conventions de métré : nu intérieur ou extérieur, règle de déduction des baies, nomenclature des parois
- [ ] Format de sortie attendu : tableur, plans annotés, fichier de coordonnées

Préférez des PDF vectoriels ou des DWG : les cotes y sont exactes. Sur un plan scanné, la précision se limite à quelques centimètres.

## Les 14 étapes

Chaque étape indique les plans à joindre, ce que j'attends de vous, un prompt type à copier, ce que je vous rends et ce que vous devez valider. Les mots entre crochets sont à remplacer.

### Étape 1 : cadrage et inventaire

- **Plans à joindre** : tous, plus les pièces écrites.
- **Ce que j'attends de vous** : les informations écrites de la liste précédente.
- **Prompt type** : « Voici toutes les pièces du projet \[nom\]. Méthode visée : \[réglementation\]. Fais l'inventaire des pièces, indique ce que chacune permet de lire, et liste ce qui manque pour l'étude thermique. Ne commence aucune analyse. »
- **Ce que je vous rends** : tableau des pièces (nom, type, niveau ou orientation, lisibilité) et liste des manques.
- **À valider** : les manques que vous pouvez combler et ceux à traiter par hypothèse.
- **Découpage** : un seul prompt.

### Étape 2 : calage géométrique

- **Plans à joindre** : toutes les pièces graphiques.
- **Ce que j'attends de vous** : une cote sûre par plan si vous en connaissez une, et la direction du nord si elle n'est pas dessinée.
- **Prompt type** : « Pour chaque plan, recale l'échelle sur une cote lisible, indique l'orientation et la rotation, et établis la correspondance des files et des niveaux entre plans, coupes et façades. »
- **Ce que je vous rends** : par plan, l'échelle vérifiée, la rotation, le nord, et un tableau de correspondance des files et des altimétries.
- **À valider** : l'échelle et le nord. Tous les métrés en dépendent.
- **Découpage** : un seul prompt, deux si les plans sont nombreux.

### Étape 3 : coupes et hauteurs

- **Plans à joindre** : toutes les coupes, les façades en appui, le carnet de détails.
- **Ce que j'attends de vous** : les hauteurs que vous connaissez déjà.
- **Prompt type** : « Sur \[COUPE-AA\], relève les niveaux finis, hauteurs d'étage et sous plafond, épaisseurs de planchers, retombées de poutres, acrotères, et la position de l'isolant à chaque liaison plancher / façade. »
- **Ce que je vous rends** : tableau des hauteurs par niveau et coupe annotée.
- **À valider** : les hauteurs retenues par niveau.
- **Découpage** : un prompt par coupe.

### Étape 4 : zonage et enveloppe chauffée

- **Plans à joindre** : le plan du niveau traité, les niveaux du dessus et du dessous, les coupes.
- **Ce que j'attends de vous** : la liste des locaux non chauffés, et vos règles de tracé (niches, poteaux, allèges, nu intérieur ou extérieur).
- **Prompt type** : « Sur \[PLAN-N1\], trace le contour de l'enveloppe chauffée au nu \[intérieur\]. Distingue murs opaques et parois vitrées. Repère les espaces extérieurs, les locaux non chauffés et les parois qui les séparent du volume chauffé. Propose un zonage thermique par usage. »
- **Ce que je vous rends** : plan annoté, fichier de coordonnées, surface et périmètre, zonage.
- **À valider** : le statut de chaque local et les règles de tracé. Elles s'appliquent ensuite à tous les niveaux.
- **Découpage** : un prompt par niveau, en commençant par le plus représentatif.

### Étape 5 : parois opaques verticales

- **Plans à joindre** : le plan du niveau, les coupes, les détails, le CCTP.
- **Ce que j'attends de vous** : les compositions de parois si elles ne figurent pas dans les pièces.
- **Prompt type** : « Sur \[PLAN-N1\], classe chaque tronçon de paroi opaque verticale par type : mur extérieur, mur sur local non chauffé, mur mitoyen, mur enterré. Donne la composition lue ou supposée, l'épaisseur mesurée et l'orientation. »
- **Ce que je vous rends** : nomenclature des types de murs, plan repéré par type, tableau des tronçons.
- **À valider** : la nomenclature et les compositions supposées.
- **Découpage** : un prompt par niveau.

### Étape 6 : planchers et toitures

- **Plans à joindre** : plan de toiture, plans du niveau le plus bas et du plus haut, coupes, détails.
- **Ce que j'attends de vous** : la nature de ce qu'il y a sous le plancher bas (terre-plein, vide sanitaire, parking, local chauffé).
- **Prompt type** : « Identifie les planchers bas, les planchers intermédiaires donnant sur l'extérieur ou sur un local non chauffé, les toitures et toitures-terrasses, les lanterneaux et les trémies. Donne type, composition et contour de chacun. »
- **Ce que je vous rends** : nomenclature des parois horizontales et plans repérés.
- **À valider** : les planchers en porte-à-faux, sous terrasse ou sur passage, souvent oubliés.
- **Découpage** : un prompt pour les planchers, un pour les toitures.

### Étape 7 : menuiseries et cadres

- **Plans à joindre** : la façade traitée, les plans des niveaux qu'elle couvre, le carnet de menuiseries, les coupes.
- **Ce que j'attends de vous** : les performances des menuiseries si vous les avez (Uw, Sw, TLw), sinon le type de vitrage et de cadre.
- **Prompt type** : « Sur \[FACADE-SUD\], recoupée avec \[PLAN-N0\] et \[PLAN-N1\], repère et numérote chaque baie. Donne largeur, hauteur, allège, type d'ouvrant, matériau et largeur du cadre, vitrage, position dans l'épaisseur du mur, orientation et inclinaison. Inclus les portes et les parois vitrées fixes. »
- **Ce que je vous rends** : façade et plans repérés, tableau des baies, regroupement par type de menuiserie.
- **À valider** : les types de menuiseries et les baies visibles sur un seul des deux documents.
- **Découpage** : un prompt par façade.

### Étape 8 : protections solaires et masques

- **Plans à joindre** : façades, plans, coupes, plan masse.
- **Ce que j'attends de vous** : la hauteur et la distance des bâtiments voisins et du relief, si le plan masse ne les donne pas.
- **Prompt type** : « Pour chaque baie du tableau validé, identifie les protections mobiles (stores, volets), les masques proches (brise-soleil, débords, balcons, tableaux profonds, loggias) et les masques lointains. Donne leurs dimensions utiles au calcul. »
- **Ce que je vous rends** : tableau des baies complété par les protections et les masques.
- **À valider** : les protections mobiles, rarement dessinées.
- **Découpage** : un prompt par façade, ou un seul si les masques sont simples.

### Étape 9 : structure

- **Plans à joindre** : le plan du niveau, les coupes, les plans de structure.
- **Ce que j'attends de vous** : les matériaux de structure (béton, acier, bois) et le mode d'isolation (intérieur, extérieur, réparti).
- **Prompt type** : « Sur \[PLAN-N1\], repère les poteaux, poutres, voiles, refends, noyaux, balcons et coursives. Pour chacun, indique s'il se trouve dans l'enveloppe, s'il la traverse ou s'il interrompt l'isolation. »
- **Ce que je vous rends** : plan repéré et tableau des éléments de structure en contact avec l'enveloppe.
- **À valider** : les cloisons lourdes ou légères, et le mode d'isolation retenu.
- **Découpage** : un prompt par niveau.

### Étape 10 : ponts thermiques

- **Plans à joindre** : aucun nouveau plan en vue en plan ; les coupes et détails pour les liaisons horizontales.
- **Ce que j'attends de vous** : la source des valeurs ψ à utiliser (règles Th-Bât, catalogue, valeurs calculées) ou la consigne de ne faire que le repérage.
- **Prompt type** : « À partir des étapes validées, repère et classe les ponts thermiques de \[PLAN-N1\] : liaisons horizontales (plancher bas, intermédiaire, haut, acrotère, balcon), verticales (angles, refends, poteaux), de menuiserie (appui, linteau, tableau) et ponctuelles. Donne la longueur de chacun et la valeur ψ selon \[source\]. »
- **Ce que je vous rends** : plan repéré par catégorie, tableau des ponts thermiques avec longueurs.
- **À valider** : les catégories à négliger et les valeurs ψ.
- **Découpage** : un prompt par niveau pour les liaisons verticales et de menuiserie, un prompt par coupe pour les liaisons horizontales.

### Étape 11 : métrés

- **Plans à joindre** : aucun ; les fichiers de coordonnées et tableaux produits.
- **Ce que j'attends de vous** : vos conventions de métré, rappelées.
- **Prompt type** : « Calcule les métrés : surfaces nettes par type de paroi et par orientation, surfaces de baies par type et orientation, linéaires de ponts thermiques par catégorie, surface et volume chauffés par zone. Livre un tableur avec le détail par niveau. »
- **Ce que je vous rends** : tableur de métrés avec formules et détail par niveau.
- **À valider** : les totaux, par comparaison avec vos ordres de grandeur.
- **Découpage** : un seul prompt.

### Étape 12 : systèmes et données non graphiques

- **Plans à joindre** : plans fluides et notices techniques, s'ils existent.
- **Ce que j'attends de vous** : chauffage, refroidissement, ventilation, eau chaude sanitaire, éclairage, production locale, perméabilité à l'air visée, classe d'inertie. Les plans d'architecte ne donnent pas ces informations.
- **Prompt type** : « Voici les données systèmes : \[données\]. Mets-les en forme pour la saisie dans \[logiciel\], par zone thermique, et signale les données manquantes. »
- **Ce que je vous rends** : fiche de saisie par zone et liste des manques.
- **À valider** : les valeurs par défaut proposées.
- **Découpage** : un seul prompt.

### Étape 13 : contrôle croisé

- **Plans à joindre** : tous, en consultation.
- **Ce que j'attends de vous** : rien de nouveau.
- **Prompt type** : « Vérifie la cohérence de l'ensemble : plans, coupes et façades entre eux ; somme des surfaces de parois par rapport à l'enveloppe ; baies présentes sur plan et sur façade ; continuité des niveaux. Liste les écarts et les points incertains, classés par impact sur le calcul. »
- **Ce que je vous rends** : liste des écarts et des incertitudes, classée par impact.
- **À valider** : chaque écart, à corriger ou à accepter.
- **Découpage** : un seul prompt.

### Étape 14 : livrable final

- **Plans à joindre** : aucun.
- **Ce que j'attends de vous** : le format exact attendu par votre logiciel ou votre rapport.
- **Prompt type** : « Assemble le livrable final : plans annotés, tableur de métrés, fichier de coordonnées, nomenclatures et note d'hypothèses, au format \[format\]. »
- **Ce que je vous rends** : le dossier complet et la note d'hypothèses.
- **À valider** : la note d'hypothèses, qui engage la fiabilité du calcul.
- **Découpage** : un seul prompt.

## Récapitulatif et nombre de prompts

Pour un bâtiment de 3 niveaux, 4 façades et 2 coupes, comptez environ 30 prompts, validations non comprises.

| Étape | Plan principal | Nombre de prompts | Exemple (3 niveaux, 4 façades, 2 coupes) |
| --- | --- | --- | --- |
| 1. Cadrage | Tous | 1 | 1 |
| 2. Calage | Tous | 1 | 1 |
| 3. Coupes et hauteurs | Coupe | 1 par coupe | 2 |
| 4. Zonage et enveloppe | Plan de niveau | 1 par niveau | 3 |
| 5. Parois opaques verticales | Plan de niveau | 1 par niveau | 3 |
| 6. Planchers et toitures | Toiture, niveau bas | 2 | 2 |
| 7. Menuiseries et cadres | Façade | 1 par façade | 4 |
| 8. Protections et masques | Façade | 1 par façade | 4 |
| 9. Structure | Plan de niveau | 1 par niveau | 3 |
| 10. Ponts thermiques | Plan de niveau, coupe | 1 par niveau + 1 par coupe | 5 |
| 11. Métrés | Aucun | 1 | 1 |
| 12. Systèmes | Plans fluides | 1 | 1 |
| 13. Contrôle croisé | Tous | 1 | 1 |
| 14. Livrable final | Aucun | 1 | 1 |
| **Total** |  |  | **32** |

Deux raccourcis réduisent ce total :

- **Niveaux identiques** : signalez-les. Je traite le premier, puis je vérifie seulement les écarts sur les suivants.
- **Façades ou coupes simples** : les étapes 7 et 8 peuvent être fusionnées par façade, et l'étape 3 traitée en un seul prompt.

## Limites et bonnes pratiques

Le résultat sera fiable si chaque étape est validée, mais il ne sera jamais « parfait » sur la seule base des plans : certaines informations ne s'y lisent pas.

**Ce que les plans ne me donnent pas**

- La composition réelle des parois et les performances des isolants, sans CCTP ni détails.
- La nature lourde ou légère des cloisons.
- Les performances des menuiseries, sans carnet ni fiches.
- Les systèmes, la perméabilité à l'air et l'inertie.
- Les protections solaires mobiles et les masques lointains.

**Ce qui limite la précision**

- Un plan traité comme une image donne des positions à quelques centimètres près ; un fichier vectoriel donne des cotes exactes.
- Le classement intérieur / extérieur et la lecture des symboles reposent sur mon interprétation du dessin. C'est pourquoi chaque étape se termine par une validation.
- Je ne signe pas l'étude : les valeurs réglementaires et le calcul final restent de votre responsabilité.

**Pour garder la qualité tout au long de l'étude**

- Changez de conversation à chaque grande étape. Au-delà d'un certain volume, la qualité baisse.
- À chaque nouvelle conversation, rejoignez les plans utiles, le dernier fichier de coordonnées et la liste des conventions validées. Je ne garde pas la mémoire d'une conversation à l'autre.
- Tenez à jour un seul document de conventions (règles de tracé, nomenclatures, hauteurs retenues) et collez-le en tête de chaque prompt.
- Corrigez une erreur dès qu'elle apparaît : elle se propage sinon aux métrés et aux ponts thermiques.
