import type { SheetNature, SheetStatus } from "./api";

export const NATURES: SheetNature[] = ["plan", "coupe", "facade", "plan_masse", "autre"];

export const NATURE_LABELS: Record<SheetNature, string> = {
  plan: "Plan de niveau",
  coupe: "Coupe",
  facade: "Façade",
  plan_masse: "Plan masse",
  autre: "Autre",
};

// Ce que chaque nature de planche apporte au métré : c'est ce qui les distingue.
export const NATURE_ROLES: Record<SheetNature, string> = {
  plan: "Murs, longueurs de façade, surfaces",
  coupe: "Hauteurs d'étage, épaisseurs de plancher",
  facade: "Baies, hauteurs de façade",
  plan_masse: "Orientation, implantation",
  autre: "Non utilisée dans le métré",
};

export const STATUS_LABELS: Record<SheetStatus, string> = {
  a_classer: "À classer",
  a_mettre_a_l_echelle: "Échelle à définir",
  prete: "Prête",
};
