# Lot F2 — le parcours du thermicien, étape par étape

> Cadrage écrit **après** la recette du 2026-09-25, donc à partir de ce que l'utilisateur a réellement
> vécu sur le R+1, et non des intentions rédigées avant que F3 et F4 n'existent.
> Décisions numérotées à la suite de F4 (qui s'arrête à D105). **Rien n'est codé avant validation.**

## 1. Ce qui existe déjà (vérifié dans le code, 2026-09-25)

| Brique | Où | État |
| --- | --- | --- |
| Colonne d'étapes | `WorkspacePage.tsx:346-368`, `<ol className="th-ws-steps">` | 5 lignes **décoratives** : Planche / Locaux / Enveloppe / Pièce par pièce / Hauteurs. Seule la première est cliquable. |
| Compteur de locaux validés | `study.ts:45` `validatedRoomCount` | Compte `local_states[].status === "valide"`. Affiché, jamais exigé. |
| Fiche du local | `StudyRoomPanel` | S'efface quand un élément est désigné (F4). |
| Éléments d'enveloppe | `ElementPanel.tsx:298-316` | Mode **un seul élément** : le détail prend tout le bandeau, retour explicite. |
| Gestes sur un élément | `thermique_etude_edition.py`, `OPERATIONS_ELEMENT` | `element_confirmer` / `element_corriger` / `element_ecarter` / `element_reactiver`. Écrivent dans `releve_brut` (D99). |
| Corrections en attente | `useStudyElements.ts` | Appliquées en local, recalcul à la demande (D105). Bandeau « N corrections en attente ». |
| Calques du plan | `MetricsShow` (`metres` / `ponts` / `elements`) | Cases à cocher **manuelles**, indépendantes de l'étape en cours. |
| Ponts thermiques | `StudyMetrics.tsx`, `liaisons_localisees` | 77 liaisons sur le R+1, pastille + étiquette (AS / AR / RF), regroupées quand elles se confondent à l'œil. |
| File d'analyse | `AnalysisQueue.tsx`, `thermique_travaux.py` | F0 : un niveau part à l'analyse, le relais local le traite. |

**Conséquence pour F2 : la mécanique est là, le chemin manque.** Aucune étape ne pilote quoi que ce
soit : le thermicien doit deviner l'ordre, cocher les bons calques, et se souvenir de ce qu'il a déjà vu.

## 2. Ce que la recette a établi (faits, pas impressions)

1. **Les ponts multiples ne sont pas une anomalie.** L'enveloppe du R+1 compte 89 tronçons et
   67 changements de direction de plus de 20°, pour 64 angles relevés. À 10 cm près, les 77 ponts sont
   tous distincts. La détection suit le tracé ; c'est le tracé qui est découpé fin.
   → **Il ne faut donc pas fusionner les ponts dans le relevé.** Il faut que le thermicien les **valide
   ou les écarte un par un**. C'est la demande explicite de l'utilisateur, et elle devient une étape.
2. **Un bandeau qui montre tout ne montre rien.** La règle « une chose à la fois », appliquée aux
   éléments en F4, doit valoir sur tout le parcours.
3. **La couche métré ne doit pas suivre le thème de l'application** : le plan est une image blanche.
   Corrigé le 2026-09-25 (encre fixe `--th-plan-encre`, halo blanc).
4. **Un geste ne coûte rien, un recalcul coûte 3,2 s** : le parcours peut être fluide geste par geste,
   à condition de ne recalculer qu'aux frontières d'étape.

## 3. Décisions proposées

**D106 — La colonne de gauche devient le parcours, et elle pilote.** Cliquer une étape change ce que
montre le bandeau de droite **et** les calques du plan. Les cases à cocher restent, en réglage fin.

**D107 — Six étapes, dans cet ordre.**

| # | Étape | Ce qu'on y fait | Fini quand |
| --- | --- | --- | --- |
| 1 | Planche | Classer, mettre à l'échelle, poser le nord | `sheet.status === "prete"` |
| 2 | Analyse | Envoyer le niveau à l'agent, attendre le relevé | une étude existe |
| 3 | Locaux | Vérifier contours, noms, surfaces | tous les locaux vus |
| 4 | Parois et menuiseries | Confirmer / corriger / écarter les éléments tracés | plus d'élément « à vérifier » |
| 5 | **Ponts thermiques** | Valider ou écarter chaque liaison | plus de liaison « à vérifier » |
| 6 | Hauteurs (coupes) | À venir | — |

**D108 — L'étape « ponts thermiques » ne crée aucun backend.** Une liaison **est** un élément du relevé
(`angle_sortant` / `angle_rentrant` / `about_refend`). Valider = `element_confirmer`, refuser =
`element_ecarter` avec un motif. Tout existe depuis F4.

**D109 — Le parcours n'interdit rien.** Une étape non finie s'affiche en retard, elle ne verrouille pas
la suivante. Le thermicien sait mieux que l'outil dans quel ordre il travaille.

**D110 — Chaque étape annonce son reste à faire, en clair.** « 12 parois à vérifier », « 31 ponts sur 77
validés ». Un compteur qui ne descend pas est un bug visible ; un parcours sans compteur est une
promesse invérifiable.

**D111 — Pas de départ silencieux.** Quitter un niveau avec des corrections en attente affiche
« N corrections ne sont pas encore enregistrées » et propose d'enregistrer ou d'abandonner.

**D112 — Recalcul aux frontières d'étape.** On recalcule en quittant une étape qui a produit des
gestes, pas à chaque geste (D105).

## 4. Questions à trancher avant de coder

**Q1 — Maille de validation des ponts.** Par local (on suit les locaux, les ponts du local défilent)
ou par niveau (une passe continue sur les 77, sans se soucier des locaux) ?
*Recommandation : par niveau.* Un pont appartient à un tronçon, pas vraiment à une pièce ; 13 liaisons
du R+1 ne sont rattachées à aucun local et seraient invisibles dans une passe par local.

**Q2 — Geste de validation.** Deux boutons (« Garder » / « Écarter ») avec passage automatique au
suivant, ou un seul « Suivant » qui vaut acceptation ?
*Recommandation : deux boutons, et le passage au suivant automatique après « Garder ».* Un « Suivant »
qui valide en silence produit 77 ponts « validés » sans que personne les ait regardés.

**Q3 — Écarter un pont : motif obligatoire ?** F4 l'exige aujourd'hui pour un élément.
*Recommandation : un choix parmi trois motifs pré-écrits* (« angle du tracé, pas un vrai pont »,
« doublon du précédent », « hors enveloppe chauffée ») **plus une case libre**. Taper une phrase
77 fois n'est pas tenable.

**Q4 — Le regroupement visuel (`AS ×3`) à l'étape ponts.** Doit-il se déplier automatiquement quand on
arrive à cette étape, puisque c'est là qu'on veut les distinguer ?
*Recommandation : oui, et le plan se centre et zoome sur le pont en cours.*

**Q5 — Un pont écarté reste-t-il visible ?**
*Recommandation : oui, en gris barré, comme un élément écarté.* L'invisible ne se corrige pas.

**Q6 — Ce que montre le plan à chaque étape.** Étape 3 → contours seuls ; étape 4 → éléments + cotes
déperditives ; étape 5 → ponts seuls, éléments estompés. Les cases à cocher redeviennent libres dès
qu'on y touche.
*Recommandation : oui, et une petite mention « calques réglés par l'étape » qui disparaît si on coche.*

**Q7 — Faut-il une étape « Analyse » distincte dans la colonne** (étape 2 ci-dessus), alors que l'écran
de file d'attente F0 existe déjà à part ?
*Recommandation : oui.* Sans elle, le thermicien ne sait pas où se trouve son niveau quand il attend.

**Q8 — Fin de parcours.** Que se passe-t-il quand les six étapes sont finies : un bouton « Clôturer le
niveau » qui figera le relevé, ou rien de plus qu'un état affiché ?
*Recommandation : un état affiché pour l'instant, pas de clôture.* Figer un niveau demande de décider
ce qu'on fait d'un plan remplacé après coup — c'est un sujet à part.

## 5. Ce que F2 ne fera pas

- Fusionner des ponts dans le relevé (le métré changerait — voir §2.1).
- Ajouter un élément ou un pont manquant, ni déplacer les bornes d'un élément (reporté en D104).
- Figer ou clôturer un niveau (Q8).
- Toucher à l'agent `thermicien-enveloppe`. Si, après validation par le thermicien, le tracé s'avère
  trop découpé, c'est un chantier distinct.
