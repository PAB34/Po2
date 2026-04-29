import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchPrmDetail, fetchPrmLoadCurve, fetchPrmMaxPower } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

function fmt(val: string | null | undefined): string {
  return val?.trim() || "—";
}

function fmtDate(isoStr: string | null | undefined): string {
  if (!isoStr) return "—";
  try {
    return new Date(isoStr).toLocaleDateString("fr-FR");
  } catch {
    return isoStr;
  }
}

function fmtDateShort(dateStr: string): string {
  try {
    const [y, m, d] = dateStr.split("-");
    return `${d}/${m}/${y.slice(2)}`;
  } catch {
    return dateStr;
  }
}

function fmtDatetime(dtStr: string): string {
  try {
    const [datePart, timePart] = dtStr.split(" ");
    const [y, m, d] = datePart.split("-");
    const [h, min] = timePart.split(":");
    return `${d}/${m} ${h}:${min}`;
  } catch {
    return dtStr;
  }
}

export function EnergieDetailPage() {
  const { prmId } = useParams<{ prmId: string }>();
  const { token } = useAuth();
  const navigate = useNavigate();

  const detailQuery = useQuery({
    queryKey: ["prm-detail", prmId],
    queryFn: () => fetchPrmDetail(token!, prmId!),
    enabled: !!token && !!prmId,
  });

  const maxPowerQuery = useQuery({
    queryKey: ["prm-max-power", prmId],
    queryFn: () => fetchPrmMaxPower(token!, prmId!),
    enabled: !!token && !!prmId,
  });

  const loadCurveQuery = useQuery({
    queryKey: ["prm-load-curve", prmId],
    queryFn: () => fetchPrmLoadCurve(token!, prmId!, 7),
    enabled: !!token && !!prmId,
  });

  const detail = detailQuery.data;

  const maxPowerPoints = (maxPowerQuery.data?.points ?? []).map((p) => ({
    date: p.date,
    label: fmtDateShort(p.date),
    kva: Math.round(p.value_va / 100) / 10,
  }));

  const loadCurvePoints = (loadCurveQuery.data?.points ?? []).map((p) => ({
    dt: p.datetime,
    label: fmtDatetime(p.datetime),
    kw: Math.round(p.value_w / 100) / 10,
  }));

  return (
    <div className="page">
      <div className="page-header">
        <button type="button" className="back-button" onClick={() => navigate("/energie")}>
          ← Retour
        </button>
        {detail && (
          <div>
            <h2>{detail.contract.name || prmId}</h2>
            <p className="page-subtitle">PRM {prmId}</p>
          </div>
        )}
        {detailQuery.isLoading && <p>Chargement…</p>}
        {detailQuery.error && <p className="error-text">{(detailQuery.error as Error).message}</p>}
      </div>

      {detail && (
        <div className="energie-detail-grid">
          {/* Contract */}
          <div className="detail-card">
            <h3>Contrat</h3>
            <dl className="detail-list">
              <dt>Type</dt>
              <dd>{fmt(detail.contract.contract_type)}</dd>
              <dt>Fournisseur</dt>
              <dd>{fmt(detail.contract.contractor)}</dd>
              <dt>Tarif</dt>
              <dd>{fmt(detail.contract.tariff)}</dd>
              <dt>Puissance souscrite</dt>
              <dd>{detail.contract.subscribed_power_kva != null ? `${detail.contract.subscribed_power_kva} kVA` : "—"}</dd>
              <dt>Segment</dt>
              <dd>{fmt(detail.contract.segment)}</dd>
              <dt>Date début</dt>
              <dd>{fmtDate(detail.contract.contract_start)}</dd>
              <dt>Organisme</dt>
              <dd>{fmt(detail.contract.organization_name)}</dd>
            </dl>
          </div>

          {/* Address + Connection */}
          <div className="detail-cards-column">
            <div className="detail-card">
              <h3>Adresse</h3>
              <dl className="detail-list">
                <dt>Voie</dt>
                <dd>{fmt(detail.address.address_number_street_name)}</dd>
                <dt>Commune</dt>
                <dd>{fmt(detail.address.address_postal_code_city)}</dd>
                <dt>Appartement / Étage</dt>
                <dd>{fmt(detail.address.address_staircase_floor_apartment)}</dd>
                <dt>Bâtiment</dt>
                <dd>{fmt(detail.address.address_building)}</dd>
                <dt>INSEE</dt>
                <dd>{fmt(detail.address.address_insee_code)}</dd>
              </dl>
            </div>

            <div className="detail-card">
              <h3>Raccordement</h3>
              <dl className="detail-list">
                <dt>N° série compteur</dt>
                <dd>{fmt(detail.connection.serial_number)}</dd>
                <dt>État</dt>
                <dd>{fmt(detail.connection.connection_state)}</dd>
                <dt>Niveau tension</dt>
                <dd>{fmt(detail.connection.voltage_level)}</dd>
                <dt>Puissance raccordement</dt>
                <dd>{detail.connection.subscribed_kva != null ? `${detail.connection.subscribed_kva} kVA` : "—"}</dd>
              </dl>
            </div>

            <div className="detail-card">
              <h3>Statut</h3>
              <dl className="detail-list">
                <dt>Communicant</dt>
                <dd>{fmt(detail.summary.services_level)}</dd>
                <dt>Activation</dt>
                <dd>{fmtDate(detail.summary.activation_date)}</dd>
                <dt>Dernière modif. puissance</dt>
                <dd>{fmtDate(detail.summary.last_power_change_date)}</dd>
              </dl>
            </div>
          </div>
        </div>
      )}

      {/* Max Power Chart */}
      <div className="chart-section">
        <h3>Puissance maximale journalière (kVA) — 3 ans</h3>
        {maxPowerQuery.isLoading && <p>Chargement du graphique…</p>}
        {maxPowerQuery.error && <p className="error-text">{(maxPowerQuery.error as Error).message}</p>}
        {maxPowerPoints.length > 0 && (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={maxPowerPoints} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                interval={Math.floor(maxPowerPoints.length / 12)}
              />
              <YAxis tick={{ fontSize: 11 }} unit=" kVA" width={60} />
              <Tooltip
                formatter={(value: number) => [`${value} kVA`, "Puissance max"]}
                labelFormatter={(label) => `Date : ${label}`}
              />
              <Line
                type="monotone"
                dataKey="kva"
                stroke="#2563eb"
                dot={false}
                strokeWidth={1.5}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
        {!maxPowerQuery.isLoading && maxPowerPoints.length === 0 && (
          <p className="cell-empty">Aucune donnée de puissance maximale disponible.</p>
        )}
      </div>

      {/* Load Curve Chart */}
      <div className="chart-section">
        <h3>Courbe de charge (kW) — 7 derniers jours, pas 30 min</h3>
        {loadCurveQuery.isLoading && <p>Chargement du graphique…</p>}
        {loadCurveQuery.error && <p className="error-text">{(loadCurveQuery.error as Error).message}</p>}
        {loadCurvePoints.length > 0 && (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={loadCurvePoints} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                interval={Math.floor(loadCurvePoints.length / 12)}
              />
              <YAxis tick={{ fontSize: 11 }} unit=" kW" width={60} />
              <Tooltip
                formatter={(value: number) => [`${value} kW`, "Puissance"]}
                labelFormatter={(label) => `Horodatage : ${label}`}
              />
              <Line
                type="monotone"
                dataKey="kw"
                stroke="#f97316"
                dot={false}
                strokeWidth={1.5}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
        {!loadCurveQuery.isLoading && loadCurvePoints.length === 0 && (
          <p className="cell-empty">Aucune courbe de charge disponible.</p>
        )}
      </div>
    </div>
  );
}
