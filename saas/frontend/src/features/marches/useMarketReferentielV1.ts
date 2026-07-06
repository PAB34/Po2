import { useQuery } from "@tanstack/react-query";
import {
  fetchMarketBpuDocuments,
  fetchMarketDpgfImports,
  fetchMarketDpgfSummary,
  fetchMarketGasBpu,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

/** BPU électricité (ENGIE / EDF) — liste des documents en vigueur / historisés. */
export function useMarketBpuDocumentsV1(supplier: string) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["market-bpu-documents", supplier],
    enabled: Boolean(token),
    queryFn: () => fetchMarketBpuDocuments(token!, supplier),
  });
}

/** BPU gaz lot 7 (TotalEnergies) — grille de prix de référence. */
export function useMarketGasBpuV1() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["market-gas-bpu"],
    enabled: Boolean(token),
    queryFn: () => fetchMarketGasBpu(token!),
  });
}

/** DPGF DALKIA — synthèse de l'état du marché en vigueur. */
export function useMarketDpgfSummaryV1(refYear: number) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["market-dpgf-summary", refYear],
    enabled: Boolean(token),
    queryFn: () => fetchMarketDpgfSummary(token!, refYear),
  });
}

/** DPGF DALKIA — journal des actes (imports maîtres, toutes versions). */
export function useMarketDpgfImportsV1() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["market-dpgf-imports"],
    enabled: Boolean(token),
    queryFn: () => fetchMarketDpgfImports(token!),
  });
}
