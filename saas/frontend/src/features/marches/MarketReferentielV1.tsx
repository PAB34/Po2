import { Card, DataTable, KpiCard } from "../../design-system";
import type {
  MarketBpuDocumentV1,
  MarketDpgfImportV1,
  MarketGasBpuPriceV1,
} from "../../lib/api";
import {
  useMarketBpuDocumentsV1,
  useMarketDpgfImportsV1,
  useMarketDpgfSummaryV1,
  useMarketGasBpuV1,
} from "./useMarketReferentielV1";

type MarketTier = "dalkia" | "gaz" | "engie" | "edf";

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Une erreur est survenue.";
}

function euro(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 0 }) + " € HT";
}

function priceMwh(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 2 }) + " €/MWh";
}

function dateFr(value: string | null | undefined) {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString("fr-FR");
}

// --------------------------------------------------------------------------- //
// DPGF DALKIA — état en vigueur + journal des actes
// --------------------------------------------------------------------------- //

function DpgfReferentiel() {
  const refYear = new Date().getFullYear();
  const summary = useMarketDpgfSummaryV1(refYear);
  const imports = useMarketDpgfImportsV1();

  return (
    <>
      <Card title="Marché en vigueur (DPGF)" eyebrow={`année de référence ${refYear} · lecture seule`}>
        {summary.isError ? (
          <p className="po2-muted-line">Synthèse indisponible : {errorMessage(summary.error)}</p>
        ) : summary.isFetching && !summary.data ? (
          <p className="po2-muted-line">Chargement de la synthèse…</p>
        ) : summary.data && summary.data.has_data ? (
          <div className="po2-kpi-grid">
            <KpiCard label="Sites" value={String(summary.data.nb_sites ?? "-")} detail={summary.data.filename ?? "—"} />
            <KpiCard label="Marché total" value={euro(summary.data.marche_total_ht)} detail="P1 + P2 + P3 toutes années" />
            <KpiCard label="P1 gaz" value={euro(summary.data.p1_gaz_ref_year_ht)} detail={`référence ${refYear}`} />
            <KpiCard label="P2 / P3" value={`${euro(summary.data.p2_ref_year_ht)} / ${euro(summary.data.p3_ref_year_ht)}`} detail={`référence ${refYear}`} />
          </div>
        ) : (
          <p className="po2-muted-line">Aucun référentiel DPGF importé pour l'instant.</p>
        )}
      </Card>

      <Card title="Journal des actes (DPGF importés)" eyebrow="toutes versions — active et remplacées">
        {imports.isError ? (
          <p className="po2-muted-line">Journal indisponible : {errorMessage(imports.error)}</p>
        ) : imports.isFetching && !imports.data ? (
          <p className="po2-muted-line">Chargement du journal…</p>
        ) : imports.data && imports.data.length > 0 ? (
          <DataTable<MarketDpgfImportV1>
            rows={imports.data}
            getRowKey={(row) => String(row.id)}
            columns={[
              { key: "import_date", header: "Import", render: (row) => dateFr(row.import_date) },
              { key: "lot", header: "Lot", render: (row) => String(row.lot) },
              { key: "acte", header: "Acte", render: (row) => row.acte_label ?? row.acte_type ?? "—" },
              { key: "date_effet", header: "Effet", render: (row) => dateFr(row.date_effet) },
              { key: "nb_sites", header: "Sites", render: (row) => String(row.nb_sites) },
              { key: "is_active", header: "État", render: (row) => (row.is_active ? "En vigueur" : "Remplacé") },
              { key: "filename", header: "Fichier", render: (row) => row.filename },
            ]}
          />
        ) : (
          <p className="po2-muted-line">Aucun import DPGF enregistré.</p>
        )}
      </Card>
    </>
  );
}

// --------------------------------------------------------------------------- //
// BPU électricité (ENGIE / EDF)
// --------------------------------------------------------------------------- //

function BpuElecReferentiel({ supplier }: { supplier: "ENGIE" | "EDF" }) {
  const query = useMarketBpuDocumentsV1(supplier);
  return (
    <Card title={`Référentiel BPU — ${supplier}`} eyebrow="documents de prix (fourniture électricité) · lecture seule">
      {query.isError ? (
        <p className="po2-muted-line">BPU indisponible : {errorMessage(query.error)}</p>
      ) : query.isFetching && !query.data ? (
        <p className="po2-muted-line">Chargement des BPU {supplier}…</p>
      ) : query.data && query.data.length > 0 ? (
        <DataTable<MarketBpuDocumentV1>
          rows={query.data}
          getRowKey={(row) => String(row.id)}
          columns={[
            { key: "valid_year", header: "Année", render: (row) => String(row.valid_year) },
            { key: "lot_number", header: "Lot", render: (row) => String(row.lot_number) },
            { key: "market_subsequent", header: "MS", render: (row) => (row.market_subsequent ? `MS${row.market_subsequent}` : "—") },
            { key: "amendment", header: "Avenant", render: (row) => row.amendment_label ?? (row.amendment_number ? `n°${row.amendment_number}` : "—") },
            { key: "validity", header: "Validité", render: (row) => `${dateFr(row.valid_from)} → ${dateFr(row.valid_to)}` },
            { key: "extraction_status", header: "Extraction", render: (row) => row.extraction_status },
            { key: "pdf_filename", header: "Fichier", render: (row) => row.pdf_filename },
          ]}
        />
      ) : (
        <p className="po2-muted-line">Aucun BPU {supplier} importé pour l'instant.</p>
      )}
    </Card>
  );
}

// --------------------------------------------------------------------------- //
// BPU gaz lot 7 (TotalEnergies)
// --------------------------------------------------------------------------- //

function BpuGazReferentiel() {
  const query = useMarketGasBpuV1();
  return (
    <Card title="Référentiel BPU gaz — TotalEnergies (lot 7)" eyebrow="prix fourniture par profil · lecture seule">
      {query.isError ? (
        <p className="po2-muted-line">BPU gaz indisponible : {errorMessage(query.error)}</p>
      ) : query.isFetching && !query.data ? (
        <p className="po2-muted-line">Chargement de la grille BPU gaz…</p>
      ) : query.data && query.data.length > 0 ? (
        <DataTable<MarketGasBpuPriceV1>
          rows={query.data}
          getRowKey={(row) => String(row.id)}
          columns={[
            { key: "annee", header: "Année", render: (row) => String(row.annee) },
            { key: "profil", header: "Profil", render: (row) => row.profil },
            { key: "fourniture", header: "Fourniture", render: (row) => priceMwh(row.fourniture_ht_mwh) },
            { key: "cee", header: "CEE", render: (row) => priceMwh(row.cee_ht_mwh) },
            { key: "cee_prec", header: "CEE précarité", render: (row) => priceMwh(row.cee_precarite_ht_mwh) },
            { key: "cpb", header: "CPB", render: (row) => priceMwh(row.cpb_ht_mwh) },
            { key: "go", header: "GO", render: (row) => priceMwh(row.go_ht_mwh) },
            { key: "source", header: "Source", render: (row) => row.source ?? "—" },
          ]}
        />
      ) : (
        <p className="po2-muted-line">Aucune grille BPU gaz enregistrée.</p>
      )}
    </Card>
  );
}

// --------------------------------------------------------------------------- //
// Dispatch par tier
// --------------------------------------------------------------------------- //

export function MarketReferentielV1({ tier }: { tier: MarketTier }) {
  if (tier === "dalkia") return <DpgfReferentiel />;
  if (tier === "gaz") return <BpuGazReferentiel />;
  if (tier === "engie") return <BpuElecReferentiel supplier="ENGIE" />;
  return <BpuElecReferentiel supplier="EDF" />;
}
