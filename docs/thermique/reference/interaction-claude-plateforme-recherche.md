---
read_policy: lire avant toute décision sur la façon dont Claude (Code, navigateur, mobile) travaille avec la plateforme thermique
---

# Comment Claude et la plateforme peuvent travailler ensemble — recherche (2026-10-02)

Demande du thermicien : « réfléchis à toutes les solutions possibles, fais une recherche, peut-être on passe à côté
de quelque chose (connexion MCP ou autre) ». Cadre : `refondation-assistant-ia-local-decisions.md` (assistant IA
d'étude thermique en local avec Claude) et `guide-etude-thermique-14-etapes.md`.

Contraintes connues : abonnement Claude, **pas de clé d'API** ; **aucune installation sur le poste** (Python et Node
présents ; ni Bun, ni OpenCV) ; je ne manipule ni jetons ni identifiants ; dépôt GitHub **public** ; les analyses
d'image marchent le mieux quand Claude **exécute du code** et choisit ses zooms.

## Ce qui existe aujourd'hui

**File de travaux + relais sur le poste** : « Analyser » sur le site met un niveau en file ; un petit programme sur
le poste (`relais_thermique.py`) la lit, lance `claude -p` (mode automatique, sans fenêtre), puis renvoie le
résultat. Le résultat s'importe aussi par fichier JSON. Limites : sens unique, pas de dialogue ni de validation,
consignes figées, mauvais modèle par l'alias `opus`.

## Toutes les solutions trouvées

| # | Solution | Ce que c'est | Ce que ça apporterait | Limites |
|---|---|---|---|---|
| 1 | **Serveur MCP de la plateforme, distant** (« connecteur personnalisé ») | Le site expose une adresse MCP (`…/mcp`), avec connexion OAuth. On l'ajoute **une fois** dans claude.ai (Personnaliser → Connecteurs). Il est alors disponible **dans le navigateur, l'application de bureau, le mobile et Claude Code** | Claude lit directement le projet : plans, conventions, étude, livrables. Il **dépose** ses livrables, qui apparaissent sur le site pour validation. Les 14 étapes deviennent des **« prompts » MCP**, c'est-à-dire des commandes toutes prêtes (`/etape-04` dans Claude Code, menu « + » dans claude.ai) | Il faut écrire le serveur MCP (outils + OAuth 2.1 côté site). Le plan transite par Anthropic, comme aujourd'hui dans le navigateur. **À vérifier par un essai** : passer une image de plan d'un outil MCP à l'environnement de code de claude.ai |
| 2 | **Serveur MCP local** (sur le poste) | Le même serveur, lancé par Claude Code sur le poste (programme Python, sans installation nouvelle) | Démarrage rapide, sans OAuth : il parle à l'API du site avec un accès que **vous** déposez dans un fichier (je n'y touche pas) | Claude Code sur le poste seulement, pas dans le navigateur |
| 3 | **MCP Apps** (interfaces dans la conversation) | Un outil MCP peut renvoyer une **petite interface HTML interactive** que Claude affiche dans la conversation (claude.ai, application de bureau) | Le plan annoté s'affiche **dans la discussion**, avec des boutons « valider / corriger » ; aucun aller-retour vers le site pour une validation simple | Spécification récente (janvier 2026), des rendus encore capricieux selon les retours ; à garder pour plus tard |
| 4 | **Compétences et extension (plugin) Claude Code** | Des commandes `/etape-01` à `/etape-14` dans le dépôt, avec la boîte à outils d'analyse d'image, l'agent outillé et la configuration MCP, réunis en une extension | Le guide devient exécutable sur le poste : chaque commande prépare la mission (plan, conventions, livrable précédent) et fait demander « hypothèses et doutes » | Claude Code uniquement ; complémentaire de 1 ou 2 |
| 5 | **Canaux (channels)** | Le site **pousse** un événement (« le thermicien demande l'étape 4 du R+2 ») dans une session Claude Code déjà ouverte sur le poste | Remplacerait la file + relais : une demande faite sur le site arrive dans votre session ouverte, qui la traite avec vous | **Aperçu de recherche** ; les canaux officiels demandent **Bun** (installation) ; un canal maison passe par un mode « développement » ; la session doit rester ouverte |
| 6 | **Mode automatique `claude -p`** (l'actuel) | Lancer Claude sans fenêtre depuis un programme | Déjà en place (relais) | Pas de dialogue ni de validation ; corriger l'alias du modèle |
| 7 | **Tâches programmées sur le poste** (application de bureau) | Une tâche Claude qui tourne à heure fixe sur votre machine | Vider la file du site sans relais à lancer à la main | Pas d'interaction ; utile seulement pour des travaux de nuit |
| 8 | **Routines dans le cloud** | Une tâche Claude dans le cloud, déclenchée par un appel d'API ou un horaire | Le site pourrait lancer une analyse cloud à la demande | Crédits cloud ; le code et les plans doivent être sur GitHub (dépôt public) ; le site détiendrait un jeton de déclenchement |
| 9 | **Contrôle à distance (Remote Control)** | Piloter depuis claude.ai ou le téléphone une session Claude Code ouverte sur le poste | Suivre ou relancer une étude du poste depuis ailleurs | Ne relie pas le site à Claude |
| 10 | **Claude pilote le navigateur** (navigateur intégré ou Claude dans Chrome) | Claude clique dans le site comme vous | Pas d'API à écrire : il utilise l'écran existant | Fragile, lent ; votre règle interdit que j'agisse connecté à votre place ; à réserver à la recette |
| 11 | **Crochets (hooks)** | Une commande lancée automatiquement à un moment de la session (fin d'étape…) | Déposer d'office un livrable sur le site à la fin d'une mission | Brique d'appoint, à combiner |
| 12 | **Agent SDK** | Bibliothèque pour fabriquer son propre agent sur le moteur de Claude Code | Un assistant intégré au serveur du site | **Exige une clé d'API** : Anthropic interdit l'usage d'un abonnement claude.ai dans un produit tiers. Écarté (pas de clé d'API) |
| 13 | **`claude mcp serve`** | Claude Code devient lui-même un serveur MCP pour une autre application | — | Local seulement ; ne sert pas ici |

## Ce qu'on était en train de rater

1. **Le connecteur personnalisé (solution 1)** : une seule intégration sert **tous** les endroits où vous parlez à
   Claude. Vos deux essais réussis dans le navigateur auraient pu **lire le plan et déposer le contour directement
   dans le projet**, sans téléchargement ni copie de fichier.
2. **Les « prompts » MCP** : les 14 étapes du guide peuvent être servies par le site lui-même comme commandes
   prêtes, à jour, avec les conventions du projet injectées. Plus de copier-coller du guide.
3. **MCP Apps** : la validation pourrait, à terme, se faire dans la conversation.

## Recommandation

**Colonne vertébrale : un serveur MCP de la plateforme** (solution 1), qui donne à Claude les outils du métier :

| Outil MCP | Rôle |
|---|---|
| `projets`, `planches` | lister les projets, les plans (noms stables PLAN-N1, COUPE-AA…), leur échelle, rotation, nord |
| `plan_image` | rendre un plan ou un zoom en image (pixels seuls) |
| `conventions` (lire / proposer une mise à jour) | le document de conventions du projet |
| `etude` | l'état validé d'un niveau (locaux, parois, menuiseries, ponts, hauteurs) |
| `deposer_livrable` | déposer le livrable d'une étape (format D272) : il arrive sur le site **comme proposition**, que vous validez |
| `hypotheses_et_doutes` | déposer la note de fin de mission, affichée à côté du livrable |
| prompts `etape-01` … `etape-14` | la consigne du guide, avec plan, conventions et livrable précédent déjà remplis |

**Par étapes, du plus sûr au plus ambitieux :**

1. **Serveur MCP local** (solution 2) + **commandes Claude Code** (solution 4) sur le poste : pas d'OAuth,
   démarrage rapide, essai sur l'étape 4 du R+1 (import du contour M1).
2. **Même serveur, publié sur le site avec OAuth** (solution 1) : disponible dans le navigateur, le bureau, le
   mobile. On vérifie par un essai le passage des images vers l'environnement de code de claude.ai.
3. Plus tard, si utile : **MCP Apps** pour valider dans la conversation, **canaux** quand ils seront sortis de
   l'aperçu et sans installation.

La file + relais reste en secours (avec le modèle corrigé) ; l'Agent SDK est écarté (clé d'API).

## Ce que change le dépôt par les clients (précision du thermicien, 2026-10-02)

« À terme, je demanderai aux clients de déposer toutes les pièces, écrites et graphiques, directement sur la
plateforme. »

1. **Le site devient la maison de chaque étude** : pièces du client, conventions, livrables, validations. Le poste
   n'est plus qu'un endroit où Claude travaille. Le « dossier d'étude local » de D276 devient un **dossier d'étude
   sur la plateforme**, dont le poste peut garder une copie de travail.
2. **Le serveur MCP publié (solution 1) devient la bonne cible**, et non une option : les pièces sont sur le
   serveur, Claude doit les lire là où elles sont, depuis le poste comme depuis le navigateur. Le serveur local
   (solution 2) ne reste qu'une étape de mise au point.
3. **L'étape 1 du guide (cadrage et inventaire) se fait sur ce que le client a déposé** : la plateforme peut tenir
   la liste des pièces attendues (plans de tous les niveaux, coupes, façades, plan masse, CCTP, carnet de
   menuiseries…), cocher ce qui est arrivé et réclamer au client ce qui manque.
4. **Pièces écrites** : CCTP, notices et carnets de menuiseries (PDF, tableurs) rejoignent les plans. L'outil
   `planches` devient `pieces` (graphiques et écrites), et l'outil `plan_image` se double d'une lecture des pièces
   écrites.
5. **Ce qu'il faudra côté site** : un espace de dépôt pour chaque client (comptes externes : voir l'ADR 013),
   les droits (le client dépose et consulte, le thermicien travaille), et l'information du client sur le
   traitement de ses pièces par une IA.
6. **Confidentialité, à regarder de près avant d'ouvrir aux clients** : les pièces lues par Claude passent par
   Anthropic. Avec un abonnement claude.ai, vérifier le réglage d'utilisation des conversations pour
   l'entraînement, et le mentionner dans vos conditions. Une offre ouverte à d'autres bureaux d'études passera
   probablement par l'API, sous les conditions commerciales d'Anthropic (voir l'Agent SDK, solution 12).

## Réponse du thermicien (2026-10-02)

**Question 1 tranchée** : « je suis super chaud de la connexion MCP » → le serveur MCP de la plateforme est la
colonne vertébrale. Premier lot : `serveur-mcp-plateforme-decisions.md` (D291–D297).

## Questions

1. **Serveur MCP de la plateforme** comme colonne vertébrale : d'accord ?
2. **Commencer en local** (poste, sans OAuth), puis le publier pour le navigateur : d'accord ? Ou directement
   publié, pour travailler dans claude.ai comme vos deux essais ?
3. **Accès du serveur local au site** : il lui faut un accès à votre compte du site. Vous préférez (a) un jeton
   d'accès que **vous** créez sur le site et déposez dans un fichier local (je n'y touche pas), ou (b) attendre
   la version publiée avec OAuth (vous vous connectez une fois depuis claude.ai) ?
4. **Confidentialité** : avec un connecteur, des images de plans passent par Anthropic, comme aujourd'hui dans le
   navigateur. Acceptable pour vos projets clients ? Faudra-t-il le leur dire au dépôt de leurs pièces ?
5. **Dépôt par les clients** : on le prévoit dès la conception du serveur MCP (pièces écrites et graphiques, liste
   des pièces attendues), mais on ne construit l'espace client qu'après le pilote R+1 ?

## Sources

- Claude Code et MCP (transports, OAuth, portées, prompts en commandes, `claude mcp serve`) :
  https://code.claude.com/docs/en/mcp
- Panorama des intégrations Claude Code (canaux, routines, tâches programmées, Remote Control, Chrome, Agent SDK) :
  https://code.claude.com/docs/en/overview
- Canaux (aperçu de recherche, Bun, liste d'autorisation, mode développement) : https://code.claude.com/docs/en/channels
- Agent SDK (clé d'API exigée pour un produit tiers) : https://code.claude.com/docs/en/agent-sdk/overview
- Connecteurs personnalisés claude.ai (MCP distant, OAuth) : https://claude.com/docs/connectors/custom/remote-mcp et
  https://support.anthropic.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers
- Limite : pas d'en-tête « Bearer » simple pour un connecteur claude.ai (OAuth seulement) :
  https://github.com/anthropics/claude-ai-mcp/issues/112
- MCP Apps (interfaces dans la conversation) : https://modelcontextprotocol.io/extensions/apps/overview ;
  retour de rendu capricieux : https://github.com/modelcontextprotocol/ext-apps/issues/671
