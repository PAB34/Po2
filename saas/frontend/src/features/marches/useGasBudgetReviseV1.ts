import { useQuery } from "@tanstack/react-query";
import { fetchGasBudgetRevise } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

// Budget révisé gaz (reconstitution fixe/variable par PCE), réalisé et atterrissage.
export function useGasBudgetReviseV1(year: number) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["gas-budget-revise", year],
    enabled: Boolean(token),
    queryFn: () => fetchGasBudgetRevise(token!, year),
  });
}
