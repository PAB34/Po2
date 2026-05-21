# GTC, GTB, données et intégration technique

tags: #GTC #GTB #API #GMAO #BACnet #LoRaWAN #données

---

## Architecture de la GTC (Gestion Technique Centralisée)

### Poste de supervision central
- Hébergé par DALKIA (pas sur le réseau informatique de la Ville)
- Architecture multiserveurs, évolutive
- Protocoles supportés : OPC UA, BACnet, LON, KNX, Mbus, Modbus, SNMP, Ethernet TCP/IP, radio
- Accès simultané : minimum 3 connexions (LAN/WAN + mobile HTML5)
- Envoi d'alertes par e-mail et SMS
- Sécurité : authentification par mot de passe (protocole LDAP), niveaux d'accès multiples

### Points de contrôle minimum par site
- Gestion des intermittences de température
- État marche/arrêt des équipements principaux
- Températures de fonctionnement (primaire, chauffage, ECS, eau glacée)
- Alarmes (seuils température/pression) et défauts (pompes, brûleurs)
- Présence tension électrique
- Alarme sur consommation d'appoint d'eau anormale
- Pilotage des systèmes passifs (free-cooling, etc.)
- **Liste des points validée conjointement avant le 31/12/2025**

### Automates locaux
- Communication BACnet TCP/IP avec le poste de supervision
- Mémoire flash avec sauvegarde 15 jours sur coupure secteur
- Entrées universelles (0-10V, 4-20mA, thermistance, TOR)
- Alimentés en 230 VAC
- Un automate intelligent par équipement CVC (armoires, chaudières, CTA, etc.)

### Réseau LoRaWAN
- La Ville étudie le déploiement d'un réseau LoRaWAN **privé**
- Objectif : lecture des données GTC de façon périodique
- Déploiement via API ou gateway sur la GTC (accès lecture seule)
- Amélioration possible de la classe GTB des systèmes

---

## API GTB — Accès données en lecture pour la Ville

La collectivité demande un accès en lecture seule aux données de la GTB (CCTPM 6.8).

### Données exposées par l'API
| Catégorie | Fréquence |
|-----------|-----------|
| Alarmes critiques | Temps réel ou toutes les 5 min |
| Données d'exploitation (températures, consommation) | Horaire |
| Rapports consolidés | Quotidien et mensuel |

### Spécifications techniques de l'API
- Type : **REST** (recommandé) ou MQTT pour IoT
- Format : **JSON** (recommandé) ou CSV
- Sécurité : **OAuth2**, chiffrement SSL/TLS
- Compatibilité : BACnet/IP, Modbus/TCP, MQTT selon équipements

### Données accessibles
1. Capteurs : températures, humidité, consommations, qualité d'air
2. Actionneurs : statuts chauffage, climatisation, vannes, pompes
3. Programmation horaire : chauffage, climatisation, ECS
4. Alarmes : défaillances critiques, alertes maintenance, anomalies de consommation

---

## GMAO (Gestion de Maintenance Assistée par Ordinateur)

### Mise en place
- Délai : **2 mois** après prise d'effet du marché
- Réunion de mise au point dès notification du marché pour définir la structure

### Fonctionnalités minimales
- Inventaire de tous les équipements du marché
- Gammes de maintenance compatibles avec l'annexe n°5 du Programme Fonctionnel
- Visualisation plan de maintenance et avancement (fait / annulé / reporté)
- Fiche d'intervention par opération (mesures, constats)
- Filtres : par bâtiment, par service, par catégorie d'équipements
- Contrôles réglementaires (disconnecteurs, étanchéité froid, etc.)
- Accès lecture seule pour la collectivité (via espace client ou site dédié)
- Identification par **QR Code** pour équipements hors locaux techniques (avec coordonnées GPS)

### Données transmises par GMAO
- Avant le **31 janvier** : bilan annuel interventions préventives et correctives + données brutes GMAO
- Avant le **15 octobre** : programme d'entretien préventif de l'exercice suivant

---

## Espace client DALKIA

Accessible dans les **2 mois** après prise d'effet du marché.

### Modules minimum
| Module | Contenu |
|--------|---------|
| Suivi dépannages | Statut : Ouverture → Prise en charge → CR → Commande pièce → Réception pièce → Planification → Pose → Clôture |
| Suivi consommations | Chauffage + ECS par site |
| Suivi facturation | P1 / P2 / P3 détaillé par site |
| Suivi contrôles périodiques | Tableau d'avancement |
| Suivi P3 | Garantie totale + Travaux programmés |
| Suivi devis hors contrat | État d'avancement |
| Pièces du marché | Documents signés |
| GMAO | Plan maintenance et avancement |

> Toute intégration nouvelle installation : mise à jour espace client dans les **2 mois** après réception OS/avenant.

---

## Compteurs et plan de comptage

### Obligations de comptage
- Conformité **décret BACS**
- Entretien par réparateur agréé, à la charge de DALKIA
- Vérification d'exactitude périodique selon fabricant
- Erreur tolérable : selon arrêté du 6 mars 2007 (compteurs d'eau froide)
- Compteur inexact → remplacement à la charge de DALKIA
- Période d'indication erronée : estimation sur 12 mois "fiables" (corrigés DJU)

### Relevés mensuels transmis
Format **EXCEL + CSV**, avant le **5ème jour ouvrable** de chaque mois :
- Code site (conforme annexe n°1)
- Nom du site
- Nom du compteur
- Date du relevé
- Index relevé
- État de marche chauffage (O/N)

### Types de compteurs suivis
Gaz, ECS (m³), eau froide, eau adoucie, électricité, énergie thermique, appoint eau chauffage

---

## Intégration dans Po2

### Flux de données attendus
```
GRDF ADICT API ──→ Consommation gaz par site (QT mensuel)
ENEDIS API ──────→ Consommation électricité par site
GTC API (DALKIA) → Températures d'ambiance, statuts équipements, alarmes
```

### Traitement dans Po2
- Stockage des index mensuels par compteur et par site
- Calcul automatique NC = QT - (m × qECS) par site et par année
- Calcul N'B = NB × (DJU-réels / 1426) à partir des DJU COSTIC/Météoclim
- Comparaison NC vs N'B et calcul intéressement / pénalité

---

## Liens
- [[03-Cibles-et-intéressement]] — utilisation des données dans le calcul
- [[02-Énergie-fourniture]] — APIs GRDF et ENEDIS
- [[08-Gouvernance]] — reporting et délais transmission
