# 31 - Analyse de la charte graphique et alignement du prototype

> Date : 2026-06-24  
> Sources : `docs/branding/charte-graphique-source.docx`, `docs/branding/planche-identite-po2.png` et actifs officiels de `saas/LOGO/po2_logos_unitaires_svg_png/`.  
> Statut : tokens et logos officiels intégrés au prototype V1 ; extraction du design system React encore à réaliser.

## Verdict

La structure du prototype V1 est cohérente avec la charte : interface claire, cartes sobres, navigation stable, dataviz utile, drill-down et densité maîtrisée. La structure et l'identité du prototype sont désormais alignées sur la charte : bleu nuit, vert accent, gris techniques, hiérarchie typographique et variantes officielles du logo.

L'alignement visuel du premier jet est estimé à environ **95 %**. Le solde concerne surtout la validation sur toutes les futures pages, les polices de production et les composants React définitifs.

## Tokens officiels à reprendre

| Rôle | Valeur | Usage |
|---|---|---|
| Bleu nuit principal | `#1D3150` | Logo, navigation, titres, CTA principaux, icônes structurantes. |
| Vert accent | `#74B44A` environ | Exposant ², progression, succès et accents ponctuels uniquement. |
| Gris clair | `#D1D5D9` | Fonds secondaires, séparateurs, premier niveau de dataviz. |
| Gris moyen | `#8A8F98` | Textes secondaires, pictogrammes et second niveau de dataviz. |
| Bleu ardoise | `#425164` | Informations techniques, structure et troisième niveau de dataviz. |
| Fond principal | blanc / blanc cassé | Surface de travail dominante. |

L'analyse colorimétrique de la planche raster confirme une famille bleu nuit autour de `#1E3451`, très proche de la référence documentaire. Le vert du raster varie avec l'anticrénelage ; la valeur normative du document reste prioritaire.

## Typographie

- titres, KPI et grands chiffres : `Montserrat SemiBold/Bold` ;
- textes, tableaux, formulaires et menus : `Source Sans 3` ou `Inter` ;
- solution de repli hors ligne : `Segoe UI Variable`, puis police système.

Les fichiers de police ne sont pas fournis. Il faudra décider s'ils sont auto-hébergés ou chargés depuis une source autorisée avant la production.

## Comparaison avec le prototype actuel

### Déjà aligné

- fonds clairs majoritaires ;
- cartes blanches avec bord discret et ombre légère ;
- navigation latérale structurante ;
- hiérarchie forte des KPI ;
- dataviz limitée à un message principal ;
- statuts sobres ;
- responsive desktop/mobile ;
- expérience orientée décision et non décoration.

### Corrections appliquées au prototype

- navigation convertie au bleu nuit PO² ;
- vert de marque réservé aux accents, progressions et validations ;
- boutons principaux en bleu nuit ;
- états et accents harmonisés ;
- graphes convertis vers le bleu nuit et les gris/ardoise ;
- priorité Montserrat pour les titres et Source Sans 3 pour le corps, avec replis système ;
- vrai logo officiel intégré dans la barre latérale ;
- produire favicon et icône PWA depuis l'icône app officielle.

## Usage des variantes du logo

- interface interne et barre latérale : monogramme ou version sans cadre ;
- page de connexion : version avec cadre fin ou logo complet ;
- documents officiels et exports : logo complet avec nom ;
- favicon, raccourci et PWA : icône app sur fond bleu nuit.

## Actifs officiels reçus et intégrés

Les variantes suivantes sont disponibles dans le dépôt et les principales ont été copiées dans `docs/prototype-refonte-v1/assets/` :

- logo sans cadre ;
- monogramme ;
- logo complet ;
- icône app ;
- version avec cadre fin ;
- formats SVG et PNG.

Il reste seulement à décider le mode de chargement des polices et à produire les tailles finales du manifeste PWA lors de l'intégration React.

## Point de vigilance produit

La charte texte présente l'énergie en V1.5 et les contrats/tickets en V2. Cette chronologie ne correspond plus à l'état réel du projet, où factures, Fluides, DALKIA et contrats sont déjà centraux.

La charte doit donc devenir la source de vérité **visuelle**, tandis que les documents 27 à 32 restent la source de vérité **fonctionnelle et produit**.

## Décision recommandée

Conserver le prototype comme base d'expérience, appliquer les tokens PO² dans une variante brandée, puis faire valider cette variante avant d'extraire le design system React. Ne pas retarder les workflows prioritaires pour revenir à l'ancienne chronologie MVP/V1.5/V2 de la charte.