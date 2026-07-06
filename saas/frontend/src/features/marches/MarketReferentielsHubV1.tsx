import { useState } from "react";
import { SegmentControl } from "../../design-system";
import { CpeDalkiaImportPage } from "../../pages/CpeDalkiaImportPage";
import { BpuReferentielV1 } from "./BpuReferentielV1";

// Hub « Référentiels des marchés » : point d'entrée unique des référentiels de prix —
//   - DPGF DALKIA (CPE)      -> page CpeDalkiaImportPage embarquée (dossier de marché complet :
//     import, sites, matrice, références DPGF, formules/indices, diff, journal des actes)
//   - BPU Hérault Énergies   -> vue curée DS V1 `BpuReferentielV1` (Consultation / Évolution,
//     admin replié « Gérer » ; la page legacy /energie/bpu reste pour l'accès complet).

type RefView = "dpgf" | "bpu";

const VIEWS: { value: RefView; label: string }[] = [
  { value: "dpgf", label: "DPGF — DALKIA (CPE)" },
  { value: "bpu", label: "BPU — Hérault Énergies (EDF · ENGIE · TotalEnergies)" },
];

export function MarketReferentielsHubV1() {
  const [view, setView] = useState<RefView>("dpgf");

  // Pas d'en-tête propre au hub : chaque page embarquée (CpeDalkiaImportPage / EnergieBpuPage)
  // porte déjà son propre titre. On n'ajoute qu'un sélecteur compact pour éviter le double bandeau.
  return (
    <div className="po2-page-v1">
      <div className="po2-page-v1__viewswitch" style={{ marginBottom: "0.5rem" }}>
        <span className="po2-eyebrow" style={{ display: "block", marginBottom: 8 }}>
          Référentiels des marchés
        </span>
        <SegmentControl value={view} options={VIEWS} onChange={setView} />
      </div>

      {view === "dpgf" ? <CpeDalkiaImportPage /> : <BpuReferentielV1 />}
    </div>
  );
}
