import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  downloadCpeFinanceInvoiceLiaison,
  fetchCpeFinanceControlReport,
  fetchCpeFinanceControls,
  fetchCpeFinanceInvoiceLines,
  fetchCpeFinanceInvoices,
  fetchEnergyInvoiceImports,
  updateCpeFinanceInvoice,
  updateEnergyInvoiceDecision,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

/** File de contrôle facture par facture (moteur CPE/DALKIA) + dates d'émission. */
export function useCpeFinanceQueueV1() {
  const { token } = useAuth();
  const report = useQuery({
    queryKey: ["cpe-finance-control-report"],
    enabled: Boolean(token),
    retry: false,
    queryFn: () => fetchCpeFinanceControlReport(token!),
  });
  const invoices = useQuery({
    queryKey: ["cpe-finance-invoices"],
    enabled: Boolean(token),
    retry: false,
    queryFn: () => fetchCpeFinanceInvoices(token!),
  });
  const energy = useQuery({
    queryKey: ["energy-invoice-imports"],
    enabled: Boolean(token),
    retry: false,
    queryFn: () => fetchEnergyInvoiceImports(token!),
  });
  return { report, invoices, energy };
}

/** Détail d'une facture : contrôles par type + lignes (décomposition comptable). */
export function useCpeInvoiceDetailV1(invoiceId: number | null) {
  const { token } = useAuth();
  const controls = useQuery({
    queryKey: ["cpe-finance-controls", invoiceId],
    enabled: Boolean(token) && invoiceId != null,
    retry: false,
    queryFn: () => fetchCpeFinanceControls(token!, invoiceId!),
  });
  const lines = useQuery({
    queryKey: ["cpe-finance-lines", invoiceId],
    enabled: Boolean(token) && invoiceId != null,
    retry: false,
    queryFn: () => fetchCpeFinanceInvoiceLines(token!, invoiceId!),
  });
  return { controls, lines };
}

/** Actions comptable : valider un numéro de facture, exporter la fiche finance. */
export function useCpeInvoiceActionsV1() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["cpe-finance-control-report"] });
    queryClient.invalidateQueries({ queryKey: ["cpe-finance-invoices"] });
    queryClient.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
  };
  const setStatus = useMutation({
    mutationFn: ({ invoiceId, status }: { invoiceId: number; status: string }) => {
      if (!token) throw new Error("Session absente.");
      return updateCpeFinanceInvoice(token, invoiceId, { status });
    },
    onSuccess: invalidate,
  });
  const setEnergyStatus = useMutation({
    mutationFn: ({ importId, decisionStatus }: { importId: number; decisionStatus: "to_review" | "approved" | "rejected" | "dispute_sent" }) => {
      if (!token) throw new Error("Session absente.");
      return updateEnergyInvoiceDecision(token, importId, { decision_status: decisionStatus });
    },
    onSuccess: invalidate,
  });
  const exportLiaison = useMutation({
    mutationFn: async ({ invoiceId, invoiceNumber }: { invoiceId: number; invoiceNumber: string }) => {
      if (!token) throw new Error("Session absente.");
      const blob = await downloadCpeFinanceInvoiceLiaison(token, invoiceId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `liaison-finance-${invoiceNumber}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    },
  });
  return { setStatus, setEnergyStatus, exportLiaison };
}
