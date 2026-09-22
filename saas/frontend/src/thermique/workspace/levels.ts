import type { Sheet } from "../api";

// Rang d'un niveau d'après son libellé : sous-sols négatifs, RDC = 0, étages positifs, toiture en dernier.
export function levelRank(label: string | null): number | null {
  if (!label) {
    return null;
  }
  const text = label
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (/toit|terrasse|couverture/.test(text)) {
    return 99;
  }
  if (/\brdc\b|rez|\br ?0\b|niveau ?0\b|\bn ?0\b/.test(text)) {
    return 0;
  }
  const basement = text.match(/sous[- ]?sol ?(\d*)|\bss ?(\d*)\b|\br ?- ?(\d+)|niveau ?- ?(\d+)|\bn ?- ?(\d+)/);
  if (basement) {
    const digits = basement.slice(1).find((group) => group);
    return -Number(digits || 1);
  }
  const upper = text.match(/\br ?\+ ?(\d+)|niveau ?\+? ?(\d+)|\bn ?\+? ?(\d+)\b|etage ?(\d+)|(\d+)(?:er|e|eme) etage/);
  if (upper) {
    return Number(upper.slice(1).find((group) => group));
  }
  return null;
}

export function sheetTitle(sheet: Sheet): string {
  return sheet.level_label?.trim() || sheet.label;
}

export type SheetGroups = {
  levels: Sheet[];
  sections: Sheet[];
  elevations: Sheet[];
  others: Sheet[];
};

// Plans de niveau dans l'ordre du bâtiment (niveaux non reconnus à la fin, par libellé), puis le reste par type.
export function groupSheets(sheets: Sheet[]): SheetGroups {
  const byTitle = (a: Sheet, b: Sheet) => sheetTitle(a).localeCompare(sheetTitle(b), "fr", { numeric: true });
  const levels = sheets
    .filter((sheet) => sheet.nature === "plan")
    .sort((a, b) => {
      const ra = levelRank(a.level_label) ?? levelRank(a.label) ?? 50;
      const rb = levelRank(b.level_label) ?? levelRank(b.label) ?? 50;
      return ra - rb || byTitle(a, b);
    });
  return {
    levels,
    sections: sheets.filter((sheet) => sheet.nature === "coupe").sort(byTitle),
    elevations: sheets.filter((sheet) => sheet.nature === "facade").sort(byTitle),
    others: sheets.filter((sheet) => sheet.nature !== "plan" && sheet.nature !== "coupe" && sheet.nature !== "facade").sort(byTitle),
  };
}

// Plan de référence (D48) : celui choisi par le thermicien, sinon le RDC, sinon le premier plan, sinon la première planche.
export function referenceSheet(sheets: Sheet[], chosenId: number | null): Sheet | undefined {
  const chosen = sheets.find((sheet) => sheet.id === chosenId);
  if (chosen) {
    return chosen;
  }
  const { levels } = groupSheets(sheets);
  return (
    levels.find((sheet) => (levelRank(sheet.level_label) ?? levelRank(sheet.label)) === 0) ??
    levels[0] ??
    sheets[0]
  );
}
