---
type: decisions
status: actif
read_policy: si la tâche concerne le lot F0 de l'outil thermique
related:
  - parcours-par-niveau-E3bis-decisions.md
  - nord-et-edition-plan-decisions.md
  - chaine-analyse-plan-raster.md
---

# Lot F0 — file d'attente et relais local — décisions

> Fichier « fil du dev » ouvert le **2026-09-24**, après la mise en production de F1, F3 et du nord.
> Décision fondatrice : **D76** (`parcours-par-niveau-E3bis-decisions.md`). Ce fichier vérifie l'existant,
> propose les décisions d'implémentation et pose les questions à trancher **avant** d'écrire du code.

## 1. Le problème, en une phrase

Le serveur ne peut pas lancer un programme sur le poste du thermicien. L'analyse d'un plan a besoin des
agents Claude Code, qui tournent sur ce poste avec l'abonnement de l'utilisateur, sans clé d'API. Il faut
donc **une file côté serveur** et **un relais côté poste** qui la vide.

## 2. Existant vérifié (rien à réécrire)

### La chaîne d'analyse est complète et scriptée

`saas/backend/scripts/run_etude_niveau.py` fait déjà tout le travail d'un niveau :

- entrées : `source` (PDF), `--niveau`, `--sorties`, `--rotation`, `--page`, `--echelle`, `--catalogue` ;
- `--mode cli` **appelle lui-même Claude Code** (`claude -p --agent …`) avec l'abonnement du poste ;
- **reprise intégrée** : un `journal.json` par niveau, la commande repart où elle s'est arrêtée ;
- codes de sortie : **0** terminé, **3** en attente d'un agent, **1** erreur ;
- le catalogue appris d'un niveau est un fichier (`enveloppe/catalogue.json`) que `--catalogue` reprend.

Rien à modifier ici : le relais n'est qu'un ordonnanceur autour de cette commande.

### Le serveur sait déjà recevoir une étude

- `POST /api/thermique/sheets/{id}/etude/importer` — envoi du fichier unique produit par la chaîne, avec un
  drapeau `remplacer` et un plafond de **10 Mio** (`thermique_etudes.MAX_ETUDE_BYTES`). L'étude du R+1 en
  v3 pèse 992 Ko ; la marge est confortable mais pas infinie sur un très grand niveau.
- `GET /api/thermique/documents/{id}/file` — téléchargement du PDF d'origine.
- La planche porte déjà **tout ce dont la chaîne a besoin** (`thermique_sheets`) : `level_label`,
  `rotation_deg`, `scale_denominator`, `page_index`, `page_width_pt`/`page_height_pt`, et depuis la
  migration 0085 le `north_json`.

### Le garde-fou a déjà sa source de vérité

`thermique_etudes.local_states_json` porte, local par local, `{"status": "a_verifier" | "valide", "motif"}`,
et `thermique_etude_versions` conserve chaque enregistrement avec son `reason`. Savoir si le thermicien a
déjà travaillé sur un niveau ne demande **aucune donnée nouvelle**.

### L'authentification existe telle quelle

`POST /api/auth/login` (courriel + mot de passe) renvoie un jeton porteur, valable
**1440 minutes (24 h)** (`settings.access_token_expire_minutes`). Toutes les routes thermiques passent par
`get_authenticated_user`.

### L'ordre des niveaux est déjà codé

`saas/frontend/src/thermique/workspace/levels.ts` → `levelRank()` classe les libellés libres : sous-sols
négatifs, RDC = 0, étages positifs, toiture en dernier. **À porter côté serveur**, pas à réinventer.

### Ce qui n'existe pas

- Aucune table de file d'attente, aucun modèle de travail à faire.
- Aucune route pour mettre en file, prendre un travail, le rendre ou le déclarer en échec.
- Aucun programme de relais sur le poste.
- Aucun affichage d'avancement dans l'interface.

## 3. Décisions proposées

### D92 — Une table de travaux, une ligne par niveau

`thermique_travaux` : `id`, `project_id`, `sheet_id`, `statut`, `rang`, `demande_par_user_id`,
`pris_a`, `fini_a`, `journal_json`, `message`. Statuts : `en_attente` → `en_cours` → `fini`, plus
`refuse` (garde-fou) et `echec`. Une seule ligne vivante par planche : redemander l'analyse d'un niveau
déjà en file ne crée pas de doublon.

**Pourquoi une table et pas un fichier** : la file doit survivre à un redémarrage du conteneur et être
lisible par l'interface, qui affiche l'avancement.

### D93 — Le serveur distribue, il ne décide de rien

Quatre routes, toutes authentifiées comme le reste :

| Route | Rôle |
|---|---|
| `POST /projects/{id}/analyser` | met en file les niveaux éligibles, renvoie ce qui a été ajouté **et ce qui a été écarté, avec le motif** |
| `GET /travaux` | ce que le relais doit faire, dans l'ordre `levelRank` |
| `POST /travaux/{id}/prendre` | passe en `en_cours` et renvoie le PDF et les réglages de la planche |
| `POST /travaux/{id}/rendre` | l'import de l'étude **et** la clôture du travail, en une transaction |

Le relais n'invente jamais un ordre ni un choix de niveau : il exécute ce que la file lui donne.

### D94 — Éligible = classé, à l'échelle, sans travail humain dessus

Un niveau entre en file s'il est `nature = "plan"`, qu'il a une échelle, et que **l'une** de ces
conditions tient :

- il n'a aucune étude ;
- il a une étude **jamais touchée** : aucun local `valide`, aucune version d'enregistrement.

Sinon la route le renvoie dans les **écartés**, avec la raison en clair (« 7 locaux déjà validés »).
Aucun écrasement silencieux du travail du thermicien.

### D95 — Le catalogue monte avec les niveaux

Le relais traite du niveau le plus bas au plus haut, et passe `--catalogue` du niveau précédent au
suivant, dans un même projet. C'est ce qui garantit qu'un même composant garde le même identifiant dans
tout le bâtiment. Le classement vient de `levelRank`, porté côté serveur ; un libellé que `levelRank` ne
sait pas lire part **en dernier**, après les niveaux classés, plutôt que de bloquer la file.

### D96 — Le relais reste un petit programme lisible

`saas/backend/scripts/relais_thermique.py`, sans dépendance nouvelle :

1. il demande une fois les identifiants du thermicien **dans son terminal**, garde le jeton dans un
   fichier local hors dépôt, et redemande quand le jeton expire ;
2. il boucle : prendre un travail → télécharger le PDF → lancer `run_etude_niveau.py --mode cli` →
   rendre le résultat ;
3. **sortie 3** de la chaîne (un agent doit intervenir à la main) : le travail repasse `en_attente` avec
   le message, et le relais passe au suivant — il ne bloque jamais la file sur un niveau ;
4. première version **à la demande** : on lance la commande, elle vide la file, elle s'arrête.

Aucun secret n'entre dans le dépôt, et le programme n'écrit jamais un mot de passe dans son journal.

### D97 — L'interface montre l'attente, pas seulement le résultat

Un bouton « Analyser avec Claude Code » sur le projet, et sous lui la file : un niveau par ligne, son
statut, et pour les écartés la raison. Tant que le relais n'a pas tourné, l'écran dit clairement
**« en attente du relais sur votre poste »** — sinon le thermicien croira que l'outil est en panne.

### D98 — Une session Claude expirée n'est pas un échec d'analyse

Constaté le 2026-09-24 en vérifiant Q1 : la session du poste avait expiré, et `claude -p` répondait
`401 OAuth access token is invalid`. Si le relais traitait cette réponse comme une erreur de chaîne, il
marquerait **tous** les niveaux en échec en quelques secondes. Il doit donc reconnaître ce cas, remettre
le travail en `en_attente`, s'arrêter et afficher « votre session Claude a expiré : `claude auth login` ».
La même prudence vaut pour le jeton du site (Q2).

## 4. Questions numérotées — réponses du 2026-09-24

**Q1 — Le relais tourne-t-il bien sur ce poste ? → OUI, vérifié.**
`claude` version 2.1.128 est installé (`C:\Users\pa.borja\.local\bin\claude.exe`). Après reconnexion :
`claude -p "…"` répond, et `claude -p "…" --agent thermicien-plan` répond depuis le dépôt. **Les deux
formes marchent, dont celle qu'utilise `run_etude_niveau.py --mode cli`.** L'hypothèse qui porte le lot
est confirmée. Au passage : la session expire, d'où D98.

**Q2 — Connexion du relais. → (a)**, le relais redemande les identifiants dans son terminal à
l'expiration. C'est l'option qui **ne demande aucun ajout côté serveur** : si le besoin d'un jeton
d'application révocable apparaît quand le relais tournera en veille, rien ne sera à défaire.

### Rappel de l'énoncé initial

**Q1 — Le relais tourne-t-il bien sur ce poste ?** `--mode cli` suppose que la commande `claude` est
installée et connectée sur ta machine. Peux-tu confirmer que `claude` répond dans un terminal ? Sinon le
relais devra rester en `--mode session`, c'est-à-dire s'arrêter à chaque agent et attendre que tu
relances depuis ta session Claude Code — beaucoup moins automatique.
*Recommandation : vérifier avant tout le reste, c'est l'hypothèse qui porte le lot.*

**Q2 — Connexion du relais.** Le jeton vaut 24 h. Trois options : (a) le relais redemande le mot de passe
à chaque expiration ; (b) on ajoute un **jeton d'application** de longue durée, révocable, créé depuis
l'interface ; (c) on allonge la durée du jeton pour tout le monde.
*Recommandation : **(a)** pour la première version — c'est une commande lancée à la demande, tu es devant
ton clavier. (b) deviendra utile le jour où le relais tournera en veille.*

**Q3 — Portée du bouton.** « Analyser » porte-t-il sur **tout le projet** (tous les niveaux éligibles) ou
faut-il aussi un bouton par planche ?
*Recommandation : les deux, mais le bouton projet d'abord — c'est la demande initiale de D76.*

**Q4 — Un niveau déjà analysé mais non travaillé.** D94 propose de le réanalyser sans rien demander,
puisque personne n'y a touché. Es-tu d'accord, ou veux-tu une confirmation à chaque fois ?
*Recommandation : réanalyser sans demander, puisque l'ancienne étude reste en version et reste
restaurable.*

**Q5 — Que faire en cas d'échec d'un niveau ?** Réessayer automatiquement une fois, ou laisser en
`echec` avec le message et un bouton « relancer » ?
*Recommandation : **pas de réessai automatique**. Un échec de la chaîne vient presque toujours d'une
donnée (rotation, échelle, plan illisible) qu'une répétition ne corrige pas ; elle ferait juste perdre du
temps d'agent.*

**Q6 — Où le relais travaille-t-il sur le disque ?** Il a besoin d'un dossier de sortie par projet et par
niveau (c'est là que vivent le journal, les bandes d'enveloppe et le catalogue).
*Recommandation : un dossier choisi à la première exécution et mémorisé, par défaut à côté du dépôt et
jamais dedans.*

**Q7 — Combien de niveaux à la fois ?** Un seul, en série, ou plusieurs en parallèle ?
*Recommandation : **un seul**. Le catalogue doit monter d'un niveau au suivant (D95), le parallélisme le
casserait, et les agents consomment déjà largement la machine.*

**Q8 — Faut-il voir le détail pendant que ça tourne ?** Le simple statut par niveau, ou aussi les étapes
de la chaîne (passe globale, bandes, lots, contrôle) ?
*Recommandation : le statut d'abord ; les étapes seulement si tu constates que l'attente est trop
opaque. La chaîne écrit déjà son journal sur le poste.*

## 5. Contrôles prévus

1. Service : éligibilité d'un niveau (sans étude, étude intacte, locaux validés, contours retouchés),
   classement des niveaux y compris un libellé illisible, absence de doublon dans la file.
2. Routes : mise en file avec écartés motivés, prise d'un travail, rendu avec import, refus d'un rendu
   sur un travail qui n'est pas en cours.
3. Relais : marche à blanc sur le banc local avec le vrai R+1, jeton expiré, sortie 3 de la chaîne.
4. Interface : bouton, file lisible, message d'attente du relais.
5. Tests thermiques ciblés, typage, construction.
