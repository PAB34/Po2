import type { CockpitKpi, CockpitPriority } from "./cockpit.types";
export const cockpitKpisMock: CockpitKpi[] = [
  { label: "Budget opérationnel", value: "8,42 M€", detail: "74 % engagé", trend: "+2,1 % vs trajectoire" },
  { label: "Atterrissage annuel", value: "8,71 M€", detail: "+286 k€ de risque", trend: "À arbitrer" },
  { label: "Consommations fluides", value: "18,4 GWh", detail: "-6,8 % corrigé DJU", trend: "Tendance favorable" },
  { label: "Travaux prioritaires", value: "1,26 M€", detail: "14 actions critiques", trend: "5 à financer en N+1" },
];
export const cockpitPrioritiesMock: CockpitPriority[] = [
  { domain: "Factures", label: "12 factures attendent une décision", value: "184 320 €", proof: "Contrôle + matrice comptable", tone: "bad" },
  { domain: "Budget", label: "Opération 231 dépasse la trajectoire", value: "+86 400 €", proof: "Engagé + facturé + atterrissage", tone: "warn" },
  { domain: "Technique", label: "5 équipements critiques sans financement", value: "342 000 €", proof: "Criticité CVC + PPT", tone: "info" },
];
