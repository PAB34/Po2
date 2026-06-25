# Session - Seconde passe V1 Fluides, contacts et historique factures

> Date : 2026-06-24

## Demandes traitees

- confirmer le renommage du domaine Energie en Fluides et anticiper l eau ;
- identifier un contact entreprise pour chaque marche et lot ;
- cadrer la generation ou l envoi des reclamations par e-mail ;
- distinguer nouvelles factures, factures traitees, reimports et historique ;
- refaire une passe complete de couverture V1 par rapport au code.

## Constat code facture

- ENGIE et EDF dedupliquent par numero de facture ;
- le mode normal ignore les factures connues ;
- la mise a jour forcee rejoue les controles et preserve les decisions utilisateur ;
- TotalEnergies ignore aussi les factures connues hors mise a jour forcee ;
- lots, doublons et decisions existent, mais les vues communes nouvelle/traitee/archivee/reouverte restent a construire.

## Arbitrage e-mail

V1 recommandee : referentiel de contacts dates, generation du destinataire/objet/message/preuves, puis ouverture de la messagerie utilisateur, copie ou fichier EML. L envoi direct est reporte jusqu a validation du besoin et choix SMTP/API.

Verification OVHcloud au 2026-06-24 : messagerie Starter 15 Go annoncee comme comprise avec le domaine ; E-mail Pro affiche a 1,59 EUR HT/mois/compte. Sources :

- https://www.ovhcloud.com/fr/domains/
- https://www.ovhcloud.com/fr/emails/
- https://www.ovhcloud.com/fr/emails/email-pro/

## Modifications atelier

- vocabulaire Fluides migre dans les modeles sauvegardes ;
- ajout du parcours V1 Contacts marches et reclamations ;
- ajout du parcours V1 Imports, deduplication et historique factures ;
- ajout de sept capacites canoniques liees aux contacts, mails et cycle facture ;
- integration des avoirs, revisions et preservation des decisions ;
- etat actuel : 11 diagrammes, 155 cadres, 171 relations, 55 capacites ;
- V1 : 16 diagrammes, 230 cadres, 259 relations, 66 capacites ;
- couverture registre/atelier : 66/66 ; aucun detail specialise manquant.

## Handoff suivant

Faire relire les deux nouveaux diagrammes par l utilisateur. Ne pas construire l envoi direct avant retour d usage sur la generation de brouillon et l ouverture de la messagerie.