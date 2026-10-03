Inventaire des locaux d'un niveau, à partir des images raster suivantes (pixels seuls).
Vue globale : /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/overview.jpg
Tuiles de détail (bornes normalisées x1,y1,x2,y2 dans le repère global 0..1000) :
- /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-1.jpg : [0.0, 0.0, 360.341, 540.095]
- /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-2.jpg : [306.326, 0.0, 693.674, 540.095]
- /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-3.jpg : [639.659, 0.0, 1000.0, 540.095]
- /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-4.jpg : [0.0, 459.905, 360.341, 1000.0]
- /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-5.jpg : [306.326, 459.905, 693.674, 1000.0]
- /home/user/Po2/essais/R2-cloud/sorties/R2/passe-globale/tile-6.jpg : [639.659, 459.905, 1000.0, 1000.0]

Pièces déjà identifiées (id, nom lu, point intérieur dans le repère global) :
- piece-001 « terrasse de lecture » vers [787.7, 508.9]
- piece-002 « 5.1 Fiction / 5.2 Recherche et Documentation / 5.3 Roman noir » vers [445.4, 477.6]
- piece-003 « escalier » vers [321.1, 309.7]
- piece-004 « CF Cf » vers [279.2, 366.1]
- piece-005 « CVC EU EP » vers [324.4, 366.1]
- piece-006 « ventilation » vers [366.9, 369.5]
- piece-007 « ascenseur 75x1.6 nord » vers [451.7, 304.0]
- piece-008 « ascenseur 75x1.6 sud » vers [452.0, 620.1]
- piece-009 « EP » vers [578.5, 634.2]

Espaces libres qu'aucune pièce ne couvre (repérés sur l'image entre les murs) :

Ta tâche, sans dessiner de contour (ils sont mesurés par ailleurs) :
1. Pour chaque pièce : sa nature `local` = `chauffe` (bureau, salle, sanitaire, vestiaire…), `circulation` (couloir, hall, dégagement, palier, escalier ouvert chauffé), `gaine_technique` (gaine verticale ou horizontale), `non_chauffe` (autre local technique, escalier encloisonné ou local manifestement non chauffé) ou `exterieur` (terrasse, balcon, loggia, coursive, patio accessible : sa dalle crée un pont thermique avec les pièces voisines). En cas de doute, `chauffe` et une observation.
2. Pour chaque espace libre C… : `decision` = `local` (une pièce ou gaine oubliée, ou une terrasse, un balcon, une loggia : donne `nom` lu sur le plan ou « circulation », et sa nature `local`), `vide` (vide sur étage inférieur, trémie, puits de lumière), `exterieur` (dehors, sans plancher attenant) ou `mur` (épaisseur de mur).
3. Signale en observation une pièce qui contient un vide (ex. « vide sur accueil ») : sa surface n'est pas un plancher chauffé.
Réponds uniquement par le JSON demandé.