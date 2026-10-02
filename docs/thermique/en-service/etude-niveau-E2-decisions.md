---
read_policy: lire avant de coder le lot E2 de l'espace de travail thermique
status: valide
---

# Étude d'un niveau — décisions du lot E2

Date : 2026-09-22. Périmètre : importer l'étude d'une planche de niveau, afficher ses locaux sur le plan,
les lister avec les locaux chauffés en premier et ouvrir la fiche d'un local en lecture seule.

**État : Q1 à Q4 validées par l'utilisateur le 2026-09-22 ; lot E2 implémenté et vérifié localement,
sans push ni déploiement.**

## 1. Objectif repris et niveau de confiance

- Objectif compris : brancher les résultats déjà produits sur le poste par la chaîne raster/Claude Code dans
  l'espace de travail livré en E1, sans lancer d'agent depuis l'application.
- Niveau de confiance : **élevé** sur le périmètre fonctionnel et l'architecture générale ; les quatre choix du
  § 6 restent à confirmer avant développement.
- Hors lot : édition des contours et des rattachements, Remodéliser, Enregistrer et suivant, restauration d'une
  version, alimentation de la bibliothèque et hauteurs. Ils restent respectivement en E3, E4 et E5.

## 2. Existant vérifié le 2026-09-22

### Chaîne d'étude sur le poste

- `saas/backend/scripts/run_etude_niveau.py` enchaîne la passe globale, le recalage et la qualification des locaux,
  la préparation de l'enveloppe, les lots de lecture et la restitution. Il écrit aujourd'hui plusieurs fichiers,
  notamment `locaux.json`, `enveloppe.json`, `enveloppe.raw.json`, le manifeste, le catalogue, le contrôle et les
  fiches. Il **ne produit pas encore** `etude-<niveau>.json`.
- La restitution appelle déjà les fonctions classiques de rattachement aux pièces, de raccord des faces, de
  synthèse et de calcul des fiches. Aucun agent n'est nécessaire pour assembler le fichier d'étude final.
- Les coordonnées finales des objets de l'analyse sont dans le repère de la **feuille raster complète tournée**,
  normalisé de 0 à 1000. Elles ne sont pas encore des points PDF. Le manifeste de la visionneuse fournit déjà la
  transformation affine PDF → pixels calculée par pdfium, rotation comprise ; son inverse est donc la référence
  pour convertir les contours à l'import.
- Les pièces ont déjà un identifiant d'analyse stable dans le fichier (`piece-001`, `piece-002`...). En revanche,
  les fiches utilisent le nom affiché et numérotent les homonymes (`6.1.2 B.asst (1)` à `(6)`). Le fichier unique
  doit expliciter cette liaison et ne jamais faire dépendre l'application d'une recherche par libellé.

### Serveur et base

- Les modèles actuels sont `ThermiqueProject`, `ThermiqueDocument`, `ThermiqueSheet` et `ThermiqueComponent`.
  Aucune table d'étude ou de version n'existe après la migration 0082.
- Les routes thermiques vérifient déjà que le projet ou la planche appartient à l'utilisateur authentifié. Les
  comptes de bureau d'études passent par `get_authenticated_user` ; les nouvelles routes doivent garder ce modèle.
- Une planche connaît le document, la page, la rotation, l'échelle et ses dimensions PDF. Le document possède le
  SHA-256 du PDF importé : il peut servir à empêcher l'import d'une étude sur le mauvais plan.
- Le plan de référence est encore stocké uniquement dans `localStorage` par `WorkspacePage`.

### Interface E1

- `WorkspacePage` fournit déjà la navigation par niveau, le plan central, la colonne d'étapes et un panneau droit
  unique à onglets.
- `TileSheetViewer` accepte déjà `renderOverlay(toScreen)`. Le calque peut donc recevoir des polygones exprimés en
  points PDF sans modifier le moteur de tuiles.
- La colonne de gauche contient l'emplacement des locaux mais aucune donnée d'étude. Le type de panneau ne contient
  pas encore l'onglet `fiche`.

### Données réelles R+1 vérifiées

Sources utilisées pour le cadrage :

- analyse des locaux :
  `C:\Users\pa.borja\Documents\Codex\2026-09-18\tu\outputs\claude_agent_R1_locaux.json` ;
- restitution complète D46 :
  `C:\Users\pa.borja\Documents\Codex\2026-09-18\tu\outputs\complement_R1\` ;
- plan :
  `C:\Users\pa.borja\Documents\Po2\Thermique\PLAN EXEMPLE PROJET 1\PC04-FRONT-NIVEAU1.pdf`.

Constats : 24 locaux et 24 fiches, dont 17 chauffés, 5 circulations et 2 non chauffés ; 2 espaces écartés ;
89 tronçons ; 227 éléments bruts avant rattachement ; 32 composants de catalogue ; 16 raccords ; 4 demandes.
Le contrôle enregistré dans ce dossier compte 88,9 % de l'isolant visible. Ces données permettent de tester E2
sans lancer Claude ni aucun autre agent.

## 3. Décisions proposées

### D53 — Un contrat d'échange unique, portable et versionné

À la fin d'une étude terminée, `run_etude_niveau.py` écrit `etude-<niveau>.json`. L'assemblage est une fonction
Python pure, testable directement avec les résultats R+1 existants. Le fichier :

- porte `format: "thermique.etude_niveau"` et `format_version: 1` ;
- contient le niveau et une section `source` : nom du PDF, SHA-256, index de page, échelle, rotation de la
  visionneuse et dimensions de la feuille raster ;
- contient l'analyse utile, les locaux intégrés, les `locaux_ecartes`, le manifeste de l'enveloppe, le relevé
  **après** rattachement aux pièces et calcul des raccords, le catalogue, les fiches, la synthèse par pièce, le
  contrôle sans les cellules et les demandes ;
- contient une liste canonique `locaux`. Chaque entrée associe explicitement `id` (`piece-001`), `nom`, `nature`,
  `contour` en repère feuille 0..1000 et sa `fiche` ;
- exclut les chemins absolus du poste, les images intermédiaires, les cellules du contrôle et toute donnée
  d'authentification ;
- conserve `uses_pdf_vectors: false` comme invariant contrôlé à l'import.

Le fichier d'étude est la seule pièce à déposer dans l'application. Les fichiers de travail restent disponibles
sur le poste pour l'audit visuel, mais le serveur n'en dépend pas.

### D54 — Import strict, sans correction silencieuse

Route proposée : `POST /thermique/sheets/{sheet_id}/etude/importer`, fichier JSON multipart, puis
`GET /thermique/sheets/{sheet_id}/etude` pour la lecture.

L'import est transactionnel et refuse le fichier avant toute écriture si :

- le format ou sa version sont inconnus, un champ obligatoire manque, un identifiant local est dupliqué ou un
  contour a moins de trois points / sort du domaine 0..1000 ;
- une fiche ne correspond pas exactement à un local ;
- `uses_pdf_vectors` n'est pas explicitement faux ;
- le SHA-256 du PDF, l'index de page ou les proportions de la feuille ne correspondent pas à la planche choisie.

La conversion des contours se fait **une seule fois côté serveur** au moment de l'import : coordonnées normalisées
→ pixels du raster de la rotation déclarée par l'étude → inversion de la transformation pdfium → points PDF. Les
points PDF deviennent la géométrie de travail durable. Ensuite, la visionneuse les affiche correctement quelle que
soit sa rotation courante et E3 pourra les éditer sans perte.

Une limite de taille de 10 Mio est proposée pour le JSON. Le résultat R+1 est très inférieur à cette borne.

### D55 — Une étude courante par planche, chaque import créant une version

Migration 0083 proposée :

1. `thermique_projects.reference_sheet_id`, nullable, clé étrangère vers `thermique_sheets`, suppression de la
   planche → valeur nulle ;
2. `thermique_etudes` : `id`, `project_id`, `sheet_id` unique, `format_version`, `content_json`,
   `local_states_json`, auteur du dernier import, dates ;
3. `thermique_etude_versions` : `id`, `etude_id`, numéro de version, motif, `content_json`, `local_states_json`,
   auteur et date, avec unicité `(etude_id, version_number)`.

À l'import initial, tous les locaux prennent l'état `a_verifier` et une version 1 de motif `import_initial` est
créée. Un nouvel import remplacera l'étude courante uniquement après confirmation dans l'interface, tout en
conservant l'état précédent comme version. Les routes de liste/restauration des versions restent en E3.

Le contenu complet est stocké dans la version afin qu'une restauration future soit exacte. L'état des locaux est
séparé du contenu technique pour permettre E3 sans réécrire ou altérer le fichier source.

### D56 — Le plan de référence appartient au projet

`reference_sheet_id` est exposé dans `ProjectRead`/`ProjectDetail` et modifiable par le `PATCH` projet, après
contrôle que la planche appartient au projet. À la première ouverture après E2 :

- si le serveur a déjà une référence, elle prévaut ;
- sinon, l'ancien choix valide de `localStorage` est envoyé une fois au serveur puis supprimé localement ;
- sans ancien choix, la règle E1 reste appliquée : RDC/niveau 0, sinon premier plan. La référence est enregistrée
  lorsqu'elle est explicitement choisie par le thermicien.

### D57 — Locaux sur le plan et sélection synchronisée

- Tous les locaux de l'étude sont affichés par `renderOverlay`, avec un fond translucide : chauffé, circulation et
  non chauffé ont trois couleurs distinctes et accessibles ; le local sélectionné reçoit un contour renforcé.
- Cliquer un polygone ou une ligne de la liste sélectionne le même local, écrit `local=<piece-id>&panneau=fiche`
  dans l'adresse et ouvre sa fiche. Une adresse partagée rouvre donc la même vue.
- La liste conserve l'ordre du fichier dans chaque groupe et trie les groupes ainsi : chauffés, circulations,
  non chauffés. Elle affiche le nom, la surface, l'état et le nombre d'alertes.
- Un local sélectionné reste sélectionné quand on ouvre un autre onglet du panneau droit ; changer de planche
  efface la sélection si ce local n'appartient pas à la nouvelle étude.

### D58 — Fiche strictement en lecture seule pour E2

Un onglet `Fiche` est ajouté au panneau droit. Il affiche : identité, nature, surface et périmètre ; côtés
(adjacence, voisin, longueur, épaisseur, orientation, déperditif) ; parois et baies rattachées ; parois sur local
non chauffé ou vide ; liaisons/ponts ; éléments à compléter ; alertes et demandes concernant le local.

Aucun champ, poignée de sommet, bouton Remodéliser ou Enregistrer n'est présent en E2. Les étapes de gauche sont
allumées à partir du contenu réellement importé : locaux présents, enveloppe présente, puis « pièce par pièce :
0/N validés ». Les hauteurs restent « à venir » et aucune hauteur par défaut n'est créée.

## 4. Fichiers probablement concernés après validation

- Production du fichier : `saas/backend/scripts/run_etude_niveau.py` et un petit module d'assemblage/validation
  réutilisable dans `saas/backend/app/services/`.
- Base/API : migration `0083`, `app/models/thermique.py`, `app/models/__init__.py`, `app/schemas/thermique.py`,
  `app/services/thermique.py`, un service d'étude dédié et `app/api/routes/thermique.py`.
- Interface : `src/thermique/api.ts`, `workspace/WorkspacePage.tsx`, `workspace/SheetPanel.tsx`, nouveaux composants
  de liste/fiche dans `workspace/`, et `thermique.css`.
- Tests : tests serveur du contrat, de l'import, des droits et de la migration isolée ; tests frontend du tri, de
  la sélection, de la transformation et de la fiche.

## 5. Vérification prévue après validation

1. Assembler `etude-R1.json` à partir des résultats réels, sans lancer les agents.
2. Tester la migration 0083 isolément en montée et en descente, puisque la chaîne historique complète n'est pas
   compatible SQLite depuis 0007.
3. Importer le R+1 sur sa vraie planche et vérifier les 24 contours visuellement, y compris les homonymes.
4. Vérifier la liste : 17 chauffés, puis 5 circulations, puis 2 non chauffés.
5. Ouvrir plusieurs fiches et contrôler leur concordance avec les données JSON.
6. Lancer uniquement les commandes ciblées de la passation :

```powershell
# saas/backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:DATABASE_URL='sqlite:///./test.db'
python -m pytest tests -k thermique -p no:cacheprovider

# saas/frontend
npx tsc -b
npx vitest run src/thermique
npm run build
```

## 6. Questions à valider avant le code

**Q1 — Réimport.** Confirmez-vous qu'un second import sur la même planche doit **remplacer l'étude courante après
confirmation**, tout en conservant automatiquement la version précédente ? **Recommandation : oui**, pour pouvoir
reprendre une étude améliorée sans perdre l'ancienne.

**Q2 — Sélection.** Confirmez-vous qu'un clic sur un local, dans le plan ou dans la liste, doit ouvrir directement
l'onglet Fiche et inscrire le local dans l'adresse ? **Recommandation : oui**, c'est le comportement le plus direct
et il rend la vue partageable.

**Q3 — Couleurs.** Pour E2, confirmez-vous la couleur de remplissage par nature du local (chauffé / circulation /
non chauffé), avec le statut affiché séparément par une pastille dans la liste ? **Recommandation : oui** ; en E3,
le contour ou la pastille pourra porter l'état de validation sans perdre la lecture thermique du plan.

**Q4 — Contrôle du plan.** Confirmez-vous le refus strict d'un fichier d'étude si le SHA-256 du PDF ou la page ne
correspond pas à la planche, sans bouton « importer quand même » ? **Recommandation : oui**, car un décalage discret
serait plus dangereux qu'un import refusé. Une étude d'un ancien PDF devra être régénérée ou importée sur la bonne
planche.

## 7. Réalisation et vérification du 2026-09-22

- `run_etude_niveau.py` produit désormais `etude-<niveau>.json` sans nouvel appel d'agent. Le contrat portable,
  sa validation stricte et sa conversion en points PDF vivent dans `app/services/thermique_etudes.py`.
- La migration 0083 crée les deux tables d'étude/version et stocke le plan de référence sur le projet. Les routes
  d'import et de lecture contrôlent l'appartenance, le PDF, la page, la rotation, les proportions et la taille.
- L'espace de travail affiche les polygones sélectionnables, trie les locaux chauffés en premier et ouvre leur fiche
  en lecture seule. Le local sélectionné est conservé dans l'adresse.
- Le fichier réel `outputs/complement_R1/etude-R1.json` a été assemblé : 640 600 octets, 24 locaux (17 chauffés,
  5 circulations, 2 non chauffés), 230 éléments après découpage/rattachement et 32 composants. Il ne contient ni
  cellules d'image ni chemin absolu du poste.
- La reprojection réelle sur le PDF R+1 tourné à 270° a validé les 24 contours ; l'erreur maximale du trajet
  repère normalisé → points PDF → raster est de 0,0003 sur 1000.
- Vérifications passées : 123 tests backend thermiques, 11 tests frontend thermiques, `tsc -b`, build Vite et
  migration 0083 isolée en montée/descente. Le seul avertissement du build concerne la taille d'un chunk global
  déjà existant ; les deux avertissements pytest viennent de `python-jose` et de `datetime.utcnow()`.
