Inventaire des locaux d'un niveau, à partir des images raster suivantes (pixels seuls).
Vue globale : /home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/passe-globale/overview.jpg
Tuiles de détail (bornes normalisées x1,y1,x2,y2 dans le repère global 0..1000) :
- /home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/passe-globale/tile-1.jpg : [0.0, 0.0, 360.341, 540.095]
- /home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/passe-globale/tile-2.jpg : [306.326, 0.0, 693.674, 540.095]
- /home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/passe-globale/tile-3.jpg : [639.659, 0.0, 1000.0, 540.095]
- /home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/passe-globale/tile-4.jpg : [0.0, 459.905, 360.341, 1000.0]
- /home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/passe-globale/tile-5.jpg : [306.326, 459.905, 693.674, 1000.0]
- /home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/passe-globale/tile-6.jpg : [639.659, 459.905, 1000.0, 1000.0]

Pièces déjà identifiées (id, nom lu, point intérieur dans le repère global) :
- piece-001 « 5.2 Recherche et Documentation (nord) » vers [443.7, 228.0]
- piece-002 « 5.2 Recherche et Documentation (accueil) » vers [597.7, 323.4]
- piece-003 « 5.1 Fiction » vers [267.8, 558.3]
- piece-004 « 5.3 Roman noir (nord) » vers [547.6, 505.2]
- piece-005 « 5.3 Roman noir (sud) » vers [547.6, 708.5]
- piece-006 « Escalier encloisonné CF » vers [311.8, 320.8]
- piece-007 « CF Cf » vers [272.5, 355.5]
- piece-008 « CVC EU EP » vers [317.0, 355.5]
- piece-009 « ventilation » vers [357.5, 355.5]
- piece-010 « Ascenseur 1 (1.75x1.6) » vers [451.4, 297.2]
- piece-011 « Ascenseur 2 (1.75x1.6) » vers [438.5, 605.0]
- piece-012 « EP » vers [565.7, 619.5]
- piece-013 « boite à vents / boite à lumière » vers [507.7, 411.7]
- piece-014 « terrasse de lecture » vers [772.0, 493.0]

Espaces libres qu'aucune pièce ne couvre (repérés sur l'image entre les murs) :
- C1 : 2.5 m² vers [654.9, 809.8]

Ta tâche, sans dessiner de contour (ils sont mesurés par ailleurs) :
1. Pour chaque pièce : sa nature `local` = `chauffe` (bureau, salle, sanitaire, vestiaire…), `circulation` (couloir, hall, dégagement, palier, escalier ouvert chauffé), `gaine_technique` (gaine verticale ou horizontale), `non_chauffe` (autre local technique, escalier encloisonné ou local manifestement non chauffé) ou `exterieur` (terrasse, balcon, loggia, coursive, patio accessible : sa dalle crée un pont thermique avec les pièces voisines). En cas de doute, `chauffe` et une observation.
2. Pour chaque espace libre C… : `decision` = `local` (une pièce ou gaine oubliée, ou une terrasse, un balcon, une loggia : donne `nom` lu sur le plan ou « circulation », et sa nature `local`), `vide` (vide sur étage inférieur, trémie, puits de lumière), `exterieur` (dehors, sans plancher attenant) ou `mur` (épaisseur de mur).
3. Signale en observation une pièce qui contient un vide (ex. « vide sur accueil ») : sa surface n'est pas un plancher chauffé.
Réponds uniquement par le JSON demandé.