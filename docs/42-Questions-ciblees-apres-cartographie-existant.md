# 42 - Questions ciblees apres cartographie de l'existant

Date : 2026-06-25  
Objet : decisions restantes avant de transformer l'atelier matrices en vrai assistant de configuration par tiers facturant.

Contexte : `docs/41-Cartographie-existant-avant-refonte-et-raccord-UX.md` confirme que beaucoup de moteurs existent deja. Les questions ci-dessous servent uniquement a verrouiller les zones ou l'UX peut changer le comportement metier.

Reponds directement sous chaque question dans la section `Reponse Pascal`.

---

## 1. Emplacement du parcours de configuration matrice

### Question

Dans chaque marche/fournisseur, veux-tu une entree dediee du type `Configurer la matrice comptable`, avec assistant en etapes :

1. importer un export facture de reference ;
2. detecter les lignes recurrentes ;
3. completer les axes comptables dans un tableau ;
4. exporter/importer XLSX ;
5. verifier que tout est couvert ;
6. activer la version.

Ou preferes-tu que cette configuration soit directement integree dans l'ecran `Factures & decisions` ?

### Reponse Pascal

Oui une entree dediee du type `Configurer la matrice comptable`, avec assistant en etapes :

1. importer un export facture de reference ;
2. detecter les lignes recurrentes ;
3. completer les axes comptables dans un tableau ;
4. exporter/importer XLSX ;
5. verifier que tout est couvert ;
6. activer la version.
---

## 2. Anciennes factures DALKIA

### Question

Pour les periodes anterieures au nouveau marche DALKIA autour du 11 octobre 2025, veux-tu :

1. les masquer par defaut dans la file courante, avec filtre `Archives / ancien marche` ;
2. les afficher mais avec badge `Ancien marche - hors controle courant` ;
3. les exclure completement du perimetre V1.

### Reponse Pascal

les afficher mais avec badge `Ancien marche - hors controle courant` ;
---

## 3. Roles exacts a traduire cote application

### Question

Tu as repondu : `tous les roles sauf fluides et technicien CVC`.

Peux-tu confirmer les libelles attendus des roles dans l'application ?

Exemples possibles :

- `ADMIN`
- `SUPERADMIN`
- `DIRECTION`
- `PATRIMOINE`
- `RESPONSABLE_MARCHE`
- `COMPTABILITE`
- `FLUIDES`
- `TECHNICIEN_CVC`

Si tu ne sais pas encore, je peux proposer une nomenclature cible.

### Reponse Pascal

C'est un sujet déjà abordé mais de mémoire c'était :
- Admin
- Direction
- Responsable maintenance
- Fluide 
- Technicien CVC
- Patrimoine
---

## 4. Contacts fournisseur

### Question

Pour les contacts par contrat, veux-tu que la V1 distingue deja les roles de contact ?

Exemples :

- facturation ;
- reclamation ;
- technique ;
- commercial / marche.

Ou suffit-il d'avoir plusieurs contacts libres avec nom, email, telephone et commentaire ?

### Reponse Pascal

Contact libre suffit
---

## 5. Organisation visible de Fluides

### Question

Dans la refonte visible, confirmes-tu cette organisation ?

- `Fluides > Portefeuille`
- `Fluides > Electricite`
- `Fluides > Gaz`
- `Fluides > Eau`
- `Fluides > Abonnements a recalibrer`
- `Fluides > Referentiels et prix`

Ou veux-tu eviter trop de sous-menus au depart et garder une seule page portefeuille avec filtres ?

### Reponse Pascal

Ok- `Fluides > Portefeuille`
- `Fluides > Electricite`
- `Fluides > Gaz`
- `Fluides > Eau`
- `Fluides > Abonnements a recalibrer`
- `Fluides > Referentiels et prix`
---

## 6. Premier raccord reel apres l'inventaire

### Question

Pour la prochaine etape de developpement, je recommande :

1. commencer par `Matrices comptables - configuration par tiers facturant` ;
2. utiliser DALKIA comme cas pilote ;
3. ensuite raccorder la file `Factures & decisions`.

Valides-tu cet ordre, ou veux-tu prioriser d'abord la file visuelle des factures ?

### Reponse Pascal

Non je veux qu'on les traite toutes, car je veux rapidement pouvoir envoyer au service comptabilité un export xlsx à remplir de leur côté
