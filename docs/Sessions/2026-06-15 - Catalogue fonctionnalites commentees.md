# 2026-06-15 - Catalogue fonctionnalites commentees

## Contexte

L'utilisateur veut comprendre l'utilite de chaque fonctionnalite deja developpee avant de decider la reaffectation
des routes, prefixes et endpoints dans la future plateforme.

Les documents de depart sont :

- `docs/08-Inventaire-fonctionnalites-developpees-2026-06-02.md`
- `docs/12-Plan-plateforme-cible-et-tri-endpoints.md`
- `docs/13-Matrice-routes-fonctionnalites-refonte-api.md`

## Travail realise

- Ajout de `docs/14-Catalogue-fonctionnalites-commentees-et-reaffectation.md`.
- Le document decrit les blocs fonctionnels developpes par utilite metier, decision aidee, utilisateurs, code/routes,
  reaffectation cible et niveau de confiance.
- Mise a jour de `docs/00-Index.md`.
- Mise a jour de `docs/04-Etat-actuel-du-dev.md`.
- Ajout des colonnes `Statut validation` et `Preuve` a la matrice generee `docs/13-Matrice-routes-fonctionnalites-refonte-api.md`.
- Mise a jour du diagramme `docs/api-cartographie/index.html` pour afficher le statut de validation et la preuve.
- Ajout de `docs/15-Validation-P0-factures-finance.md` pour le premier perimetre facture -> controle -> decision -> export finance.

## Points importants

- La matrice `13` reste technique et generee.
- Le catalogue `14` devient la couche humaine/metier au-dessus de la matrice.
- La reaffectation proposee ne doit pas provoquer de renommage massif immediat des endpoints.
- Le parcours P0 reste : facture fournisseur energie -> controle -> decision -> matrice comptable -> export XLSX finance.
- Les echecs de tests CPE/DJU/codification observes localement restent a traiter avant migration.
- Tests cibles energie/factures executes : `test_energie_accounting.py`, `test_engie_xlsx_parser.py`, `test_invoice_batches.py`,
  `test_invoice_analysis_bpu_mapping.py`, `test_billing_bpu_sync.py` = 21 tests OK.
- La decision facture energie reste seulement `import app OK` : test service/HTTP a creer.

## Handoff suivant

Prochaine etape recommandee : ajouter les tests HTTP du parcours P0 energie, puis corriger les tests CPE rouges
avant validation front/prod.
