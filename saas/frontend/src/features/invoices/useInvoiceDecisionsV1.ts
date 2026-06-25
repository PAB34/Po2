import { useQuery } from "@tanstack/react-query";
import { fetchCpeFinanceInvoices, fetchEnergyInvoiceImports, fetchGasInvoices } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import { invoicesMock } from "./invoices.mock";
import { adaptCpeFinanceInvoiceToDecisionV1, adaptEnergyInvoiceImportToDecisionV1, adaptGasInvoiceToDecisionV1 } from "./invoiceDecisionV1.adapters";
import type { InvoiceDecisionV1 } from "./invoiceDecisionV1.types";

function rank(invoice: InvoiceDecisionV1) {
  const statusRank: Record<InvoiceDecisionV1["status"], number> = { anomalie: 0, decision: 1, conforme: 2, transmise: 3, archivee: 4 };
  const due = invoice.dueAt ? Date.parse(invoice.dueAt) : Number.POSITIVE_INFINITY;
  return [statusRank[invoice.status] ?? 9, Number.isNaN(due) ? Number.POSITIVE_INFINITY : due, invoice.invoiceNumber] as const;
}
function sortInvoices(a: InvoiceDecisionV1, b: InvoiceDecisionV1) {
  const ar = rank(a);
  const br = rank(b);
  return ar[0] - br[0] || ar[1] - br[1] || ar[2].localeCompare(br[2]);
}

export function useInvoiceDecisionsV1() {
  const { token } = useAuth();
  const query = useQuery({
    queryKey: ["invoice-decisions-v1"],
    enabled: Boolean(token),
    queryFn: async () => {
      const [energy, gas, cpe] = await Promise.allSettled([
        fetchEnergyInvoiceImports(token!),
        fetchGasInvoices(token!),
        fetchCpeFinanceInvoices(token!),
      ]);
      const rows: InvoiceDecisionV1[] = [];
      if (energy.status === "fulfilled") rows.push(...energy.value.map(adaptEnergyInvoiceImportToDecisionV1));
      if (gas.status === "fulfilled") rows.push(...gas.value.map(adaptGasInvoiceToDecisionV1));
      if (cpe.status === "fulfilled") rows.push(...cpe.value.map(adaptCpeFinanceInvoiceToDecisionV1));
      if (rows.length === 0) return invoicesMock;
      return rows.sort(sortInvoices);
    },
  });
  return { ...query, invoices: query.data ?? invoicesMock, isUsingFallback: !token || query.isError || !query.data };
}
