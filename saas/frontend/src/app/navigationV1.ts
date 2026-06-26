export type AppProfileV1 = "direction" | "fluides" | "technique" | "finances" | "patrimoine";
export type NavItemV1 = { key: string; label: string; to: string; badge?: string; };
export type NavSectionV1 = { label: string; items: NavItemV1[]; };
export const profilesV1: Record<AppProfileV1, string> = { direction: "Direction", fluides: "Responsable Fluides", technique: "Technicien CVC", finances: "Comptable", patrimoine: "Référent Patrimoine" };
export const navigationV1: NavSectionV1[] = [
  { label: "Pilotage", items: [{ key: "cockpit", label: "Mon cockpit", to: "/" }, { key: "invoices", label: "Factures & décisions", to: "/factures", badge: "12" }, { key: "matrices", label: "Matrices comptables", to: "/refonte-v1/matrices" }, { key: "sites", label: "Sites 360°", to: "/patrimoine/sites" }] },
  { label: "Métiers", items: [{ key: "fluids", label: "Fluides", to: "/energie" }, { key: "contracts", label: "Marchés & contrats", to: "/marches" }, { key: "maintenance", label: "Maintenance", to: "/technique", badge: "8" }, { key: "technique", label: "Technique & PPT", to: "/buildings/technique" }] },
  { label: "Ressources", items: [{ key: "patrimoine", label: "Patrimoine", to: "/patrimoine" }, { key: "admin", label: "Administration", to: "/administration" }] },
];
