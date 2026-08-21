# 2026-08-21 — ASTECH : réexport livré, nouvel export intégré, écran remanié

Suite de `2026-08-19 - Referentiel patrimoine historique ASTECH.md`.
Décisions : `docs/refonte-v1/patrimoine-fichier-historique-rapprochement-decisions.md`
(§19 hiérarchie bâtiment/local, **§20 nouvel export ASTECH**).

## État en prod au 2026-08-21

| | |
|---|---|
| Gabarit importé | `OPUS_Patrimoine20260707.xlsx` · feuille `Worksheet` · en-têtes ligne 1 |
| Biens ASTECH | **380** — 310 à traiter · 69 à confirmer · 1 hors périmètre |
| Patrimoine Po2 | 185 bâtiments · 627 locaux · 160 sites |

Fichier source : `saas/energie/ASTECH/OPUS_Patrimoine20260707.xlsx`.

## Ce qui a été livré

**Incrément 3 — le réexport ASTECH** (`services/patrimoine_legacy_export.py`,
`GET /patrimoine/legacy/export` + `/export/preview`, bouton « 4. Exporter pour ASTECH »).
Trois feuilles : réinjectable, Traçabilité, À vérifier. En-têtes recopiés à l'octet près
depuis `headers_json`, `CODE_BIEN` jamais réécrit, rien d'inventé — le doute envoie la
ligne en « À vérifier ».

**Nouvel export ASTECH intégré** (§20). Le lecteur accepte les **deux générations** de
fichier : table d'alias par colonne, comparaison sans accent ni casse, ligne d'en-têtes
trouvée par son contenu, valeurs composites décomposées (`BATI / BATIMENT` → `BATI`).
Trois colonnes **ajoutées** à l'export car absentes du nouveau gabarit : `Ref cadastrale`,
`Latitude`, `Longitude` (Q22).

**Hiérarchie bâtiment / local** : création d'un local depuis un bien, ajout d'un local à
la liste ASTECH, panneau du local symétrique de celui du bâtiment, typologie modifiable
dans les deux sens, locaux dessinés sur la carte (héritant de la position du bâtiment
quand ils n'en ont pas).

**Écran remanié** : trois colonnes (file · carte · panneau), bloc « Rattachement » unique,
code couleur **violet = ASTECH / bleu = Po2** partout, passage automatique au bien suivant,
compteur d'avancement, filtres d'affinage, disposition en araignée sur la carte.

## Pièges rencontrés — à ne pas réintroduire

1. **`update_building` remettait à plat tout le bâtiment.** Renommer effaçait position,
   adresse et cadastre. Rendu partiel (`model_fields_set`). Vérifier ce réflexe sur
   `update_site` et `update_local`, non audités.
2. **Le reclassement supprime puis recrée** avec un nouvel identifiant : il faut
   transporter adresse/position/cadastre **et** reporter les biens ASTECH, sinon ils sont
   orphelinés en silence (`ON DELETE SET NULL`).
3. **`candidate_building_id` n'a pas de clé étrangère** : il survit à une purge du parc.
   Nettoyé par « Reconnaître les noms », refusé proprement à la validation.
4. **Le CODE_BIEN a changé de schéma** entre les deux exports (0 code commun). Un import
   dont aucun code ne recoupe l'existant est signalé (`codes_disjoints`).
5. **La recherche IGN** : la couche `batiment` saturait son plafond de 500 (résultat
   tronqué) et les stades, terrains, parkings vivaient dans des couches non interrogées.
6. **Ordre de dessin Leaflet** : la dernière couche ajoutée capte les clics. Les polygones
   IGN sont dessinés du plus grand au plus petit, sinon un terrain de sport rend
   inatteignable tout ce qu'il recouvre.
7. **Les positions ASTECH sont empruntées** : un bien n'a pas de coordonnées propres
   (1 sur 444 dans le fichier). Détacher lui rend son absence de position.
8. **67 bâtiments Po2 sur 184 partagent leurs coordonnées** avec un autre (héritées de la
   parcelle). Écartés à l'affichage — le fond du problème reste la donnée.
9. **Le local par défaut portait le nom du bâtiment.** L'import fabriquait un jumeau
   homonyme et vide par bâtiment : invisible dans l'arbre replié, mais dessiné comme un
   second point sur la carte ASTECH dont il hérite la position. 121 supprimés en prod le
   2026-08-21, l'option coupée à l'import. Voir §21 du doc de rapprochement (Q23/Q24) —
   qui apporte aussi le statut **« disparu chez ASTECH »** pour les biens que la
   collectivité a retirés de sa base : hors parcours, hors réexport, réversible.

## Reprise prochaine session

1. **Confirmer les 69 rattachements proposés**, puis traiter les 310 restants. L'export
   ne prend que les rattachements **validés par un humain**.
2. **Relire la feuille Traçabilité** avant toute réinjection : elle liste chaque valeur
   remplacée. Le nom Po2 écrase le nom ASTECH au rattachement (Q11) — c'est voulu, mais
   un mauvais rattachement y devient visible.
3. **Q19 rouverte si besoin** : un bien ASTECH couvrant plusieurs bâtiments Po2 n'est pas
   traité (relation N biens → 1 cible).
4. **Chantier distinct** : les positions par bâtiment ont été perdues à l'import du
   patrimoine (143 positions distinctes pour 185 bâtiments).
5. Le test d'import réel dans ASTECH n'a jamais eu lieu : c'est lui qui validera le
   format de retour.
