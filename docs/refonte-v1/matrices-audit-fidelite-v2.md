# Audit de fidélité — matrice système B vs `MATRICE_DALKIA-COMPATBILITE V2.xlsx`

Méthode : exécution du **vrai** parser de production `import_codification_workbook`
(`app/services/cpe_accounting.py`) sur le fichier source, en base sqlite mémoire,
puis comparaison au contenu brut des feuilles. Aucune ré-implémentation.
Fichier source : `saas/energie/DALKIA/COMPTABILITE/MATRICE_DALKIA-COMPATBILITE V2.xlsx`.

## Résultat global
- **Sites : 75 produits / 75** (feuille « Sites vers codes », 76 lignes = 1 en-tête + 75).
- **Natures : 43 produites / 44 lignes de données** (feuille « Poste facturé vers Nature ctpab »).
- **0 erreur** de parsing. En-têtes tous correctement normalisés.
- Les 2 autres feuilles (« Signification poste facturés », « Codes contrat - marchés »)
  sont des références documentaires, non importées (normal).

**Conclusion : la matrice produite correspond fidèlement au fichier source.** Ce que la
page `/refonte-v1/matrices` affiche = ce que le parser met en base = le contenu du V2
(à condition que le V2 ait été (ré)importé dans l'environnement consulté).

## Points vérifiés / rassurants
1. **Opération sur les sites = None pour les 75 sites.** Confirmé par la structure du
   fichier : la feuille « Sites vers codes » n'a que **11 colonnes** et **aucune colonne
   opération**. Donc le `98004` / service `ATBA` vus autrefois par la comptable **ne
   viennent pas du V2** → c'était de la donnée prod périmée. Un réimport V2 corrige.
2. **Axes site fidèles** : code_site, désignation, service, fonction, antenne repris
   à l'identique (ex. `VDS-BAM 08` CTM → service MABA, fonction 020, antenne CTM).
3. **Natures fidèles** : contrat + poste + nature + libellé repris à l'identique
   (ex. P3/P3.4 → 21351, P2 → 6156, P1 élec → 60612).
4. **1 seule ligne ignorée**, à juste titre : une note de la comptable
   « RAJOUTER 3.2, 3,3 » (sans poste ni nature) → non importée.

## Nuances à connaître (pas des bugs, mais à valider)
1. **Marché dérivé du poste, pas de la colonne « marché/périmètre » du fichier.**
   La colonne source `marché/périmètre` est un **texte libre descriptif**
   (« Ville - nouveau CPE/MPGP lot 1 », « Agglo - CREM Piscine Fonquerne »…), pas un
   code marché. Le parser déduit le code marché du poste : P1/P2/P3/R1/R2. C'est correct
   pour ces postes. En revanche, pour les **sous-postes P1 gaz du CPE** (ABT, CPB, CTA,
   LOCATION, STOCKAGE, TERME FIXE, PREST PONC), le « marché » produit = **le nom du poste
   lui-même** (pas « P1 »). Impact = étiquette de regroupement uniquement ; la nature
   comptable est bien importée. À décider : faut-il les regrouper sous « P1 » ?
2. **Opérations d'investissement P3 présentes dans le fichier mais non stockées dans la
   matrice.** La feuille nature porte une colonne `opération si investissement` :
   `98001-98002-98003-98004` pour P3, `98023` pour P3.4. Le parser des **natures** ne
   stocke pas l'opération (les règles de nature n'ont pas de champ opération ; seul le
   *site* en a un, et il est vide). Le rapport comptable calcule l'opération P3 par un
   autre chemin (`_cpe_p3_operation_fallback`). **À valider** : vérifier que le rapport
   affiche bien la bonne opération pour une ligne P3/P3.4, puisque cette info du V2 n'est
   pas persistée dans la matrice.
3. **Qualité de la donnée source** (importée fidèlement, à nettoyer côté fichier) :
   - `nature = « Selon service vendu »` (C00032657J, P1) : ambiguïté, pas un vrai code.
   - Coquilles d'antenne : « BAT ADNIM » (pour ADMIN), « PAS D ANTENNE ».
   - Sites sans service/fonction/antenne (CCAS 02/03/04/09/10, VDS-BAM 09, VDS-ENS 18) :
     cellules vides dans le fichier.

## Recommandations
- **Réimporter le V2** dans l'environnement cible (prod et/ou staging) via la page
  `/refonte-v1/matrices` (onglet DALKIA → « Importer le classeur V2 ») pour garantir que
  la donnée affichée = V2.
- Trancher les nuances 1 et 2 ci-dessus (regroupement P1 des sous-postes gaz ; opération
  P3 dans le rapport).
- Corriger les coquilles source (nuance 3) directement dans la matrice éditable, ce qui
  la rendra plus propre que le fichier Excel.
