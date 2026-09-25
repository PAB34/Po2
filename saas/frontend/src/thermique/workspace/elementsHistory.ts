import type { StudyContent, StudyOperation } from "../api";
import { appliquerEnLocal } from "./elementsLocal";

export type ElementsHistory = {
  operations: StudyOperation[];
  annulees: StudyOperation[];
};

export function rejouerOperations(base: StudyContent, operations: StudyOperation[]): StudyContent {
  return operations.reduce((content, operation) => appliquerEnLocal(content, operation), base);
}

export function annulerOperation(history: ElementsHistory): ElementsHistory {
  const derniere = history.operations.at(-1);
  if (!derniere) return history;
  return {
    operations: history.operations.slice(0, -1),
    annulees: [...history.annulees, derniere],
  };
}

export function retablirOperation(history: ElementsHistory): ElementsHistory {
  const derniere = history.annulees.at(-1);
  if (!derniere) return history;
  return {
    operations: [...history.operations, derniere],
    annulees: history.annulees.slice(0, -1),
  };
}

export function cibleEditable(target: EventTarget | null): boolean {
  if (!target || typeof (target as Element).matches !== "function") return false;
  return (target as Element).matches("input, textarea, select, [contenteditable]:not([contenteditable='false'])");
}
