import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FluidsClimateOverview } from "../../lib/api";

const MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"];
const HEAT = "#3e6ea8";
const COOL = "#e39a2c";

function pct(value: number | null | undefined, digits = 0): string {
  if (value == null) return "—";
  const rounded = value.toLocaleString("fr-FR", { maximumFractionDigits: digits });
  return `${value > 0 ? "+" : ""}${rounded} %`;
}

function ChipDeltas({ prev, avg, invert }: { prev: number | null; avg: number | null; invert?: boolean }) {
  // invert=true : une hausse est défavorable (climatisation). Sinon hausse de rigueur = plus de conso.
  const cls = (v: number | null) => (v == null ? "" : (invert ? v > 0 : v < 0) ? "po2-fluid-chip__down" : "po2-fluid-chip__up");
  return (
    <>
      <em className={cls(prev)}>{pct(prev)} N-1</em>
      <em className={cls(avg)}>{pct(avg)} moy</em>
    </>
  );
}

export function FluidsClimateSectionV1({ climate }: { climate: FluidsClimateOverview | undefined }) {
  if (!climate) {
    return (
      <div className="po2-card po2-fluid-todo">
        <div className="po2-card__body"><p>Chargement de la lecture climatique…</p></div>
      </div>
    );
  }

  const { heating, cooling, thermal, current_year, previous_year } = climate;
  const data = MONTHS.map((label, i) => {
    const h = heating.monthly[i];
    const c = cooling.monthly[i];
    return {
      label,
      heatCur: h?.current ?? null, heatPrev: h?.previous ?? null, heatAvg: h?.average ?? null,
      coolCur: c?.current ?? null, coolPrev: c?.previous ?? null, coolAvg: c?.average ?? null,
    };
  });

  const sCur = thermal.sensitivity_kwh_per_dju;
  const sPrev = thermal.sensitivity_previous;
  const maxS = Math.max(sCur ?? 0, sPrev ?? 0, 1);
  const yCur = 70 - ((sCur ?? 0) / maxS) * 50;
  const yPrev = 70 - ((sPrev ?? 0) / maxS) * 50;
  const delta = thermal.sensitivity_delta_pct;
  const evoClass = delta == null ? "" : delta > 0 ? "po2-perf__evo--bad" : "po2-perf__evo--good";

  return (
    <div className="po2-fluid-climate-grid">
      <section className="po2-card">
        <header className="po2-card__header">
          <div>
            <span className="po2-eyebrow">Trajectoire climatique {current_year}</span>
            <h2>Degrés-jours chauffage &amp; froid</h2>
          </div>
        </header>
        <div className="po2-card__body">
          <div className="po2-fluid-chips">
            <div className="po2-fluid-chip po2-fluid-chip--heat">
              <span>Chauffage</span>
              <b>{heating.current_total != null ? `${heating.current_total.toLocaleString("fr-FR")} DJU` : "—"}</b>
              <ChipDeltas prev={heating.delta_previous_pct} avg={heating.delta_average_pct} />
            </div>
            <div className="po2-fluid-chip po2-fluid-chip--cool">
              <span>Froid / clim.</span>
              <b>{cooling.current_total != null ? `${cooling.current_total.toLocaleString("fr-FR")} DJU` : "—"}</b>
              <ChipDeltas prev={cooling.delta_previous_pct} avg={cooling.delta_average_pct} invert />
            </div>
          </div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} width={40} />
                <Tooltip
                  formatter={(v: number, name: string) => [`${v.toLocaleString("fr-FR")} DJU`, name]}
                  labelFormatter={(l) => `Mois : ${l}`}
                />
                <Line dataKey="heatAvg" name={`Chauffage moy.`} stroke={HEAT} strokeWidth={2} strokeDasharray="1 6" strokeOpacity={0.5} dot={false} connectNulls />
                <Line dataKey="heatPrev" name={`Chauffage ${previous_year}`} stroke={HEAT} strokeWidth={2} strokeDasharray="6 5" strokeOpacity={0.6} dot={false} connectNulls />
                <Line dataKey="heatCur" name={`Chauffage ${current_year}`} stroke={HEAT} strokeWidth={3} dot={false} connectNulls />
                <Line dataKey="coolAvg" name={`Froid moy.`} stroke={COOL} strokeWidth={2} strokeDasharray="1 6" strokeOpacity={0.55} dot={false} connectNulls />
                <Line dataKey="coolPrev" name={`Froid ${previous_year}`} stroke={COOL} strokeWidth={2} strokeDasharray="6 5" strokeOpacity={0.6} dot={false} connectNulls />
                <Line dataKey="coolCur" name={`Froid ${current_year}`} stroke={COOL} strokeWidth={3} dot={false} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="po2-fluid-legend">
            <span><i style={{ background: HEAT }} />Chauffage</span>
            <span><i style={{ background: COOL }} />Froid / clim.</span>
            <span>· trait plein = {current_year} · tirets = {previous_year} · pointillés = moyenne</span>
          </div>
        </div>
      </section>

      <aside className="po2-perf">
        <div className="po2-perf__head">
          <span className="po2-perf__ic">∿</span>
          <div>
            <small>Performance énergétique · corrigée du climat</small>
            <strong>{sCur != null ? `${sCur.toLocaleString("fr-FR")} kWh/DJU` : "—"}</strong>
          </div>
        </div>
        {thermal.reliable && sCur != null ? (
          <>
            <div className={`po2-perf__evo ${evoClass}`}>
              <span className="po2-perf__ev">{pct(delta, 1)}</span>
              <div>
                <small>Thermosensibilité vs {previous_year}</small>
                <b>{delta != null && delta > 0 ? "⚠ le parc consomme plus par degré — performance qui se dégrade" : "performance stable ou en amélioration à climat égal"}</b>
              </div>
            </div>
            <div className="po2-perf__sig">
              <div className="po2-perf__sig-cap"><span>Signature énergétique (conso / DJU)</span><span>{previous_year} → {current_year}</span></div>
              <svg viewBox="0 0 300 96" role="img" aria-label="Signature énergétique : pente actuelle vs N-1">
                <line x1="26" y1="82" x2="290" y2="82" className="po2-perf__ax" />
                <line x1="26" y1="10" x2="26" y2="82" className="po2-perf__ax" />
                <line x1="26" y1="70" x2="284" y2={yPrev} className="po2-perf__sig-prev" />
                <line x1="26" y1="70" x2="284" y2={yCur} className="po2-perf__sig-cur" />
                <circle cx="284" cy={yPrev} r="3" className="po2-perf__sig-dotp" />
                <circle cx="284" cy={yCur} r="3" className="po2-perf__sig-dotc" />
                <text x="30" y="93" className="po2-perf__sig-lab">talon</text>
                <text x="250" y="93" className="po2-perf__sig-lab">DJU →</text>
              </svg>
            </div>
            <div className="po2-perf__split">
              <div><b>{thermal.thermosensitive_share_pct != null ? `${thermal.thermosensitive_share_pct.toLocaleString("fr-FR")} %` : "—"}</b><span>part thermosensible</span></div>
              <div><b>{thermal.base_load_share_pct != null ? `${thermal.base_load_share_pct.toLocaleString("fr-FR")} %` : "—"}</b><span>talon non climatique</span></div>
            </div>
            <p className="po2-perf__note">
              À climat égal, la pente {thermal.sensitivity_delta_pct != null && thermal.sensitivity_delta_pct > 0 ? "monte" : "évolue"} vs {previous_year} :
              signal de performance intrinsèque, indépendant de la météo. Périmètre : {thermal.scope} · {thermal.months_used} mois
              {thermal.r2 != null ? ` · R² ${thermal.r2.toLocaleString("fr-FR")}` : ""}.
            </p>
          </>
        ) : (
          <p className="po2-perf__note">
            Signature énergétique non fiable pour l'instant ({thermal.months_used} mois exploitables).
            Il faut au moins 4 mois de consommation appariés aux DJU pour estimer la thermosensibilité du parc.
          </p>
        )}
      </aside>
    </div>
  );
}
