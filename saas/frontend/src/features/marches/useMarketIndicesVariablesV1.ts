import { useQuery } from "@tanstack/react-query";
import { fetchMarketIndicesVariables } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

export function useMarketIndicesVariablesV1(yearFrom: number, yearTo: number) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["market-indices-variables", yearFrom, yearTo],
    enabled: Boolean(token),
    queryFn: () => fetchMarketIndicesVariables(token!, yearFrom, yearTo),
  });
}