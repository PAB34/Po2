import { useQuery } from "@tanstack/react-query";
import { fetchContractBudgetLanding } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

// Atterrissage « budget contractuel − réalisé » par poste CPE (stratégie §5bis).
export function useContractBudgetLandingV1(year: number, lot: number | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["cpe-contract-budget-landing", year, lot],
    enabled: Boolean(token),
    queryFn: () => fetchContractBudgetLanding(token!, year, lot),
  });
}
