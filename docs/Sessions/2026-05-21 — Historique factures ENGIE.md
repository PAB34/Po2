# 2026-05-21 — Historique factures ENGIE

## Objectif

Faire passer le module existant `/energie/factures` d'un controle facture par facture a une integration pilotable d'un historique important de PDF ENGIE, sans creer de module parallele avant la future API ENGIE.

## Point de depart verifie

- Dossier source local : `saas/energie/ENGIE/FACTURES`
- Volume constate : 83 PDF ENGIE.
- `/energie/factures` contient deja l'import manuel multi-fichiers, la liste des factures, les KPI de revue, les controles et les decisions.
- `/energie/factures/:invoiceImportId` contient deja l'identite facture, le resume simple, les PRM/FIC, les lignes extraites et le commentaire de decision.
- Le backend conserve aujourd'hui le detail dans `analysis_result_json` et `control_report_json` sur `EnergyInvoiceImport`.

## Decisions retenues

- V1 limitee aux PDF ENGIE electricite du lot reel.
- L'UI existante facture reste le point d'entree utilisateur.
- Le lot historique doit etre trace par un objet d'import persistant avec bilan, doublons et erreurs.
- Les donnees extraites doivent etre projetees vers les tables normalisees deja ciblees par `saas/specs/04_mapping_facture_engie.md`.
- L'API ENGIE future remplacera la source PDF, pas le moteur de normalisation, de controle ni de decision.

## Plan de qualification

1. Auditer un echantillon representatif du lot avec le parser ENGIE actuel.
2. Mesurer les parses complets, parses partiels, echecs et variantes de mise en page.
3. Corriger seulement les ecarts reveles par les PDF reels.
4. Ajouter import lot, normalisation et historique de lot.
5. Qualifier ensuite le lot complet des 83 PDF dans le flux applicatif.

## Audit parser local

Execution du parser ENGIE actuel via le runtime Python Codex sur les 83 PDF locaux :

- 83 PDF parses, 0 echec, 0 warning de parsing ;
- numero facture, total TTC et periode extraits sur 83/83 ;
- 1 936 pages PDF analysees ;
- 582 FIC detectees ;
- 407 PRM detectes dans les factures ;
- plus gros PDF qualifie : `130000078102.pdf`, 104 pages, 37 FIC, 20 PRM.

Conclusion : la V1 doit surtout industrialiser l'import et la persistance analytique. Les corrections parser restent ciblees sur les anomalies de controle qui apparaitront apres import applicatif complet.

## Criteres de reussite

- Les imports unitaires existants restent fonctionnels.
- Un depot multi-PDF ou ZIP ne s'arrete pas au premier fichier en erreur.
- Le bilan du lot permet de retrouver les factures importees, les doublons et les echecs.
- Les donnees facture deviennent requetables au niveau facture, PRM/site, FIC/periode, lignes, releves et controles.
- Les controles BPU, TURPE, taxes, periodes, ENEDIS et puissance restent visibles dans le detail facture.

## Mise en oeuvre du jour

- Ajout d'un lot d'import persistant avec ses items, compteurs, liens vers les imports facture et endpoints `/api/billing/invoices/batches`.
- Ajout des tables normalisees facture, site/PRM, periode/FIC, ligne, releve/puissance et controle ; `EnergyInvoiceImport` reste la preuve documentaire et la compatibilite JSON.
- La relance d'analyse remplace la projection normalisee ; une relance en echec supprime la projection derivee devenue obsolete sans toucher a la decision utilisateur.
- `/energie/factures` accepte maintenant un lot PDF ou ZIP, expose l'historique et le detail des lots, puis propose recherche, filtres et acces rapides pour la revue.
- Le depot unitaire historique reste disponible cote API par `/api/billing/invoices/imports`.

## Extension de revue livree

- Le parser ENGIE lisait deja `Titulaire du contrat` ; la liste des imports expose maintenant cette valeur pour filtrer les factures Ville / Agglomeration depuis `/energie/factures`.
- La page principale remonte les familles et codes de problemes jusque-la visibles surtout dans le detail facture, puis permet de filtrer par categorie et type de probleme.
- Le volet `Lots d'import` est replie par defaut afin que les 83 PDF du lot historique ne prennent pas la place de la liste a traiter.
- Commit pousse sur `main` : `fe84fca` (`feat(billing): add invoice holder and issue filters`).
- Prochaine verification metier : importer/relire le lot reel en production et confirmer les libelles titulaire attendus avant de decider si une normalisation `ville` / `agglomeration` doit etre ajoutee.

## Validation de la session

- `python -m compileall` passe sur les modeles, services, schemas, routes, migration et tests ajoutes.
- `git diff --check` passe ; seuls les avertissements CRLF du worktree Windows restent affiches.
- Les tests `pytest` ne sont pas executables dans ce shell : `pytest` est absent et le runtime Python Codex ne fournit pas le module `pytest`.
- Le build frontend n'est pas executable dans ce shell : `npm` n'est pas disponible dans le PATH et `saas/frontend/node_modules` n'est pas installe.
- Les tests ajoutes couvrent le bilan de lot et le traitement ZIP PDF/non-PDF quand l'environnement backend complet rejouera `pytest`.

## Handoff API ENGIE

La future connexion ENGIE devra alimenter les memes tables normalisees et la meme interface de revue. Le chantier PDF sert de source initiale et de banc de qualification metier pendant l'attente des acces API.
