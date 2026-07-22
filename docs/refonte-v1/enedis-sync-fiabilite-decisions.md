# ENEDIS — fiabilité de la collecte journalière (décisions)

> Statut : diagnostic terminé, corrections à valider
> Date : 2026-07-22
> Code concerné : `saas/backend/app/services/enedis_sync.py`, `saas/backend/app/core/scheduler.py`

## 1. Constat sur la prod (vérifié, pas déduit)

Relevés le 2026-07-22 sur `/home/ubuntu/Po2/saas/energie/output/` :

| Élément | Valeur constatée |
|---|---|
| `enedis_sync_state.json` → `last_sync_date` | **2026-07-16** |
| Date max réelle dans `enedis_data.csv` | **2026-07-15** |
| Couverture totale | 2023-05-01 → 2026-07-15 (1171 jours) |
| Jours manquants dans la plage | **1 seul : `2026-06-10`** |
| Dernier diagnostic de sync | généré le 2026-07-17, fenêtre 2026-06-11 → 2026-07-16 |
| Outcomes du dernier run | 370 `ok_data`, 138 `invalid_request`, 40 `access_not_subscribed`, 1 `not_found` |

Le doute initial « plus rien depuis avril » est **infirmé** : la série est complète
d'avril à mi-juillet, à un jour près.

## 2. Cause racine (mécanisme démontré)

`run_daily_consumption_sync()` calcule `end_d = today - 1 jour` (hypothèse « ENEDIS J-1 »),
puis, en fin de run réussi, exécute `_save_persistent_state(end_str)` avec la date
**demandée**, sans jamais vérifier la date **réellement reçue**.

Or ENEDIS publie avec un décalage réel plus proche de J-2 : la requête jusqu'à J-1
renvoie des données qui s'arrêtent à J-2. Le run suivant repart de `last_sync + 1`,
donc **au-delà** du dernier jour réellement collecté.

**Conséquence : chaque exécution de la sync perd définitivement exactement un jour.**

Vérification par les faits — les deux trous observés correspondent aux deux derniers runs :

- run du 2026-06-11 → `end_d = 2026-06-10`, données reçues jusqu'au 06-09 → **trou 2026-06-10**
- run du 2026-07-17 → `end_d = 2026-07-16`, données reçues jusqu'au 07-15 → **trou 2026-07-16** (à venir)

Le trou n'est pas aléatoire ni lié à une panne ENEDIS : il est **systématique et
reproductible**, un par run.

## 3. Cause racine secondaire

`run_daily_consumption_sync` **n'est planifié nulle part**. `start_scheduler()`
n'enregistre que `enedis_async_poll`, `enedis_customer_sync`, `grdf_*` et
`pronostics_score_sync`. La collecte de consommation journalière est donc
**100 % manuelle** (bouton / appel API).

C'est ce qui explique l'absence de données depuis le 2026-07-16 : personne n'a
relancé la sync depuis le 17/07.

Ces deux causes se combinent de façon perverse : la sync manuelle est rare, donc
chaque lancement crée un trou isolé au milieu d'une longue plage, difficile à
repérer à l'œil.

## 4. Décisions

### D1 — L'état ne dépasse jamais la donnée réelle *(retenu)*

`_save_persistent_state()` reçoit `min(date demandée, date max réellement collectée)`.
Si aucune ligne n'est collectée, l'état **n'avance pas du tout**.

**Pourquoi c'est le bon niveau de correction** : ça rend le système *auto-réparateur*.
Le run suivant repart du lendemain de la donnée réelle et redemande donc
automatiquement les jours restés vides, jusqu'à ce qu'ENEDIS les publie. Aucun
réglage « J-2 » en dur n'est nécessaire — le décalage de publication réel est
absorbé quel qu'il soit, y compris s'il change.

Alternative écartée : forcer `end_d = today - 2`. Ça déplace le problème d'un jour
au lieu de le supprimer, et ça casse dès qu'ENEDIS publie plus vite ou plus lentement.

### D2 — Le statut dit la vérité *(retenu)*

`get_sync_status()` expose en plus :

- `data_max_date` — date max réellement présente dans `enedis_data.csv`
- `missing_days` — nombre de jours manquants dans la plage couverte
- `missing_days_sample` — jusqu'à 10 dates manquantes, pour affichage

L'écran de synchro ne peut plus afficher une date d'avance sur la réalité.

### D3 — Rattrapage des trous existants *(retenu)*

D1 ne répare que le futur. Le trou `2026-06-10` est *intérieur* à la plage : il ne
sera jamais redemandé par une sync incrémentale. Un rattrapage ciblé est nécessaire
(voir §5).

### D4 — Planification quotidienne *(retenu, arbitré le 2026-07-22)*

Job APScheduler quotidien sur `run_daily_consumption_sync`, piloté par
`enedis_daily_sync_enabled` (défaut `True`) et `enedis_daily_sync_interval_hours`
(défaut 24).

Coût quota : ≈ 550 appels/jour pour un plafond de 950/h — large marge. La garde
`is_sync_running()` évite le recouvrement, et une fenêtre déjà à jour sort sans
aucun appel API.

Combiné à D1, le passage quotidien redemande automatiquement les jours qu'ENEDIS
n'avait pas encore publiés la veille : le décalage de publication ne crée plus de trou.

## 5. Reste à faire

1. **Rattrapage du 2026-06-10** *(arbitré : à faire)* — D1 ne répare que les trous
   en bord de fenêtre. Le 2026-06-10 est intérieur à la plage : il faut un backfill
   ciblé, à lancer une fois le correctif déployé.
2. **138 PRM en `invalid_request`** *(arbitré : à diagnostiquer)* — un quart du parc
   (138 sur 549) ne remonte rien. Sujet distinct de la fiabilité de la sync, mais qui
   pèse bien plus lourd sur la qualité des données que le trou d'un jour. Piste
   probable : PRM résiliés, ou dates de contrat hors période demandée.
