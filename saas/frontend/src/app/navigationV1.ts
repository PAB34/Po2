export type AppProfileV1 = "direction" | "fluides" | "technique" | "finances" | "patrimoine";
export type NavItemV1 = { key: string; label: string; to: string; badge?: string; comingSoon?: boolean; };
export type NavSectionV1 = { label: string; items: NavItemV1[]; };
export const profilesV1: Record<AppProfileV1, string> = { direction: "Direction", fluides: "Responsable Fluides", technique: "Technicien CVC", finances: "Comptable", patrimoine: "Référent Patrimoine" };
export const navigationV1: NavSectionV1[] = [
  { label: "Pilotage", items: [
    { key: "cockpit", label: "Cockpit", to: "/refonte-v1" },
    { key: "invoices", label: "Factures & décisions", to: "/refonte-v1/factures", badge: "12" },
  ] },
  { label: "Patrimoine", items: [
    { key: "sites", label: "Sites 360°", to: "/refonte-v1/sites" },
    { key: "meters", label: "Compteurs & matching", to: "/refonte-v1/compteurs", comingSoon: true },
  ] },
  { label: "Moteurs métiers", items: [
    { key: "fluids", label: "Énergie / Fluides", to: "/refonte-v1/fluides" },
    { key: "contracts", label: "Marchés & contrats", to: "/refonte-v1/marches" },
    { key: "technique", label: "Technique & CVC", to: "/refonte-v1/technique", comingSoon: true },
  ] },
  { label: "Référentiels & admin", items: [
    { key: "referentiels", label: "Référentiels marchés", to: "/refonte-v1/referentiels" },
    { key: "matrices", label: "Matrices comptables", to: "/refonte-v1/matrices" },
    { key: "admin", label: "Administration", to: "/refonte-v1/administration", comingSoon: true },
  ] },
];
