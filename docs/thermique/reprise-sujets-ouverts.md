# Sujets ouverts, relevés par l'utilisateur le 2026-09-25

> Écrit à la fin du quota hebdomadaire de Claude Code, pour la reprise avec Codex.
> **Chaque sujet : ce que l'utilisateur a demandé (mot pour mot), ce que le code fait aujourd'hui
> (vérifié, pas supposé), ce qui manque, et une piste.** Ordre = valeur décroissante, pas ordre de citation.
>
> À lire avec `passation-codex-F2.md` (état du dépôt, règles, contrat de données) et
> `parcours-F2-decisions.md` (le parcours en six étapes, D106 à D114).

---

## Sujet 1 — Supprimer et ajouter des pièces ⭐ priorité haute

> « parfois il a été dessiné des pièces qui ne devrait pas exister j'aimerais les supprimer. Il ya aussi
> des pièces que je souhaiterai ajouter. »

**Ce qui existe.** `thermique_etude_edition.py` porte déjà les gestes sur les contours :
`OPERATIONS` contient couper, fusionner, modifier, remodeler. `useStudyEdition.ts` et le menu contextuel
du plan (`PlanMenu.tsx`, clic droit) offrent « Reprendre le contour » et « Couper en deux ».
**Il n'y a ni suppression ni création de pièce.**

**Ce qui manque.** Deux opérations symétriques, côté serveur et côté plan.

**Piste.**
- **Supprimer** : ne pas effacer. Suivre **D100**, comme pour un élément d'enveloppe : la pièce reste dans
  l'étude avec un `exclu` et un motif, sort de tout ce qui se mesure, s'affiche en grisé et peut revenir.
  C'est la seule façon de garder le geste réversible et traçable. Conséquence à traiter : la
  **couverture** (`controler_couverture`) va signaler la surface libérée comme « non affectée » — c'est
  correct, mais il faut que le message le dise sans affoler.
- **Ajouter** : une opération `local_ajouter` qui reçoit un contour tracé à la main. L'outil de tracé
  existe déjà (le brouillon de `useStudyEdition`, `tool === "edition"`) : le réemployer plutôt que d'en
  écrire un second. Le nouveau local a besoin d'un nom, d'une nature (voir sujet 6) et doit passer par
  `reconstruire()` pour recevoir ses côtés, son métré et ses ponts.
- **Attention** : une pièce ajoutée ou supprimée change les contours, donc le **rattachement des liaisons**
  (`liaisons_localisees` cherche le contour le plus proche à moins de 1 m). Vérifier les 77 ponts après.

**Repères à ne pas casser** : 222 côtés, 170,12 m déperditifs sur le R+1 (avant ajout/suppression).

---

## Sujet 2 — Cliquer un côté dans « Côtés et adjacences » le sélectionne sur le plan ⭐ priorité haute

> « quand je clique sur une pièce dan sle volet de droite s'affiche des éléments dans "Côtés et
> adjacences" j'aimerais pouvoir cliquer dessus qu'il se sélectionne dans le plan automatiquement »

**Ce qui existe.** La liste est dans `StudyPanel.tsx` (fiche du local, section « Côtés et adjacences »),
alimentée par `room.fiche.cotes`. Chaque côté porte déjà **`trace_pdf`** : son tracé sur la feuille.
Sur le plan, `StudyMetrics.tsx` dessine ces côtés via le composant `Cote`. **Les deux ne communiquent
pas** : la liste est inerte.

**Ce qui manque.** Un état « côté désigné », partagé entre la fiche et le plan — exactement le motif déjà
en place pour les éléments d'enveloppe (`selectedElement` → halo + tracé passé en dernier).

**Piste, courte et sûre.** Le chemin est balisé, c'est un patron à recopier :
1. Un état `coteVisee: number | null` (le rang du côté dans `room.fiche.cotes`) dans `WorkspacePage.tsx`.
2. `StudyPanel` reçoit `coteVisee` et `onCote(rang)` ; chaque ligne de la liste devient un bouton.
3. `StudyMetrics` reçoit `coteVisee` et donne au côté visé un halo, comme `th-metric-element__halo`.
   **Le dessiner en dernier** — sinon il disparaît sous les autres couches, erreur déjà commise et
   corrigée pour les éléments.
4. Bonus utile : amener le plan sur le côté avec la nouvelle entrée **`focus`** de `TileSheetViewer`
   (`{point, cle, zoom}`), qui existe depuis F2 et sert déjà aux ponts.
5. **Réciproque** : cliquer un côté sur le plan devrait le surligner dans la liste. Même état, rien de plus.

---

## Sujet 3 — Les ponts thermiques entre deux pièces : la règle des 50 % ⭐ priorité haute

> « parfoi il est situé entre deux pièces, est-ce prévu que sa valeur soit de 50% pour l'une et 50% pour
> l'autre comme de manière conventionnel c'est fait ? »

**Réponse vérifiée dans le code : à moitié seulement.**

`thermique_enveloppe_pieces.py`, `decouper_par_piece()` :

| Type de liaison | Nombre sur le R+1 | Partage aujourd'hui |
| --- | --- | --- |
| `about_refend` | 13 | **✅ 50 / 50 déjà fait** — ligne 167 : `[[avant, 0.5], [apres, 0.5]]` dès que les deux pièces diffèrent |
| `angle_sortant` | 43 | ❌ **100 % à une seule pièce** (branche `else`, ligne 170 : `[[nom, 1.0]]`) |
| `angle_rentrant` | 21 | ❌ **100 % à une seule pièce**, même branche |

Donc la convention est appliquée aux abouts de refend, **et pas aux 64 angles**. C'est une vraie lacune,
pas un choix documenté.

**Piste.** Étendre la logique des abouts aux angles : chercher la pièce de part et d'autre de l'angle
(`piece_derriere` de chaque côté) et partager `0.5 / 0.5` quand elles diffèrent. Mais attention, un angle
n'est pas un refend : il **tourne**, ses deux côtés ne sont pas dans le prolongement l'un de l'autre.
Il faut donc sonder de part et d'autre du **coin** (les deux tronçons qui s'y rejoignent), pas le long d'un
seul tronçon. Écrire un fichier de décisions avant : cela **change le métré**, donc l'utilisateur doit
valider la règle.

**Ne pas confondre deux choses.** `liaisons[].piece` (la pastille sur le plan) désigne **une seule** pièce,
la plus proche à moins de 1 m — c'est de l'affichage. Le métré, lui, lit `element["pieces"]`, la liste
`[[nom, part], …]`. Corriger le métré ne demande pas de toucher à la pastille.

**Vérification attendue** : la somme des parts d'un angle partagé doit faire 1,0, et le total des ponts du
niveau doit rester 43 / 21 / 13 après redistribution.

---

## Sujet 4 — Comment une étape est-elle considérée comme terminée ? (question, réponse ci-dessous)

> « comment est-ce que chacune des étapes est considéré comme terminé ? »

Tout est dans **`workspace/parcours.ts`**, fonction `parcours()`, et **rien n'est verrouillé** : une étape
en retard ne barre jamais la suivante (**D109**). Voilà la règle exacte, étape par étape.

| Étape | Terminée quand | Sur le R+1 aujourd'hui |
| --- | --- | --- |
| **Planche à l'échelle** | `sheet.status === "prete"` **et** le nord est posé (`sheet.nord`). Sans nord, aucune orientation n'est calculable (D84), donc l'étape reste en cours. | selon la planche |
| **Analyse du plan** | dès qu'une étude existe pour la planche. En cours si la planche est prête et le relevé absent. | faite |
| **Locaux** | **tous** les locaux sont validés, c'est-à-dire `local_states[id].status === "valide"` pour chacun. C'est le bouton « Enregistrer et valider » de la fiche du local qui pose cet état. | à voir |
| **Parois et menuiseries** | plus aucun des **150** éléments non-pont n'est à la fois marqué `a_verifier` par l'agent **et** non tranché. Ce que l'agent a lu sans hésiter compte pour jugé (**D114**) : on n'impose pas 150 clics. | **64 restent à vérifier** |
| **Ponts thermiques** | **chacun** des **77** est confirmé, corrigé ou écarté. Régime exigeant (**D114**) : ici la confiance de l'agent ne vaut **pas** validation, choix confirmé par l'utilisateur (« Ok 77 »). | **77 à juger** |
| **Hauteurs (coupes)** | jamais : toujours « à venir », la lecture des coupes n'existe pas. | — |

`etapeCourante()` propose la **première étape non terminée**. Tout étant fini, on se pose sur les ponts,
dernière étape réellement travaillable.

**Sujet dérivé à trancher (D-à-écrire).** Rien ne relie aujourd'hui la validation d'un local (étape
Locaux) à l'état de ses éléments et de ses ponts. On peut donc valider un local dont les ponts n'ont pas
été jugés. Faut-il que « valider un local » exige que ses côtés et ses ponts soient tranchés ? C'est une
question pour l'utilisateur, pas une décision d'implémentation.

---

## Sujet 5 — Les terrasses sont des pièces extérieures ⭐ à cadrer avant de coder

> « une terrasse devrait être considéré comme une pièce extérieur, pourquoi, parce que son
> plancher/paroi/poteau crée une liason avec le spièces adjacentes créant des ponts thermiques »

**Ce qui existe.** Une pièce n'a que **trois** natures : `chauffe`, `circulation`, `non_chauffe`
(`StudyLocalNature` côté front, `natures_du_plan()` côté serveur, D24). **Il n'y a pas d'« extérieur ».**
Une terrasse est donc aujourd'hui soit comptée comme un local, soit absente — dans les deux cas, faux.

**Pourquoi c'est structurant.** Le raisonnement de l'utilisateur est juste et il porte loin : une terrasse
n'est pas un volume à chauffer, c'est une **source de ponts thermiques** pour ses voisines. Son plancher
se prolonge, ses poteaux traversent, sa paroi fait retour. Elle doit donc exister dans le modèle pour
**produire des liaisons**, sans jamais entrer dans les surfaces chauffées ni dans les déperditions par
paroi.

**Piste.**
1. Ajouter une nature `exterieur` (ou `terrasse`) aux trois existantes, côté serveur et côté front.
2. Décider ce qu'elle fait dans chaque calcul, et l'écrire noir sur blanc : hors surface chauffée, hors
   périmètre déperditif propre, **mais** ses limites avec une pièce chauffée deviennent des tronçons
   porteurs de liaisons.
3. Regarder ce que fait déjà `sur_non_chauffe_m` et la notion de tronçon `face_interieure` : le mécanisme
   « ma limite donne sur du non chauffé » existe et servira probablement de base.
4. **Fichier de décisions obligatoire.** Cela touche le métré, les fiches et la couverture.

---

## Sujet 6 — Les contours parasites (portes, aires de rotation PMR) — reporté par l'utilisateur

> « sur certaines pièces (très peu, j'ai encore des zones correspondant à l'ouverture d'une porte ou d'une
> zone PMR dont les traits servent de contour depièce alors que ca ne devrait pas mais bon sujet autre à
> travailler plustard »

**L'utilisateur le reporte lui-même.** À garder en vue, sans l'attaquer maintenant.

**Diagnostic probable** : l'agent prend l'arc d'ouverture d'une porte ou le cercle de rotation PMR pour un
trait de contour. Cela se corrige **en amont**, dans l'agent, pas dans l'interface — sauf que, dès que le
sujet 1 existe, le thermicien pourra **supprimer la pièce parasite** lui-même. C'est une bonne raison de
traiter le sujet 1 d'abord : il rend celui-ci vivable en attendant la vraie correction.

---

## Sujet 7 — Le tracé de l'enveloppe est très découpé — chantier de fond

Non cité aujourd'hui, mais c'est le fond du sujet des « trop nombreux ponts ». Mesuré : l'enveloppe du R+1
compte **89 tronçons et 67 changements de direction de plus de 20°**, pour **64 angles relevés**. À 10 cm
près, les 77 ponts sont **tous distincts** : la détection suit fidèlement le tracé.

Si, après la passe de validation, le thermicien juge qu'il y a encore trop d'angles, le coupable est
l'agent **`thermicien-enveloppe`**, pas l'affichage. Chantier distinct et plus profond. Ne pas le
confondre avec une question d'interface, et ne pas retoucher l'affichage pour le masquer.

**Interdit sans l'accord de l'utilisateur** : fusionner des ponts dans le relevé. Cela changerait le
métré. Le choix actuel — il les écarte un par un — est traçable et réversible.

---

## Ordre de travail proposé

1. **Sujet 2** (cliquer un côté → le voir sur le plan). Le plus rapide, le patron existe, gain immédiat.
2. **Sujet 1** (supprimer / ajouter une pièce). Déverrouille aussi le sujet 6.
3. **Sujet 3** (50 / 50 sur les 64 angles). Touche le métré → fichier de décisions d'abord.
4. **Sujet 5** (terrasses). Le plus structurant, donc celui qui mérite le cadrage le plus soigné.
5. Sujet 4 : déjà répondu ; seule la question dérivée (valider un local exige-t-il ses ponts ?) reste à
   poser à l'utilisateur.
6. Sujets 6 et 7 : plus tard, et pas par l'interface.

**Et n'oublie pas** : le Ctrl+Z demandé juste avant (annuler la dernière action) est décrit en détail au
§5 de `passation-codex-F2.md`, avec ses cinq pièges. Il reste la tâche numéro zéro si l'utilisateur ne
change pas d'avis.
