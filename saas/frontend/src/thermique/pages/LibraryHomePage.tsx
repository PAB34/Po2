import { useState } from "react";

import { ComponentLibrary } from "../library/ComponentLibrary";
import { ElementsPanel } from "./ElementsPanel";
import { MaterialsPanel } from "./MaterialsPanel";
import { WindowsLibraryPanel } from "./LibraryPage";

type Section = "modeles" | "menuiseries" | "materiaux" | "elements";

// « Mes modèles » : compositions réutilisables d'un projet à l'autre ; les autres onglets sont
// le référentiel Th-Bât (valeurs officielles, en lecture).
const SECTIONS: { id: Section; label: string }[] = [
  { id: "modeles", label: "Mes modèles" },
  { id: "menuiseries", label: "Référentiel : menuiseries" },
  { id: "materiaux", label: "Référentiel : matériaux" },
  { id: "elements", label: "Référentiel : éléments tabulés" },
];

function ModelsPanel() {
  return (
    <>
      <div className="th-page-head">
        <div>
          <p className="po2-eyebrow">Bibliothèque</p>
          <h1>Mes modèles</h1>
          <p className="th-muted">
            Vos compositions réutilisables d'un projet à l'autre. Dans un projet, « Depuis mes modèles » en fait une copie que vous
            pouvez adapter sans modifier le modèle.
          </p>
        </div>
      </div>
      <ComponentLibrary scope={{ kind: "modeles" }} />
    </>
  );
}

// Bibliothèque de composants, commune à l'étude thermique et au calcul des déperditions.
export function LibraryPage() {
  const [section, setSection] = useState<Section>("modeles");
  return (
    <>
      <div className="th-segmented th-section" role="tablist" aria-label="Bibliothèque de composants">
        {SECTIONS.map((item) => (
          <button key={item.id} type="button" className={section === item.id ? "is-active" : undefined} onClick={() => setSection(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      {section === "modeles" && <ModelsPanel />}
      {section === "menuiseries" && <WindowsLibraryPanel />}
      {section === "materiaux" && <MaterialsPanel />}
      {section === "elements" && <ElementsPanel />}
    </>
  );
}
