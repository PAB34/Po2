import { useQuery } from "@tanstack/react-query";
import { fetchCpeAccountingNatureRules, fetchCpeAccountingSiteMappings, fetchEnergyNatureRules, fetchEnergySiteMappings } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import { accountingMatricesMock } from "./invoices.mock";
import type { AccountingMatrixSummary } from "./invoices.types";

function pct(part: number, total: number) {
  if (total <= 0) return "0 %";
  return `${Math.round((part / total) * 100)} %`;
}
function activeLabel(active: number, total: number) {
  const inactive = Math.max(total - active, 0);
  return inactive === 0 ? "Aucune" : `${inactive} inactive(s)`;
}
export function useAccountingMatricesV1() {
  const { token } = useAuth();
  const query = useQuery({
    queryKey: ["accounting-matrices-v1"],
    enabled: Boolean(token),
    queryFn: async () => {
      const [energySites, energyRules, cpeSites, cpeRules] = await Promise.allSettled([
        fetchEnergySiteMappings(token!),
        fetchEnergyNatureRules(token!),
        fetchCpeAccountingSiteMappings(token!),
        fetchCpeAccountingNatureRules(token!),
      ]);
      const rows: AccountingMatrixSummary[] = [];
      if (energySites.status === "fulfilled" || energyRules.status === "fulfilled") {
        const sites = energySites.status === "fulfilled" ? energySites.value : [];
        const rules = energyRules.status === "fulfilled" ? energyRules.value : [];
        const activeRules = rules.filter((rule) => rule.active).length;
        const activeSites = sites.filter((site) => site.active).length;
        rows.push({ id: "energy-live", supplier: "ENGIE / EDF", contract: "Électricité · matrice énergie", version: "Live · codification actuelle", status: rules.length > 0 ? "Active" : "À compléter", coverage: pct(activeRules + activeSites, rules.length + sites.length), rules: `${rules.length} règles · ${sites.length} sites`, exceptions: activeLabel(activeRules + activeSites, rules.length + sites.length) });
      }
      if (cpeSites.status === "fulfilled" || cpeRules.status === "fulfilled") {
        const sites = cpeSites.status === "fulfilled" ? cpeSites.value : [];
        const rules = cpeRules.status === "fulfilled" ? cpeRules.value : [];
        const activeRules = rules.filter((rule) => rule.active).length;
        const activeSites = sites.filter((site) => site.active).length;
        rows.push({ id: "cpe-live", supplier: "DALKIA", contract: "CPE · codification finances", version: "Live · export DALKIA", status: rules.length > 0 ? "Active" : "Incomplète", coverage: pct(activeRules + activeSites, rules.length + sites.length), rules: `${rules.length} règles · ${sites.length} sites`, exceptions: activeLabel(activeRules + activeSites, rules.length + sites.length) });
      }
      const missingMock = accountingMatricesMock.filter((mock) => !rows.some((row) => row.supplier.includes(mock.supplier) || mock.supplier.includes(row.supplier)));
      return [...rows, ...missingMock];
    },
  });
  return { ...query, matrices: query.data ?? accountingMatricesMock, isUsingFallback: !token || query.isError || !query.data };
}
