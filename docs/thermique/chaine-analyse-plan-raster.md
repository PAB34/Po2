---
read_policy: lire en entier avant toute nouvelle étude sur plans raster ; source de vérité de la chaîne
---

# Chaîne d'analyse thermique d'un plan raster — mode d'emploi et plan d'automatisation

Mise à jour : 2026-09-22. Cas de référence : R+1 de la médiathèque de Frontignan
(`Thermique/PLAN EXEMPLE PROJET/PC04-FRONT-NIVEAU1.pdf`, 1/100, 300 dpi, rotation antihoraire 90°).
Décisions détaillées : [analyse-ia-visuelle-r1-decisions.md](analyse-ia-visuelle-r1-decisions.md) et
[parcours-enveloppe-decisions.md](parcours-enveloppe-decisions.md) (D1 à D23).

## 1. Principe

Le plan est lu **comme une image** (pixels seuls, aucun vecteur PDF). Un agent Claude joue le rôle du
thermicien qui regarde le plan ; des algorithmes classiques préparent ce qu'il regarde, vérifient ce qu'il dit
et font les mesures. Rien n'est remplacé silencieusement par un autre modèle ; les incertitudes sont signalées
« à vérifier » ou « à confirmer ».

## 1 bis. Les agents IA, expliqués simplement

**Ce qu'est un agent ici.** Un agent est Claude (le même modèle que Claude Code, Opus) à qui l'on donne un rôle
écrit, des outils limités et une consigne précise. Son rôle est décrit dans un fichier du dépôt
(`.claude/agents/<nom>.md`) : qui il est, ce qu'il doit relever, comment, et ce qu'il ne doit pas faire.
Il ne garde aucune mémoire d'un appel à l'autre : tout ce qu'il doit savoir est dans la consigne (images à lire,
repères, catalogue déjà appris). Sa seule permission est **lire des images** (outil Read) : il ne peut ni modifier
un fichier, ni lancer une commande, ni aller sur Internet. Il répond par un JSON dont la forme est imposée (un
« schéma »), que les algorithmes vérifient, nettoient et mesurent ensuite.

| | `thermicien-plan` | `thermicien-enveloppe` |
|---|---|---|
| Fichier de rôle | `.claude/agents/thermicien-plan.md` | `.claude/agents/thermicien-enveloppe.md` |
| Étape | 2 (passe globale) | 5 (parcours de l'enveloppe) |
| Il lit | une vue d'ensemble du plan et 6 tuiles de détail | le plan guide, la planche des vignettes du catalogue, puis 3 planches de 6 bandes redressées et graduées par lot |
| Il rend | la liste des objets : pièces (nom lu, contour au nu intérieur), murs, refends, cloisons, isolants, menuiseries, terrasses, balcons, poteaux, garde-corps, avec coordonnées, confiance et indice visuel | pour chaque tronçon, des intervalles sans trou : paroi (couches, nus extérieur et intérieur, au début et à la fin), menuiserie (type, cadre), poteau, angle, about ; plus les fiches nouvelles du catalogue |
| Il ne fait pas | les mesures fines, la mise au propre des formes | le guide, les bandes, les longueurs intérieures, le découpage par pièce, le contrôle |
| Ce qui le cadre | ignorer cotes, textes, mobilier ; ne rien inventer (« indéterminé » + à vérifier) | repères des bandes, nommage stable des couches, réutiliser un composant connu, justifier un nouveau |
| Durée | quelques minutes | quelques minutes par lot (4 lots sur le R+1) |

**Comment il « apprend ».** Le parcours de l'enveloppe se fait en lots successifs. Après chaque lot, les
composants rencontrés sont ajoutés au catalogue (`catalogue.json`) avec une image de la première fois où ils ont
été vus et leur règle de reconnaissance. Le lot suivant reçoit ce catalogue : l'agent reconnaît les composants
déjà vus et garde leur identifiant. Le catalogue validé d'un niveau peut servir de départ au niveau suivant
(`--catalogue`). L'agent lui-même n'est pas modifié : c'est le catalogue, transmis dans la consigne, qui porte
l'apprentissage.

**Qui lance les agents : deux modes, sans clé d'API.**

- **Mode session (recommandé, par défaut)** : l'utilisateur travaille dans Claude Code (application de bureau)
  et demande l'étude d'un niveau. Claude Code suit la compétence `.claude/skills/etude-thermique/SKILL.md` :
  il lance la commande `run_etude_niveau.py`, qui s'arrête quand un agent doit intervenir ; Claude Code lance
  alors l'agent dans la session, enregistre sa réponse, relance la commande, et ainsi de suite jusqu'au bout.
  Aucune connexion supplémentaire n'est nécessaire.
- **Mode autonome (`--mode cli`)** : la commande appelle elle-même Claude Code en ligne de commande
  (`claude -p --agent …`), avec l'abonnement Claude de l'utilisateur (pas de clé d'API). Il faut pour cela que
  la commande `claude` du poste soit connectée (`claude auth login --claudeai`, qui est la connexion par
  abonnement). Utile pour lancer une étude sans session ouverte.

## 2. Les étapes, dans l'ordre

| # | Étape | Qui | Ce qui est produit | Code |
|---|---|---|---|---|
| 1 | Rendu du plan, recadrage, rotation | algorithme | images de travail | `run_thermicien_claude.py` |
| 2 | Passe globale : pièces, murs, menuiseries, terrasses… | agent `thermicien-plan` | `claude_agent_R1.json` + projection | `thermique_claude_agent.py`, `thermique_vision*.py` |
| 3 | Mise au propre des formes (angles droits, directions dominantes, enclaves) | algorithme | géométrie éditable | `thermique_vision_geometrie.py` |
| 3 bis | Locaux : contours recalés sur les murs, espaces libres repérés ; l'agent donne la nature de chaque pièce (chauffé, circulation, non chauffé) et nomme ou écarte les espaces libres (vide, patio, mur) | algorithme + agent `thermicien-plan` (consigne courte) | `recalage.json`, `locaux.json` | `thermique_locaux.py` ([locaux-decisions.md](locaux-decisions.md)) |
| 4 | Guide de l'enveloppe : face extérieure réelle (remplissage de l'extérieur), tronçons ≤ 5 m, bandes redressées graduées | algorithme | `enveloppe-manifeste.json`, `enveloppe-XX.png`, `enveloppe-guide.jpg` | `thermique_parcours_enveloppe.py` (`preparer`) |
| 5 | Parcours de l'enveloppe par lots de 3 planches, avec **catalogue appris** | agent `thermicien-enveloppe` | `reponse-lot-K.json`, `catalogue.json`, `catalogue-avant-lot-K.png` | `run_enveloppe_claude.py --lot/--integrer-lot` |
| 6 | Résolution : couches de la fiche, doublage BA13 présumé, épaisseurs commerciales | algorithme | relevé résolu | `resoudre`, `epaisseur_commerciale` |
| 7 | Découpage pièce par pièce, raccord des angles, ponts thermiques par pièce | algorithme | section « Par pièce », plan des pièces | `thermique_enveloppe_pieces.py` |
| 7 bis | Fiche par local : tour de chaque pièce, ce qu'il y a derrière chaque côté (extérieur, local non chauffé, vide, circulation, local chauffé), épaisseur du mur, côtés déperditifs, enveloppe rattachée, alertes | algorithme | `.locaux.md`, `.adjacences.png`, `fiches_locaux` | `thermique_fiches_locaux.py` ([fiches-locaux-decisions.md](fiches-locaux-decisions.md)) |
| 8 | Reprojection sur la feuille : un objet par couche (voiles, isolant, doublage), baies, poteaux | algorithme | `enveloppe_R1.json` (importable dans `/analyse`) | `reprojeter`, `fusionner` |
| 9 | Contrôle par l'image : alvéoles d'isolant et béton gris comparés au relevé | algorithme | `controle.json`, `controle-image.png`, section « Contrôle par l'image » | `thermique_controle_image.py` |
| 10 | Restitution : bibliothèque, planches de relevé, catalogue, plan des pièces, demandes | algorithme | `.bibliotheque.md`, `releve-XX.png`, `catalogue.png`, `.pieces.png` | `run_enveloppe_claude.py` |

## 3. Commandes (depuis `saas/backend`)

**Une seule commande par niveau** (reprend là où elle s'est arrêtée ; journal dans `<sorties>/<niveau>/journal.json`,
tâche en cours ou reste à faire dans `<sorties>/<niveau>/A-FAIRE.md`) :

```bash
python scripts/run_etude_niveau.py "<plan.pdf>" --niveau R1 --sorties "<dossier de l'étude>" --rotation 90 [--catalogue <catalogue validé.json>] [--mode cli]
```

Codes de sortie : 0 terminé, 3 en attente d'un agent (voir `A-FAIRE.md`), 1 erreur. Validé le 2026-09-22 sur le
R+1 en mode session (guide identique : 72 tronçons, 171,31 m ; mêmes résultats que la chaîne manuelle).

Commandes détaillées, étape par étape (utiles pour reprendre une seule étape) :

```bash
# 2. passe globale (agent) — rotation à donner à l'agent = (360 - rotation visionneuse) % 360
python scripts/run_thermicien_claude.py "<plan.pdf>" --output <sorties>/claude_agent_R1.json --work-dir <sorties>/agent_R1 --rotation 90
# 4. préparation du parcours de l'enveloppe
python scripts/run_enveloppe_claude.py "<plan.pdf>" --analysis <sorties>/claude_agent_R1.json --work-dir <sorties>/enveloppe_R1 --output <sorties>/enveloppe_R1.json --prepare-only
# 5. parcours complet, lots enchaînés automatiquement (quand la commande claude est connectée)
python scripts/run_enveloppe_claude.py "<plan.pdf>" --analysis <sorties>/claude_agent_R1.json --work-dir <sorties>/enveloppe_R1 --output <sorties>/enveloppe_R1.json
# 5 bis. mode manuel lot par lot (agent lancé ailleurs) : consigne, puis intégration de la réponse
python scripts/run_enveloppe_claude.py ... --lot 1
python scripts/run_enveloppe_claude.py ... --integrer-lot 1 reponse-lot-1.json
# 6 à 10. restitution à partir des réponses déjà obtenues
python scripts/run_enveloppe_claude.py ... --from-raw reponse-lot-1.json reponse-lot-2.json reponse-lot-3.json reponse-lot-4.json
```

Condition de l'automatisme complet : la commande `claude` locale doit être connectée
(`claude auth login --claudeai`, à faire par l'utilisateur). Tant qu'elle répond 401, l'agent est lancé depuis
une session Claude Code et ses réponses sont recopiées dans `reponse-lot-K.json` (mode 5 bis).

## 4. Les données collectées et à quoi elles servent

| Donnée | Fichier | Rôle | Réutilisable |
|---|---|---|---|
| Pièces et objets de la passe globale | `claude_agent_R1.json` | guide de l'enveloppe, rattachement aux pièces | par niveau |
| Tronçons, repères des bandes | `enveloppe-manifeste.json` | convertit une lecture (abscisse, profondeur) en coordonnées du plan | par niveau |
| Relevé linéaire par intervalles | `reponse-lot-K.json`, `enveloppe_R1.raw.json` | composition, nus, baies, liaisons | par niveau |
| **Catalogue appris** (23 composants sur le R+1) | `catalogue.json`, `catalogue.png` | bibliothèque de composants : fiche, règle de reconnaissance, décision | **oui : autres niveaux, puis autres projets** |
| Objets éditables (un par couche) | `enveloppe_R1.json` | correction dans `/analyse` | par niveau |
| Bilan par composant, familles, parois, baies, liaisons | `enveloppe_R1.bibliotheque.md` | métré | par niveau |
| Par pièce : façade, parois, baies, poteaux, ψ, liaison plancher | idem, section « Par pièce » | métré pièce par pièce | par niveau |
| Raccords d'angles et raccords refusés | idem | longueurs intérieures justes, relevés à revoir | par niveau |
| Demandes à formuler | idem, section « Demandes » | apport de l'étude (découpage des zones…) | par projet |
| Contrôle par l'image | `controle-isolant.png` | taux de confirmation par composant | par niveau |

## 5. Règles métier appliquées (validées par l'utilisateur)

- Métré en **dimensions intérieures** (convention française) : l'isolant d'un angle n'entre pas dans les
  surfaces, il est porté par le pont thermique d'angle.
- Parois : voile extérieur, isolant, voile intérieur (double peau), **doublage BA13 présumé** si non dessiné.
- Épaisseurs ramenées aux épaisseurs commerciales, l'épaisseur lue restant affichée.
- Découpage par pièce : coupe au droit des cloisons et refends ; baie à cheval coupée ; angle à la pièce qui le
  contient ; refend moitié-moitié ; liaison plancher sur toute la façade de la pièce.
- Angles : faces intérieures prolongées jusqu'à leur rencontre (mur contre mur, ou angle tout vitré) ; un mur
  contre une baie s'arrête au tableau.
- Espace regroupant plusieurs locaux : pas de découpage automatique, demande de découpage précis.
- Tout local donnant sur l'extérieur ou un local non chauffé est déperditif et source d'apports.

## 6. Ponts thermiques et normes (NF EN ISO 14683 et 10211, juillet 2017)

Lecture faite le 2026-09-22 (copies fournies par l'utilisateur, non reproduites ici) :

- **ISO 14683** donne des valeurs par défaut de ψ pour des jonctions courantes (toits, balcons, planchers,
  angles, refends, baies, poteaux) selon la position de l'isolant, **pour trois systèmes de dimensions**
  (extérieures, intérieures globales, intérieures). Les angles de murs y sont **à 90° uniquement**. En
  dimensions intérieures, un angle sortant a un ψ positif et un angle rentrant un ψ négatif : c'est l'effet du
  système de dimensions, pas un défaut de la paroi.
- **ISO 10211** définit le calcul numérique : ψ = L2D − Σ Uj·lj, les longueurs lj étant prises dans le système
  de dimensions du bâtiment. Il n'y a **pas de seuil d'angle** : toute jonction hors catalogue se calcule.
  Règle utile à l'automatisation : un modèle 2D s'arrête à au moins **dmin = max(1 m ; 3 × épaisseur de
  l'élément latéral)** de la jonction, et deux ponts thermiques plus proches que dmin se calculent **dans un même
  modèle**.
- Conséquence pour l'outil : pour un angle d'écart θ entre deux murs d'épaisseur e et de coefficient U,
  l'écart entre dimensions extérieures et intérieures vaut environ 2·e·tan(θ/2), d'où ψi ≈ ψe + U·2·e·tan(θ/2).
  C'est une estimation continue, sans seuil, de la part géométrique de l'angle. Les pointes des dents de scie
  (jonctions à moins de dmin l'une de l'autre, baie contre mur en biais) et l'angle sud-est (voile non isolé
  contre mur-rideau) relèvent d'un calcul 2D particulier, que l'utilisateur fait avec ubakus.

## 7. Plan d'automatisation (proposé le 2026-09-22)

Objectif : pour la prochaine étude, une seule commande par niveau, qui enchaîne tout et s'arrête seulement sur
les décisions du thermicien.

| Lot | Contenu | État |
|---|---|---|
| A1 | Ce document, tenu à jour à chaque étape | fait |
| A2 | Contrôle par l'image intégré au moteur (`thermique_controle_image.py`) avec taux « confirmé par l'image » par composant et planche d'écarts ; tests | fait (2026-09-22) |
| A3 | Commande unique `run_etude_niveau.py` : passe globale → préparation → lots de l'enveloppe → contrôle → pièces → restitution ; reprise là où elle s'est arrêtée ; journal ; `A-FAIRE.md` ; compétence `etude-thermique` pour le mode session | fait (2026-09-22) |
| A4 | Catalogue réutilisable : départ du catalogue validé d'un autre niveau ou projet (`--catalogue`, déjà branché), décisions du thermicien enregistrées | en partie |
| A5 | Ponts thermiques : chaque changement de direction devient une liaison avec son angle et sa part géométrique ; jonctions hors catalogue regroupées selon dmin ; fiche par pont thermique particulier (image, compositions, angle, arrêt de l'isolant) prête pour ubakus ; valeur ψ saisie stockée dans le catalogue | à faire |
| A6 | Rapport de synthèse d'un niveau (une page : chiffres, images, demandes, points à vérifier) | à faire |
| A7 | Passe globale : circulations identifiées comme pièces (règle D23) | à faire, relance de l'agent |
| — | Coupes : zonage thermique, hauteurs, planchers, toitures, surfaces | prochain chantier |

Points qui resteront manuels : connexion de la commande `claude` ; validation du catalogue (décisions à
confirmer) ; ψ des ponts thermiques particuliers (calcul 2D) ; demandes à l'architecte.

## 8. Limites connues (R+1)

- Guide qui suit le claustra au sud-ouest (T39–T45, T56–T57) et boucle parasite T70–T71.
- Guide qui coupe au plus court certaines dents de scie (T34, T67, T68) : mur hors de la bande lue.
- Espaces ouverts regroupés (Pôle multimédia) ; circulations non identifiées comme pièces.
- Largeur des baies de retour des dents de scie à lire en profondeur.
- Surfaces en attente des hauteurs (coupes).
