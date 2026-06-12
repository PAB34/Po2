# Rapport audit PRM ENEDIS - 2026-06-12

## Synthese

L'audit PRM confirme que le moteur distingue maintenant mieux les causes d'absence de donnees ENEDIS. Le parc compte 533 PRM contractuels.

- Complets sur les trois flux mesures : 341 PRM
- Partiels : 37 PRM
- Anomalies a corriger : 26 PRM
- Alertes : 87 PRM
- Vides normaux : 81 PRM non alimentes

Les volumes collectes sont coherents avec l'etat du parc :

- Consommation journaliere : 422 700 lignes, 378 / 533 PRM couverts
- Puissance max journaliere : 382 951 lignes, 341 / 533 PRM couverts
- Courbe de charge : 13 982 547 lignes, 341 / 533 PRM couverts
- DJU meteo : 4 179 lignes

## Lecture des absences

Les 192 PRM sans puissance max / courbe de charge ne sont pas tous des erreurs applicatives.

Repartition structurante :

- 81 PRM non alimentes : absence normale
- 40 PRM non communicants : CDC/Pmax structurellement non attendues ; seule la conso journaliere peut etre exploitable
- 1 PRM communicant non ouvert aux services : activation CDC requise
- 72 cas identifies comme service/droits API ENEDIS a verifier
- 26 anomalies critiques : PRM alimentes et communicants ouverts mais sans flux exploitable

## Appels ENEDIS directs

Des appels directs en lecture seule ont ete effectues sur un echantillon de PRM de l'audit.

PRM temoin avec donnees (`24322141674180`) :

- Conso journaliere : HTTP 200
- Puissance max : HTTP 200
- Courbe de charge : HTTP 200
- Les memes appels fonctionnent sur une fenetre recente et sur des chunks annuels.

PRM communicants ouverts sans donnees, exemples `24304196703989`, `24317510714281`, `24325614938302` :

- Contract summary : HTTP 200
- Conso / CDC : HTTP 400 avec code metier `403`
- Message ENEDIS : `aucun service souscrit ACCES a la donnee pour la periode demandee`
- Conclusion : le PRM existe bien dans le referentiel, mais le service d'acces aux mesures n'est pas disponible sur la periode demandee.

PRM avec `Requete invalide`, exemples `24343704654246`, `50001805114778`, `24309840798709`, `24350217015563` :

- Contract summary : HTTP 200
- Conso / Pmax : HTTP 400, message `Demande non valide, verifier les parametres`
- Le resultat reste identique sur une fenetre recente, annuelle et ancienne.
- Conclusion : ce n'est pas un probleme de date trop fraiche ; il faut verifier profil, eligibilite ou droits ENEDIS sur ces PRM.

## Conclusion technique

Le moteur d'appel fonctionne : un PRM temoin repond correctement sur les trois flux. Les absences restantes viennent principalement de droits/services ENEDIS ou de profils non eligibles, pas d'un defaut general du moteur.

Les libelles d'audit sont maintenant plus exploitables :

- `Acces non souscrit` : droit/service ENEDIS absent pour la periode
- `Requete invalide` : profil, eligibilite ou parametre a clarifier avec ENEDIS
- `Erreur tech.` : a relancer ou investiguer cote collecte
- `Non alimente` : absence normale

## Actions recommandees

1. Ne pas relancer massivement les 81 PRM non alimentes.
2. Pour les 40 non communicants, ne pas attendre de CDC/Pmax ; verifier seulement si la conso journaliere est necessaire.
3. Pour les 26 anomalies critiques, transmettre a ENEDIS la liste des PRM avec le message d'erreur exact.
4. Pour les cas `Requete invalide`, demander a ENEDIS si le PRM est eligible aux endpoints mesures synchrones et a partir de quelle date.
5. Conserver Pmax comme source prioritaire pour le dimensionnement ; reserver la CDC aux analyses fines.
