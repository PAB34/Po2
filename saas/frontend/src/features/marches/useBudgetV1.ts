import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAccountingBudgetLine,
  deleteAccountingBudgetLine,
  fetchAccountingBudgetLines,
  fetchAccountingMatrixContracts,
  fetchBudgetSuivi,
  updateAccountingBudgetLine,
  type AccountingBudgetLineCreateV1,
  type AccountingBudgetLineUpdateV1,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

export function useMarketContractsV1() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["accounting-matrix-contracts"],
    enabled: Boolean(token),
    queryFn: () => fetchAccountingMatrixContracts(token!),
  });
}

export function useBudgetLinesV1(matrixContractId: number | null, year: number) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["accounting-budget-lines", matrixContractId, year],
    enabled: Boolean(token) && matrixContractId != null,
    queryFn: () => fetchAccountingBudgetLines(token!, matrixContractId!, year),
  });
}

export function useBudgetSuiviV1(matrixContractId: number | null, year: number) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["accounting-budget-suivi", matrixContractId, year],
    enabled: Boolean(token) && matrixContractId != null,
    queryFn: () => fetchBudgetSuivi(token!, matrixContractId!, year),
  });
}

function useInvalidateBudget(matrixContractId: number | null, year: number) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["accounting-budget-lines", matrixContractId, year] });
    queryClient.invalidateQueries({ queryKey: ["accounting-budget-suivi", matrixContractId, year] });
  };
}

export function useCreateBudgetLineV1(matrixContractId: number | null, year: number) {
  const { token } = useAuth();
  const invalidate = useInvalidateBudget(matrixContractId, year);
  return useMutation({
    mutationFn: (payload: AccountingBudgetLineCreateV1) => createAccountingBudgetLine(token!, payload),
    onSuccess: invalidate,
  });
}

export function useUpdateBudgetLineV1(matrixContractId: number | null, year: number) {
  const { token } = useAuth();
  const invalidate = useInvalidateBudget(matrixContractId, year);
  return useMutation({
    mutationFn: ({ lineId, payload }: { lineId: number; payload: AccountingBudgetLineUpdateV1 }) =>
      updateAccountingBudgetLine(token!, lineId, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteBudgetLineV1(matrixContractId: number | null, year: number) {
  const { token } = useAuth();
  const invalidate = useInvalidateBudget(matrixContractId, year);
  return useMutation({
    mutationFn: (lineId: number) => deleteAccountingBudgetLine(token!, lineId),
    onSuccess: invalidate,
  });
}
