# 2026-05-20 — Import inventaire CVC terrain (PO2-CVC-001)

> IA : Claude Sonnet 4.6
> Durée approximative : 1h
> Précédente session : `[[Sessions/2026-05-20 — Import patrimoine hierarchique]]`

## 🎯 Objectif de la session

Implémenter le chantier **PO2-CVC-001** : permettre l'import de l'inventaire terrain CVC depuis `saas/CVC/listing materiels V2.xlsx` et le rattachement de chaque équipement à un bâtiment de la base patrimoniale + au référentiel SYPEMI pour calcul de vétusté.

## ✅ Ce qui a été fait

### PO2-CVC-001 — Import inventaire CVC terrain

**Architecture décidée** : nouvelle table `cvc_inventory_items` séparée de `BuildingEquipment` (SYPEMI normalisé), pour stocker les équipements réels terrain avec toutes leurs métadonnées. La `equipment_ref_id` est nullable — si la famille correspond à un équipement SYPEMI, la durée de vie théorique + vétusté sont calculées ; sinon les champs restent nuls.

- Commit `fd192fe` : feat(cvc) — 11 fichiers, 1171 insertions
- Commit `fff24e1` : fix(cvc) — TS7053 referenceCounts clé terrain manquante

**Fichiers backend créés** :
- `app/models/cvc.py` — ORM `CvcInventoryItem` (17 colonnes)
- `app/schemas/cvc.py` — Pydantic preview / match / import / read
- `app/services/cvc.py` — fuzzy match sites↔bâtiments (difflib.SequenceMatcher), fuzzy match famille↔SYPEMI, import bulk, calcul vétusté
- `app/api/routes/cvc.py` — 6 endpoints REST
- `alembic/versions/0016_add_cvc_inventory.py` — migration appliquée en prod

**Fichiers frontend créés/modifiés** :
- `pages/CvcImportPage.tsx` — wizard 3 étapes (upload → mapping → résultat)
- `pages/BuildingTechniquePage.tsx` — onglet "Inventaire terrain" + badges vétusté
- `lib/api.ts` — 6 fonctions API CVC
- `App.tsx` — route `/buildings/cvc-import` + lien sidebar

**Migration appliquée en prod** : `alembic upgrade head` exécuté dans `infra-backend-1`.

**Données source** :
- `saas/CVC/listing materiels V2.xlsx` : 1133 lignes, 71 sites, 44 familles
- Colonnes : SITE / BATIMENT / NIVEAU / LOCAL / DESIGNATION / STATUT / ETAT SANTE / QTE / FAMILLE / MARQUE / MODELE / DATE MES

**Logique vétusté** :
```
age = 2026 - date_mis_en_service
duree_vie_restante = sypemi_reference_annees - age
criticite_pct = min(100, age / sypemi_reference_annees × 100)
```
Seuils badge : < 50 % → vert · 50-80 % → orange · ≥ 80 % → rouge

## 🚧 Ce qui reste à faire / handoff

### Priorité 1 — Lancer l'import réel depuis l'UI

L'utilisateur doit maintenant faire tourner le wizard une première fois pour valider les 71 mappings sites/bâtiments :

1. Aller sur `https://patrimoineaucarre.com/buildings/cvc-import`
2. Uploader `saas/CVC/listing materiels V2.xlsx`
3. Vérifier les suggestions automatiques (score ≥ 65 % → pré-sélectionné)
4. Corriger les cas problématiques (ambiguïtés dans les noms)
5. Cliquer "Importer"

### Priorité 2 — Améliorer le fuzzy match si nécessaire

Si trop de sites ne sont pas auto-matchés (score < 65 %), il faudra améliorer la stratégie :
- Extraire les mots-clés du nom de site (supprimer codes préfixes "VDS-BAM", "CCAS")
- Comparer les tokens plutôt que la chaîne entière

**Fichier à modifier** : `app/services/cvc.py::match_buildings_for_sites` et `_similarity`

### Côté utilisateur — Pending validations externes

- Valider le premier import et signaler si le mapping automatique est suffisant ou s'il faut affiner le seuil de 65 %

## 📝 Notes & décisions

- **ADR non créé** : la décision de séparer `cvc_inventory_items` de `BuildingEquipment` est documentée dans le module [[Modules/Gestion-technique]] mais ne mérite pas d'ADR dédié (choix pragmatique sans impact futur structurant).
- **Double container** sur le VPS : `infra-*` = production active (Caddy exposé sur 80/443) ; `saas-*` = anciens containers non actifs depuis > 3 semaines. À supprimer proprement.
- **Fuzzy match famille↔SYPEMI** : seuil à 50 %. Les familles très génériques ("Autre à qualifier") ne seront pas matchées — intentionnel.

## 🔁 Pour la prochaine IA — entrée en matière

```
J'ai lu :
- docs/00-Index.md
- docs/07-Environnement-poste-entreprise.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-05-20 — Import inventaire CVC terrain (PO2-CVC-001)

Je sais que le poste utilisateur est verrouille entreprise : je ne demanderai aucune installation locale.
Je comprends que PO2-CVC-001 est livré (migration 0016 en prod, wizard import opérationnel).
La prochaine étape immédiate est de valider le mapping sites/bâtiments lors du premier import réel.
Après ça, les chantiers P1 ouverts sont : PO2-GT-001 (scinder CVC/Enveloppe), PO2-METER-001 (rattachement compteurs), PO2-OCC-001 (import occupation).

OK pour partir là-dessus ?
```
