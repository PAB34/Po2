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

## 5. Rattrapage du 2026-06-10 — fait

Backfill de 45 jours lancé en prod le 2026-07-22 (fenêtre 2026-06-07 → 2026-07-21).

Résultat vérifié après exécution :

```
data_min_date : 2023-05-01
data_max_date : 2026-07-20
missing_days  : 0
```

La série est désormais **continue, sans aucun trou**, du 2023-05-01 au 2026-07-20.

Ce run a aussi validé D1 en conditions réelles : la fenêtre demandait jusqu'au
2026-07-21, ENEDIS n'a publié que jusqu'au 2026-07-20, et l'état persistant s'est
bien arrêté à **2026-07-20**. Avec l'ancien code il aurait enregistré 2026-07-21 et
créé un nouveau trou.

## 6. PRM muets — diagnostic

> ⚠️ **Section périmée (2026-07-23).** Le comptage des outcomes ci-dessous reste
> exact, mais l'interprétation qui suit — « 138 identifiants inconnus d'ENEDIS » — est
> **fausse**. Vérification faite : ENEDIS renvoie une fiche contractuelle complète pour
> ces 138 points, et le référentiel local est un sous-ensemble strict du périmètre de
> consentement déclaré par ENEDIS. Diagnostic corrigé et causes réelles :
> `enedis-referentiel-prm-qualite-decisions.md`.

Sur 549 PRM du référentiel contractuel, **179 ne renvoient jamais rien** :

| Outcome | Nombre | Message ENEDIS |
|---|---|---|
| `ok_data` | 370 | — |
| `invalid_request` | 138 | `ADAM-ERR0155` — *Demande non recevable : point inexistant.* |
| `access_not_subscribed` | 40 | `ADAM-ERR0191` — *aucun service souscrit ACCES à la donnée pour la période demandée.* |
| `not_found` | 1 | — |

Constat déterminant : **aucun de ces 138 PRM n'a jamais produit la moindre ligne**
dans `enedis_data.csv`. Ce ne sont pas des points qui auraient cessé d'émettre —
ils n'ont jamais fonctionné.

Il ne s'agit donc pas d'un incident technique ni d'une régression, mais de
**deux problèmes de référentiel distincts** :

1. **138 points inconnus d'ENEDIS** (`ADAM-ERR0155`). Le référentiel contractuel
   contient des identifiants qu'ENEDIS ne reconnaît pas. À rapprocher de la source
   qui alimente `enedis_contracts.csv`.
2. **40 points sans droit d'accès** (`ADAM-ERR0191`). Le consentement / la
   souscription au service ACCES ne couvre pas ces points sur la période. Relève
   d'une démarche contractuelle auprès d'ENEDIS, pas du code.

Piste écartée : la corrélation avec le préfixe du PRM n'est pas concluante. Les
points en échec sont majoritairement en `50…` (79 sur 138) mais 11 PRM en `50…`
remontent normalement — le préfixe n'est donc pas un critère fiable.

Le classement a été affiné (`unknown_usage_point` distinct de `invalid_request`)
pour que le prochain diagnostic sépare directement les deux causes.

## 7. Reste à faire

> Repris et remplacé le 2026-07-23 — voir `enedis-referentiel-prm-qualite-decisions.md`.
> En résumé : il n'y a pas de source amont à corriger (le référentiel vient d'ENEDIS) ;
> 126 des 179 muets sont des points coupés ou des compteurs non communicants, donc
> normaux ; et le vrai gisement est à l'inverse **60 PRM facturés (464 829 € TTC, 40 %
> de la dépense) absents du référentiel**.

1. ~~**Origine des 138 points inconnus**~~ — sans objet : ces identifiants viennent
   du périmètre de consentement ENEDIS et sont valides.
2. **40 points sans droit d'accès** — démarche contractuelle ENEDIS à instruire.
   Toujours valable (groupe C du diagnostic corrigé, 42 881 € facturés).
