# Résultat : essai R+2 en session cloud (2026-10-02)

Chaîne complète en **mode session** (agents lancés par l'outil Agent, jamais `--mode cli`), pixels seuls,
une seule passe par étape, aucune réponse d'agent retouchée. Commande :
`run_etude_niveau.py PC05-FRONT-NIVEAU2.pdf --niveau R2 --rotation 90 --catalogue catalogue-R1.json`.
Fin de l'étude : code 0 (`R2/A-FAIRE.md`).

## Comparaison

| Indicateur | R+2 cloud, Opus 5 (cet essai) | R+2 Opus 4.7 (2026-10-01) | R+1 Opus 5 (2026-09-21/23) |
|---|---|---|---|
| Objets de la passe globale | **57** | 25 | 130 |
| · par catégorie | poteau 13, menuiserie ext. 10, mur ext. 9, pièce 9, refend 4, cloison 4, indéterminé 3, garde-corps 3, menuiserie int. 1, terrasse 1 | n.d. (journal sans détail) | n.d. |
| Pièces (passe globale) | 9 | 8 | 22 |
| Locaux finaux | 9 | 8 | 24 |
| · dont circulations | 0 | 0 | 5 |
| · dont non chauffés / gaines / extérieurs | 1 non chauffé (escalier) + 6 gaines + 1 extérieur (terrasse) | n.d. | n.d. |
| Pièces recalées | 5/9 | 5/8 | n.d. |
| Espaces libres | 0 | 0 | n.d. |
| Guide : tronçons / périmètre | 58 (53 façade + 5 côtés sur local non chauffé) / 139,23 m | 99 / 154,6 m | n.d. |
| Lots de l'enveloppe | 4 | 6 | n.d. |
| Composants du catalogue à la fin | 29 (23 repris du R+1 + L9, P5, P6, M6, L10, L11) | 25 | 23 |
| Incohérences du fichier d'étude | **11** | 21 | n.d. |
| Arrêts / erreurs pendant la chaîne | 0 | 5 (2 × limite d'usage 429, 2 × « right < left », 1 interruption) | — |

## Modèle et durée de chaque agent (repris de `MODELES.md`)

| Étape | Agent | Modèle relevé dans la trace | Durée |
|---|---|---|---|
| Passe globale | thermicien-plan | claude-opus-5-5 | 152 s |
| Locaux | thermicien-plan | claude-opus-5-5 | 15 s |
| Lot 1 (T01–T18) | thermicien-enveloppe | claude-opus-5-5 | 136 s |
| Lot 2 (T19–T36) | thermicien-enveloppe | claude-opus-5-5 | 215 s |
| Lot 3 (T37–T53) | thermicien-enveloppe | claude-opus-5-5 | 286 s |
| Lot 4 (U01–U05) | thermicien-enveloppe | claude-opus-5-5 | 71 s |

Total agents : environ 14,6 min ; chaîne de bout en bout : 07:31 → 07:51 (20 min).

## Lecture

- **Avec Opus 5, la passe globale passe de 25 à 57 objets** et les incohérences tombent de 21 à 11. La chaîne est
  allée au bout sans aucun arrêt, alors que l'essai Opus 4.7 en avait eu 5.
- **Pièces et locaux restent bas (9 contre 22 au R+1)**. L'agent décrit le plateau de bibliothèque comme
  **une seule pièce** (« 5.1 Fiction / 5.2 Recherche et Documentation / 5.3 Roman noir », 676 m²) et indique en
  observation qu'il ne voit aucune cloison entre les zones. Le R+2 semble donc réellement ouvert : le nombre de
  pièces ne se compare pas directement au R+1. Il faudrait le confirmer sur le plan
  (`A-FAIRE.md` demande d'ailleurs à l'architecte le découpage des zones).
- La qualité du R+1 n'est **pas retrouvée sur la passe globale** : 57 objets contre 130. Les petits poteaux de
  la façade ouest et des rives de terrasse ne sont pas inventoriés un par un (l'agent le dit lui-même).
- Les incohérences restantes portent sur trois points :
  - les gaines (ascenseurs, EP) incluses dans le plateau, qui le chevauchent sur 6,6 m² ;
  - la terrasse de lecture, hors emprise et sans éléments d'enveloppe en vis-à-vis ;
  - deux contours à reprendre à la main (terrasse, CF).
- Le guide de façade fait des détours, aux tronçons T06–T08 et T51–T52 : il passe par le claustra et la bulle
  d'axe 2. Il est aussi décalé d'environ 50 cm vers l'intérieur aux tronçons T31, T36 et T39. Les agents l'ont
  signalé en observation sans rien corriger.

## Fichiers

- `R2/etude-R2.json`, `R2/A-FAIRE.md`, `R2/journal.json` ;
- images de contrôle : `R2/enveloppe.pieces.png`, `R2/enveloppe/catalogue.png`, `R2/enveloppe/controle-image.png` ;
- réponses brutes des agents : `R2/passe-globale.reponse.json`, `R2/locaux.reponse.json`, `R2/enveloppe/reponse-lot-*.json`.

Rien n'a été importé sur le site.
