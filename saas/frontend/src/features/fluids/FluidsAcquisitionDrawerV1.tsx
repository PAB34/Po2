import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Drawer, StatusBadge } from "../../design-system";
import { fetchDataRanges, fetchGrdfConsoStatus } from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString("fr-FR");
  } catch {
    return value;
  }
}

export function FluidsAcquisitionDrawerV1({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { token } = useAuth();
  const navigate = useNavigate();

  const { data: ranges } = useQuery({
    queryKey: ["energie-data-ranges"],
    queryFn: () => fetchDataRanges(token!),
    enabled: !!token && open,
    staleTime: 60_000,
  });
  const { data: grdf } = useQuery({
    queryKey: ["grdf-conso-status"],
    queryFn: () => fetchGrdfConsoStatus(token!),
    enabled: !!token && open,
    staleTime: 60_000,
  });

  const go = (to: string) => {
    onClose();
    navigate(to);
  };

  const elecGaps: string[] = [];
  if (ranges) {
    if (ranges.max_power.row_count === 0) elecGaps.push("Puissance max absente");
    if (ranges.load_curve.row_count === 0) elecGaps.push("Courbe de charge absente");
  }
  const gasLoaded = grdf ? grdf.rows_upserted > 0 : undefined;

  return (
    <Drawer
      open={open}
      onClose={onClose}
      eyebrow="Acquisition des données"
      title="Collecte par distributeur"
      description="Choisir un distributeur pour ouvrir sa fenêtre de collecte. L'état ci-dessous vient des sources réelles."
    >
      <div className="po2-acq-list">
        <button type="button" className="po2-acq-item po2-acq-item--elec" onClick={() => go("/refonte-v1/fluides/electricite/collecte")}>
          <span className="po2-acq-item__ic">ϟ</span>
          <span className="po2-acq-item__body">
            <b>Électricité — ENEDIS</b>
            <small>Conso au {fmtDate(ranges?.consumption.last_date)} · {ranges ? ranges.contracts.count.toLocaleString("fr-FR") : "—"} PRM</small>
            {elecGaps.length > 0 ? (
              <StatusBadge tone="bad">{`⚠ ${elecGaps.join(" · ")}`}</StatusBadge>
            ) : ranges ? (
              <StatusBadge tone="ok">Sources à jour</StatusBadge>
            ) : null}
          </span>
          <span className="po2-acq-item__open">Ouvrir la collecte →</span>
        </button>

        <button type="button" className="po2-acq-item po2-acq-item--gaz" onClick={() => go("/refonte-v1/fluides/gaz")}>
          <span className="po2-acq-item__ic">♨</span>
          <span className="po2-acq-item__body">
            <b>Gaz — GRDF</b>
            <small>{grdf ? `${grdf.pce_total.toLocaleString("fr-FR")} PCE · ${grdf.rows_upserted.toLocaleString("fr-FR")} relevés` : "GRDF ADICT"}</small>
            {gasLoaded === false ? (
              <StatusBadge tone="bad">⚠ Consommation non chargée</StatusBadge>
            ) : gasLoaded ? (
              <StatusBadge tone="ok">Consommation chargée</StatusBadge>
            ) : null}
          </span>
          <span className="po2-acq-item__open">Ouvrir la collecte →</span>
        </button>

        <button type="button" className="po2-acq-item po2-acq-item--eau" onClick={() => go("/refonte-v1/fluides/eau")}>
          <span className="po2-acq-item__ic">◌</span>
          <span className="po2-acq-item__body">
            <b>Eau — SUEZ</b>
            <small>aucune source distributeur</small>
            <StatusBadge tone="warn">À raccorder</StatusBadge>
          </span>
          <span className="po2-acq-item__open">Voir le chantier →</span>
        </button>
      </div>
    </Drawer>
  );
}
