# Vision & Utilisateur

## Le produit
**Po2 / PatrimoineOp** est une plateforme SaaS de pilotage du patrimoine immobilier des collectivités territoriales. Le périmètre cible est **multi-tenant par ville** (`city_id` partout) et la première ville déployée est Sète (commune française, ≈ 44 000 habitants).

L'utilisateur final est un **chargé de patrimoine / responsable bâtiments / DGS** d'une mairie ou d'une intercommunalité, qui doit :

1. **Connaître son patrimoine** (combien de bâtiments, où, en propriété ou en location, dans quel état)
2. **Suivre les fluides** consommés par ces bâtiments (élec, gaz, eau) compteur par compteur
3. **Auditer les factures** envoyées par ses fournisseurs (ENGIE, DALKIA, TOTAL, SUEZ)
4. **Préconiser des actions** (renégocier la puissance souscrite, planifier le remplacement d'équipements vétustes, comparer les prix BPU dans le temps)

## Le contexte métier

### Sources de données externes
| Source | Type | Utilisation |
|---|---|---|
| DGFIP / MAJIC | Excel (fichiers fiscaux) | Recensement propriétaire des bâtiments |
| IGN | Open data | Géométrie / hauteurs / surfaces des bâtiments |
| OSM | Open data | Compléments (catégories, noms) |
| ENEDIS | API OAuth2 | Consommations électriques, courbes de charge, P max |
| GRDF | API | Consommations gaz (pas encore intégrée) |
| SUEZ | PDF / Excel | Conso eau + factures |
| Hérault Énergies | PDF (BPU) | Bordereaux de Prix Unitaires d'achat groupé d'électricité |
| Météo / DJU | API ou fichier | Degrés-Jour Unifiés pour corriger la conso de la température |

### Spécificités réglementaires françaises
- **TURPE** (Tarif d'Utilisation des Réseaux Publics d'Électricité) : segmentation par tension et plage horaire (HPH, HCH, HPE, HCE, Pointe, Base) — utilisée pour la facturation et l'analyse
- **Marchés subséquents** : les collectivités achètent l'électricité via des accords-cadres pluriannuels avec une centrale d'achat (Hérault Énergies pour les communes héraultaises) ; les prix sont fixés dans des BPUs avec parfois plusieurs avenants par an
- **CEE / Garanties d'Origine** : composantes de prix réglementaires à isoler dans les BPU

## Différenciateurs visés
- Couplage automatique **conso × DJU × occupation** (pour identifier les surchauffes et fuites)
- Auditabilité des factures (réconciliation prix BPU vs prix facturé pour chaque PRM)
- Roadmap "Inventaire technique" : tracker chaque équipement CVC + matériau enveloppe avec sa durée de vie résiduelle (référentiel SYPEMI 310 lignes)

## Contraintes utilisateur
- L'utilisateur final n'est **pas un ingénieur** : l'UI doit être lisible (badges colorés, tooltips, légendes systématiques)
- Environnement entreprise restreint côté admin (pas d'install logiciel libre, pas d'accès admin local)
- Développement principalement piloté par **PAB34** (l'utilisateur du repo) avec assistance IA — d'où l'importance de ce vault de coordination

## Profils cibles - reorientation 2026-06-22

Le profil principal actuel reste le **pilote maintenance & energie**, utilisateur transversal et administrateur de fait. Le produit doit cependant etre prepare pour des profils cumulatifs : analyste energie, responsable maintenance/patrimoine technique, controleur finances, direction, gestionnaire/referent de site et administrateur fonctionnel. Un profil prestataire externe reste futur.

Les profils pilotent l'accueil, le vocabulaire et la densite ; les permissions pilotent les actions ; le perimetre limite les villes, services, marches ou sites. Voir [[22-Developpement-deux-pistes-et-profils-utilisateurs]].
