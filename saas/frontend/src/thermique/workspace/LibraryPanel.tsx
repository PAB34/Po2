import { useState } from "react";

import { ComponentLibrary } from "../library/ComponentLibrary";
import { ElementsPanel } from "../pages/ElementsPanel";
import { WindowsLibraryPanel } from "../pages/LibraryPage";
import { MaterialsPanel } from "../pages/MaterialsPanel";

type Section = "projet" | "modeles" | "menuiseries" | "materiaux" | "elements";

const SECTIONS: { id: Section; label: string }[] = [
  { id: "projet", label: "Ce projet" },
  { id: "modeles", label: "Mes modèles" },
  { id: "menuiseries", label: "Menuiseries" },
  { id: "materiaux", label: "Matériaux" },
  { id: "elements", label: "Éléments" },
];

// Panneau « Bibliothèque » : composants du projet, modèles du compte et référentiel Th-Bât (en lecture).
export function LibraryPanel({ projectId }: { projectId: number }) {
  const [section, setSection] = useState<Section>("projet");
  return (
    <>
      <div className="th-segmented th-ws-subtabs" role="tablist" aria-label="Bibliothèque">
        {SECTIONS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={section === item.id}
            className={section === item.id ? "is-active" : undefined}
            onClick={() => setSection(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {section === "projet" && <ComponentLibrary scope={{ kind: "projet", projectId }} />}
      {section === "modeles" && <ComponentLibrary scope={{ kind: "modeles" }} />}
      {section === "menuiseries" && <WindowsLibraryPanel />}
      {section === "materiaux" && <MaterialsPanel />}
      {section === "elements" && <ElementsPanel />}
    </>
  );
}
