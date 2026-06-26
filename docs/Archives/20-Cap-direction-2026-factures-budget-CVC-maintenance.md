# 20 - Cap direction 2026 : factures, budget, CVC et maintenance

> Date : 2026-06-22
> Statut : cadrage produit prioritaire
> Objet : recentrer PatrimoineAuCarre sur les preuves attendues par la direction.

## 1. Decision de reorientation

Les travaux realises ne sont pas hors sujet : ENGIE, TotalEnergies, DALKIA, BPU/TURPE, matrice comptable, patrimoine, rapprochements et inventaire CVC constituent une base solide.

Le risque est que le produit reste raconte comme une addition de modules, alors que la direction attend cinq reponses simples et defensables :

1. **Cette facture est-elle conforme au contrat signe et peut-elle etre payee ?**
2. **Ou en est-on du budget vote et quel sera l'atterrissage au 31 decembre ?**
3. **Quels equipements CVC sont a risque et quels travaux faut-il financer ?**
4. **Tous les sites et equipements qui doivent etre entretenus sont-ils couverts par un marche ?**
5. **Comment evoluent les consommations, quel est l'effet du climat et ou finirons-nous en kWh et en euros ?**

Ces questions deviennent les cinq programmes P0. Les autres sujets ne doivent plus interrompre ce fil sauf s'ils debloquent directement une preuve.

## 2. Existant et manque critique

| Programme | Socle disponible | Manque pour une preuve direction |
|---|---|---|
| Factures | ENGIE avance ; TotalEnergies v1-v3 ; DALKIA avance ; BPU/TURPE ; decisions et exports | EDF a consolider ; SPIE absent ; versions contractuelles non unifiees ; file multi-marches |
| Budget | Matrice comptable ; factures ; suivi DALKIA partiel ; consolidation finances | budget initial/revisions ; engage/facture/mandate ; projection ; ventilation complete |
| CVC/PPT | Inventaire terrain ; SYPEMI ; etat, age, duree de vie ; F-Gaz/ESP | doubles inventaires ; criticite explicable ; couts ; PPT 5-10 ans |
| Maintenance | Patrimoine hierarchique ; CVC ; sites DALKIA ; rapprochements | contrats generiques ; perimetres SPIE/DALKIA ; matrice de couverture ; sites non entretenus |
| Consommations/DJU | ENEDIS, DJU, premiers services GRDF, controles facture-conso | series unifiees, qualite/couverture, DJU transversal, atterrissage kWh et conversion contractuelle en euros |
| Front | shell par domaines ; routes conteneurs ; theme sombre | design system ; pages/API/CSS monolithiques ; responsive/accessibilite ; langage coherent |

## 2b. Fondations obligatoires des cinq axes

Les axes reposent sur quatre fondations qui ne doivent pas devenir des modules oublies : patrimoine maitre ; qualite/rapprochements/provenance ; documents/versions contractuelles/preuves ; workflow/securite/audit. Chaque tranche verticale doit montrer comment elle les utilise. Voir [[23-Seconde-passe-audit-fonctionnel-et-angles-morts]].

## 3. P0-A - Controle contractuel des factures

```text
Facture recue -> marche/version identifies -> patrimoine rattache
-> prix, quantites, indices, taxes et prestations controles
-> ecarts chiffres et preuves -> decision motivee
-> ventilation comptable -> export et horodatage
```

| Marche | Controle minimal cible |
|---|---|
| ENGIE / EDF | PRM/site, periode, doublon, quantite vs ENEDIS, BPU, TURPE, taxes, puissance, total, avoirs/FIC |
| TotalEnergies | PCE/site, periode, quantite, conversion m3/kWh, BPU/PEG, ATRD/ATRT, TICGN/CEE, TVA, total |
| DALKIA | contrat/lot/site, P1/P2/P3, DPGF/BPU, indices/formules, acomptes/decomptes, cibles, penalites/interessement, compte P3 |
| SPIE | contrat/lot/site/equipements, echeancier P2, prestations, revision, periode, justificatifs, penalites applicables |

SPIE ne doit pas etre clone sur le CPE DALKIA. Il partage dossier, decision, matrice comptable et export, mais conserve ses regles P2.

Donnees indispensables : actes, CCAP/CCTP utiles, DPGF, BPU, avenants, versions/dates d'effet, perimetres, tiers, mapping patrimoine, matrice comptable, factures/avoirs, preuves et historique.

### Definition de termine

- file unique de toutes les factures sans masquer les moteurs specifiques ;
- anomalie avec regle, reference, valeur facturee, ecart et source ;
- blocage obligatoire resolu ou leve avec justification avant `payable` ;
- modifications apres decision historisees ;
- export identique a la decision et ventilation validees ;
- echantillon reel de chaque marche valide de bout en bout.

## 4. P0-B - Budget, realise et atterrissage

| Mesure | Definition |
|---|---|
| Budget initial | enveloppe votee au debut de l'exercice |
| Budget courant | budget initial + decisions modificatives/virements |
| Engage | commandes ou engagements juridiques connus |
| Facture recue | factures importees, avant/apres controle selon le filtre |
| Valide / transmis | facture acceptee et transmise aux finances |
| Mandate / paye | information comptable si disponible |
| Reste a engager | budget courant - engage |
| Atterrissage | realise + engagements restant a facturer + projection de fin d'exercice |
| Ecart projete | atterrissage - budget courant |

Lecture par exercice, service, tiers, marche/lot/contrat, matrice comptable, site/batiment et P1/P2/P3 ou fluide. La matrice comptable devient l'axe de consolidation, pas un simple export.

```text
Atterrissage V1
= factures validees a date
+ factures recues non decidees (scenario parametrable)
+ engagements/commandes restant a facturer
+ echeancier contractuel restant
+ projection consommation/prix energie
+ ajustements manuels documentes
```

### Definition de termine

- budget initial et revisions importables/versionnes ;
- vue direction : budget, realise, engage, atterrissage, ecart et confiance ;
- drill-down matrice -> marche -> site -> facture/engagement ;
- scenarios prudent/central/haut et journal des ajustements ;
- aucun double comptage et chaque synthese explicable ;
- totaux matrice reconcilies avec le total direction ;
- date, hypotheses et confiance visibles.

## 5. P0-C - Etat CVC et plan pluriannuel de travaux

La direction attend une trajectoire d'investissement : quels equipements remplacer, pourquoi, quand et pour quel budget.

La fiche cible porte identite/localisation, source/date du constat, mise en service/age/duree de vie, etat/criticite/redondance/impact, conformites et preuves, contrat/prestataire, cout/source/confiance et action/annee cible.

La criticite V1 combine vetuste, etat, criticite d'usage, redondance, risque securite/reglementaire, pannes/couts recurrents, performance energetique et fraicheur. Le detail reste visible et corrigeable.

Le PPT couvre 5 a 10 ans, actions surveiller/maintenir/renover/remplacer/etudier, cout bas/central/haut source, regroupements site/famille/urgence/annee, arbitrages justifies, CAPEX/OPEX et lien P3 utile.

### Definition de termine

- `CvcInventoryItem` et `BuildingEquipment` arbitres ou presentes sans double comptage ;
- couverture et fraicheur des visites visibles ;
- toute action PPT remonte a un besoin justifie ;
- couts sans source identifies comme estimations ;
- besoin annuel et risques non finances lisibles par la direction.

## 6. P0-D - Couverture des marches de maintenance

Question : pour chaque site, batiment et famille exigeant une maintenance, quel contrat s'applique, sur quelle periode, avec quel prestataire et quelle preuve ?

Un contrat porte fournisseur, marche, lot, dates, statut, montant, pieces, prestations, periodicites, versions et perimetres patrimoine/equipements.

Statuts : `couvert et prouve`, `a confirmer`, `non couvert`, `hors perimetre justifie`, `chevauchement`, `expire/proche echeance`.

| Niveau | Lecture attendue |
|---|---|
| Portefeuille | sites couverts, non couverts, ambigus |
| Site | lots attendus vs contrats applicables |
| Batiment/local | heritage du site et exceptions |
| Equipement/famille | prestataire, periodicite et preuve |
| Marche | sites contractuels vs patrimoine reel |

Le systeme montre les deux anomalies : site sans maintenance et site facture/couvert mais absent du patrimoine ou sans equipement correspondant.

### Definition de termine

- DALKIA/SPIE rattaches sans liste parallele opaque ;
- chaque site a une vue couverture ;
- sites non entretenus exportables avec motif ;
- contrats expires, chevauchants et sans piece signales ;
- facture de maintenance verifie site/prestation contre le perimetre.

## 7. P0-E - Consommations, DJU et atterrissage energetique

Les consommations ENEDIS et GRDF forment la source physique de reference. Les factures servent a controler la couverture et a convertir les volumes projetes en euros, sans remplacer les donnees distributeurs.

Les DJU sont transversaux : comparaison temporelle, normalisation climatique, detection de derive, atterrissage annuel, CPE DALKIA, diagnostic CVC et mesure de l'effet des travaux.

```text
Atterrissage physique = reel distributeur connu
+ consommation restante projetee selon DJU, saison, tendance et perimetre

Atterrissage financier energie = volumes projetes x prix contractuels applicables
+ acheminement + taxes + capacite/CEE + termes fixes
```

### Definition de termine

- series ENEDIS/GRDF consultables dans le temps par compteur, site et portefeuille ;
- couverture, fraicheur et trous de donnees visibles ;
- DJU avec source, station, periode, normale et qualite ;
- comparaison reel/N-1/reference/DJU et detection des ruptures ;
- scenarios bas/central/haut en kWh et euros avec hypotheses explicites ;
- composantes variables et fixes correctement distinguees ;
- volumes factures rapproches des volumes distributeurs sans double comptage ;
- drill-down de l'atterrissage vers PRM/PCE, periodes, prix et formules.

## 8. Frontend moderne : chantier transversal P0-UX

Le front doit devenir un outil de decision dense, calme et credible. Moderne signifie hierarchie nette, parcours courts, composants coherents, accessibilite et performances previsibles.

Dette constatee : `CpeDalkiaPage.tsx` approche 180 Ko, `lib/api.ts` depasse 150 Ko, `styles.css` depasse 110 Ko, plusieurs pages depassent 60-80 Ko. Routes/outils experts restent melanges et les statuts, filtres et tableaux ne forment pas encore un systeme.

```text
src/
  app/             shell, routes, providers
  design-system/   tokens, boutons, champs, badges, cartes, tableaux, feedback
  features/        invoices, budgets, maintenance, cvc, patrimoine
  shared/          formats, dates, exports, permissions
  lib/api/         client HTTP + modules par domaine
```

Regles : une page orchestre ; panneaux en features ; API/types par domaine ; couleurs par tokens semantiques ; meme statut partout ; tables avec filtres, colonnes, vide/erreur/chargement/export ; clavier, focus, contrastes et responsive inclus.

Ordre : fondations -> factures -> budget -> maintenance -> CVC -> nettoyage apres non-regression. Pas de nouvelle page monolithique, de regle metier uniquement React, ni de refonte globale en un lot. Les anciennes routes restent redirigees.

## 9. Sequencement recommande

### Lot 0 - Preuves et donnees

- reunir contrats/avenants/DPGF/BPU DALKIA/SPIE ;
- obtenir budget initial et matrice comptable reelle ;
- confirmer sites/equipements couverts ;
- choisir des factures echantillons ;
- figer statuts et regles bloquantes.

### Lot 1 - Factures demonstrables

- terminer ENGIE/EDF/TotalEnergies ;
- fiabiliser DALKIA DPGF/indices/P1-P2-P3 ;
- unifier file, decision et export ;
- refondre le premier parcours front.

### Lot 2 - Budget et atterrissage V1

- importer/versionner budget/revisions ;
- consolider factures, engagements, echeanciers ;
- produire scenarios et drill-down ;
- reconcilier avec un export finance de reference.

### Lot 3 - SPIE et couverture

- referentiel contrat generique ;
- perimetre SPIE rattache ;
- matrice de couverture et sites non entretenus ;
- controle facture SPIE P2.

### Lot 4 - CVC et PPT

- arbitrer les doubles sources ;
- fiabiliser criticite/fraicheur ;
- ajouter couts/actions ;
- produire plan 5-10 ans et risques non finances.

## 10. Indicateurs de succes direction

| Question | Indicateur |
|---|---|
| Factures | % et montant controles, delai, ecarts, montant bloque/recupere, preuves manquantes |
| Budget | budget courant, engage, valide, mandate, atterrissage, ecart, confiance |
| CVC | couverture, equipements critiques, travaux 1/3/5/10 ans, risques non finances |
| Maintenance | % sites/equipements couverts, non couverts, echeances, perimetres ambigus |
| Produit | objets non rattaches, donnees anciennes, parcours valides, erreurs front |

## 11. Sujets repousses

Baux, OPERAT, portail usagers, GTB/BACS avance, eau et automatisations secondaires passent apres les quatre preuves, sauf dependance reglementaire ou donnee indispensable.

## 12. Prochaine action

Demarrer le Lot 0, puis livrer une tranche verticale : un marche reel -> pieces versionnees -> factures controlees -> decision -> ventilation -> export -> restitution direction.

ENGIE est recommande comme parcours front de reference, avec fiabilisation DALKIA en parallele. SPIE commence apres reception et classement de ses pieces/perimetres reels.
