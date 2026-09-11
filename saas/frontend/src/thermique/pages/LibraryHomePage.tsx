import { useState } from "react";

import { ElementsPanel } from "./ElementsPanel";
import { MaterialsPanel } from "./MaterialsPanel";
import { WallCalculatorPanel } from "./WallCalculatorPanel";
import { WindowsLibraryPanel } from "./LibraryPage";

type Section = "menuiseries" | "materiaux" | "elements" | "paroi";

const SECTIONS: { id: Section; label: string }[] = [
  { id: "menuiseries", label: "Menuiseries" },
  { id: "materiaux", label: "Matériaux" },
  { id: "elements", label: "Éléments tabulés" },
  { id: "paroi", label: "Composer une paroi" },
];

// Bibliothèque de composants, commune à l'étude thermique et au calcul des déperditions.
export function LibraryPage() {
  const [section, setSection] = useState<Section>("menuiseries");
  return (
    <>
      <div className="th-segmented th-section" role="tablist" aria-label="Bibliothèque de composants">
        {SECTIONS.map((item) => (
          <button key={item.id} type="button" className={section === item.id ? "is-active" : undefined} onClick={() => setSection(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      {section === "menuiseries" && <WindowsLibraryPanel />}
      {section === "materiaux" && <MaterialsPanel />}
      {section === "elements" && <ElementsPanel />}
      {section === "paroi" && <WallCalculatorPanel />}
    </>
  );
}
