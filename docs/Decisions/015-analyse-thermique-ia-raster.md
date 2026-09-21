# 015 — Analyse thermique des plans par IA sur rendu raster

> **Statut** : Accepté
> **Date** : 2026-09-21
> **Décideur(s)** : PAB34 + Codex
> **Session liée** : `[[Sessions/2026-09-21 — Analyse IA visuelle du R+1]]`

## Contexte

Les PDF fournis aux thermiciens sont souvent aplatis, sans calques fiables, et leurs conventions de dessin
varient selon l'architecte. Le parcours fondé sur les traits et signatures vectoriels imposait de désigner murs
et menuiseries avant de pouvoir détecter les pièces ; cette dépendance a produit une expérience trop imbriquée
et des résultats difficiles à corriger. L'utilisateur dispose presque toujours du PDF seul et demande un moteur
réplicable sur des projets différents.

## Décision

La nouvelle route d'analyse sémantique travaille uniquement sur le rendu raster haute définition du plan. Une
IA multimodale classe et localise les composants ; le backend normalise la géométrie, projette le résultat dans
le repère de la visionneuse et réserve la correction manuelle aux objets douteux ou manquants. Les anciens
moteurs vectoriels restent présents mais ne contribuent ni à cette détection ni à son score.

## Conséquences

### Positives

- le moteur raisonne sur le même document visuel que le thermicien, même si le PDF est aplati ;
- aucune désignation préalable de calques ou de menuiseries n'est nécessaire ;
- chaque objet porte une confiance, une justification et des points directement éditables ;
- le fournisseur de vision reste configurable derrière un contrat JSON stable ;
- les corrections validées peuvent devenir une vérité terrain pour les évaluations multi-projets.

### Négatives / coûts assumés

- l'analyse nécessite un service multimodal externe, une clé serveur et un coût par planche ;
- la précision géométrique de la vision doit être mesurée sur plusieurs plans avant tout calcul de déperditions ;
- l'envoi des images doit respecter les règles de confidentialité des projets ; `store=false` est imposé au
  premier adaptateur ;
- les résultats sont d'abord conservés dans le stockage de la planche ; une migration en base sera nécessaire
  lorsque le contrat aura été validé sur le R+1.

### Alternatives écartées

- **Détection par vecteurs PDF** — trop dépendante de l'export et explicitement écartée par l'utilisateur.
- **Conversion en DWG** — aucune source DWG fiable n'est disponible et une conversion du PDF n'ajoute pas
  l'information métier manquante.
- **Dessin manuel intégral** — conservé comme secours mais incompatible avec l'objectif d'automatisation.

## Liens

- Décisions détaillées : `docs/thermique/analyse-ia-visuelle-r1-decisions.md`
- Service : `saas/backend/app/services/thermique_vision.py`
- Interface : `saas/frontend/src/thermique/pages/AutoZoningPage.tsx`
