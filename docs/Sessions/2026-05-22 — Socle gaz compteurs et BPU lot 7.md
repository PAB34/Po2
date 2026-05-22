# Session - Socle gaz compteurs et BPU lot 7

## Demande

Mettre en oeuvre les recommandations de cadrage gaz avec les elements disponibles : clarifier le role de GRDF, de TotalEnergies via HERAULT ENERGIE et du P1 DALKIA.

## Fait

- Ajout de `BuildingMeterLink` pour saisir un premier lien manuel batiment-compteur multi-fluides.
- Routes/API/UI fiche batiment pour lister, ajouter et supprimer ces rattachements.
- Ajout d'un import cible `app.scripts.import_bpu_gas_lot7` sur la feuille `Lot 7 - Gaz` du BPU 2026 HERAULT ENERGIE.
- Ajout des composantes BPU gaz `cee_precarite` et `cpb`, des profils gaz T1-T4 et de leur affichage timeline.
- Mise a jour du vault avec [[Modules/Energie-Gaz]], [[Modules/Energie-BPU]], [[Backlog]] et [[04-Etat-actuel-du-dev]].

## Limites

- Pas de donnees GRDF de test importees dans cette session.
- Le modele V1 porte une cle de repartition sur un lien batiment-compteur, mais l'ecran ne couvre pas encore un compteur partage entre plusieurs batiments.
- Aucun parser de facture gaz TotalEnergies n'est disponible pour l'instant.

## Handoff suivant

Prendre un petit echantillon de PCE gaz Ville et DALKIA, le rattacher aux batiments, puis definir le format d'import GRDF CSV/XLSX avant de demarrer l'API GRDF.
