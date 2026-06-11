# 2026-06-11 - Reprise collecte ENEDIS synchrone

> IA : Codex GPT-5
> Duree approximative : 1h
> Precedente session : `[[Sessions/2026-06-09 - Analyse et scaffolding API GRDF ADICT]]`

## Objectif de la session

Reprendre le chantier `PO2-ENEDIS-001` malgre le blocage externe de l'API asynchrone ENEDIS.
Question initiale : verifier si le moteur synchrone existe encore, puis rendre sa reprise exploitable
dans `/energie` sans casser les donnees historiques deja collectees.

## Ce qui a ete fait

### Chantier - Collecte ENEDIS synchrone de secours

- Confirme que le moteur synchrone existe toujours :
  `app/services/enedis_sync.py`, routes `/api/energie/sync/*`, helpers front dans `lib/api.ts`.
- Backend :
  - ajout de `prm_limit` sur conso journaliere et puissance max ;
  - ajout de `prm_limit` et `history_days` sur courbe de charge ;
  - le mode limite/test n'avance pas les fichiers d'etat globaux `enedis_*_state.json` ;
  - la CDC synchrone n'ajoute plus les points deja presents `(usage_point_id, datetime)`.
- Frontend :
  - panneau `/energie` restructure en "Collecte de donnees ENEDIS" ;
  - etape prerequis : referentiel contractuel ENEDIS + DJU ;
  - etape collecte synchrone : conso, P max, CDC, chacune avec action incrementale, backfill et test 5 PRM ;
  - panneau async renomme "Collecte asynchrone ENEDIS / FTP".
- Documentation mise a jour : `[[04-Etat-actuel-du-dev]]`, `[[Backlog]]`, `[[Modules/Energie-Consommation]]`.

Fichiers principaux touches :

- `saas/backend/app/services/enedis_sync.py`
- `saas/backend/app/api/routes/enedis_sync.py`
- `saas/frontend/src/lib/api.ts`
- `saas/frontend/src/pages/EnergiePage.tsx`
- `saas/frontend/src/components/EnergieAsyncJobsPanel.tsx`
- `saas/frontend/src/styles.css`

## Validation

- Backend : `python -m compileall app` OK depuis `saas/backend`.
- Frontend : `npm run build` non executable localement (`npm` absent, `node_modules` absent).
  Validation frontend a faire via CI/GitHub Actions ou conteneur frontend.

## Ce qui reste a faire / handoff

### Priorite 1 - Tester en prod ou environnement connecte ENEDIS

- **Objectif** : lancer les boutons "Tester 5 PRM" sur `/energie`.
- **Ordre conseille** :
  1. "Mettre a jour les contrats" si le perimetre PRM a change ;
  2. "Tester 5 PRM" sur consommations journalieres (30 jours) ;
  3. "Tester 5 PRM" sur puissances max (30 jours) ;
  4. "Tester 5 PRM / 7j" sur courbes de charge.
- **A verifier** : statuts `success/error`, logs, lignes ajoutees, puis couverture dans la barre "Couverture des donnees".

### Priorite 2 - Reprise large si le test est sain

- Conso et P max : lancer "Mise a jour incrementale" pour reprendre depuis `last_sync_date`.
- Si besoin historique complet : "Backfill 3 ans" est idempotent par PRM/date pour conso et P max.
- CDC : preferer incrementale ; le backfill CDC complet reste couteux en quotas car 1 appel par PRM et par fenetre de 7 jours.

### Cote utilisateur - Pending externe

- Le blocage async ENEDIS reste externe : dossiers fantomes / support ENEDIS / publication FTP.
- Ne pas afficher de secret ENEDIS/FTP en conversation ; utiliser uniquement les variables serveur.

## Notes & decisions

- Decision de produit temporaire : l'async reste le chemin cible pour les backfills profonds, mais le sync redevient
  un mode de secours visible pour avancer sur factures, preconisations et controles de consommation.
- Le mode test 5 PRM ecrit les lignes collectees mais n'avance pas l'etat global, pour eviter de bloquer ensuite
  la reprise complete du parc.

## Pour la prochaine IA - entree en matiere

```
J'ai lu :
- docs/00-Index.md
- docs/07-Environnement-poste-entreprise.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-06-11 - Reprise collecte ENEDIS synchrone.md

Je sais que le poste utilisateur est verrouille entreprise : je ne demanderai aucune installation locale.
Je comprends que la priorite 1 est : deployer/valider l'UI ENEDIS puis lancer les tests 5 PRM.
Je propose de commencer par : verifier le build frontend via CI, puis tester les trois collectes synchrones limitees.

OK pour partir la-dessus ?
```
