# Passation à Codex — après le lot F2 (2026-09-25)

> Écrit par Claude Code à la fin de son quota hebdomadaire. Tout ce qu'il faut pour reprendre sans
> redécouvrir le terrain. À lire en entier **avant** de toucher au code.

## 1. Où en est le dépôt, exactement

| | |
| --- | --- |
| Worktree | `C:\Users\pa.borja\Documents\Po2-thermique` |
| Branche locale | `feat/thermique-socle-raster` |
| **En production** | `origin/main` = **`1813701b`** (thermique.patrimoineaucarre.com) |
| **Commits faits et NON POUSSÉS** | `090976f2` (étiquette lisible en thème sombre + cadrage F2) et `7ca754c2` (lot F2) |

Le déploiement se fait en poussant sur `main` (`git push origin HEAD:main` déclenche `deploy.yml`).
**L'utilisateur n'a pas encore autorisé ce push.** Ne pas le faire sans son « pousse » explicite.

⚠️ `origin/feat/thermique-socle-raster` est resté à `365a9055` : il est périmé, ne pas s'y fier.

## 2. Règles permanentes de l'utilisateur (non négociables)

- **Ne rien pousser sur GitHub sans son autorisation explicite** — un push sur `main` déploie en prod.
- **Toujours répondre en français**, et **terminer chaque tâche par « ce que j'ai fait, en clair »**,
  en langage non technique (pas une liste de commits et de fichiers).
- **Un fichier de décisions par sujet, écrit AVANT de coder** : existant vérifié + décisions datées +
  questions numérotées, validées par l'utilisateur. Règle « fil du dev », `docs/05-Conventions-IA.md` §2.
- **Ne jamais afficher ni saisir un mot de passe, une clé ou un jeton.** Conséquence directe : on ne peut
  pas se connecter au banc, donc **on ne fait jamais la recette à la souris soi-même** — c'est l'utilisateur
  qui teste. Le dire franchement au lieu de laisser croire qu'on a vérifié.
- **Dépôt partagé avec une autre IA** : `git status` avant toute chose, `git commit -- <pathspec>` explicite,
  **jamais de force-push**.
- Ne pas remplacer silencieusement Claude par un autre modèle, ne pas revenir à une détection vectorielle.
- **Ne pas modifier `.claude/agents/thermicien-plan.md`.**
- Préserver les changements en cours qui ne concernent pas la tâche.

## 3. Ce que le projet est

Outil de métré thermique pour thermiciens en bureau d'études, **projet à part** (aucun lien avec Po2).
Les plans sont lus **comme des images** par des agents Claude Code tournant **sur le poste de
l'utilisateur** (abonnement, pas de clé API). Le serveur n'exécute que des algorithmes classiques.
Le thermicien valide **pièce par pièce**, et c'est lui qui a le dernier mot sur tout.

### Le contrat de données, à connaître par cœur

`thermique.etude_niveau` v3. Sur le R+1 de référence :

- `enveloppe.releve_brut.elements` (**227**) = **la source de vérité**. Une correction s'écrit **ici**.
- `enveloppe.objets` (**289 formes**) et `enveloppe.liaisons` (**77 ponts**) sont **régénérés à chaque
  recalcul**. **D99 : ne jamais corriger le dessin, toujours le relevé.**
- Identité d'un élément : le triplet **`(troncon, debut_m, fin_m)`**, unique sur les 227, porté aussi par
  `objets[].source_parcours` — c'est ce qui permet à un clic de remonter au relevé.
- **Un pont thermique EST un élément du relevé** : les 77 liaisons correspondent 1 pour 1 aux 77 éléments
  de type `angle_sortant` (43), `angle_rentrant` (21), `about_refend` (13). Ces types **n'ont aucune
  forme dessinée** : ils n'existent sur le plan que comme pastilles.
- Les **murs sont EN DEHORS du contour** du local (le contour est le nu intérieur). D'où l'obligation de
  chercher un élément dans **tout le niveau** au clic, pas dans le seul local ouvert.

### Repères chiffrés du R+1 (à vérifier après toute modification du calcul)

| Mesure | Valeur attendue |
| --- | --- |
| Éléments relevés | 227 (150 parois/menuiseries + 77 ponts) |
| Côtés cotés | **222** |
| Linéaire déperditif | **170,12 m** |
| Formes dessinées | 289 |
| Liaisons | 77 |
| Recalcul complet | ~3,2 s |

## 4. Ce que F2 a livré (commit `7ca754c2`)

Décisions : **`docs/thermique/parcours-F2-decisions.md`** (D106 à D114, huit questions tranchées).

**Six étapes** qui pilotent : planche → analyse → locaux → parois et menuiseries → **ponts thermiques** →
hauteurs. Chaque étape annonce son reste à faire, ouvre son panneau et règle les calques du plan.
Toucher une case d'affichage rend la main au thermicien jusqu'au changement d'étape.

| Fichier | Rôle |
| --- | --- |
| `workspace/parcours.ts` | **Le modèle, fonction pure** : `parcours()`, `avancement()`, `etapeCourante()`, `pontsDuNiveau()`, `paroisDuNiveau()`. Testable sans écran. |
| `workspace/PontsPanel.tsx` | L'étape des ponts : passe continue sur les 77, deux gestes, trois motifs pré-écrits. |
| `workspace/WorkspacePage.tsx` | Colonne d'étapes, calques pilotés, garde-fou de départ (D111), cadrage du plan. |
| `workspace/StudyMetrics.tsx` | `grouperPonts`, état « écartée », étiquette AS/AR/RF sur fond blanc. |
| `components/TileSheetViewer.tsx` | Nouvelle entrée `focus={{point, cle, zoom}}` : recentrage demandé de l'extérieur. |
| `services/thermique_calage_contours.py` | **D113** : `liaisons_localisees` reçoit le relevé complet et reporte `exclu` / `a_verifier` / `confirme`. |
| `services/thermique_etude_edition.py` | Passe `releve_brut` (et non `brut`) à `liaisons_localisees`. |

**D114, à ne pas défaire** : deux régimes de validation. Les 150 parois se fient à l'agent quand il n'a
pas douté (64 restent à vérifier) ; les **77 ponts passent tous** devant le thermicien, même ceux lus
avec assurance. **L'utilisateur a confirmé ce choix explicitement le 2026-09-25 (« Ok 77 »).**

**Vérifié sur le vrai R+1** : 222 côtés et 170,12 m déperditifs **inchangés**. Écarter un angle sortant
fait passer le décompte de 43 à 42, **et rien d'autre ne change** dans le métré (comparaison par
empreinte des fiches, hors décompte des ponts).

**Jamais exercé à la souris** : 82 tests front et 23 tests d'édition, mais aucune recette réelle.

## 5. ▶️ La tâche suivante : annuler la dernière action

Demande de l'utilisateur, 2026-09-25, mot pour mot :

> « Autre sujet avoir la possibilité d'annuler la dernière action via ctrl z et deux boutons
> précédent/suivant »

**Lever l'ambiguïté d'abord** (une question, pas trois) : « deux boutons précédent/suivant » se lit de
deux façons. Soit **Annuler / Rétablir** (un historique), soit la navigation dans la passe des ponts —
mais celle-ci existe déjà (« ← Précédent » et « Passer sans juger → » dans `PontsPanel`). La lecture
retenue par Claude est donc **l'historique**, à confirmer d'un mot avant de coder.

### Pourquoi c'est faisable proprement

`appliquerEnLocal(content, operation)` (`workspace/elementsLocal.ts`) est une **fonction pure**, et
`useStudyElements` conserve déjà la **liste ordonnée des opérations**. L'annulation n'a donc pas besoin
d'inverse : il suffit de **rejouer** la liste privée de sa dernière entrée, à partir de `study.content`.

### Conception proposée, dans `workspace/useStudyElements.ts`

```ts
const [annulees, setAnnulees] = useState<StudyOperation[]>([]);

const rejouer = (liste: StudyOperation[]) =>
  liste.length ? liste.reduce((etat, op) => appliquerEnLocal(etat, op), study!.content) : null;

const annuler = () => { /* pop operations -> push annulees -> setLocal(rejouer(restantes)) */ };
const retablir = () => { /* pop annulees -> push operations -> setLocal(rejouer(suivantes)) */ };
```

`apply()` doit **vider `annulees`** : un nouveau geste après une annulation coupe la branche rétablie.
`reset()` vide les deux piles.

### Les cinq pièges, tous déjà payés une fois dans ce projet

1. **Le raccourci clavier doit être posé en phase de CAPTURE.** `window.addEventListener("keydown", fn,
   true)`. En phase de bulle, un vrai événement de confiance n'arrive jamais — c'est exactement le bug
   D91 (Échap qui ne fermait pas le menu contextuel), qui a coûté une demi-session.
2. **Ne pas voler le Ctrl+Z d'un champ de saisie.** Si `event.target` est un `input`, un `textarea` ou un
   élément `contenteditable`, laisser le navigateur faire. Sinon la case « Autre raison » de l'écart d'un
   pont devient inutilisable.
3. **Après un `recompute()` serveur, `local` contient la réponse du serveur**, pas un pliage local.
   Annuler repart du pliage local : le plan revient donc à l'état « corrections en attente » et il faut
   recalculer à nouveau. **Le dire dans le bandeau**, ne pas laisser deviner.
4. **Ne pas annuler à travers un enregistrement.** Une fois `save()` passé, les opérations sont parties au
   serveur et les piles sont vidées : Ctrl+Z ne doit rien faire, et doit le dire.
5. **Portée** : s'en tenir d'abord aux gestes sur les éléments (`useStudyElements`). L'édition de contour
   (`useStudyEdition`) a son propre brouillon ; Ctrl+Z pendant un tracé devrait défaire le dernier point,
   mais c'est un second sujet — l'annoncer, ne pas le bâcler.

### Où poser les boutons

Dans le bloc `th-element-enregistrer` de `WorkspacePage.tsx`, à côté de « Enregistrer les corrections »,
« Recalculer le plan » et « Tout annuler ». Libellés explicites : **« Annuler (Ctrl+Z) »** et
**« Rétablir »**, désactivés quand leur pile est vide.

### Tests à écrire

Dans `workspace/elementsLocal.test.ts` ou un nouveau fichier : annuler un écart rend l'élément au calcul ;
annuler puis rétablir revient au même contenu ; un nouveau geste après une annulation vide la pile de
rétablissement ; annuler sur une pile vide ne casse rien.

## 5bis. ⚠️ Sept sujets ouverts relevés par l'utilisateur le 2026-09-25

**`docs/thermique/reprise-sujets-ouverts.md`** — à lire aussi. Supprimer et ajouter des pièces ; cliquer
un côté dans la fiche pour le voir sur le plan ; la règle des 50 % sur les 64 angles (elle n'existe que
pour les 13 abouts de refend) ; comment une étape est déclarée terminée (répondu) ; les terrasses comme
pièces extérieures ; les contours parasites de portes et d'aires PMR ; le tracé trop découpé.
Un ordre de travail y est proposé.

## 6. La recette que l'utilisateur doit encore faire sur F2

Elle n'a **pas** eu lieu (rien n'est déployé). Trois points, et il a déjà donné son avis sur le principe :

1. la colonne de gauche change bien le panneau **et** les calques ;
2. la passe sur les 77 ponts est tenable — **il a confirmé vouloir les 77** ;
3. un pont écarté se voit sur le plan **et** revient dans le calcul — **il a confirmé vouloir les deux**.

## 7. Le reste du chantier, par ordre d'intérêt

- **Le relais local n'a jamais tourné de bout en bout.** `saas/backend/scripts/relais_thermique.py` :
  ses fonctions sont testées, l'enchaînement complet sur un vrai plan reste à éprouver.
- **Reporté par D104** : ajouter un élément ou un pont absent du relevé ; déplacer les bornes d'un élément
  sur son tronçon ; `couches`, `menuiserie_type`, `cadre_cm`.
- **Question ouverte, jamais tranchée** : faut-il fusionner des ponts dans le relevé ? **Non sans l'accord
  de l'utilisateur** — cela changerait le métré. Le choix actuel est qu'il les écarte un par un, ce qui est
  traçable et réversible.
- **Si, après la passe, le thermicien juge qu'il y a trop d'angles** : le coupable n'est pas l'affichage
  mais le **tracé de l'enveloppe** (89 tronçons, 67 changements de cap de plus de 20°, pour 64 angles).
  C'est l'agent `thermicien-enveloppe` qu'il faudrait reprendre. Chantier distinct, plus profond.
- Étape « hauteurs » : attend la lecture des coupes.

## 8. Commandes qui marchent sur ce poste (Windows, zéro install)

```bash
# Front — dans saas/frontend
npx tsc -b                      # typecheck seul
npx vitest run src/thermique    # 82 tests
npm run build
```

```powershell
# Back — dans saas/backend. `pytest.exe` bloque en collecte : passer par le lanceur Python.
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:DATABASE_URL='sqlite:///./test.db'
python -m pytest tests/test_thermique_etude_edition.py -p no:cacheprovider -q
```

**Ne jamais lancer la suite complète** : uniquement les tests ciblés.

## 9. Deux erreurs à ne pas refaire

- **Ne jamais vérifier un déploiement sur une empreinte de bundle calculée en local** : la CI en produit
  une différente, et la sonde tourne dans le vide pendant que le déploiement a réussi depuis longtemps.
  Interroger le **contenu servi** (chercher une chaîne nouvelle dans le bundle en ligne).
- **Vérifier qu'un fichier de test n'existe pas avant de l'écrire.** `tests/test_thermique_elements.py`
  (bibliothèque B2b-1) a été écrasé une fois par mégarde et restauré au `git checkout --`.
  Les tests du relevé vivent dans `tests/test_thermique_elements_releve.py`.
