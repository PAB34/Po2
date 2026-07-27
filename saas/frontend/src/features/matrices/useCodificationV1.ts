import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createCpeAccountingNatureRule,
  createCpeAccountingSiteMapping,
  createEnergyNatureRule,
  createEnergySiteMapping,
  deleteCpeAccountingNatureRule,
  deleteCpeAccountingSiteMapping,
  deleteEnergyNatureRule,
  deleteEnergySiteMapping,
  exportCpeAccountingCodification,
  importFinanceCodification,
  fetchCpeAccountingNatureRules,
  fetchCpeAccountingSiteMappings,
  fetchEnergyNatureRules,
  fetchEnergySiteMappings,
  updateCpeAccountingNatureRule,
  updateCpeAccountingSiteMapping,
  updateEnergyNatureRule,
  updateEnergySiteMapping,
  bootstrapEnergySiteMappings,
  type CpeAccountingNatureRule,
  type CpeAccountingSiteMapping,
  type EnergyAccountingNatureRule,
  type EnergyAccountingSiteMapping,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

// Cles alignees sur celles de la page legacy /cpe pour partager le cache.
const CPE_SITES_KEY = ["cpe-accounting-site-mappings"] as const;
const CPE_NATURES_KEY = ["cpe-accounting-nature-rules"] as const;
const ENERGY_SITES_KEY = ["energy-accounting-site-mappings"] as const;
const ENERGY_NATURES_KEY = ["energy-accounting-nature-rules"] as const;

// ---- DALKIA (systeme B, endpoints /cpe/accounting/*) ----

export function useCpeSiteMappings() {
  const { token } = useAuth();
  return useQuery({
    queryKey: CPE_SITES_KEY,
    enabled: Boolean(token),
    queryFn: () => fetchCpeAccountingSiteMappings(token!),
  });
}

export function useCpeNatureRules() {
  const { token } = useAuth();
  return useQuery({
    // Marché Ville EN COURS uniquement (C00190116O / C00190155J).
    queryKey: [...CPE_NATURES_KEY, "current-scope"],
    enabled: Boolean(token),
    queryFn: () => fetchCpeAccountingNatureRules(token!, true),
  });
}

export function useSaveCpeSiteMapping() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<CpeAccountingSiteMapping> & { id?: number; code_site: string; site_name: string }) =>
      payload.id != null
        ? updateCpeAccountingSiteMapping(token!, payload.id, payload)
        : createCpeAccountingSiteMapping(token!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: CPE_SITES_KEY }),
  });
}

export function useDeleteCpeSiteMapping() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteCpeAccountingSiteMapping(token!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: CPE_SITES_KEY }),
  });
}

export function useSaveCpeNatureRule() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<CpeAccountingNatureRule> & { id?: number; market: string; billed_item: string; accounting_nature: string }) =>
      payload.id != null
        ? updateCpeAccountingNatureRule(token!, payload.id, payload)
        : createCpeAccountingNatureRule(token!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: CPE_NATURES_KEY }),
  });
}

export function useDeleteCpeNatureRule() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteCpeAccountingNatureRule(token!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: CPE_NATURES_KEY }),
  });
}

export function useExportCpeCodification() {
  const { token } = useAuth();
  return useMutation({
    mutationFn: () => exportCpeAccountingCodification(token!),
  });
}

// Import du gabarit finance COMBINE (DALKIA + ENGIE/EDF) : rafraîchit les 4 jeux.
export function useImportFinanceCodification() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => importFinanceCodification(token!, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: CPE_SITES_KEY });
      qc.invalidateQueries({ queryKey: CPE_NATURES_KEY });
      qc.invalidateQueries({ queryKey: ENERGY_SITES_KEY });
      qc.invalidateQueries({ queryKey: ENERGY_NATURES_KEY });
    },
  });
}

// ---- ENGIE / EDF (systeme B, endpoints /billing/accounting/*) ----
// NB : le PATCH energie remplace TOUS les champs -> toujours envoyer l'objet complet.

export function useEnergySiteMappings() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ENERGY_SITES_KEY,
    enabled: Boolean(token),
    queryFn: () => fetchEnergySiteMappings(token!),
  });
}

export function useEnergyNatureRules() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ENERGY_NATURES_KEY,
    enabled: Boolean(token),
    queryFn: () => fetchEnergyNatureRules(token!),
  });
}

export function useSaveEnergySiteMapping() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<EnergyAccountingSiteMapping> & { id?: number; prm_id: string }) =>
      payload.id != null
        ? updateEnergySiteMapping(token!, payload.id, payload)
        : createEnergySiteMapping(token!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ENERGY_SITES_KEY }),
  });
}

export function useDeleteEnergySiteMapping() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteEnergySiteMapping(token!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ENERGY_SITES_KEY }),
  });
}

export function useSaveEnergyNatureRule() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<EnergyAccountingNatureRule> & { id?: number; billed_item: string; accounting_nature: string }) =>
      payload.id != null
        ? updateEnergyNatureRule(token!, payload.id, payload)
        : createEnergyNatureRule(token!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ENERGY_NATURES_KEY }),
  });
}

export function useDeleteEnergyNatureRule() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteEnergyNatureRule(token!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ENERGY_NATURES_KEY }),
  });
}

export function useBootstrapEnergySites() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => bootstrapEnergySiteMappings(token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ENERGY_SITES_KEY }),
  });
}
