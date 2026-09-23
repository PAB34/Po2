---
read_policy: lire avant tout benchmark d'agents thermiciens
status: pilote_r1_execute
---

# Comparatif des agents thermiciens Claude Code et OpenAI

Date : 2026-09-23. Ce lot vérifie si des sous-agents OpenAI connectés avec l'abonnement ChatGPT peuvent produire
les mêmes contrats d'étude que les agents Claude Code, sans clé API et sans lecture des vecteurs PDF.

## Décisions

### A1 — Deux producteurs, un contrat commun

Claude Code et OpenAI reçoivent exactement les mêmes images raster, repères de tuiles, règles métier et schémas
JSON. Ils écrivent dans des dossiers distincts. L'application thermique ne connaît pas le fournisseur : elle importe
uniquement `etude-<niveau>.json`.

### A2 — Benchmark aveugle

L'agent candidat ne peut lire ni les sorties, ni les projections, ni les conversations de l'autre agent. Le premier
pilote utilise un paquet neutre copiant seulement `overview.jpg`, `source.jpg` et les six tuiles du R+1. Aucun PDF ne
lui est fourni. Les sorties Claude existantes servent de référence d'appariement, pas de vérité terrain.

### A3 — Mesurer l'accord sans désigner automatiquement un vainqueur

Le comparateur mesure : conformité du JSON, comptages par catégorie, appariement symétrique, IoU géométrique,
couverture et chevauchement des pièces, accord des noms et natures, confiance, besoins de revue, objets sans
correspondant. Une projection superpose les deux sorties. Le thermicien arbitre les divergences sur l'image.

### A4 — Instructions persistantes et permissions minimales

Les agents OpenAI du projet vivent dans `.codex/agents/` et sont en lecture seule. Ils reprennent les deux rôles
existants : `thermicien_plan_openai` et `thermicien_enveloppe_openai`. Le parent est responsable d'enregistrer leur
JSON. Aucun secret, jeton ou clé n'entre dans le dépôt.

### A5 — Séquence de validation

1. Comparer la passe `thermicien-plan` sur le R+1 connu.
2. Faire arbitrer les divergences importantes par le thermicien.
3. Comparer ensuite les lots `thermicien-enveloppe` avec le même catalogue initial.
4. Rejouer le protocole sur au moins un niveau jamais vu par aucun agent.
5. Répéter chaque candidat au moins trois fois avant de conclure sur sa stabilité.

## Artefacts du pilote R+1

- Entrée neutre : `outputs/benchmark_agents/R1/input/`.
- Sortie OpenAI : `outputs/benchmark_agents/R1/openai/run-01/thermicien-plan.raw.json`.
- Référence d'appariement Claude : `outputs/claude_agent_R1.raw.json`.
- Rapport attendu : `outputs/benchmark_agents/R1/comparaison-plan-run-01/`.

## Commande de comparaison

Depuis `saas/backend` :

```powershell
python scripts/compare_thermicien_agents.py `
  --reference "<outputs>/claude_agent_R1.raw.json" `
  --candidate "<outputs>/benchmark_agents/R1/openai/run-01/thermicien-plan.raw.json" `
  --background "<outputs>/benchmark_agents/R1/input/overview.jpg" `
  --output-dir "<outputs>/benchmark_agents/R1/comparaison-plan-run-01"
```

## Critères provisoires avant généralisation

- zéro erreur de contrat JSON ;
- 100 % des grandes zones intérieures représentées sans chevauchement majeur ;
- IoU de couverture des pièces à interpréter avec le contrôle visuel, cible initiale ≥ 0,85 ;
- toute omission de façade, pièce ou vide majeur est bloquante ;
- les composants ambigus doivent être signalés plutôt qu'inventés ;
- aucun résultat fournisseur n'est déclaré meilleur sans arbitrage humain sur les divergences.

## Résultats du pilote — trois répétitions aveugles

Les trois exécutions ont utilisé les mêmes sept rasters, le même repère et le même contrat. Aucune n'a lu la sortie
Claude ni celle d'une autre répétition.

| Mesure face à Claude Code | Run 01 | Run 02 | Run 03 |
|---|---:|---:|---:|
| Objets OpenAI | 89 | 116 | 78 |
| Objets appariés | 60 | 29 | 56 |
| Taux d'appariement symétrique | 54,8 % | 23,6 % | 53,9 % |
| Accord géométrique moyen | 62,4 % | 39,4 % | 53,7 % |
| IoU de couverture des pièces | 85,0 % | 67,7 % | 77,9 % |
| Erreurs de contrat JSON | 0 | 0 | 0 |
| Polygones de pièces invalides | 0 | 0 | 0 |
| Chevauchement des pièces | 0,8 % | 4,3 % | 0,0 % |
| Confiance moyenne déclarée | 86,6 % | 88,8 % | 86,8 % |
| Objets déclarés à revoir | 38,2 % | 8,6 % | 23,1 % |

Entre répétitions OpenAI, l'IoU des pièces vaut 69,3 % (01/02), 81,0 % (01/03) et 69,6 % (02/03), soit 73,3 %
en moyenne. Les nombres d'objets vont de 78 à 116. Le run 02 projette plusieurs objets sur les axes et la légende alors
qu'il annonce la confiance la plus forte et le plus faible besoin de revue : la confiance auto-déclarée ne constitue
donc pas un garde-fou exploitable.

### Lecture métier provisoire

- Le zonage des pièces est prometteur : le meilleur run atteint 85,0 % de couverture face à Claude, sans polygone
  invalide, et les runs 01/03 s'accordent à 81,0 %.
- Les cloisons et terrasses sont globalement retrouvées dans les runs propres.
- Les murs, isolants et menuiseries restent trop variables pour alimenter automatiquement un métré : l'accord de
  couverture avec Claude est faible et dépend du découpage retenu.
- Claude reste une référence d'appariement, pas une vérité terrain. Les zones ouvertes 4.2/4.3/4.4 et la coursive est
  demandent un arbitrage humain sur les projections.
- Aucune importation automatique en production n'est autorisée à ce stade.

### Correction testée après l'échec du run 02

La consigne de recalage impose désormais la transformation affine explicite de chaque tuile et une reprojection finale
sur la vue globale. Tout tracé suivant une cote, un axe, une légende ou un cartouche doit être corrigé ou retiré. Cette
consigne est enregistrée dans `.codex/agents/thermicien-plan-openai.toml`.

Le run correctif 04 produit 75 objets sans débordement manifeste. Face à Claude, 51 objets sont appariés, l'accord
géométrique moyen monte à 66,3 % et sa médiane à 75,1 %, meilleurs résultats du pilote. En revanche, l'agent refuse de
polygoniser le plateau ouvert 4.2/4.3/4.4 faute de cloisons physiques : la couverture des pièces chute à 44,3 %. La
correction de recalage améliore donc la précision mais dégrade fortement la complétude.

### Décision A6 — Séparer géométrie physique et découpage fonctionnel

Un même passage IA ne doit plus arbitrer seul entre inventer des limites et omettre un grand espace ouvert. La suite doit
produire deux informations distinctes :

1. une couverture physique complète de l'intérieur, contrôlée par l'algorithme raster ;
2. des sous-zones fonctionnelles proposées par l'IA, avec une frontière explicitement marquée `à_recaler` lorsqu'elle ne
   correspond pas à une paroi visible.

Le moteur peut ainsi garantir qu'aucune surface n'est oubliée tout en laissant le thermicien déplacer ou supprimer les
frontières sémantiques. Le contrat actuel ne distingue pas encore ces deux géométries ; c'est le prochain ajustement avant
tout branchement à l'import E2/E3.

### Garde-fous requis avant branchement à l'application

1. Valider strictement le contrat JSON sans correction silencieuse.
2. Générer systématiquement la projection de divergences avec légende.
3. Rejeter un run contenant un polygone invalide ou plus de 2 % de chevauchement entre pièces.
4. Ajouter un contrôle de débordement hors emprise du bâtiment et de cohérence entre vue globale et tuiles.
5. Vérifier que l'union des pièces couvre l'emprise intérieure raster, même quand le plan montre un plateau ouvert.
6. Ne promouvoir une sortie qu'après accord de plusieurs runs ou validation du thermicien.
7. Comparer ensuite l'agent enveloppe, lot par lot, une fois le recalage stabilisé.

## Témoin manquant : stabilité de Claude Code (2026-09-23)

Le pilote comparait trois répétitions OpenAI à **une seule** sortie Claude. Sans mesure de la reproductibilité de
Claude, la phrase « l'agent OpenAI n'est pas assez stable » n'était pas démontrée : on savait seulement qu'il ne
reproduisait pas un tirage. Deux lectures aveugles supplémentaires ont donc été demandées à l'agent
`thermicien-plan`, sur le paquet neutre `input/` (les sept mêmes images), avec la consigne de `build_prompt` et
l'interdiction explicite de lire tout résultat antérieur.

| Comparaison | Objets | Taux symétrique | Accord géométrique moyen | IoU pièces | Accord nature |
|---|---:|---:|---:|---:|---:|
| Claude 01 / 02 | 130 vs 118 | 50,8 % | 46,4 % | **85,0 %** | n/a |
| Claude 01 / 03 | 130 vs 115 | 62,9 % | 54,8 % | **83,8 %** | n/a |
| Claude 02 / 03 | 118 vs 115 | 62,7 % | 60,6 % | **87,0 %** | 100 % (29 pièces) |

IoU moyen des pièces entre runs Claude : **85,3 %**, contre 73,3 % côté OpenAI. La comparaison propre est
**02 / 03** (même consigne, même jour, deux tirages indépendants) : 87,0 %.

Le run Claude de référence (`claude_agent_R1.raw.json`, 130 objets) a été produit avant l'ajout du champ `local`
dans la consigne : ses 22 pièces n'ont pas de nature, d'où `n/a` sur les deux premières lignes et un taux
d'appariement tiré vers le bas par l'écart de comptage. Les runs 02 et 03 déclarent 30 et 31 pièces.

### A7 — Lecture corrigée du pilote

1. **Claude est plus reproductible qu'OpenAI**, sur toutes les mesures : IoU des pièces 85,3 % contre 73,3 %,
   appariement symétrique 58,8 % contre 34,0 %, dispersion du nombre d'objets 115–130 contre 78–116.
2. **Le critère « IoU ≥ 0,85 face à Claude » était inatteignable par construction** : il demandait au candidat
   d'être plus proche de Claude que Claude ne l'est de lui-même. Le bon seuil est l'accord Claude/Claude, et le
   run 01 d'OpenAI (85,0 %) l'atteint : sur ce tirage, il est indiscernable d'une autre lecture de Claude.
3. **15 % de la surface change d'une lecture à l'autre, même chez Claude.** L'instabilité du zonage n'est donc pas
   un défaut de fournisseur : elle est intrinsèque à la tâche. Cela confirme A6 par un autre chemin.
4. **La confiance déclarée reste inutilisable, mais `review_required` est un bon signal.** Sur les objets où les
   deux lectures Claude divergent, 82 % (run 02) et 88 % (run 03) étaient déjà marqués à revoir, contre 53 % et
   56 % des objets concordants ; la confiance moyenne, elle, ne bouge pas (0,51 contre 0,53).
5. **La carte des divergences est la liste de contrôle du thermicien.** Sur `stabilite-claude-run-02-vs-03`, tout
   le bâti et la trame des bureaux se superposent ; les écarts portent exactement sur les objets ambigus : l'alcôve
   EAPMR, la boîte à vents / boîte à lumière, le vide sur Accueil, la bande d'escalier le long de la façade est et
   les parois de la salle de réunion 6.1.6. Ce sont les points à faire trancher, et eux seuls.

### Conséquences pratiques

- Ne pas promouvoir une sortie issue d'un tirage unique : **deux lectures, puis arbitrage des divergences**, quel
  que soit le fournisseur.
- La bande le long de la façade est (escalier extérieur ou intérieur) est une question ouverte sur l'enveloppe :
  les runs 02 et 03 la classent `indetermine` et placent le nu de façade à x ≈ 778 ; le run 01 la traitait
  autrement. À trancher par le thermicien avant tout métré de façade sur ce niveau.
- Artefacts : `claude/run-02/`, `claude/run-03/` et `stabilite-claude-run-01-vs-02`, `-01-vs-03`, `-02-vs-03`
  dans `outputs/benchmark_agents/R1/`.

## Références OpenAI

- Sous-agents Codex : <https://learn.chatgpt.com/docs/agent-configuration/subagents>.
- Authentification par abonnement ChatGPT : <https://learn.chatgpt.com/docs/auth>.
- Import sélectif depuis Claude Code : <https://learn.chatgpt.com/docs/import>.
