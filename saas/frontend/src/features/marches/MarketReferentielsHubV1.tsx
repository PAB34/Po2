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

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Moteurs métiers — Référentiels des marchés</span>
        <h1>Référentiels contractuels — DPGF &amp; BPU</h1>
        <p>
          Point d'entrée unique des référentiels de prix des marchés : le DPGF du CPE DALKIA et les BPU de
          fourniture Hérault Énergies. Import, révisions et historique sont assurés par les moteurs existants,
          ici regroupés au même endroit.
        </p>
      </header>

      <div className="po2-page-v1__viewswitch" style={{ marginBottom: "1rem" }}>
        <SegmentControl value={view} options={VIEWS} onChange={setView} />
      </div>

      {view === "dpgf" ? <CpeDalkiaImportPage /> : <EnergieBpuPage />}
    </div>
  );
}
