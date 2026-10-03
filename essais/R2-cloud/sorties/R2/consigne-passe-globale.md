Analyse ce plan de bâtiment uniquement à partir des images raster suivantes.
L'image géométrique globale mesure 2814 x 2731 pixels.
Vue globale : /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/overview.jpg
Lis la vue globale puis chacune des six tuiles avec l'outil Read.
Tuile 1/6 : /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-1.jpg ; bornes globales normalisées x1,y1,x2,y2 = [0.0, 0.0, 360.341, 540.095].
Tuile 2/6 : /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-2.jpg ; bornes globales normalisées x1,y1,x2,y2 = [306.326, 0.0, 693.674, 540.095].
Tuile 3/6 : /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-3.jpg ; bornes globales normalisées x1,y1,x2,y2 = [639.659, 0.0, 1000.0, 540.095].
Tuile 4/6 : /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-4.jpg ; bornes globales normalisées x1,y1,x2,y2 = [0.0, 459.905, 360.341, 1000.0].
Tuile 5/6 : /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-5.jpg ; bornes globales normalisées x1,y1,x2,y2 = [306.326, 459.905, 693.674, 1000.0].
Tuile 6/6 : /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-6.jpg ; bornes globales normalisées x1,y1,x2,y2 = [639.659, 459.905, 1000.0, 1000.0].
Produis l'inventaire exhaustif mais prudent des composants du bâtiment, puis des pièces et espaces (catégorie piece, polygone au nu intérieur, nom lu dans subtype).
Les pièces couvrent tout l'intérieur du niveau, murs exceptés : circulations, halls, dégagements, paliers, sanitaires et locaux techniques compris. Pour chaque pièce, indique sa nature dans local : chauffe, circulation, gaine_technique (gaine verticale ou horizontale), non_chauffe (autre local technique, escalier encloisonné) ou exterieur.
Une terrasse, un balcon, une loggia, une coursive ou un patio accessible est une pièce de nature exterieur, avec le nom lu sur le plan : sa dalle crée un pont thermique avec les pièces voisines, il faut donc pouvoir la voir et la recadrer. Un vide sur l'étage inférieur, une trémie ou un puits de lumière n'est pas une pièce.
Toutes les coordonnées finales doivent être globales et normalisées de 0 à 1000.
Fusionne les doublons entre tuiles et simplifie les portions droites pour éviter les zigzags.