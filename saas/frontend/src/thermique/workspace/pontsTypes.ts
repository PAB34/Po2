import type { PontType, PontsCatalogue } from "../api";

/** Un pont que le catalogue ne couvre pas : compté, mais sa valeur ψ se calcule à part (NF EN ISO 10211). */
export const A_MODELISER = "a_modeliser";

/** Les trois liaisons que l'agent relève, et ce qu'on peut en faire en les réattribuant. */
export const TYPES_PONT_REATTRIBUABLES = [
  { type: "angle_sortant", label: "Angle sortant" },
  { type: "angle_rentrant", label: "Angle rentrant" },
  { type: "about_refend", label: "About de refend (mur intérieur)" },
] as const;

/**
 * Les ponts types qui correspondent à une liaison du relevé (D158) : un angle sortant renvoie à C1–C4,
 * un angle rentrant à C5–C8, un about de refend à IW1–IW6. Les autres familles restent proposables, à
 * part : un « angle » de l'agent peut être en réalité un balcon ou un poteau.
 */
export function pontsTypesPour(catalogue: PontsCatalogue, type: string): PontType[] {
  return catalogue.ponts.filter((pont) =>
    type === "angle_sortant"
      ? pont.famille === "C" && pont.angle === "sortant"
      : type === "angle_rentrant"
        ? pont.famille === "C" && pont.angle === "rentrant"
        : type === "about_refend"
          ? pont.famille === "IW"
          : false,
  );
}

const psi = (valeur: number) => valeur.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** « C1 — isolant à l'extérieur · ψi 0,15 W/(m·K) ». ψi : l'outil mesure au nu intérieur (D159). */
export function libellePontType(pont: PontType, catalogue: PontsCatalogue): string {
  const precisions = [
    pont.angle ? `angle ${pont.angle}` : "",
    pont.isolant ? `isolant ${catalogue.emplacement_isolant[pont.isolant] ?? pont.isolant}` : "",
    pont.plancher ? `plancher ${pont.plancher}` : "",
    pont.croquis ?? "",
  ].filter(Boolean);
  return `${pont.code}${precisions.length ? ` — ${precisions.join(", ")}` : ""} · ψi ${psi(pont.psi_i)} W/(m·K)`;
}

/** Ce qu'on dit d'une référence déjà posée sur un pont. */
export function libelleReference(reference: string | undefined, catalogue: PontsCatalogue | null | undefined): string | null {
  if (!reference) return null;
  if (reference === A_MODELISER) return "À modéliser : absent du catalogue, ψ à calculer (NF EN ISO 10211)";
  const pont = catalogue?.ponts.find((item) => item.code === reference);
  return pont && catalogue ? `Pont type ${libellePontType(pont, catalogue)}` : `Pont type ${reference}`;
}
