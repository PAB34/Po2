import type { FluidDrift, FluidKpi, SubscriptionAnalysis } from "./fluids.types";
export const fluidKpisMock: FluidKpi[] = [
  { label: "Électricité", value: "11,8 GWh", detail: "-4,2 % vs N-1", trend: "Couverture 98 %", tone: "ok" },
  { label: "Gaz corrigé DJU", value: "6,2 GWh", detail: "-8,7 % vs référence", trend: "3 dérives à analyser", tone: "warn" },
  { label: "Atterrissage fluides", value: "2,94 M€", detail: "+48 k€ vs budget", trend: "Prix contractuels appliqués", tone: "bad" },
  { label: "Données distributeurs", value: "96,8 %", detail: "487 compteurs suivis", trend: "16 rattachements à traiter", tone: "info" },
];
export const subscriptionAnalysesMock: SubscriptionAnalysis[] = [
  { id: "fonquerne-elec", kind: "electricity", site: "Centre sportif Fonquerne", source: "ENEDIS", supplier: "ENGIE", meter: "PRM 30002411873001", current: "250 kVA", recommendation: "210 kVA", diagnostic: "Surdimensionné", potential: "3 840 €/an", confidence: "Haute · 99,2 %", tone: "ok" },
  { id: "hotel-elec", kind: "electricity", site: "Hôtel de Ville", source: "ENEDIS", supplier: "EDF", meter: "PRM 30002411928412", current: "160 kVA", recommendation: "190 kVA", diagnostic: "À sécuriser", potential: "+920 €/an", confidence: "Haute · 98,7 %", tone: "warn" },
  { id: "michelet-gas", kind: "gas", site: "École Michelet", source: "GRDF", supplier: "TotalEnergies", meter: "PCE GI077812", current: "CAR 1,20 GWh", recommendation: "Profil à revoir", diagnostic: "Écart contractuel", potential: "À chiffrer", confidence: "Moyenne · 94,1 %", tone: "warn" },
  { id: "water-future", kind: "water", site: "Médiathèque Mitterrand", source: "À raccorder", supplier: "Futur titulaire", meter: "Compteur principal · DN65", current: "DN65", recommendation: "Instrumenter", diagnostic: "Données insuffisantes", potential: "Non calculé", confidence: "À construire", tone: "info" },
];
export const fluidDriftsMock: FluidDrift[] = [
  { rank: 1, label: "Talon nocturne persistant", site: "Centre sportif Fonquerne", impact: "+42 MWh/an", proof: "Courbe de charge 30 min", tone: "bad" },
  { rank: 2, label: "Consommation week-end", site: "Hôtel de Ville", impact: "+11 MWh/an", proof: "Profil samedi supérieur de 34 %", tone: "warn" },
  { rank: 3, label: "Rupture de profil gaz", site: "École Michelet", impact: "Confiance 72 %", proof: "GRDF mensuel + DJU", tone: "info" },
];
