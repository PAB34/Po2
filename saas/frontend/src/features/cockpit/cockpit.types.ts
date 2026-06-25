export type CockpitPriorityTone = "bad" | "warn" | "info";
export type CockpitKpi = { label: string; value: string; detail: string; trend?: string; };
export type CockpitPriority = { domain: string; label: string; value: string; proof: string; tone: CockpitPriorityTone; };
