import { useState } from "react";
import { Card, SegmentControl } from "../../design-system";
import { ContractBudgetLandingV1 } from "./ContractBudgetLandingV1";
import { CpeCibleConsoV1 } from "./CpeCibleConsoV1";
import { ElecBudgetReviseV1 } from "./ElecBudgetReviseV1";
import { GasBudgetReviseV1 } from "./GasBudgetReviseV1";
import { IndicesVariablesV1 } from "./IndicesVariablesV1";

type MarketTier = "dalkia" | "gaz" | "engie" | "edf";
type SubView = "atterrissage" | "cible" | "indices";

type TierConfig = {
  value: MarketTier;
  label: string;
  eyebrow: string;
  families: string[]; // familles indices affichées pour ce tier
  subs: { value: SubView; label: string }[];
};

const TIERS: TierConfig[] = [
  {
    value: "dalkia",
    label: "DALKIA CPE",
    eyebrow: "Performance énergétique",
    families: ["dalkia"],
    subs: [
      { value: "atterrissage", label: "Atterrissage (budget / révisé / réalisé)" },
      { value: "cible", label: "Cible conso & intéressement" },
      { value: "indices", label: "Indices & variables" },
    ],
  },
  {
    value: "gaz",
    label: "Gaz TotalEnergies",
    eyebrow: "Hérault Énergie (Ville)",
    families: ["gaz"],
    subs: [
      { value: "atterrissage", label: "Atterrissage (fixe / variable)" },
      { value: "indices", label: "Indices & variables" },
    ],
  },
  {
    value: "engie",
    label: "ENGIE",
    eyebrow: "Électricité",
    families: ["elec"],
    subs: [
      { value: "atterrissage", label: "Atterrissage" },
      { value: "indices", label: "Indices & variables" },
    ],
  },
  {
    value: "edf",
    label: "EDF",
    eyebrow: "Éclairage public",
    families: ["elec"],
    subs: [
      { value: "atterrissage", label: "Atterrissage" },
      { value: "indices", label: "Indices & variables" },
    ],
  },
];

function ComingSoon({ tier }: { tier: MarketTier }) {
  const supplier = tier === "engie" ? "ENGIE" : "EDF";
  return (
    <div className="po2-page-v1">
      <Card title={`Atterrissage ${supplier} — à venir`} eyebrow="prochain incrément">
        <p className="po2-muted-line">
          Le moteur d'atterrissage fixe / variable sera branché pour {supplier} sur le même patron que le gaz :
          part variable = conso attendue (ENEDIS) × prix de référence (fourniture BPU + acheminement TURPE), part
          fixe = abonnement + TURPE fixe. L'onglet « Indices &amp; variables » ci-dessus montre déjà l'évolution
          TURPE utilisée pour la révision.
        </p>
      </Card>
    </div>
  );
}

export function MarketsBudgetPageV1() {
  const [tier, setTier] = useState<MarketTier>("dalkia");
  const [sub, setSub] = useState<SubView>("atterrissage");

  const tierConfig = TIERS.find((t) => t.value === tier) ?? TIERS[0];
  const activeSub = tierConfig.subs.some((s) => s.value === sub) ? sub : tierConfig.subs[0].value;

  function handleTierChange(next: MarketTier) {
    setTier(next);
    const nextTier = TIERS.find((t) => t.value === next) ?? TIERS[0];
    if (!nextTier.subs.some((s) => s.value === sub)) {
      setSub(nextTier.subs[0].value);
    }
  }

  return (
    <div className="po2-page-v1">
      <header className="po2-page-v1__head">
        <span className="po2-eyebrow">Marchés &amp; contrats</span>
        <h1>Marchés — budget, atterrissage et indices</h1>
        <p>
          Choisis un marché (tiers), puis navigue entre son atterrissage (budget base / révisé / réalisé) et le
          suivi des indices &amp; variables qui pilotent sa révision.
        </p>
      </header>

      <div className="po2-matrix-supplier-grid" style={{ marginBottom: "1rem" }}>
        {TIERS.map((t) => (
          <button
            type="button"
            key={t.value}
            className={
              t.value === tier
                ? "po2-matrix-supplier-card po2-matrix-supplier-card--active"
                : "po2-matrix-supplier-card"
            }
            onClick={() => handleTierChange(t.value)}
          >
            <span className="po2-eyebrow">{t.eyebrow}</span>
            <strong>{t.label}</strong>
          </button>
        ))}
      </div>

      <div className="po2-page-v1__viewswitch" style={{ marginBottom: "1rem" }}>
        <SegmentControl value={activeSub} options={tierConfig.subs} onChange={setSub} />
      </div>

      {activeSub === "indices" ? (
        <IndicesVariablesV1 embedded families={tierConfig.families} />
      ) : tier === "dalkia" && activeSub === "cible" ? (
        <CpeCibleConsoV1 />
      ) : tier === "dalkia" && activeSub === "atterrissage" ? (
        <ContractBudgetLandingV1 />
      ) : tier === "gaz" && activeSub === "atterrissage" ? (
        <GasBudgetReviseV1 />
      ) : tier === "engie" && activeSub === "atterrissage" ? (
        <ElecBudgetReviseV1 supplier="ENGIE" />
      ) : tier === "edf" && activeSub === "atterrissage" ? (
        <ElecBudgetReviseV1 supplier="EDF" />
      ) : (
        <ComingSoon tier={tier} />
      )}
    </div>
  );
}
