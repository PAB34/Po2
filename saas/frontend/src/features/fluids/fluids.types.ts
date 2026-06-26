export type FluidKind = "electricity" | "gas" | "water";
export type FluidAlertTone = "ok" | "warn" | "bad" | "info";
export type FluidKpi = { label: string; value: string; detail: string; trend?: string; tone?: FluidAlertTone; };
export type SubscriptionAnalysis = { id: string; kind: FluidKind; site: string; source: string; supplier: string; meter: string; current: string; recommendation: string; diagnostic: string; potential: string; confidence: string; tone: FluidAlertTone; };
export type FluidDrift = { rank: number; label: string; site: string; impact: string; proof: string; tone: FluidAlertTone; };
