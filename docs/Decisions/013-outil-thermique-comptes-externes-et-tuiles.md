# ADR 013 — Outil thermique : comptes externes sur la base Po2 et planches rendues en tuiles

- **Statut** : acceptée (2026-09-11)
- **Contexte de décision** : `docs/thermique/metre-thermique-decisions.md`

## Contexte

L'outil de métré thermique (`thermique.patrimoineaucarre.com`) doit fonctionner avec **le même
compte** que patrimoineaucarre.com, et être ouvert à des **bureaux d'études extérieurs** qui ne
doivent jamais voir les données de la Ville. Il affiche des plans d'architecte A1 vectoriels très
lourds (jusqu'à 650 000 traits par planche).

## Décision

1. **Une seule base de comptes.** L'outil utilise la table `users` et le JWT de Po2 ; ses routes
   vivent dans le backend Po2 (`/api/thermique/*`).
2. **Rôle `THERMIQUE_EXTERNE`** pour les bureaux d'études. `get_current_user`, dépendance de
   toutes les routes Po2, refuse ce rôle (403). Les routes de l'outil et du profil utilisent
   `get_authenticated_user`, qui accepte tout compte actif. La garde navigateur du site principal
   (`/api/internal/basic-auth`) refuse aussi ce rôle. Pas d'inscription libre sur `thermique.*` :
   les comptes externes sont créés par un admin (`POST /api/thermique/admin/external-accounts`).
   - **Amendement 2026-09-11 (Q6, décision utilisateur) : une seule connexion sur `thermique.*`.**
     La garde navigateur de ce sous-domaine (`basic-auth-thermique`) est supprimée : seule la page
     de connexion de l'outil demande les identifiants. Le front (pages statiques) devient public ;
     toutes les données restent derrière le jeton de l'API.
3. **Planches rendues côté serveur par pdfium en pyramide de tuiles PNG**, servies par adresse
   signée (HMAC, une planche, 12 h). Les mesures sont en points PDF ; la transformation PDF →
   pixels vient de pdfium (`FPDF_PageToDevice`).

## Conséquences

- Toute **nouvelle route Po2** doit continuer à dépendre de `get_current_user` (jamais de
  `get_authenticated_user`), sinon elle s'ouvre aux comptes externes.
- Un compte externe connecté sur le site principal n'y voit rien : garde navigateur refusée, API
  en 403.
- Dépendance ajoutée : `pypdfium2`. Stockage : volume `thermique_data` (fichiers + tuiles, 4 à
  8 Mo de tuiles par planche). Rendu : 2 à 3,6 s par planche, une fois par rotation.
- Les adresses de tuiles donnent accès aux images d'une planche pendant 12 h sans jeton : risque
  accepté, limité à une planche.

## Alternatives écartées

- **Application séparée avec ses propres comptes** (modèle `ligue1`) : contraire au besoin
  « même compte ».
- **Rôle externe vérifié route par route** : trop de routes (400 usages de `get_current_user`),
  oubli probable. Le verrou unique est testé.
- **pdf.js dans le navigateur** : mesuré à 10 s pour un plan et 46,8 s pour une coupe, à chaque
  zoom ; en tuiles, la même coupe s'affiche en 0,49 s.
- **Jeton JWT dans l'adresse des tuiles** : il donnerait accès à tout le compte s'il fuitait
  (journaux, historique).

## Liens

- `docs/thermique/00-audit-existant-faisabilite.md` · `docs/thermique/metre-thermique-decisions.md`
- Code : `saas/backend/app/core/roles.py`, `app/api/deps.py`, `app/services/thermique_raster.py`
