# 2026-06-08 - CVC cockpit fluides F-Gaz ESP

## Contexte

Demande utilisateur : revoir `/buildings/cvc-fluides` pour en faire une vraie centrale de pilotage, en s'inspirant du classeur :

- `saas/energie/CVC/modele_GMAO_suivi_fluides_collectivite_simple.xlsx`

Lecture initiale :

- `docs/00-Index.md`
- `docs/Backlog.md`
- `docs/04-Etat-actuel-du-dev.md`

## Analyse du classeur

Le classeur contient 8 onglets structurants :

- `00_Tableau_Bord` : KPI conformite fluides / ESP ;
- `01_Pilotage_FGaz` : registre F-Gaz avec calcul tEqCO2, statut, frequence, echeance, priorite, preuve ;
- `02_Plan_Action` : actions initiales pour GMAO ;
- `03_Journal_Interventions` : historique controles, fuites, recharges, recuperations, Cerfa ;
- `04_Signaux_ESP` : suivi ESP/DESP separe ;
- `05_Parametres_Regles` : regles simplifiees et sources ;
- `06_Export_GMAO` : colonnes minimales export ;
- `Mode_Emploi` : workflow collectivité / titulaire.

Decision produit : ne pas embarquer le fichier Excel tel quel, mais transformer sa logique en modele applicatif vivant.

## Travaux realises

- Migration additive `0048_add_cvc_refrigerant_pilotage_fields.py`.
- Extension `CvcRefrigerantItem` :
  - detection permanente ;
  - dernier controle etancheite ;
  - prochaine echeance ;
  - titulaire ;
  - responsable collectivite ;
  - statut action ;
  - commentaire GMAO.
- Calculs serveur F-Gaz :
  - statut selon seuils 5 / 50 / 500 t eq. CO2 ;
  - frequence 12 / 6 / 3 mois, doublee si detection permanente ;
  - conformite : donnees a completer, dernier controle a demander, en retard, a programmer, OK ;
  - action prioritaire ;
  - preuve attendue ;
  - priorite.
- Nouvel endpoint :
  - `GET /api/cvc/refrigerants/dashboard`
- Refondue `/buildings/cvc-fluides` en 5 onglets :
  - Cockpit ;
  - Registre F-Gaz ;
  - Actions ;
  - ESP/DESP ;
  - Import.
- Le PATCH d'une ligne fluide est devenu partiel : modifier un statut ou une date ne detache plus l'equipement CVC.

## Validation

- `python -m compileall app` OK depuis `saas/backend`.
- `git diff --check` OK, seulement avertissements CRLF Windows.
- `npm run build` non execute : `npm` et `node_modules` absents du poste local.

## Handoff suivant

1. Lancer la CI frontend pour valider TypeScript/Vite.
2. Tester en prod ou environnement conteneur apres migration Alembic `0048`.
3. Ajouter l'etape suivante si le cockpit est valide :
   - table dediee `cvc_refrigerant_interventions` ;
   - upload/lien de preuves ;
   - export XLSX/CSV GMAO reprenant `06_Export_GMAO`.
