import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  commitAccountingMatrixImport,
  downloadAccountingMatrixVersionXlsx,
  fetchAccountingMatrixContract,
  fetchAccountingMatrixContracts,
  fetchAccountingMatrixVersionRules,
  previewAccountingMatrixImport,
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

export function useExportMatrixVersionV1() {
  const { token } = useAuth();
  return useMutation({
    mutationFn: ({ versionId, label }: { versionId: number; label?: string }) =>
      downloadAccountingMatrixVersionXlsx(token!, versionId, label),
  });
}

export function usePreviewMatrixImportV1() {
  const { token } = useAuth();
  return useMutation({
    mutationFn: ({ contractId, file }: { contractId: number; file: File }) =>
      previewAccountingMatrixImport(token!, contractId, file),
  });
}

export function useCommitMatrixImportV1() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contractId, versionLabel, file }: { contractId: number; versionLabel: string; file: File }) =>
      commitAccountingMatrixImport(token!, contractId, versionLabel, file),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: CONTRACTS_KEY });
      queryClient.invalidateQueries({ queryKey: ["accounting-matrix-contract", variables.contractId] });
    },
  });
}