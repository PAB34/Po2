# Decisions - suite refonte Matrices + Factures

Date : 2026-06-25
Source : reponses utilisateur dans `docs/44-Questions-suite-refonte-matrices-factures.md`

## Lecture globale

Les reponses ne sont pas contradictoires. Elles indiquent une strategie en deux rails :

1. continuer a prototyper vite l'experience utilisateur, car cela aide a clarifier le produit ;
2. remettre en route un environnement API/base fiable, car les ecrans doivent ensuite etre confrontes aux vraies factures et aux vrais cas limites.

La bonne interpretation n'est donc pas "A ou B", mais :

- UX preview en continu pour aller vite ;
- backend local/staging en parallele pour raccorder aux donnees reelles ;
- pas de bascule brutale vers le frontend definitif tant que les flux metier critiques ne sont pas valides.

## Decisions retenues

### 1. Priorite immediate

Decision : mener deux actions paralleles.

- Continuer la maquette UX sans backend pour garder le rythme produit.
- Remettre le backend local/API en route pour tester les vraies donnees.

Impact : la prochaine tranche peut etre concue visuellement, mais chaque ecran devra rapidement etre confronte aux donnees reelles.

### 2. Export comptabilite XLSX

Decision : viser un export complet.

Nuance assistant : pour eviter un fichier impossible a remplir, il faudra probablement structurer le XLSX avec plusieurs onglets :

- un onglet "A completer" centre sur les colonnes utiles a la comptabilite ;
- un onglet "Details / controle" avec toutes les donnees techniques ;
- eventuellement un onglet "Aide" expliquant les colonnes et les valeurs attendues.

Interpretation : tu veux garder toutes les informations utiles, mais l'UX du fichier doit rester lisible.

### 3. Statuts factures

Decision : valider la liste de statuts proposee.

Statuts V1 retenus :

- Nouvelle
- Deja traitee
- Reimportee identique
- Reimportee modifiee
- A controler
- En litige fournisseur
- Validee comptabilite
- Exportee finance

Point d'attention : ces statuts doivent etre visibles dans l'interface comme un vrai workflow, pas seulement comme une colonne technique.

### 4. Decisions apres controle facture

Decision : valider les actions proposees.

Actions V1 retenues :

- Valider quand meme avec commentaire.
- Mettre en attente fournisseur.
- Generer un mail fournisseur.
- Corriger manuellement l'imputation.
- Demander correction de la matrice comptable.
- Exclure la facture du traitement courant.

Point d'attention : la decision doit toujours produire une trace explicable. La plateforme doit pouvoir dire pourquoi une facture a ete validee, bloquee, contestee ou exportee.

### 5. Fournisseurs V1

Decision : traiter prioritairement :

- DALKIA
- ENGIE
- EDF
- TotalEnergies

SUEZ et SPIE sont importants, mais passent apres ce premier noyau V1.

### 6. Role de la comptabilite

Decision : trajectoire progressive.

- V1 : la comptabilite complete un XLSX hors plateforme.
- Plus tard : acces plateforme limite pour lecture/ecriture ciblee.

Interpretation : le XLSX n'est pas un pis-aller, c'est une bonne premiere etape pour embarquer la comptabilite sans lui imposer tout de suite un nouvel outil.

### 7. Backend local / donnees reelles

Decision : remettre l'environnement complet en priorite.

Constat actuel :

- front React OK sur `http://127.0.0.1:5173` ;
- backend FastAPI absent sur `127.0.0.1:8000` ;
- Postgres local absent sur `5432` ;
- la route preview `/refonte-v1/matrices-preview` fonctionne sans backend ;
- la route reelle `/refonte-v1/matrices` necessite API + login + base.

Impact : pour avancer serieusement sur les donnees reelles, il faut restaurer un environnement backend local ou stabiliser l'usage du staging.

### 8. Niveau d'ambition UI

Decision : prototype visuel avance.

Tu ne veux pas un simple wireframe gris. La prochaine tranche doit deja donner une impression proche de l'interface definitive : claire, moderne, agreable, dynamique, mais sans sacrifier la logique metier.

## Prochaine etape recommandee

### Etape 1 - Stabiliser l'acces aux donnees

Objectif : ne plus etre bloque par l'erreur API locale.

Deux options :

- Option A : remettre le backend local + Postgres en route.
- Option B : utiliser staging comme source de donnees reelles, si c'est plus rapide.

Recommandation assistant : commencer par identifier comment l'environnement backend et la base etaient lances auparavant. Sans cela, on risque de multiplier les previews non raccordees.

### Etape 2 - Finaliser l'atelier Matrices V1

Objectif : obtenir un flux export/import XLSX comprehensible pour la comptabilite.

Fonctions a consolider :

- liste des tiers facturants ;
- selection d'une matrice/version ;
- export XLSX ;
- import retour compta ;
- preview des modifications ;
- creation d'une version brouillon ;
- activation controlee.

### Etape 3 - Construire Factures & decisions V1

Objectif : ecran central du processus : facture -> controle -> decision -> imputation -> export finance.

Le jalon produit a atteindre :

> Je prends une vraie facture, je vois son controle, je vois l'imputation comptable proposee, je decide quoi faire, puis je produis un export exploitable par la comptabilite.

## Questions restantes a ne pas trancher tout de suite

Ces questions peuvent attendre la confrontation aux vraies donnees :

1. Le XLSX doit-il etre separe par fournisseur ou consolide dans un seul fichier multi-fournisseurs ?
2. Quelle granularite exacte pour la matrice : contrat, fournisseur, site, compteur, poste facture, ou combinaison ?
3. Qui aura le droit d'activer une version de matrice ?
4. Le mail fournisseur doit-il etre seulement copie/pre-rempli ou envoye depuis la plateforme ?
5. Les factures anciennes doivent-elles etre recontrolees ou seulement archivees comme historique ?

## Decision operative immediate

La prochaine action recommandee est :

1. diagnostiquer et documenter le demarrage backend/API/base ;
2. garder la preview UX comme support de discussion ;
3. puis raccorder progressivement l'atelier Matrices et l'ecran Factures & decisions aux vraies donnees.