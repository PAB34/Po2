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

**Corrigé (arbitrage du 2026-07-22 : retirer le talon).** Le talon est estimé par moindres
carrés sur `kwh = base + a·DJU_chaud + b·DJU_froid`, et le ratio ne porte plus que sur
`kwh − talon`. Repli sur l'ancien comportement si l'historique fait moins de 12 mois ou si
le système est mal conditionné.

Résultat constaté en prod après déploiement — **talon = 413 659 kWh/mois** :

| Saison | Avant | Après |
|---|---|---|
| Été, mois à DJU significatifs | 3 933 → 8 581 | **537 → 983** |
| Cible juin / juillet / août | ~5 000-6 000 | **654 / 731 / 699** |
| Septembre 2023 (20,1 DJU) | 25 066 | **4 486** |

L'échelle Y passe de 26 000 à ~4 500 : les valeurs utiles, jusqu'ici écrasées en bas du
graphique, sont enfin lisibles.

**Limite résiduelle assumée** : septembre reste un point haut (4 486 contre ~700). Le
retrait du talon suppose une base constante sur l'année, alors qu'une partie de la
consommation non thermosensible est elle-même saisonnière (l'éclairage public remonte en
septembre quand les jours raccourcissent). Même constat, atténué, sur octobre côté hiver
(2 719 et 2 467 les deux premières saisons, contre ~1 150 la dernière). Traiter cette
part demanderait d'ajouter une variable de durée du jour au modèle.

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

## 4. Projection prix électricité via le BPU — **bloqué, ne pas livrer en l'état**

Arbitrage du 2026-07-22 : brancher la projection sur la trajectoire BPU. Vérification
faite avant implémentation, **le résultat est inexploitable**.

Historique BPU disponible (moyenne toutes composantes, €/MWh) :

| 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| 63,5 | 184,6 | 290,4 | 133,6 | 97,9 | 87,1 |

Cette série est dominée par la crise énergétique 2022-2023 : elle monte à 290 puis
redescend à 87. Une régression linéaire dessus donne :

| Fenêtre | Pente | +5 ans | +10 ans |
|---|---|---|---|
| 2021-2026 (tout) | −8,5 €/MWh/an | 78,8 (**−35 %**) | 36,1 (**−70 %**) |
| 2024-2026 (post-crise) | −23,2 €/MWh/an | **−33,3 €/MWh** | **−149,6 €/MWh** |

Sur l'historique complet, on annoncerait une **baisse de 70 % de la facture d'électricité
à 10 ans**. Sur la seule période post-crise, on obtient un **prix négatif dès +5 ans**.

Le modèle existant de `EnergieBpuPage` masque le problème avec un `Math.max(0, …)` : il
affiche 0 au lieu d'un prix négatif — le chiffre reste faux, il est seulement moins visible.

Une extrapolation linéaire ne convient pas à une série qui contient un choc de marché.
Le brancher tel quel produirait un chiffre faux dans un document destiné aux finances.

### Profondeur d'historique réellement disponible (mesuré le 2026-07-23)

La voie 1 ci-dessous suppose qu'un historique 2024/2025 existe quelque part. Relevé en
base de prod (`energy_invoice_sites`, € TTC par mois de début de période) :

| 2024-04 | 2024-07 | 2025-08 | 2025-09 | 2025-10 | 2025-11 | 2025-12 | 2026-01 → 06 |
|---|---|---|---|---|---|---|---|
| 6 027 | −173 | −18 | 244 | 5 590 | **72 962** | **70 072** | **999 791** |

La facturation ne devient significative qu'à partir de **novembre 2025** : avant, il
s'agit de quelques lignes isolées (1 à 2 PRM), pas d'un historique. La base couvre donc
**8 mois**, pas deux années. Les rares lignes 2024 ne constituent pas un point de
comparaison exploitable.

Conséquence : la voie 1 ne consiste pas à « importer » un historique déjà là, mais à
**l'obtenir du fournisseur** (factures 2024 et 2025 complètes) — c'est une demande
externe, pas une tâche technique. Tant qu'elle n'a pas abouti, aucune tendance de prix
observé n'est calculable, quelle que soit la méthode.

**Reste à arbitrer** — trois voies possibles :
1. importer les factures 2024/2025 pour obtenir une vraie tendance de prix observé
   (suppose de les obtenir d'abord du fournisseur, voir ci-dessus) ;
2. retenir une hypothèse d'évolution explicite et paramétrable (% par an), assumée comme
   hypothèse et non présentée comme une prévision ;
3. conserver le BPU mais en écartant la période de crise et en bornant la projection —
   suppose de décider ce qui est « atypique », donc un choix de méthode à documenter.

## 5. Suite

- **Éclairage public / saisonnalité du talon** : ajouter une variable de durée du jour
  pour lisser septembre et octobre (voir limite résiduelle §1).
- **Projection prix électricité** : voir §4.
