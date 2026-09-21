# Vigie Foncier Sète — décisions de cadrage (MVP toutes zones + carte + filtres)

> Projet **à part** (aucun lien fonctionnel avec Po2). Cadrage source :
> `Documents/IMMOBILIER/Vigie_Foncier_Sete_Moteur_B_Cadrage.md` (V0.1).
> Données réglementaires : `reglement_plu_sete_par_zone.xml` (prioritaire) puis
> `classement_prospection_fonciere_sete.xlsx` (couche qualitative).
> Statut : **décidé 2026-09-21 (V1-V10 validées) — É0 à É3 livrés**.

---

## 1. Demande (2026-09-21)

1. Un sous-domaine du type **immobilier.patrimoineaucarre.com**.
2. Une **carte** qui montre clairement les parcelles concernées.
3. Un **panneau de filtres** qui pilote ce qui s'affiche, calé sur le besoin réel de prospection.
4. Un MVP qui couvre **toutes les zones** du PLU (pas seulement UD), filtrables **par sous-secteur**
   (UD1, UD1a, UD1v, UD2…), de la même manière pour chaque zone.
5. Avancer **étape par étape**.

Écart assumé avec le cadrage V0.1 (§15 « UD uniquement ») : le **calcul** couvre toutes les zones dès
le départ (il ne coûte presque rien de plus) ; c'est le **filtre** qui restreint l'affichage. Les
étapes géométriques fines (jardin arrière, accès…) restent d'abord calibrées sur le pavillonnaire.

---

## 2. Existant vérifié (2026-09-21)

| Élément | Constat |
|---|---|
| XML règlement | 13 zones, 83 sous-secteurs, 16 articles/zone, texte page par page. Bloc `normalized_data/emprise_au_sol` **présent pour 100 % des secteurs** avec mode (`ratio`, `conditionnelle`, `formule_spatiale`, `non_reglementee`, `document_graphique`, `non_explicite`, `majoration_piscine`), pages source et niveau de confiance. |
| Excel classement | 84 lignes (UA5a scindé en « alignement » 80 % / « recul » non réglementée). Apporte : habitation standard Oui/Conditionnelle/Non, profil d'opération, contraintes, score de zone /100, priorité, segments de prospection, 7 contrôles, anomalies. |
| Concordance XML ↔ Excel | **Taux d'emprise identiques sur les 83 secteurs** (contrôle automatique). Seule différence : la scission UA5a. Anomalie 3UB9/3UB9v signalée dans les deux. |
| Zonage officiel (API Carto GPU, partition `DU_34301`) | 259 polygones, **80 codes `libelle`** = exactement les codes du règlement (UD1, UD2v, UC4bv…). → filtre par sous-secteur **directement possible**. Absents du zonage : UEc1, UC5a (déjà notés comme anomalies). |
| Cadastre Etalab (commune 34301) | **11 283 parcelles**, **20 219 bâtiments** (≈ 1 Mo compressé chacun). → toute la commune tient dans un seul fichier chargé par le navigateur ; filtrage instantané, sans base de données serveur. |
| Hébergement | VPS existant, Caddy + réseau Docker `po2-edge`. Précédent réutilisable : **PRONO** (`ligue1.patrimoineaucarre.com`) = application séparée, ses propres conteneurs, un bloc Caddy dédié (`saas/infra/caddy/Caddyfile`). |
| Scripts du dossier IMMOBILIER | `immobilier_mdb.py`, `dvf.py`, `bienici_mdb.py` (moteur « annonces / DVF ») : non lus, hors périmètre du Moteur B. |

---

## 3. Hiérarchie des sources (proposition)

| Donnée | Source retenue | Pourquoi |
|---|---|---|
| Taux d'emprise, mode de règle, pages, confiance | **XML** | Extraction directe du règlement opposable, traçable page par page. |
| Texte des articles 3/6/7/8/12/13 (accès, retraits, distances, stationnement, pleine terre) | **XML** (à chiffrer étape É4) | Seule source complète. |
| Habitation standard, profil d'opération, contraintes, priorité de zone, segments | **Excel** | Lecture experte que le XML ne contient pas. |
| Score de zone Excel (/100) | **Excel, en critère secondaire seulement** | Il note la *zone* (et favorise les zones denses : UC3 1er, UD2 à 70) ; il ne mesure pas le potentiel d'une *parcelle* pour une division. |
| Conflit éventuel | **Le XML l'emporte**, conflit listé dans un rapport de génération. | |

Le fichier `config/plu_sete.yaml` est **généré automatiquement** (XML + Excel), jamais saisi à la
main, avec un test qui échoue si une valeur diverge ou si un code du zonage n'a pas de règle.

---

## 4. Toutes les zones : familles d'opération

Mélanger toutes les zones dans un score unique n'a pas de sens (une parcelle UA à 75 % d'emprise
dans un tissu mitoyen n'est pas une « réserve foncière »). Chaque sous-secteur reçoit donc une
**famille**, issue des segments de l'onglet Méthode de l'Excel :

| Famille | Sous-secteurs (proposition) | Ce que mesure le moteur |
|---|---|---|
| **Division pavillonnaire** | UD1, UD1a, UD2, UD3, UD4, UC4a, UC4b, UV2, UV3 | Réserve d'emprise + terrain libre ; puis (É4) jardin arrière / réserve latérale / accès |
| **Densification / promoteur** | 3UB1-4, 3UB6-9, UC3, UC4c, UC4d, UA5, UA5a | Réserve d'emprise + surface ; 3UB7 = formule bande de 16 m (approchée) |
| **Réhabilitation / division bâtie** | UA1-4, 1UB1-5, 2UB, UV1, UV4 | Pas de réserve au sol pertinente : affichage + surface bâtie, sans score de réserve |
| **Protégé « v »** | tous les secteurs `…v` | Affichés sur demande, pénalisés (EVP, 8-10 %) |
| **Hors cible** | UE*, UP*, A, N*, AU0, AUE0, 3UB5, UV3a, UC1, UC2, UC5, UC4e | Masqués par défaut, affichables |

Règles non chiffrées (2UB, UV4, UA4v, UA5a en recul) : réserve = **« non calculable »**, parcelle
affichée avec un badge, jamais éliminée silencieusement (sensibilité avant tout, cadrage §13).

---

## 5. Calculs par parcelle (étape É2, toutes zones)

- **Secteur** : intersection parcelle × zonage. Parcelle à cheval → secteur majoritaire affiché +
  liste des secteurs, et emprise max = Σ (surface dans le secteur × taux du secteur).
- **Bâti** : Σ surfaces des bâtiments cadastraux intersectés ; nombre de bâtiments.
- **Terrain libre** = surface − bâti.
- **Emprise max** = Σ surface × taux (la majoration piscine UD de 8 % / 40 m² est **exclue** : elle
  ne sert qu'aux piscines).
- **Réserve d'emprise** = emprise max − bâti ; **taux d'utilisation** = bâti / emprise max.
- **Terrain nu** (0 bâtiment) : repéré à part (dent creuse).
- **Score provisoire** /100 dans chaque famille (réserve, terrain libre, surface, priorité de zone
  Excel ≤ 10 pts, pénalité « v »), clairement étiqueté « provisoire » jusqu'à l'étape géométrique.
- Limite affichée : le PLU raisonne en **unité foncière** (parcelles contiguës d'un même
  propriétaire) ; le moteur raisonne à la parcelle.

---

## 6. Panneau de filtres (étape É3)

| Groupe | Filtres |
|---|---|
| **Préréglages** | « Division pavillonnaire » (défaut), « Densification promoteur », « Terrains nus », « Tout afficher » ; sauvegarde de mes propres réglages |
| **Zonage** | Arbre zone → sous-secteurs à cocher (UD ▸ UD1, UD1a, UD1v, UD2…), identique pour chaque zone ; bascule « inclure les secteurs v » ; famille d'opération |
| **Qualitatif (Excel)** | Priorité de zone P1/P2/P3/À valider/Hors cible ; habitation standard Oui/Conditionnelle/Non ; profil d'opération |
| **Parcelle** | Surface min/max ; surface bâtie ; terrain libre min ; nombre de bâtiments ; terrain nu oui/non |
| **Potentiel** | Réserve d'emprise min (m²) ; taux d'utilisation max (%) ; score min ; « règle non calculable » inclure/exclure |
| **Géométrie** (É4) | Plus grande zone libre min ; configuration A/B/C/D ; accès potentiel ; largeur d'accès min |
| **Contraintes** (É5) | Exclure / signaler PPRI, SPR, EVP, emplacements réservés |
| **Suivi** (É6) | Statut : à étudier / rejetée / recherche propriétaire ; avec note |
| **Recherche** | Référence cadastrale ou section |

Carte : couleur = classe de score (ou famille), compteur « N parcelles affichées », liste triable à
côté de la carte, clic → fiche parcelle (chiffres + motif + lien orthophoto / Géoportail).

---

## 7. Architecture proposée

- **Préparation hors ligne (Python)** : téléchargement cadastre + zonage (+ prescriptions GPU),
  génération `plu_sete.yaml`, calculs → un fichier `parcelles_sete.geojson` (ou FlatGeobuf) enrichi.
  Relancé à la main quand le PLU ou le cadastre change.
- **Site** : une page web légère (carte **MapLibre**, fond IGN Plan + orthophoto) qui charge ce
  fichier et filtre **dans le navigateur** (11 283 parcelles : instantané).
  Plutôt que Streamlit + Folium du cadrage V0.1 : Folium recharge toute la carte à chaque filtre et
  devient lent au-delà de quelques milliers de polygones.
- **Petit serveur (étape É6 seulement)** pour enregistrer statuts et notes.
- **Hébergement** : conteneur dédié sur le VPS, bloc Caddy `immobilier.patrimoineaucarre.com`
  (modèle PRONO), HTTPS automatique, accès protégé par mot de passe.

---

## 8. Étapes

| Étape | Contenu | Livrable visible |
|---|---|---|
| **É0** | Sous-domaine + page protégée | Site en ligne avec une carte de Sète vide |
| **É1** | Matrice PLU générée (XML + Excel), test de concordance | `plu_sete.yaml` + rapport des anomalies |
| **É2** | Données + calculs niveau 1-2, toutes zones | Fichier des 11 283 parcelles enrichies |
| **É3** | Carte + panneau de filtres + fiche parcelle | **Premier outil utilisable** |
| **É3b** | Jeu test 20/20/10 (cadrage §13), réglage des seuils | Mesure « bonnes parcelles remontées » |
| **É4** | Géométrie : plus grande zone libre, retraits art. 6/7/8, types A-D, accès | Filtres géométriques + score complet |
| **É5** | Contraintes : PPRI, SPR, EVP, emplacements réservés | Pénalités + filtres contraintes |
| **É6** | Suivi de prospection (statuts, notes) | Boutons de la fiche actifs |

Proposition : livrer **É0 → É3 d'un bloc** (carte filtrable toutes zones), puis itérer.

---

## 9. Questions

- **V1** — Nom de domaine : `immobilier.patrimoineaucarre.com` (proposé) ou `foncier.` ?
- **V2** — Accès : vous seul avec un mot de passe simple (proposé), ou comptes pour d'autres personnes ?
- **V3** — DNS : qui ajoute l'enregistrement A chez le registraire (comme pour thermique / ligue1) ?
- **V4** — Technique : page web légère MapLibre (proposé) plutôt que Streamlit du cadrage ?
- **V5** — Familles d'opération du §4 : répartition validée ? (points sensibles : UC4a/UC4b et
  UV2/UV3 en « division pavillonnaire », 3UB4/6/8 en « densification »).
- **V6** — Affichage par défaut à l'ouverture : préréglage « Division pavillonnaire » (proposé) ?
- **V7** — Parcelles à cheval sur deux secteurs : emprise pondérée par surface (proposé) ?
- **V8** — Terrains nus (0 bâtiment) : les inclure comme opportunités, filtrables à part (proposé) ?
- **V9** — Emplacement du code : dossier `VIGIE/` dans le dépôt Po2, comme PRONO (proposé), ou
  dépôt séparé ?
- **V10** — Premier livrable = É0 → É3 d'un bloc (proposé) ?

## 10. Décisions

**2026-09-21 — « ok pour tout » : V1 à V10 validées telles que proposées.**

- V1 `immobilier.patrimoineaucarre.com` · V2 accès unique par mot de passe (Caddy `basic_auth`,
  utilisateur `vigie`, hash dans `saas/.env` du VPS) · V3 DNS ajouté par l'utilisateur
  (enregistrement A → 135.125.152.112) · V4 page web MapLibre · V5 familles du §4
  (`VIGIE/config/familles.yaml`) · V6 ouverture sur « Division pavillonnaire » · V7 emprise pondérée
  · V8 terrains nus inclus, filtrables · V9 code dans `VIGIE/` · V10 É0 → É3 livrés d'un bloc.

## 11. Livré (É0 → É3, 2026-09-21)

- **É1** : matrice générée, 83 secteurs, **0 écart XML/Excel**, 28 règles non calculables listées
  (`VIGIE/config/rapport_regles.md`). UA5a (conditionnelle) pris à 80 % (cas alignement).
- **É2** : 11 268 parcelles calculées (15 hors zonage écartées), 783 à cheval sur plusieurs
  secteurs, 97 partiellement non calculables. « Terrain nu » = bâti < 20 m² (abris, murets).
- **É3** : carte (plan IGN / photo aérienne, zonage, bâti), arbre zone → sous-secteurs pour toutes
  les zones, raccourcis par famille, filtres parcelle / potentiel / lecture Excel / référence,
  5 réglages prédéfinis + réglages personnels (navigateur), liste triable, fiche parcelle avec
  liens Géoportail / GPU / Street View / DVF, export CSV.
- Ajustements après premier essai : le préréglage « Division pavillonnaire » fait remonter sinon
  des terrains nus et de grandes résidences → **bâti 40-300 m², surface 350-3 000 m²**
  (modifiables). Seuils du cadrage §6 conservés (libre ≥ 180, réserve ≥ 60).

Prochaine étape proposée : **É3b** — jeu test 20/20/10 (cadrage §13) pour régler seuils et score,
puis **É4** (géométrie : plus grande zone libre, accès, retraits art. 6/7/8).

## 12. Voiries (2026-09-21)

Demande : ne plus faire remonter les voiries (« si trop compliqué ou risque de fausser, laisse tomber »).
Retenu parce que fiable au contrôle visuel (orthophoto : allées de résidence, rue de zone d'activités,
chemin du lido, accès, bande de parking — 7/7 correctes) et sans effet sur les parcelles bâties :

- **Voirie probable** = parcelle bâtie < 20 m² ET (couverte ≥ 50 % par une chaussée BD TOPO, ou
  ≥ 25 % si largeur < 8 m, ou bande < 6 m de large, 5× plus longue que large, ≥ 150 m²).
- 530 parcelles repérées ; **masquées par défaut, jamais supprimées** (case « Exclure les voiries
  probables », alerte dans la fiche, colonne dans l'export).
- Effet : « Division pavillonnaire » inchangé (256, bâti ≥ 40 m²) ; « Terrains nus » 416 → 268.
