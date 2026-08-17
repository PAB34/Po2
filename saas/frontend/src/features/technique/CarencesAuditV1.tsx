import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { StatusBadge } from "../../design-system";
import {
  downloadCvcCarencesWorkbook,
  fetchCvcCarences,
  type CvcCarenceChamp,
  type CvcCarenceProvider,
} from "../../lib/api";
import { useAuth } from "../../providers/AuthProvider";

function fmtInt(value: number): string {
  return value.toLocaleString("fr-FR");
}

function completudeTone(pct: number): "ok" | "warn" | "bad" {
  if (pct >= 80) return "ok";
  if (pct >= 50) return "warn";
  return "bad";
}

/** Barre de remplissage d'un champ : rouge = ce qui manque. */
function ChampRow({ champ }: { champ: CvcCarenceChamp }) {
  const rempli = 100 - champ.manquants_pct;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, gap: 8 }}>
        <span>
          {champ.label}{" "}
          <small className="po2-muted-line" style={{ fontSize: 11 }}>{champ.groupe}</small>
        </span>
        <strong>{fmtInt(champ.manquants)} manquants ({champ.manquants_pct} %)</strong>
      </div>
      <div style={{ height: 6, background: "rgba(148,163,184,0.18)", borderRadius: 4, overflow: "hidden", marginTop: 3 }}>
        <div
          style={{
            width: `${Math.max(0, rempli)}%`,
            height: "100%",
            background: rempli >= 80 ? "#247a60" : rempli >= 50 ? "#91631b" : "#a6413b",
          }}
        />
      </div>
    </div>
  );
}

function ProviderCard({ provider }: { provider: CvcCarenceProvider }) {
  const { token } = useAuth();
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onExport = async () => {
    setDownloading(true);
    setError(null);
    try {
      const blob = await downloadCvcCarencesWorkbook(token!, provider.provider);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `demande-completude-${provider.provider.toLowerCase()}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export impossible");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <section className="po2-card">
      <header className="po2-card__header">
        <div>
          <span className="po2-eyebrow">Titulaire</span>
          <h2>{provider.provider}</h2>
        </div>
        <StatusBadge tone={completudeTone(provider.completude_globale_pct)}>
          {`${provider.completude_globale_pct} % renseigné`}
        </StatusBadge>
      </header>
      <div className="po2-card__body">
        <p className="po2-muted-line" style={{ fontSize: 13, marginTop: 0 }}>
          {fmtInt(provider.equipements)} équipements inventoriés, dont{" "}
          <strong>{fmtInt(provider.equipements_incomplets)}</strong> auxquels il manque au moins une
          information exigible.
        </p>

        {provider.champs_non_livres.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ margin: "0 0 4px" }}>Champs absents de l'export</h4>
            <p className="po2-muted-line" style={{ fontSize: 12, marginTop: 0 }}>
              Ces colonnes n'existent pas dans le fichier livré : la demande porte sur une évolution
              du format, pas sur un remplissage ligne à ligne.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {provider.champs_non_livres.map((champ) => (
                <StatusBadge key={champ.champ} tone="bad">{champ.label}</StatusBadge>
              ))}
            </div>
          </div>
        )}

        {provider.champs_incomplets.length > 0 ? (
          <div>
            <h4 style={{ margin: "0 0 4px" }}>Champs livrés mais incomplets</h4>
            <p className="po2-muted-line" style={{ fontSize: 12, marginTop: 0 }}>
              La colonne existe : la demande porte sur les équipements non renseignés.
            </p>
            {provider.champs_incomplets.map((champ) => (
              <ChampRow key={champ.champ} champ={champ} />
            ))}
          </div>
        ) : (
          <p className="po2-muted-line">Aucun champ livré n'est incomplet.</p>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            className="po2-button po2-button--primary"
            onClick={onExport}
            disabled={downloading || provider.equipements_incomplets === 0}
          >
            {downloading ? "Préparation…" : "Télécharger la demande de complétude"}
          </button>
          <span className="po2-muted-line" style={{ fontSize: 12 }}>
            Classeur Excel : un équipement par ligne, identification pré-remplie, colonnes à compléter
            laissées vides — réimportable une fois rempli.
          </span>
        </div>
        {error && <p className="po2-muted-line" style={{ color: "#a6413b", fontSize: 12 }}>{error}</p>}
      </div>
    </section>
  );
}

export function CarencesAuditV1() {
  const { token } = useAuth();
  const { data: report, isLoading } = useQuery({
    queryKey: ["cvc-carences"],
    queryFn: () => fetchCvcCarences(token!),
    enabled: !!token,
    staleTime: 60_000,
  });

  if (isLoading && !report) {
    return <p className="po2-muted-line">Analyse des carences…</p>;
  }
  if (!report || report.providers.length === 0) {
    return <p className="po2-muted-line">Aucun inventaire importé.</p>;
  }

  const rattachementPct = report.rattachement_total
    ? Math.round((100 * (report.rattachement_total - report.rattachement_manquant)) / report.rattachement_total)
    : 0;

  return (
    <>
      {report.providers.map((provider) => (
        <ProviderCard key={provider.provider} provider={provider} />
      ))}

      {/* Ce qui ne relève PAS du titulaire : à traiter en interne. */}
      <section className="po2-card">
        <header className="po2-card__header">
          <div>
            <span className="po2-eyebrow">À traiter en interne</span>
            <h2>Rattachement au patrimoine</h2>
          </div>
          <StatusBadge tone={completudeTone(rattachementPct)}>{`${rattachementPct} % rattachés`}</StatusBadge>
        </header>
        <div className="po2-card__body">
          <p className="po2-muted-line" style={{ marginTop: 0 }}>
            <strong>{fmtInt(report.rattachement_manquant)}</strong> équipements sur{" "}
            {fmtInt(report.rattachement_total)} ne sont reliés à aucun bâtiment. Ce n'est pas une
            carence du titulaire : le rattachement résulte du rapprochement entre son libellé de site
            et notre référentiel patrimoine. Il se traite dans l'écran des rattachements, ou en créant
            au patrimoine les bâtiments manquants.
          </p>
        </div>
      </section>
    </>
  );
}
