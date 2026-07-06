import { useState } from "react";
import { SegmentControl } from "../../design-system";
import { CpeDalkiaImportPage } from "../../pages/CpeDalkiaImportPage";
import EnergieBpuPage from "../../pages/EnergieBpuPage";

// Hub « Référentiels des marchés » : point d'entrée unique qui EMBARQUE les moteurs
// existants et fonctionnels (pas de réécriture) —
//   - DPGF DALKIA (CPE)      -> page CpeDalkiaImportPage (dossier de marché : import,
//     sites, matrice, références DPGF, formules/indices, diff, journal des actes)
//   - BPU Hérault Énergies   -> page EnergieBpuPage (tous fournisseurs EDF/ENGIE/TotalE :
//     timeline, TURPE, documents/import, édition)
// L'import et les révisions sont déjà gérés par ces pages ; ici on centralise l'accès.

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

      {view === "dpgf" ? <CpeDalkiaImportPage /> : <EnergieBpuPage />}
    </div>
  );
}
