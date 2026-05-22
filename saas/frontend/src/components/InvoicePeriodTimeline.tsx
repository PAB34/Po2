import { useMemo } from "react";

// ─────────────────────────────────────────────────────────────────────────────
// Composant SVG natif (zéro dépendance) qui affiche les périodes de facturation
// d'un parc sur l'année glissante en cours, groupées par regroupement (fallback site).
//
// Détecte visuellement :
// - Trous (gaps) : portions de la timeline sans barre couvrant une lacune > N jours
// - Chevauchements (overlaps) : 2 périodes du même PRM qui se superposent → bandeau rouge
//
// L'idée est qu'un visuel Gantt « parle » 100× mieux qu'une liste de scopes :
// les anomalies de facturation sautent aux yeux et c'est imprimable dans le rapport.
// ─────────────────────────────────────────────────────────────────────────────

export type TimelineItem = {
  // Identifiant logique de la ligne (ex: PRM 24309117128642)
  rowKey: string;
  // Libellé affiché à gauche (ex: "PRM 24309117128642" ou "DECHETTERIES C - 5 fev → 4 avr")
  rowLabel: string;
  // Sous-libellé optionnel (ex: nom du site)
  rowSubLabel?: string | null;
  // Période couverte par cette barre
  startISO: string; // YYYY-MM-DD
  endISO: string; // YYYY-MM-DD
  // Tooltip riche au survol
  tooltip?: string;
  // Marque la barre comme anormale (couleur différente)
  isIssue?: boolean;
  // Type d'anomalie pour cumul d'aide à la lecture
  issueKind?: "gap" | "overlap" | "other";
};

export type TimelineGroup = {
  // Nom du regroupement (ex: "DECHETTERIES C", "MAIRIE DE SETE - PLAGES")
  name: string;
  // Sous-libellé optionnel (ex: titulaire)
  subLabel?: string | null;
  // Items dans ce groupe (1 par PRM ou 1 par facture selon usage)
  items: TimelineItem[];
};

type Props = {
  groups: TimelineGroup[];
  // Bornes temporelles affichées. Si non fournies, on dérive 12 mois glissants à partir de today.
  startDateISO?: string;
  endDateISO?: string;
  // Hauteur d'une ligne de barre en pixels
  rowHeight?: number;
  // Largeur de la colonne libellés
  labelWidth?: number;
};

const MONTH_LABELS_FR = [
  "Jan",
  "Fev",
  "Mar",
  "Avr",
  "Mai",
  "Jui",
  "Jul",
  "Aou",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function parseISO(value: string): number {
  // Retourne le timestamp UTC pour une date YYYY-MM-DD (évite le décalage timezone local)
  const [y, m, d] = value.split("-").map(Number);
  return Date.UTC(y, (m ?? 1) - 1, d ?? 1);
}

function formatISOShort(value: string): string {
  const [y, m, d] = value.split("-");
  return `${d}/${m}/${y.slice(2)}`;
}

function dayBoundary(ts: number): number {
  // Force au jour entier (UTC)
  const date = new Date(ts);
  return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
}

function addMonths(ts: number, months: number): number {
  const d = new Date(ts);
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + months, d.getUTCDate());
}

function startOfMonth(ts: number): number {
  const d = new Date(ts);
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1);
}

// Détecte les overlaps dans une liste de périodes (même rowKey)
function hasOverlap(a: TimelineItem, b: TimelineItem): boolean {
  return parseISO(a.startISO) <= parseISO(b.endISO) && parseISO(b.startISO) <= parseISO(a.endISO);
}

export function InvoicePeriodTimeline({
  groups,
  startDateISO,
  endDateISO,
  rowHeight = 24,
  labelWidth = 240,
}: Props) {
  // ── Calcul des bornes temporelles ─────────────────────────────────────────
  const { rangeStart, rangeEnd } = useMemo(() => {
    if (startDateISO && endDateISO) {
      return { rangeStart: parseISO(startDateISO), rangeEnd: parseISO(endDateISO) };
    }
    // Année glissante : 12 mois en arrière par défaut
    const today = Date.now();
    const end = dayBoundary(today);
    const start = addMonths(end, -12);
    return { rangeStart: start, rangeEnd: end };
  }, [startDateISO, endDateISO]);

  // ── Lignes (1 par rowKey distinct dans chaque groupe) ─────────────────────
  // Plusieurs items peuvent partager le même rowKey (plusieurs factures pour le même PRM)
  // → on les regroupe sur la même ligne pour détecter visuellement les chevauchements.
  const renderedGroups = useMemo(() => {
    return groups.map((group) => {
      const itemsByRow = new Map<string, TimelineItem[]>();
      for (const item of group.items) {
        const arr = itemsByRow.get(item.rowKey) ?? [];
        arr.push(item);
        itemsByRow.set(item.rowKey, arr);
      }
      const rows = Array.from(itemsByRow.entries())
        .map(([rowKey, items]) => {
          // Trie les items chronologiquement
          const sorted = [...items].sort((a, b) => parseISO(a.startISO) - parseISO(b.startISO));
          // Marque les overlaps : pour chaque paire qui se chevauche, on flag les deux
          const overlapFlags = new Set<number>();
          for (let i = 0; i < sorted.length; i++) {
            for (let j = i + 1; j < sorted.length; j++) {
              if (hasOverlap(sorted[i], sorted[j])) {
                overlapFlags.add(i);
                overlapFlags.add(j);
              }
            }
          }
          // Détection des gaps internes : entre 2 items consécutifs > 2 jours
          const gaps: Array<{ startISO: string; endISO: string }> = [];
          for (let i = 1; i < sorted.length; i++) {
            const prevEnd = parseISO(sorted[i - 1].endISO);
            const curStart = parseISO(sorted[i].startISO);
            const gapDays = (curStart - prevEnd) / 86400000;
            if (gapDays > 2) {
              const start = new Date(prevEnd + 86400000);
              const end = new Date(curStart - 86400000);
              gaps.push({
                startISO: `${start.getUTCFullYear()}-${String(start.getUTCMonth() + 1).padStart(2, "0")}-${String(start.getUTCDate()).padStart(2, "0")}`,
                endISO: `${end.getUTCFullYear()}-${String(end.getUTCMonth() + 1).padStart(2, "0")}-${String(end.getUTCDate()).padStart(2, "0")}`,
              });
            }
          }
          return {
            rowKey,
            label: sorted[0].rowLabel,
            subLabel: sorted[0].rowSubLabel ?? null,
            items: sorted.map((item, idx) => ({ ...item, isOverlap: overlapFlags.has(idx) })),
            gaps,
          };
        })
        .sort((a, b) => a.label.localeCompare(b.label, "fr"));
      return { ...group, rows };
    });
  }, [groups]);

  // Total rows pour calculer la hauteur du SVG
  const totalRows = renderedGroups.reduce((sum, g) => sum + g.rows.length, 0);
  const groupHeaderHeight = 22;
  const axisHeight = 30;
  const chartWidth = 760;
  const chartHeight = totalRows * rowHeight + renderedGroups.length * groupHeaderHeight + axisHeight + 8;
  const totalWidth = labelWidth + chartWidth + 20;

  // Helper conversion timestamp → x en pixels dans la zone graphique
  const rangeSpan = rangeEnd - rangeStart;
  function dateToX(ts: number): number {
    const clamped = Math.max(rangeStart, Math.min(rangeEnd, ts));
    return labelWidth + ((clamped - rangeStart) / rangeSpan) * chartWidth;
  }
  function dateToWidth(startTs: number, endTs: number): number {
    const a = Math.max(rangeStart, startTs);
    const b = Math.min(rangeEnd, endTs);
    if (b <= a) return 0;
    return ((b - a) / rangeSpan) * chartWidth;
  }

  // ── Génération des ticks mensuels ─────────────────────────────────────────
  const monthTicks = useMemo(() => {
    const ticks: Array<{ x: number; label: string; year: number }> = [];
    let cur = startOfMonth(rangeStart);
    while (cur <= rangeEnd) {
      const d = new Date(cur);
      ticks.push({
        x: dateToX(cur),
        label: MONTH_LABELS_FR[d.getUTCMonth()],
        year: d.getUTCFullYear(),
      });
      cur = addMonths(cur, 1);
    }
    return ticks;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rangeStart, rangeEnd]);

  if (totalRows === 0) {
    return (
      <div className="invoice-timeline-empty">
        Aucune periode a afficher sur la fenetre {formatISOShort(new Date(rangeStart).toISOString().slice(0, 10))} – {formatISOShort(new Date(rangeEnd).toISOString().slice(0, 10))}.
      </div>
    );
  }

  let y = axisHeight;
  return (
    <div className="invoice-timeline-wrapper">
      <svg
        className="invoice-timeline-svg"
        viewBox={`0 0 ${totalWidth} ${chartHeight}`}
        width="100%"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Frise des periodes de facturation"
      >
        {/* Axe X : graduations mensuelles */}
        {monthTicks.map((tick, idx) => (
          <g key={`tick-${idx}`}>
            <line
              x1={tick.x}
              y1={axisHeight - 4}
              x2={tick.x}
              y2={chartHeight - 4}
              stroke="#e2e8f0"
              strokeDasharray="2 3"
            />
            <text
              x={tick.x}
              y={axisHeight - 10}
              fontSize="10"
              fill="#475569"
              textAnchor="middle"
            >
              {tick.label}
            </text>
            {(idx === 0 || tick.label === "Jan") && (
              <text x={tick.x} y={axisHeight - 22} fontSize="9" fill="#94a3b8" textAnchor="middle">
                {tick.year}
              </text>
            )}
          </g>
        ))}

        {/* Lignes et barres */}
        {renderedGroups.map((group) => {
          const groupY = y;
          y += groupHeaderHeight;
          const rowsY = y;
          y += group.rows.length * rowHeight;
          return (
            <g key={group.name}>
              {/* En-tête de groupe */}
              <rect
                x={0}
                y={groupY}
                width={totalWidth}
                height={groupHeaderHeight}
                fill="#f1f5f9"
              />
              <text x={8} y={groupY + 15} fontSize="11" fontWeight="700" fill="#0f172a">
                {group.name}
              </text>
              {group.subLabel && (
                <text x={labelWidth - 4} y={groupY + 15} fontSize="10" fill="#64748b" textAnchor="end">
                  {group.subLabel}
                </text>
              )}

              {/* Rows */}
              {group.rows.map((row, rIdx) => {
                const rowY = rowsY + rIdx * rowHeight;
                return (
                  <g key={`${group.name}-${row.rowKey}`}>
                    {/* Label gauche */}
                    <text x={12} y={rowY + rowHeight / 2 + 3} fontSize="11" fill="#1e293b">
                      {row.label}
                    </text>
                    {row.subLabel && (
                      <text
                        x={labelWidth - 4}
                        y={rowY + rowHeight / 2 + 3}
                        fontSize="9"
                        fill="#64748b"
                        textAnchor="end"
                      >
                        {row.subLabel}
                      </text>
                    )}
                    {/* Fond de ligne */}
                    <rect
                      x={labelWidth}
                      y={rowY + 2}
                      width={chartWidth}
                      height={rowHeight - 4}
                      fill="#fafafa"
                    />
                    {/* Gaps en hachuré rouge clair */}
                    {row.gaps.map((gap, gIdx) => {
                      const gx = dateToX(parseISO(gap.startISO));
                      const gw = dateToWidth(parseISO(gap.startISO), parseISO(gap.endISO));
                      if (gw <= 0) return null;
                      return (
                        <rect
                          key={`gap-${gIdx}`}
                          x={gx}
                          y={rowY + 3}
                          width={gw}
                          height={rowHeight - 6}
                          fill="url(#timeline-gap-pattern)"
                          opacity="0.7"
                        >
                          <title>{`Trou de facturation : ${formatISOShort(gap.startISO)} → ${formatISOShort(gap.endISO)}`}</title>
                        </rect>
                      );
                    })}
                    {/* Barres de période */}
                    {row.items.map((item, iIdx) => {
                      const bx = dateToX(parseISO(item.startISO));
                      const bw = dateToWidth(parseISO(item.startISO), parseISO(item.endISO));
                      if (bw <= 0) return null;
                      const overlap = (item as TimelineItem & { isOverlap: boolean }).isOverlap;
                      const color = overlap
                        ? "#dc2626"
                        : item.isIssue
                          ? "#f59e0b"
                          : "#2563eb";
                      return (
                        <rect
                          key={`item-${iIdx}`}
                          x={bx}
                          y={rowY + 4}
                          width={Math.max(bw, 1)}
                          height={rowHeight - 8}
                          fill={color}
                          opacity={overlap ? 0.7 : 0.85}
                          rx={2}
                        >
                          <title>
                            {item.tooltip ||
                              `${formatISOShort(item.startISO)} → ${formatISOShort(item.endISO)}${overlap ? " (chevauchement)" : ""}`}
                          </title>
                        </rect>
                      );
                    })}
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* Pattern hachuré pour les gaps */}
        <defs>
          <pattern id="timeline-gap-pattern" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
            <rect width="6" height="6" fill="#fef2f2" />
            <line x1="0" y1="0" x2="0" y2="6" stroke="#fca5a5" strokeWidth="1.5" />
          </pattern>
        </defs>
      </svg>

      <div className="invoice-timeline-legend">
        <span className="invoice-timeline-legend-item">
          <span className="invoice-timeline-swatch" style={{ background: "#2563eb" }} /> Periode facturee
        </span>
        <span className="invoice-timeline-legend-item">
          <span className="invoice-timeline-swatch" style={{ background: "#f59e0b" }} /> Periode signalee
        </span>
        <span className="invoice-timeline-legend-item">
          <span className="invoice-timeline-swatch" style={{ background: "#dc2626" }} /> Chevauchement
        </span>
        <span className="invoice-timeline-legend-item">
          <span className="invoice-timeline-swatch invoice-timeline-swatch-gap" /> Trou de facturation
        </span>
      </div>
    </div>
  );
}
