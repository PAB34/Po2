import type { ProjectDetail, Sheet } from "./api";

export const projectsQueryKey = ["thermique", "projects"] as const;

export function projectQueryKey(projectId: number) {
  return ["thermique", "project", projectId] as const;
}

export function allSheets(project: ProjectDetail): Sheet[] {
  return project.documents.flatMap((document) => document.sheets);
}

export function replaceSheet(project: ProjectDetail, sheet: Sheet): ProjectDetail {
  return {
    ...project,
    documents: project.documents.map((document) =>
      document.id !== sheet.document_id
        ? document
        : { ...document, sheets: document.sheets.map((item) => (item.id === sheet.id ? sheet : item)) },
    ),
  };
}

const dateFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });

export function formatDate(value: string): string {
  return dateFormat.format(new Date(value));
}

export function formatSize(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} Mo`;
}
