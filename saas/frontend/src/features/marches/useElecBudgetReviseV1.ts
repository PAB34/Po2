import { useQuery } from "@tanstack/react-query";
import { fetchEdfBudgetRevise, fetchEngieBudgetRevise } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

export type ElecSupplier = "ENGIE" | "EDF";

// Budget révisé élec (fixe/variable par PRM + agrégats), réalisé et atterrissage — ENGIE ou EDF.
export function useElecBudgetReviseV1(supplier: ElecSupplier, year: number) {
  const { token } = useAuth();
  const fetcher = supplier === "EDF" ? fetchEdfBudgetRevise : fetchEngieBudgetRevise;
  return useQuery({
    queryKey: ["elec-budget-revise", supplier, year],
    enabled: Boolean(token),
    queryFn: () => fetcher(token!, year),
  });
}
