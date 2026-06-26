# 011 — Assistant matrices comptables et décisions Factures V1

> **Statut** : Accepté
> **Date** : 2026-06-25
> **Décideur(s)** : PAB34 + IA
> **Remplace / consolide** : docs 43, 44, 45 (archivés)
> **Complète** : [[Decisions/010-matrices-comptables-versionnees]]

## Contexte

Les documents 42→45 ont tranché plusieurs choix produit/workflow durables sur les matrices
comptables versionnées et la file `Factures & décisions`. Ces décisions étaient noyées dans des
fichiers de questions/réponses intermédiaires. On les consolide ici pour éviter de relire les
archives à chaque session. L'invariant d'architecture (versions immuables, snapshot facture) reste
porté par l'ADR 010 ; la spec d'exécution active reste [[49-Spec-execution-refonte-Factures-Decisions-V1]].

## Décision

### Configuration des matrices = atelier dédié, séparé de la file factures
`Configurer la matrice comptable` est une entrée à part (parcours en 6 étapes : importer un export
facture de référence → détecter les lignes récurrentes → compléter les axes comptables → export/import
XLSX → vérifier la couverture → activer la version). La file `Factures & décisions` **consomme** les
matrices activées mais ne les administre pas.

### Assistant multi-tiers dès le départ
Ne pas limiter à DALKIA. Noyau V1 prioritaire : **DALKIA, ENGIE, EDF, TotalEnergies** ; SUEZ/SPIE après.
Objectif rapide : produire des exports XLSX exploitables par la comptabilité pour tous les tiers, avec
des schémas de détection différents selon la source.

### Export XLSX comptabilité = multi-onglets
Onglet `À compléter` (colonnes utiles compta) + onglet `Détails / contrôle` (données techniques) +
éventuel onglet `Aide`. Garder toute l'information utile sans rendre le fichier illisible.

### Anciennes factures DALKIA = visibles avec badge
Badge `Ancien marché - hors contrôle courant`. Ne pas supprimer ni masquer ; distinguer pour ne pas
polluer le contrôle du nouveau marché (~11 octobre 2025).

### Rôles autorisés sur les matrices
Tous les rôles **sauf** Fluides et Technicien CVC.
- Autorisés : `ADMIN`, `SUPERADMIN`, `DIRECTION`, `RESPONSABLE_MAINTENANCE`, `PATRIMOINE`, `FINANCE`, `COMPTA`, `COMPTABILITE`.
- Exclus : `FLUIDES`, `FLUIDE`, `RESPONSABLE_FLUIDES`, `TECHNICIEN_CVC`.
- Lecture conservée pour tout utilisateur authentifié de la ville.

### Statuts factures V1 (workflow visible, pas simple colonne)
`Nouvelle`, `Déjà traitée`, `Réimportée identique`, `Réimportée modifiée`, `À contrôler`,
`En litige fournisseur`, `Validée comptabilité`, `Exportée finance`.

### Actions après contrôle facture (chaque action = trace explicable)
Valider avec commentaire · Mettre en attente fournisseur · Générer un mail fournisseur (copié/pré-rempli,
pas d'envoi direct en V1) · Corriger manuellement l'imputation · Demander correction de la matrice ·
Exclure du traitement courant.

### Comptabilité = trajectoire progressive
V1 : la compta complète un XLSX hors plateforme. Plus tard : accès plateforme limité lecture/écriture ciblée.

### Contacts fournisseur = libres en V1
Champs minimaux nom / email / téléphone / commentaire. Pas de typologie stricte au départ.

### Navigation Fluides cible
`Portefeuille`, `Électricité`, `Gaz`, `Eau`, `Abonnements à recalibrer`, `Référentiels et prix`.

## Conséquences

- La file factures et l'atelier matrices sont deux surfaces distinctes : pas de configuration noyée dans la file.
- Le frontend `/refonte-v1/matrices` applique déjà les rôles ci-dessus et expose export/import/preview/commit XLSX.
- Questions volontairement non tranchées (à revoir face aux vraies données) : XLSX séparé par fournisseur
  ou consolidé ; granularité exacte de la matrice ; envoi direct du mail fournisseur ; recontrôle des
  factures anciennes. Voir [[49-Spec-execution-refonte-Factures-Decisions-V1]] §10.

## Liens

- Invariant d'architecture : [[Decisions/010-matrices-comptables-versionnees]]
- Spec d'exécution active : [[49-Spec-execution-refonte-Factures-Decisions-V1]]
- Détail historique archivé : `docs/Archives/43-...`, `docs/Archives/44-...`, `docs/Archives/45-...`
