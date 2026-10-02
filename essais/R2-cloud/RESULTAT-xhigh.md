# Résultat : R+2 en effort xhigh, Opus 5.5 et Fable 5.1 (2026-10-02)

Même chaîne que `sorties/RESULTAT.md` (mode session, pixels seuls, une passe par étape, réponses d'agents non
retouchées), agents `thermicien-plan` et `thermicien-enveloppe` en `effort: xhigh`. Effort et modèle vérifiés
dans chaque trace (`"effort":"xhigh"`, voir `sorties-*-xhigh/MODELES.md`).
Branche poussée : `claude/essai-r2-xhigh-0er7sn` (branche imposée à cette session cloud).

## Comparaison

| Indicateur | R+2 Opus 4.7 | R+2 Opus 5.5 medium (`sorties/`) | R+2 Opus 5.5 xhigh | R+2 Fable 5.1 xhigh | R+1 Opus 5 (réf.) |
|---|---|---|---|---|---|
| Objets de la passe globale | 25 | 57 | **79** | 55 | 130 |
| · par catégorie | n.d. | poteau 13, menuis. ext. 10, mur ext. 9, pièce 9, refend 4, cloison 4, indét. 3, garde-corps 3, menuis. int. 1, terrasse 1 | menuis. ext. 17, poteau 13, pièce 13, mur ext. 9, isolation 8, garde-corps 6, refend 5, menuis. int. 3, cloison 3, indét. 1, terrasse 1 | pièce 14, menuis. ext. 10, garde-corps 7, mur ext. 5, refend 4, cloison 4, isolation 3, menuis. int. 3, poteau 3, terrasse 1, indét. 1 | n.d. |
| Pièces (passe globale) | 8 | 9 | 13 | 14 | 22 |
| Locaux finaux | 8 | 9 | 13 | 15 | 24 |
| · dont circulations | 0 | 0 | 0 | 0 | 5 |
| · non chauffés / gaines / extérieurs | n.d. | 1 / 6 / 1 | 1 / 8 / 1 | 1 / 7 / 1 (6 chauffés) | n.d. |
| Pièces recalées / espaces libres | 5/8 / 0 | 5/9 / 0 | **12/13** / 0 | 9/14 / 1 | n.d. |
| Guide : tronçons / périmètre | 99 / 154,6 m | 58 (53 T + 5 U) / 139,2 m | 91 (72 T + 19 U) / 150,0 m | 104 (69 T + 35 U) / 156,1 m | n.d. |
| Lots de l'enveloppe | 6 | 4 | 6 | 6 | n.d. |
| Composants du catalogue à la fin | 25 | 29 | 43 | 40 | 23 |
| Incohérences du fichier d'étude | 21 | **11** | 16 | **13** | n.d. |
| Incidents | 5 | 0 | 0 | lot 3 : `max_output_tokens` (JSON complet récupéré, pas de relance) | — |
| Durée totale des agents | n.d. | 14,6 min | 1 h 50 | 3 h 51 | n.d. |
| Durée de la chaîne | n.d. | 21 min | 2 h 08 | ≈ 4 h 15 | n.d. |
| **Coût estimé (tarif API)** | n.d. (pas de trace) | n.d. (pas de trace) | **≈ 14,8 $** | **≈ 48,6 $** | n.d. |

## Coût : méthode et tarifs retenus

Usage relevé dans les traces `subagents/agent-*.jsonl`, par message API. La sortie du dernier message de chaque
agent est tronquée dans la trace ; elle est corrigée avec le total de jetons de la notification de fin
(total = contexte + sortie du dernier message). Lot 3 Fable : pas de total (fin en erreur), sortie prise
telle que tracée (borne basse). Les traces des colonnes Opus 4.7 et Opus 5.5 medium ne sont pas dans ce
conteneur : coût non disponible.

| Tarif ($/M jetons) | Entrée | Sortie | Lecture cache | Écriture cache 5 min | Écriture cache 1 h |
|---|---|---|---|---|---|
| Opus 5.5 | 4 | 20 | 0,20 | **5** (1,25 × entrée, retenu) | 8 (2 × entrée, non utilisé) |
| Fable 5.1 | 10 | 50 | **1** (0,1 × entrée, retenu) | **12,5** (1,25 × entrée, retenu) | 20 (non utilisé) |

Toutes les écritures de cache des traces sont en 5 min.

| Chaîne | Entrée | Écriture cache | Lecture cache | Sortie | Coût |
|---|---|---|---|---|---|
| Opus 5.5 xhigh (8 appels) | 68 | 510 490 | 498 764 | 608 169 | 14,82 $ |
| Fable 5.1 xhigh (8 appels) | 234 | 975 993 | 564 756 | 715 988 | 48,57 $ |

## Lecture

- **xhigh fait mieux qu'en medium sur la lecture du plan** : la passe globale Opus passe de 57 à 79 objets, les
  pièces recalées de 5/9 à 12/13 et le catalogue de 29 à 43 composants. Les côtés sur local non chauffé
  (cage, gaines, boîte à vents) sont relevés en détail (19 U contre 5).
- **Mais les incohérences remontent (11 → 16 en Opus)**. Le guide fait passer l'enveloppe est sur la rive de la
  terrasse de lecture : la façade vitrée réelle est hors des bandes (signalé par les agents dès le lot 1), d'où
  les écarts contour / façade de 5.3 Roman noir et de 5.2. 93 m² d'intérieur restent sans local (plateau ouvert).
- **Fable 5.1 xhigh** lit moins d'objets (55) mais finit avec 13 incohérences (aucun recouvrement de locaux,
  95,6 % d'emprise couverte, 5 locaux à recaler, 1 hors emprise). Il coûte environ 3,3 fois plus qu'Opus xhigh
  pour une chaîne deux fois plus longue ; un lot a dépassé la limite de 64 000 jetons de sortie.
- La qualité du R+1 (130 objets, 22 pièces) n'est pas retrouvée : le R+2 est un plateau ouvert, le nombre de
  pièces ne se compare pas directement.
- Pour la suite, le levier est le **guide de l'enveloppe** (détours sur claustras, terrasses, bulles d'axe),
  pas l'effort des agents.

## Fichiers

`sorties-opus55-xhigh/` et `sorties-fable51-xhigh/` : `MODELES.md`, `usage.jsonl`, `R2/etude-R2.json`,
`R2/A-FAIRE.md`, images `R2/enveloppe.pieces.png`, `R2/enveloppe/catalogue.png`, `R2/enveloppe/controle-image.png`.
Rien n'a été importé sur le site.

## Recommandations

Bilan : environ 63 $ d'agents (Opus 5.5 xhigh ≈ 15 $, Fable 5.1 xhigh ≈ 49 $). S'y ajoute la session
d'orchestration : recopie des consignes à chaque lot et suivi des deux chaînes pendant environ 4 h, soit près de
100 $ au total. Le résultat ne justifie pas ce coût : xhigh lit mieux le plan mais ne réduit pas les
incohérences, qui viennent surtout du guide.

### 1. Modèle et effort

- **Garder Opus 5.5 à l'effort par défaut** pour la chaîne. C'est l'état des agents depuis le retour de ce
  commit : la ligne `effort` est supprimée. Il donne le meilleur rapport qualité/coût : 11 incohérences en 21 min.
- **Ne pas utiliser Fable 5.1** pour cette chaîne. Il coûte environ 3,3 fois plus qu'Opus xhigh et lit moins
  d'objets (55 contre 79). Un lot a aussi dépassé la limite de 64 000 jetons de sortie.
- **Réserver xhigh à un essai ciblé** : par exemple la seule passe globale, sur un plan dense, si l'inventaire des
  objets devient le facteur limitant. Il ne sert pas pour les lots d'enveloppe.

### 2. Corriger le guide de l'enveloppe (code Python, aucun appel de modèle)

Ce sont les défauts signalés par les agents, lot après lot, sur les deux chaînes :

- **Façade derrière une terrasse** : à l'est, le guide suit la rive de la terrasse de lecture (claustra, ailettes,
  lisse) au lieu du mur-rideau, situé 2 à 5 m en retrait. Le guide doit suivre la paroi du volume chauffé, pas
  le contour des dalles extérieures. Les terrasses, balcons et rives sont à traiter à part.
- **Allers-retours parasites** : le guide fait des boucles sur les claustras ou potelets (terrasse du personnel)
  et sur les lignes d'axe jusqu'à leur bulle (« 2 », « 1' »). Il faut exclure les traits d'axe, les bulles et
  les éléments extérieurs isolés avant de tracer le contour.
- **Bandes rendues à l'envers** : sur plusieurs tronçons (T38, T44, T53, T62, T69 en Opus ; T43, T48 en
  Fable), l'extérieur est en bas. Les agents ont dû inverser les profondeurs à la main. Il faut garantir le sens
  extérieur en haut pour chaque bande, ou indiquer le sens dans le titre.
- **Guide décalé de la paroi** : il est décalé de 20 à 50 cm devant les baies des trémies et de 40 cm sur
  certains côtés U. Les coins tombent alors hors des bornes des tronçons. Il faut recaler le guide sur le nu
  relevé, ou élargir la bande, par exemple de -90 à +100 cm.
- **Côtés U qui entrent dans les locaux techniques ou les débattements de porte** : le contour de 5.1 et 5.2 est
  passé par la porte CF ouverte et dans les gaines CF, CVC et ventilation. Il faut fermer les contours des
  locaux sur les baies de porte avant de générer les côtés U.

### 3. Réduire le coût d'orchestration

- **Faire lire la consigne par l'agent** dans son fichier (`consigne-lot-N.md`, `schema-lot-N.json`) au lieu de
  la recopier dans le prompt. L'orchestrateur ne transmet alors que deux chemins par lot.
- **Récupérer la réponse depuis la trace** de l'agent : c'est déjà fait par un script, sans la retaper.
- **Une seule chaîne à la fois**, sans suivi détaillé pendant les lots.

### 4. Lecture des locaux

- Le R+2 est un plateau ouvert : 5.1, 5.2 et 5.3 n'ont pas de cloison. Le nombre de pièces ne se compare pas au
  R+1. Il faut demander à l'architecte le découpage des zones, ou accepter une pièce unique.
- **Statut thermique à confirmer** pour la cage d'escalier CF, les gaines d'ascenseur et EP, les locaux
  CVC/ventilation et la boîte à vents. De ce statut dépend l'entrée dans l'enveloppe des composants P6, P7, M7,
  etc.

### 5. Prochain essai conseillé

Corriger le guide (§ 2), puis relancer **une seule** chaîne Opus 5.5 à l'effort par défaut sur le R+2, en
appliquant le § 3. Comparer ensuite à la colonne « Opus 5.5 medium » de ce tableau.
