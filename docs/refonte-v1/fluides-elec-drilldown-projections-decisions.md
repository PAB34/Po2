# Fluides / électricité — graphique kWh/DJU, fiche compteur, projections (décisions)

> Statut : diagnostic terminé, 3 corrections livrées, 2 arbitrages ouverts
> Date : 2026-07-22
> Code : `saas/frontend/src/features/fluids/FluidsElecDetailV1.tsx`,
> `FluidsPortfolioPageV1.tsx`, `saas/backend/app/services/energie.py`

## 1. Graphique « Ratio kWh/DJU » — pourquoi seule la cible s'affiche

### Constat vérifié en prod (2026-07-22)

```
saison été 2026 : 1 mois exploitable / 5
Mai 2026  → low_dju    (17,7 DJU froid < seuil 20)
Jun 2026  → displayed  (77,3 DJU, ratio 6141)
Jul 2026  → exclu : mois en cours
Aoû, Sep  → à venir
```

### Cause A — la série courante se réduit à un point, et un point isolé n'était pas dessiné

Les deux `<Line>` étaient en `dot={false}`. Recharts ne trace un segment qu'entre deux
points : **une série d'un seul point ne dessine donc strictement rien**. La courbe bleue
existait dans le DOM (`d="M114.25,162.289Z"`) mais restait invisible.

Ce n'est pas un accident de données : en début de saison estivale, il y a *toujours*
1 à 2 mois exploitables. Le graphique était donc structurellement vide de mai à août
chaque année.

**Corrigé** : `dot` activé sur les deux séries + mention explicite sous le graphique
quand la saison en cours compte 0 ou 1 mois exploitable, avec les mois écartés et leur motif.

### Cause B — le filtre DJU laisse passer des mois qui produisent des ratios aberrants

Le seuil est de 20 DJU (`_DJU_SEASONAL_COOLING_MIN`). Or :

| Saison | Mois | DJU froid | Ratio kWh/DJU |
|---|---|---|---|
| 2023 | Jun | 54,5 | 8 573 |
| 2023 | Jul | 112,3 | 4 373 |
| 2023 | Aoû | 88,5 | 5 479 |
| **2023** | **Sep** | **20,1** | **25 066** |
| 2025 | Jun | 90,1 | 5 128 |
| 2026 | Jun | 77,3 | 6 141 |

Septembre 2023 passe le seuil de justesse (20,1) et produit un ratio **5× supérieur** à
tous les autres mois. C'est le seul septembre retenu de tout l'historique : il devient à
lui seul la « cible septembre » (25 066) et **écrase l'échelle Y de 0 à 26 000**, alors
que toutes les valeurs utiles tiennent entre 3 900 et 8 600.

Mécanisme : le ratio kWh/DJU rapporte *toute* la consommation du parc (dont un talon non
thermosensible important — éclairage public, bâtiments) à un DJU froid faible. Quand le
DJU tend vers zéro, le ratio diverge. Le seuil de 20 est trop bas pour l'empêcher.

**Non corrigé — arbitrage nécessaire** (voir §4, question 1).

## 2. Fiche compteur au clic — fait

Une fiche compteur complète existait déjà : route `/energie/:prmId`, servie par 8
endpoints (préconisation, puissance max, courbe de charge, profil annuel, conso
journalière, performance DJU, DJU saisonnier).

Le besoin ne demandait donc **aucune nouvelle page** : les lignes du tableau « Tous les
compteurs » pointent désormais vers cette fiche.

Choix d'implémentation : `onClick` sur la ligne (toute la surface cliquable à la souris)
**et** un vrai `<Link>` sur la colonne Nom — ce dernier porte l'accès clavier et permet
l'ouverture en nouvel onglet, qu'un `onClick` seul aurait supprimés.

## 3. Projections +5 / +10 ans

### Électricité — pourquoi « — » aujourd'hui

`_project_price()` renvoie `None` dès que l'historique compte moins de 2 points. Or la
base ne contient **qu'une seule année de factures électricité** :

```
2026 : 228 factures, 4 515 523 kWh, 0,22031 €/kWh TTC
```

Une régression linéaire sur un point n'a pas de sens : le « — » est donc un comportement
correct, mais il n'était accompagné d'aucune explication et se lisait comme un bug.

**Corrigé** : le motif est désormais affiché sous les deux lignes de projection.
**La levée du blocage demande un arbitrage** (voir §4, question 2).

### Gaz TotalEnergies — champs ajoutés, volontairement vides

Les lignes « Projection +5 ans » et « Projection +10 ans » ont été ajoutées au bloc gaz,
au même format que l'électricité, et affichent « — » : le moteur de projection prix gaz
n'existe pas encore. Demande explicite du 2026-07-22.

## 4. Arbitrages ouverts

1. **Seuil DJU froid** — comment neutraliser les mois à faible DJU qui font diverger le
   ratio ? Options : relever le seuil (à 50, on perd tout septembre) ; retirer le talon
   non thermosensible avant de diviser (plus juste, plus lourd) ; borner/écarter les
   valeurs aberrantes. Impact : la cible septembre et l'échelle du graphique.
2. **Projection prix électricité** — trois voies : importer les factures 2024/2025 pour
   obtenir une vraie tendance observée ; brancher sur la trajectoire BPU (un moteur de
   projection +5/+10 ans existe déjà dans `EnergieBpuPage`) ; ou retenir une hypothèse
   d'évolution explicite et paramétrable (% par an).
