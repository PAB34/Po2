import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchCpeReleves,
  fetchCpeConsommations,
  upsertCpeReleve,
  CpeGazReleve,
  CpeConsoReleve,
  CpeSite,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const MOIS_LABELS = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
];

const SOURCE_LABEL: Record<string, string> = {
  csv_dalkia: "CSV DALKIA",
  grdf_api: "API GRDF",
  saisie_manuelle: "Saisie manuelle",
};

function fmt(val: number | null | undefined, decimals = 2): string {
  if (val == null) return "—";
  return val.toFixed(decimals).replace(".", ",");
}

export default function CpeSiteDetailPage() {
  const { siteId } = useParams<{ siteId: string }>();
  const { token } = useAuth();
  const qc = useQueryClient();
  const [annee, setAnnee] = useState(new Date().getFullYear());
  const [editMois, setEditMois] = useState<number | null>(null);
  const [editQt, setEditQt] = useState("");
  const [editEcs, setEditEcs] = useState("");

  const relevesQ = useQuery({
    queryKey: ["cpe-releves", siteId, annee],
    queryFn: () => fetchCpeReleves(token!, Number(siteId), annee),
    enabled: !!token && !!siteId,
  });

  const saveMutation = useMutation({
    mutationFn: (payload: { annee: number; mois: number; qt_mwh_pci?: number; volume_ecs_m3?: number }) =>
      upsertCpeReleve(token!, Number(siteId), payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cpe-releves", siteId, annee] });
      setEditMois(null);
      setEditQt("");
      setEditEcs("");
    },
  });

  const consoQ = useQuery({
    queryKey: ["cpe-consommations", siteId, annee],
    queryFn: () => fetchCpeConsommations(token!, Number(siteId), annee),
    enabled: !!token && !!siteId,
  });

  const releves = relevesQ.data ?? [];
  const releveByMois = Object.fromEntries(releves.map((r) => [r.mois, r]));

  function handleEdit(mois: number) {
    const existing = releveByMois[mois];
    setEditMois(mois);
    setEditQt(existing?.qt_mwh_pci != null ? String(existing.qt_mwh_pci) : "");
    setEditEcs(existing?.volume_ecs_m3 != null ? String(existing.volume_ecs_m3) : "");
  }

  function handleSave(mois: number) {
    const qt = editQt.replace(",", ".").trim();
    const ecs = editEcs.replace(",", ".").trim();
    saveMutation.mutate({
      annee,
      mois,
      qt_mwh_pci: qt ? parseFloat(qt) : undefined,
      volume_ecs_m3: ecs ? parseFloat(ecs) : undefined,
    });
  }

  const totalQt = releves.reduce((s, r) => s + (r.qt_mwh_pci ?? 0), 0);
  const nbMois = releves.filter((r) => r.qt_mwh_pci != null).length;

  // Consommations multi-fluides : pivot fluide -> {mois -> valeur}
  const conso = consoQ.data ?? [];
  const FLUID_LABEL: Record<string, string> = {
    GAZ: "Gaz", ELEC: "Électricité", ECS: "ECS (eau chaude)", EAU: "Eau", CHALEUR: "Chaleur",
  };
  const FLUID_UNIT: Record<string, string> = {
    GAZ: "MWh PCS", ELEC: "MWh", CHALEUR: "MWh", ECS: "m³", EAU: "m³",
  };
  const consoByFluide: Record<string, { mois: Record<number, number | null>; total: number; estime: boolean }> = {};
  for (const c of conso) {
    const isEnergy = c.fluide === "GAZ" || c.fluide === "ELEC" || c.fluide === "CHALEUR";
    const v = isEnergy ? c.energie_mwh : c.consommation;
    const entry = (consoByFluide[c.fluide] ??= { mois: {}, total: 0, estime: false });
    entry.mois[c.mois] = v;
    entry.total += v ?? 0;
    if (c.nb_estimes > 0) entry.estime = true;
  }
  const fluidesOrder = ["GAZ", "ELEC", "CHALEUR", "ECS", "EAU"].filter((f) => consoByFluide[f]);

  return (
    <div style={{ maxWidth: 900 }}>
      <div style={{ marginBottom: 16 }}>
        <Link to="/cpe" style={{ color: "#6b7280", fontSize: 13, textDecoration: "none" }}>
          ← Retour au bilan CPE
        </Link>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ margin: 0 }}>Relevés gaz — Site {siteId}</h2>
          <p style={{ margin: "4px 0 0", color: "#6b7280", fontSize: 13 }}>
            Saisie manuelle des consommations mensuelles QT (en MWhPCI)
          </p>
        </div>
        <select
          value={annee}
          onChange={(e) => setAnnee(Number(e.target.value))}
          style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #d1d5db" }}
        >
          {[2026, 2027, 2028, 2029].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Résumé */}
      <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
        <div className="card" style={{ padding: "12px 20px", flex: 1 }}>
          <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>QT TOTAL ANNUEL</p>
          <p style={{ margin: "4px 0 0", fontSize: 22, fontWeight: 700, color: "#2563eb" }}>
            {fmt(totalQt, 1)} MWhPCI
          </p>
        </div>
        <div className="card" style={{ padding: "12px 20px", flex: 1 }}>
          <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>MOIS RENSEIGNÉS</p>
          <p style={{ margin: "4px 0 0", fontSize: 22, fontWeight: 700, color: nbMois < 12 ? "#f97316" : "#16a34a" }}>
            {nbMois} / 12
          </p>
        </div>
      </div>

      {/* Tableau mois par mois */}
      <div className="card" style={{ overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb" }}>
              <th style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600, color: "#374151" }}>Mois</th>
              <th style={{ padding: "10px 16px", textAlign: "right", fontWeight: 600, color: "#374151" }}>
                QT (MWhPCI)
              </th>
              <th style={{ padding: "10px 16px", textAlign: "right", fontWeight: 600, color: "#374151" }}>
                ECS (m³)
              </th>
              <th style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600, color: "#374151" }}>Source</th>
              <th style={{ padding: "10px 16px" }}></th>
            </tr>
          </thead>
          <tbody>
            {MOIS_LABELS.map((label, idx) => {
              const mois = idx + 1;
              const releve: CpeGazReleve | undefined = releveByMois[mois];
              const isEditing = editMois === mois;

              return (
                <tr key={mois} style={{ borderBottom: "1px solid #f3f4f6", background: isEditing ? "#f0f9ff" : undefined }}>
                  <td style={{ padding: "10px 16px", fontWeight: 500 }}>
                    {label} {annee}
                  </td>

                  {isEditing ? (
                    <>
                      <td style={{ padding: "6px 16px", textAlign: "right" }}>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="MWhPCI"
                          value={editQt}
                          onChange={(e) => setEditQt(e.target.value)}
                          style={{ width: 100, padding: "4px 8px", borderRadius: 6, border: "1px solid #93c5fd", textAlign: "right" }}
                          autoFocus
                        />
                      </td>
                      <td style={{ padding: "6px 16px", textAlign: "right" }}>
                        <input
                          type="number"
                          step="0.1"
                          placeholder="m³"
                          value={editEcs}
                          onChange={(e) => setEditEcs(e.target.value)}
                          style={{ width: 80, padding: "4px 8px", borderRadius: 6, border: "1px solid #93c5fd", textAlign: "right" }}
                        />
                      </td>
                      <td style={{ padding: "6px 16px", color: "#6b7280", fontSize: 13 }}>saisie_manuelle</td>
                      <td style={{ padding: "6px 16px", textAlign: "right" }}>
                        <button
                          type="button"
                          className="primary-button"
                          style={{ fontSize: 12, padding: "4px 10px", marginRight: 6 }}
                          onClick={() => handleSave(mois)}
                          disabled={saveMutation.isPending}
                        >
                          ✓
                        </button>
                        <button
                          type="button"
                          className="secondary-button"
                          style={{ fontSize: 12, padding: "4px 10px" }}
                          onClick={() => setEditMois(null)}
                        >
                          ✕
                        </button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td style={{ padding: "10px 16px", textAlign: "right", fontWeight: releve?.qt_mwh_pci != null ? 600 : 400, color: releve?.qt_mwh_pci != null ? "#111827" : "#9ca3af" }}>
                        {fmt(releve?.qt_mwh_pci, 2)}
                      </td>
                      <td style={{ padding: "10px 16px", textAlign: "right", color: "#6b7280" }}>
                        {fmt(releve?.volume_ecs_m3, 1)}
                      </td>
                      <td style={{ padding: "10px 16px", color: "#9ca3af", fontSize: 12 }}>
                        {releve ? (SOURCE_LABEL[releve.source] ?? releve.source) : "—"}
                      </td>
                      <td style={{ padding: "10px 16px", textAlign: "right" }}>
                        <button
                          type="button"
                          className="secondary-button"
                          style={{ fontSize: 12, padding: "4px 10px" }}
                          onClick={() => handleEdit(mois)}
                        >
                          Saisir
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr style={{ borderTop: "2px solid #e5e7eb", background: "#f9fafb" }}>
              <td style={{ padding: "10px 16px", fontWeight: 700 }}>TOTAL</td>
              <td style={{ padding: "10px 16px", textAlign: "right", fontWeight: 700, color: "#2563eb" }}>
                {fmt(totalQt, 2)} MWhPCI
              </td>
              <td colSpan={3}></td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Consommations multi-fluides (import DALKIA détaillé) */}
      <div style={{ marginTop: 28 }}>
        <h3 style={{ margin: "0 0 4px" }}>Consommations {annee} — tous fluides</h3>
        <p style={{ margin: "0 0 12px", color: "#6b7280", fontSize: 13 }}>
          Issu de l'export DALKIA « consommation détaillée ». Énergie en MWh (gaz/élec/chaleur), volume en m³ (ECS/eau).
        </p>
        {fluidesOrder.length === 0 ? (
          <p style={{ color: "#9ca3af", fontSize: 13 }}>
            Aucune consommation importée pour {annee}. Importer le CSV DALKIA depuis{" "}
            <Link to="/cpe" style={{ color: "#2563eb" }}>le bilan CPE</Link>.
          </p>
        ) : (
          <div className="card" style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb" }}>
                  <th style={{ padding: "8px 12px", textAlign: "left" }}>Fluide</th>
                  {MOIS_LABELS.map((m) => (
                    <th key={m} style={{ padding: "8px 6px", textAlign: "right", color: "#6b7280", fontWeight: 600 }}>{m.slice(0, 3)}</th>
                  ))}
                  <th style={{ padding: "8px 12px", textAlign: "right" }}>Total</th>
                  <th style={{ padding: "8px 12px", textAlign: "left" }}>Unité</th>
                </tr>
              </thead>
              <tbody>
                {fluidesOrder.map((f) => {
                  const row = consoByFluide[f];
                  return (
                    <tr key={f} style={{ borderBottom: "1px solid #f3f4f6" }}>
                      <td style={{ padding: "8px 12px", fontWeight: 600 }}>
                        {FLUID_LABEL[f] ?? f}
                        {row.estime ? (
                          <span title="Contient des relevés estimés/calculés (pas tous réels)" style={{ marginLeft: 6, fontSize: 10, color: "#b45309", cursor: "help" }}>~estimé</span>
                        ) : null}
                      </td>
                      {MOIS_LABELS.map((_, idx) => (
                        <td key={idx} style={{ padding: "8px 6px", textAlign: "right", color: row.mois[idx + 1] != null ? "#111827" : "#d1d5db" }}>
                          {row.mois[idx + 1] != null ? fmt(row.mois[idx + 1], 1) : "·"}
                        </td>
                      ))}
                      <td style={{ padding: "8px 12px", textAlign: "right", fontWeight: 700, color: "#2563eb" }}>{fmt(row.total, 1)}</td>
                      <td style={{ padding: "8px 12px", color: "#6b7280" }}>{FLUID_UNIT[f] ?? ""}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p style={{ marginTop: 16, fontSize: 12, color: "#9ca3af" }}>
        QT = consommation gaz totale (chauffage + ECS). NC sera calculé par le moteur : NC = QT – (m × qECS).
        <br />
        Source recommandée : fichier CSV mensuel DALKIA (avant le 5e jour ouvrable). Import via{" "}
        <Link to="/cpe" style={{ color: "#2563eb" }}>le bilan CPE</Link>.
      </p>
    </div>
  );
}
