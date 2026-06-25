import type { Site360, SiteDecision } from "./sites.types";
export const sitesMock: Site360[] = [
  { id: "beaux-arts", name: "École des Beaux-Arts", address: "23 rue Jean Moulin · Sète", usage: "Enseignement", quality: "96 %", budget: "142 k€", energy: "-7,2 %", equipment: "18", critical: "2", meters: "2 PRM · 1 PCE" },
  { id: "hotel-ville", name: "Hôtel de Ville", address: "20 bis rue Paul Valéry · Sète", usage: "Administration", quality: "93 %", budget: "386 k€", energy: "+1,8 %", equipment: "42", critical: "4", meters: "3 PRM · 2 PCE" },
  { id: "fonquerne", name: "Centre sportif Fonquerne", address: "1 chemin des Poules d’Eau · Sète", usage: "Sport", quality: "88 %", budget: "611 k€", energy: "+12,4 %", equipment: "67", critical: "7", meters: "5 PRM · 3 PCE" },
  { id: "mitterrand", name: "Médiathèque Mitterrand", address: "Boulevard Danielle Casanova · Sète", usage: "Culture", quality: "98 %", budget: "218 k€", energy: "-4,1 %", equipment: "31", critical: "1", meters: "2 PRM · 1 PCE" },
];
export const siteDecisionsMock: SiteDecision[] = [
  { label: "Facture à décider", value: "TotalEnergies TG-88412", proof: "Contrôle + matrice comptable", tone: "warn" },
  { label: "Abonnement à vérifier", value: "2 PRM · 1 PCE", proof: "Courbe de charge / profil distributeur", tone: "info" },
  { label: "Maintenance", value: "2 équipements critiques", proof: "Couverture DALKIA / SPIE et action P3", tone: "bad" },
  { label: "Budget site", value: "142 k€", proof: "Atterrissage et arbitrage annuel", tone: "info" },
];
