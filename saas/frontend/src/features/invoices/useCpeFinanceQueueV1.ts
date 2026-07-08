import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  downloadCpeFinanceInvoiceLiaison,
  fetchCpeFinanceControlReport,
  fetchCpeFinanceControls,
  fetchCpeFinanceInvoiceLines,
  fetchCpeFinanceInvoices,
  fetchEnergyInvoiceBatch,
  fetchEnergyInvoiceImports,
  fetchSupplierContacts,
  purgeCpeFinanceDuplicates,
  purgeEnergyInvoiceDuplicates,
  reanalyzeAllEnergyInvoices,
  recalculateAllCpeFinanceControls,
  updateCpeFinanceInvoice,
  updateEnergyInvoiceDecision,
  uploadEdfCsvExport,
  uploadEngieXlsxExport,
  upsertSupplierContact,
  type EnergyInvoiceBatchDetail,
  type SupplierContactInput,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

/** Types de fichier d'import branchés en v1 (parseurs back existants). */
export type InvoiceImportKind = "engie_xlsx" | "edf_csv";

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

/** Contacts fournisseurs (réclamations) : liste + upsert par fournisseur. */
export function useSupplierContactsV1() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const contacts = useQuery({
    queryKey: ["supplier-contacts"],
    enabled: Boolean(token),
    retry: false,
    queryFn: () => fetchSupplierContacts(token!),
  });
  const save = useMutation({
    mutationFn: ({ supplier, payload }: { supplier: string; payload: SupplierContactInput }) => {
      if (!token) throw new Error("Session absente.");
      return upsertSupplierContact(token, supplier, payload);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["supplier-contacts"] }),
  });
  return { contacts, save };
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
  const purgeDuplicates = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Session absente.");
      const [cpe, energy] = await Promise.all([
        purgeCpeFinanceDuplicates(token),
        purgeEnergyInvoiceDuplicates(token),
      ]);
      return { removed: cpe.removed + energy.removed };
    },
    onSuccess: invalidate,
  });
  const recomputeControls = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Session absente.");
      const [, energy] = await Promise.all([
        recalculateAllCpeFinanceControls(token),
        reanalyzeAllEnergyInvoices(token),
      ]);
      return { reanalyzed: energy.reanalyzed };
    },
    onSuccess: invalidate,
  });
  return { setStatus, setEnergyStatus, exportLiaison, purgeDuplicates, recomputeControls };
}

const IMPORT_POLL_INTERVAL_MS = 1500;
const IMPORT_POLL_MAX_TRIES = 40; // ~60 s max

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** Import d'un fichier de factures (ENGIE xlsx / EDF csv). L'analyse back est
 *  asynchrone : on poste, puis on poll le batch jusqu'à finalisation pour renvoyer
 *  le compte-rendu (créées / doublons / erreurs). Rafraîchit la file après import. */
export function useInvoiceImportV1() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const runImport = useMutation({
    mutationFn: async (
      { kind, file, forceUpdate }: { kind: InvoiceImportKind; file: File; forceUpdate: boolean },
    ): Promise<EnergyInvoiceBatchDetail> => {
      if (!token) throw new Error("Session absente.");
      const batch = kind === "engie_xlsx"
        ? await uploadEngieXlsxExport(token, file, { forceUpdate })
        : await uploadEdfCsvExport(token, file, { forceUpdate });
      let current = batch;
      for (let i = 0; i < IMPORT_POLL_MAX_TRIES && current.status === "processing"; i += 1) {
        await delay(IMPORT_POLL_INTERVAL_MS);
        current = await fetchEnergyInvoiceBatch(token, batch.id);
      }
      return current;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["energy-invoice-imports"] });
      queryClient.invalidateQueries({ queryKey: ["cpe-finance-control-report"] });
      queryClient.invalidateQueries({ queryKey: ["cpe-finance-invoices"] });
    },
  });
  return { runImport };
}
