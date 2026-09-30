# Cadres des vues corrigés par le thermicien — décisions (2026-09-30)

## Existant vérifié

- `run_lecture_coupes.py --type coupes` : étape « vues-ensemble » (l'agent encadre chaque vue de la planche,
  donne son haut), puis une étape par coupe, lue en tuiles quadrillées **dans ce cadre**.
- Essai réel du 2026-09-30 sur le projet 1 : cadres faux (PC10 : coupe A encadrée en y 1900–2360 au lieu de
  x 882–1573 × y 978–2003 ; une « FACADE » inventée sur PC11). Dans un mauvais cadre, l'agent ne trouve pas
  les pièces (A : 0, C : 0) → seule la coupe D se place sur le R+1.
- Constat constant (essai de septembre) : l'agent lit bien les textes, mal les positions fines.

## Décisions (D205, accord « ok go » du 2026-09-30)

1. Sur une planche de coupes ou de façades, **chaque vue lue est encadrée sur la planche** (rectangle et nom).
2. La fiche de la planche liste ses vues ; pour chacune : **Redessiner le cadre** (deux clics, coins opposés),
   **haut de la vue** (haut / bas / gauche / droite de la page), **Supprimer**.
3. Redessiner le cadre ou changer le haut **vide les pièces lues** (elles venaient du mauvais cadre), marque la
   vue « à relire », oublie les traits déduits de cette vue et **met la relecture en file** (travail `vues`),
   que le relais traite comme les autres ; à la main : `run_lecture_coupes.py --vues <fichier>` puis
   « Importer la lecture » (la vue garde son identifiant, les autres vues de la planche ne bougent pas).
4. Le haut donné par le thermicien l'emporte sur celui que l'agent déduit des cotes.
5. Serveur : pas de migration (l'état « à relire » vit dans `lecture_json`).
