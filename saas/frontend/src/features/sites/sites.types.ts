export type Site360 = { id: string; name: string; address: string; usage: string; quality: string; budget: string; energy: string; equipment: string; critical: string; meters: string; };
export type SiteDecision = { label: string; value: string; proof: string; tone: "ok" | "warn" | "bad" | "info"; };
