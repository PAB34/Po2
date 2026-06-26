import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  applyAccountingMatrixToInvoice,
  exportInvoiceAccountingSnapshotToFinance,
  fetchInvoiceAccountingSnapshot,
  validateInvoiceAccountingSnapshot,
  type ApplyAccountingMatrixPayloadV1,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import type { InvoiceDecisionV1 } from "./invoiceDecisionV1.types";

function snapshotKey(invoice: InvoiceDecisionV1 | null) {
  return ["invoice-accounting-snapshot-v1", invoice?.source, invoice?.sourceId] as const;
}

export function useInvoiceAccountingSnapshotV1(invoice: InvoiceDecisionV1 | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: snapshotKey(invoice),
    enabled: Boolean(token && invoice && invoice.source !== "mock"),
    retry: false,
    queryFn: () => fetchInvoiceAccountingSnapshot(token!, invoice!.source, invoice!.sourceId),
  });
}

export function useInvoiceAccountingActionsV1(invoice: InvoiceDecisionV1 | null) {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const invalidate = () => {
    if (invoice) queryClient.invalidateQueries({ queryKey: snapshotKey(invoice) });
  };

  const apply = useMutation({
    mutationFn: (payload: ApplyAccountingMatrixPayloadV1) => {
      if (!token || !invoice) throw new Error("Facture ou session absente.");
      return applyAccountingMatrixToInvoice(token, invoice.source, invoice.sourceId, payload);
    },
    onSuccess: invalidate,
  });

  const validate = useMutation({
    mutationFn: () => {
      if (!token || !invoice) throw new Error("Facture ou session absente.");
      return validateInvoiceAccountingSnapshot(token, invoice.source, invoice.sourceId);
    },
    onSuccess: invalidate,
  });

  const exportFinance = useMutation({
    mutationFn: () => {
      if (!token || !invoice) throw new Error("Facture ou session absente.");
      return exportInvoiceAccountingSnapshotToFinance(token, invoice.source, invoice.sourceId);
    },
    onSuccess: invalidate,
  });

  return { apply, validate, exportFinance };
}
