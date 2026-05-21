# 2026-05-21 — Filtres titulaire et problemes factures

## Objectif

Rendre la revue des factures ENGIE plus exploitable depuis `/energie/factures` apres l'import du lot historique.

## Besoin utilisateur

- Exploiter `Titulaire du contrat` pour distinguer les factures portees par la Ville et celles portees par l'Agglomeration.
- Replier par defaut `Lots d'import` afin que les dizaines de PDF importes ne polluent pas l'ecran de revue.
- Eviter d'ouvrir chaque detail facture pour retrouver les categories et types de problemes du controle.

## Livraison

- `EnergyInvoiceImport` expose le titulaire du contrat deja extrait par le parser ENGIE.
- La liste facture affiche et filtre le titulaire.
- La classification des problemes est partagee entre la page detail et la page liste.
- `/energie/factures` permet de filtrer par categorie de probleme et type/code de probleme.
- Les tags de controle apparaissent directement dans le tableau principal.
- `Lots d'import` devient un volet ferme par defaut.

## Validation

- `python -m compileall` passe sur le backend et le test facture ajoute.
- `git diff --check` passe.
- `pytest` n'est pas disponible sur le poste ni dans le runtime Python embarque.
- `npm` n'est pas disponible localement pour lancer le build frontend.

## Suivi

- Commit pousse sur `main` : `fe84fca` (`feat(billing): add invoice holder and issue filters`).
- Backlog mis a jour sur `PO2-FACT-001`.
- Module mis a jour : [[Modules/Energie-Facturation]].
- Session parente : [[Sessions/2026-05-21 — Historique factures ENGIE]].

## Suite recommandee

Qualifier les 83 PDF en production, verifier les valeurs reelles de titulaire puis choisir si l'application doit conserver seulement le libelle source ou ajouter un champ analytique normalise `ville` / `agglomeration` / `autre`.

## Extension rapport fournisseur

- Ajout d'un bouton `Editer rapport` dans le bloc de filtres de `/energie/factures`.
- Le rapport reprend uniquement les factures filtrees qui portent des points de controle a clarifier.
- Les filtres categorie/type de probleme pilotent aussi les points inclus dans le rapport.
- Le texte destinataire, emetteur, objet, contexte et demande reste editable avant impression.
- La sortie fournisseur synthétise les points a clarifier, les filtres retenus, le TTC selectionne et les factures concernees ; elle reste prudente sur la conclusion et demande une explication ou une correction.
