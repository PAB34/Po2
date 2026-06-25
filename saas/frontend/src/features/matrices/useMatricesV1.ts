import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchAccountingMatrixContract,
  fetchAccountingMatrixContracts,
  fetchAccountingMatrixVersionRules,
  seedAccountingMatrices,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

const CONTRACTS_KEY = ["accounting-matrix-contracts"] as const;

export function useMatrixContractsV1() {
  const { token } = useAuth();
  return useQuery({
    queryKey: CONTRACTS_KEY,
    enabled: Boolean(token),
    queryFn: () => fetchAccountingMatrixContracts(token!),
  });
}

export function useMatrixContractDetailV1(contractId: number | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["accounting-matrix-contract", contractId],
    enabled: Boolean(token) && contractId != null,
    queryFn: () => fetchAccountingMatrixContract(token!, contractId!),
  });
}

export function useMatrixVersionRulesV1(versionId: number | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["accounting-matrix-version-rules", versionId],
    enabled: Boolean(token) && versionId != null,
    queryFn: () => fetchAccountingMatrixVersionRules(token!, versionId!),
  });
}

export function useSeedMatricesV1() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => seedAccountingMatrices(token!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CONTRACTS_KEY }),
  });
}
