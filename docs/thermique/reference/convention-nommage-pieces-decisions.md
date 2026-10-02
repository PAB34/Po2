# Convention de nommage des pièces et tri par l'IA au dépôt (D281 à D285, proposées)

Date : 2026-10-02. Demande du thermicien : « lorsque le client a déposé les pièces sur la plateforme, il y a un
premier travail de l'IA : renommer les pièces selon la convention (à écrire) ». C'est l'étape qui précède l'étape 1
du guide (`guide-etude-thermique-14-etapes.md`), qui demande des « noms de fichiers stables » repris dans tous les
livrables.

## Existant vérifié

- Le site n'accepte que des **PDF** ; chaque **page** devient une planche ; le DWG et le DXF sont annoncés « pour
  plus tard ».
- Le nom d'origine est gardé (`original_filename`). Chaque planche a un libellé, une nature (plan, coupe, façade,
  plan masse, autre), un niveau et une échelle.
- La nature et le niveau sont **devinés d'après le nom du fichier** (`suggest_nature_and_level`). Le commentaire du
  code dit pourquoi : les PDF de plans n'ont pas de texte lisible. Une IA qui **lit le cartouche sur l'image** lève
  cette limite.
- Une page peut porter **plusieurs vues** : par exemple PC08 « ELEVEST-NORD » (deux façades), ou PC10 « COUPESAB »
  (deux coupes). Les vues existent déjà dans la plateforme (`thermique_vues`).

## Décisions proposées

- **D281 — On ne touche jamais au fichier du client.** Le fichier d'origine et son nom sont gardés tels quels
  (traçabilité, échanges avec l'architecte). Le « renommage » donne à chaque **page** un **code** stable et un
  **titre**, et à chaque vue d'une page son propre code.
- **D282 — La forme des codes.** Majuscules, sans accent ni espace, parties séparées par un tiret. On reprend les
  exemples du guide :

  | Famille | Code | Exemples |
  |---|---|---|
  | Plan de niveau | `PLAN-<niveau>` | `PLAN-S1` (sous-sol 1), `PLAN-N0` (rez-de-chaussée), `PLAN-N1`, `PLAN-COMBLES` |
  | Toiture | `TOITURE` | `TOITURE` |
  | Plan masse | `MASSE` | `MASSE` |
  | Coupe (vue) | `COUPE-<repère doublé>` | `COUPE-AA`, `COUPE-BB` |
  | Façade (vue) | `FACADE-<orientation>` | `FACADE-SUD`, `FACADE-NE` ; avant que le nord soit validé : `FACADE-<repère du plan>` |
  | Page de plusieurs vues | famille au pluriel + vues | `COUPES-AA-BB`, `FACADES-EST-NORD` |
  | Détails | `DETAIL-<numéro ou sujet>` | `DETAIL-01`, `DETAIL-ACROTERE` |
  | Structure | `STRUCT-<niveau>` | `STRUCT-N1` |
  | Fluides | `FLUIDES-<lot>-<niveau>` | `FLUIDES-CVC-N0`, `FLUIDES-VMC-N1` |
  | CCTP | `CCTP-<lot>` | `CCTP-LOT02`, `CCTP-MENUISERIES-EXT` |
  | Notices | `NOTICE-<sujet>` | `NOTICE-DESCRIPTIVE`, `NOTICE-THERMIQUE` |
  | Carnet de menuiseries | `CARNET-MENUISERIES` | `CARNET-MENUISERIES` |
  | Étude antérieure | `ETUDE-THERMIQUE-<année>` | `ETUDE-THERMIQUE-2019` |
  | Non reconnue | `A-CLASSER-<n>` | `A-CLASSER-1` |

  Indice ou version lu au cartouche : suffixe `-IND<lettre>` (`PLAN-N1-INDB`). Quand une pièce plus récente arrive,
  l'ancienne est marquée « remplacée » ; elle reste consultable mais n'est plus utilisée.
- **D283 — La fiche de chaque pièce**, remplie par l'IA et validée par le thermicien : code, titre lu au cartouche,
  famille, niveau ou orientation ou repère, échelle lue, indice et date, émetteur (architecte, bureau d'études),
  fichier et page d'origine, confiance et « à vérifier ».
- **D284 — La mission de tri** (avant l'étape 1 du guide), une par dépôt. Pour chaque page :
  1. rendu de la page entière, puis zoom sur le cartouche ;
  2. lecture du titre, du numéro de planche, de l'échelle, de l'indice et de la date ;
  3. famille, niveau, orientation ou repère, et code proposé ;
  4. pour une page à plusieurs vues, découpage en vues avec leur code.

  Elle rend un tableau de toutes les pièces, les **doublons** (deux `PLAN-N1`), les **pièces attendues qui
  manquent** (liste de l'étape 1) et ses **hypothèses et doutes**. Le thermicien valide ou corrige, puis les codes
  sont figés.
- **D285 — Les codes servent partout** : outils MCP, commandes `/etape-…`, livrables, plans annotés, et à terme les
  échanges avec le client (« il manque `COUPE-CC` »).

## Exemple : le projet 1 (médiathèque)

| Fichier déposé | Code de la page | Vues |
|---|---|---|
| PC01-FRONT-PLANMASSE.pdf | `MASSE` | |
| PC02-FRONT-NIVEAU-1.pdf | `PLAN-S1` | |
| PC03-FRONT-NIVEAU0.pdf | `PLAN-N0` | |
| PC04-FRONT-NIVEAU1.pdf | `PLAN-N1` | |
| PC05-FRONT-NIVEAU2.pdf | `PLAN-N2` | |
| PC06-FRONT-NIVEAU3.pdf | `PLAN-N3` | |
| PC07-FRONT-NIVEAUTOITURE.pdf | `TOITURE` | |
| PC08-FRONT-ELEVEST-NORD.pdf | `FACADES-EST-NORD` | `FACADE-EST`, `FACADE-NORD` |
| PC09-FRONT-ELEVSUD-OUEST.pdf | `FACADES-SUD-OUEST` | `FACADE-SUD`, `FACADE-OUEST` |
| PC10-FRONT-COUPESAB.pdf | `COUPES-AA-BB` | `COUPE-AA`, `COUPE-BB` |
| PC11-FRONT-COUPESCD.pdf | `COUPES-CC-DD` | `COUPE-CC`, `COUPE-DD` |

À vérifier par la mission : l'orientation réelle des façades (« ELEVSUD-OUEST » désigne-t-il deux façades, ou une
façade sud-ouest ?) ; elle sera confirmée quand le nord sera validé (étape 2).

## Questions

1. **Niveaux** : `N0` pour le rez-de-chaussée, `N1`, `N2`… et `S1`, `S2` pour les sous-sols, comme le guide ? Ou
   les noms déjà utilisés dans vos dossiers (`RDC`, `R1`, `R2`, `SS1`) ?
2. **Façades** : un code par orientation (`FACADE-SUD`), provisoire tant que le nord n'est pas validé, ça vous va ?
3. **Qui valide le tri** : vous seul, ou le client voit aussi les codes et la liste des pièces manquantes ?
4. **Pièces écrites** : la liste des familles (CCTP par lot, notices, carnet de menuiseries, étude antérieure) est-elle
   complète pour vos études ?
5. **Formats** : faut-il accepter dès le dépôt client les tableurs (carnet de menuiseries en Excel), les DWG, les
   images, ou seulement des PDF ?
