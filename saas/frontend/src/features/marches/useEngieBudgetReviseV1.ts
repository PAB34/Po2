import { useQuery } from "@tanstack/react-query";
import { fetchEngieBudgetRevise } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

// Budget révisé ENGIE élec (fixe/variable par PRM + agrégat bâtiment), réalisé et atterrissage.
export function useEngieBudgetReviseV1(year: number) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["engie-elec-budget-revise", year],
    enabled: Boolean(token),
    queryFn: () => fetchEngieBudgetRevise(token!, year),
  });
}
