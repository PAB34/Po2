# Serveur MCP de la plateforme — premier lot (D291 à D297, proposées)

Date : 2026-10-02. Décision du thermicien : « je suis super chaud de la connexion MCP » → **la plateforme devient
un serveur MCP**, colonne vertébrale de la nouvelle version (question 1 de
`interaction-claude-plateforme-recherche.md` tranchée). Par lui, Claude lit les pièces et l'état d'une étude, et
dépose ses livrables, depuis le poste (Claude Code) comme depuis claude.ai (connecteur).

## Existant vérifié

- Le site thermique envoie tout `/api/*` vers le serveur (Caddy) ; l'authentification est un jeton de connexion (JWT)
  partagé avec Po2 (`get_authenticated_user`). Les comptes sont créés par un administrateur.
- Le serveur sait déjà : lister projets et planches, rendre une planche en tuiles d'image, servir l'étude d'un niveau,
  les vues de coupe, les hauteurs, les modèles de menuiserie.
- Le paquet Python `mcp` (SDK officiel) n'est **pas** installé ; il s'ajoute aux dépendances du **serveur** (image
  Docker), rien sur le poste.

## Décisions proposées

- **D291 — Une adresse** : `https://thermique.patrimoineaucarre.com/api/thermique/mcp`, transport HTTP « streamable »
  du protocole MCP, servie par le serveur existant (SDK officiel `mcp`, monté dans FastAPI).
- **D292 — Les outils du premier lot** (lecture d'abord, une seule écriture) :

  | Outil | Ce qu'il rend |
  |---|---|
  | `projets` | les projets du compte |
  | `pieces` | les pièces d'un projet : planches (nature, niveau, échelle, rotation, nord), page et fichier d'origine |
  | `plan_image` | l'image d'une planche ou d'un zoom (cadre en mètres ou en pixels), à la résolution demandée — pixels seuls |
  | `etude` | l'état d'un niveau : locaux (nature, hauteur, contour), parois (adjacence, composition, menuiseries, surfaces), ponts |
  | `regles_metier` | `regles-metier-validees.md` et, plus tard, les conventions du projet |
  | `deposer_livrable` | dépose le livrable d'une étape (format D272 + note « hypothèses et doutes ») : il est **rangé comme proposition**, rien n'est appliqué tout seul |

  Plus les **prompts** `etape-00` (tri et nommage) puis les étapes du guide, au fur et à mesure.
- **D293 — Livrables rangés à part** : une table `thermique_livrables` (projet, planche, étape, auteur, modèle annoncé,
  contenu JSON, hypothèses et doutes, statut : proposé / validé / rejeté, date). Le site les listera ; l'application
  d'un livrable à l'étude (par exemple les codes des pièces) est un geste du thermicien.
- **D294 — Accès, en deux temps** :
  1. **Jeton personnel pour Claude** : dans le site, « Créer un jeton pour Claude » (durée limitée, révocable,
     lecture des projets + dépôt de livrables seulement). **Vous** le collez dans la configuration de Claude Code
     (`claude mcp add … --header`) ; je ne le vois ni ne le manipule.
  2. **OAuth 2.1** ensuite, pour le connecteur claude.ai (navigateur, bureau, mobile) ; Claude Code sait aussi
     l'utiliser, le jeton personnel devient alors inutile.
- **D295 — Sécurité** : un compte ne voit que ses projets ; aucune écriture hors `deposer_livrable` au premier lot ;
  chaque appel est journalisé (outil, projet, compte, date) ; taille des images bornée.
- **D296 — Modèle annoncé** : chaque livrable porte le modèle déclaré par Claude ; la mission demande de l'indiquer
  (règle du thermicien : pas de modèle remplacé en silence).
- **D297 — Premier essai réel** : la mission **étape 0, tri et nommage des 11 pièces du projet 1**, lancée depuis
  Claude Code sur le poste : lecture des cartouches par `plan_image`, proposition de codes, doublons, pièces
  manquantes, dépôt par `deposer_livrable`. Critère : les 11 codes attendus
  (`convention-nommage-pieces-decisions.md`) retrouvés, et le livrable visible dans le site.

## Ordre du lot

1. Fichier de décisions validé (celui-ci).
2. Serveur MCP + outils de lecture + `deposer_livrable` + table des livrables + jeton personnel ; tests par le
   chemin réel (requête MCP de bout en bout).
3. Mise en ligne ; vous créez le jeton et l'ajoutez à Claude Code ; essai de l'étape 0 sur le projet 1.
4. Lot suivant : OAuth pour le connecteur claude.ai, puis les prompts des étapes, puis l'affichage des livrables
   sur le site.

## Réponses du thermicien (2026-10-02)

1. **OAuth directement** (pas de jeton personnel) : le connecteur marche dans claude.ai et dans Claude Code dès ce lot.
2. **Premier essai : l'étape 4**, import du contour au nu intérieur du R+1 (mission M1), plutôt que l'étape 0.
3. **Paquet officiel `mcp` ajouté au serveur** : accord.
4. **Codes des niveaux comme le guide** : `N0` (rez-de-chaussée), `N1`, `N2`…, `S1` pour le sous-sol.

Conséquences : D294 devient « OAuth 2.1 seul » ; D297 devient « essai : étape 4 sur le R+1 ».

## Questions (posées avant les réponses)

1. **Accès** : jeton personnel d'abord (D294-1, le plus rapide), ou directement OAuth pour travailler aussi dans
   claude.ai dès le premier lot ?
2. **Premier essai** : l'étape 0 (tri des 11 pièces du projet 1) vous convient, ou préférez-vous l'étape 4 (import du
   contour au nu intérieur du R+1) ?
3. **Dépendance serveur** : d'accord pour ajouter le paquet officiel `mcp` au serveur (rien sur le poste) ?
4. **Codes des niveaux** pour l'étape 0 : `N0`/`N1`/`S1` (guide) ou `RDC`/`R1`/`SS1` (vos dossiers) ?
