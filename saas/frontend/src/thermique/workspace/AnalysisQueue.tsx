import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type QueueResult, type Work } from "../api";

const STATUT_LABELS: Record<Work["statut"], string> = {
  en_attente: "à analyser",
  en_cours: "en cours sur votre poste",
  fini: "analysé",
  refuse: "écarté",
  echec: "échec",
};

const STATUT_TONS: Record<Work["statut"], string> = {
  en_attente: "th-work--attente",
  en_cours: "th-work--cours",
  fini: "th-work--fini",
  refuse: "th-work--ecarte",
  echec: "th-work--echec",
};

export function worksQueryKey(projectId: number) {
  return ["thermique", "travaux", projectId] as const;
}

/**
 * File d'analyse d'un projet (D97).
 *
 * Le serveur ne peut pas lancer les agents : ils tournent sur le poste du thermicien. L'écran doit donc
 * dire franchement que la suite dépend du relais, sinon une file qui ne bouge pas passe pour une panne.
 */
export function AnalysisQueue({ projectId }: { projectId: number }) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [dernier, setDernier] = useState<QueueResult | null>(null);

  const travaux = useQuery({
    queryKey: worksQueryKey(projectId),
    queryFn: () => thermiqueApi.listWorks(token!, projectId),
    enabled: Boolean(token),
  });

  const liste = travaux.data ?? [];
  const enFile = liste.filter((item) => item.statut === "en_attente" || item.statut === "en_cours");

  async function analyser() {
    setBusy(true);
    setErreur(null);
    try {
      setDernier(await thermiqueApi.analyseProject(token!, projectId));
      await queryClient.invalidateQueries({ queryKey: worksQueryKey(projectId) });
    } catch (echec) {
      setErreur(echec instanceof Error ? echec.message : "La mise en file a échoué.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="th-queue">
      <h2>Analyse des niveaux</h2>
      <div className="th-inline">
        <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => void analyser()}>
          {busy ? "Mise en file…" : "Analyser avec Claude Code"}
        </button>
        <button type="button" className="th-link" disabled={travaux.isFetching} onClick={() => void travaux.refetch()}>
          Actualiser
        </button>
      </div>
      <p className="th-muted">
        Les plans sont analysés sur votre poste, du niveau le plus bas au plus haut, pour que les composants
        reconnus à un étage servent au suivant.
      </p>

      {erreur && <p className="th-alert th-alert--error">{erreur}</p>}

      {dernier?.ecartes.length ? (
        <div className="th-alert">
          <strong>
            {dernier.ecartes.length} planche{dernier.ecartes.length > 1 ? "s écartées" : " écartée"}
          </strong>
          <ul className="th-work-ecartes">
            {dernier.ecartes.map((item) => (
              <li key={item.sheet_id}>
                <span>{item.label}</span> — {item.motif}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {enFile.length > 0 && (
        <p className="th-alert th-alert--warn">
          {enFile.length} niveau{enFile.length > 1 ? "x attendent" : " attend"} le relais sur votre poste. Lancez&nbsp;:
          <code>python scripts/relais_thermique.py</code>
        </p>
      )}

      {liste.length === 0 ? (
        <p className="th-muted">Aucun niveau n'a encore été envoyé à l'analyse.</p>
      ) : (
        <ul className="th-works">
          {liste.map((item) => (
            <li key={item.id} className={STATUT_TONS[item.statut]}>
              <div className="th-work-ligne">
                <span className="th-work-nom">{item.level_label || item.label}</span>
                <span className="th-work-statut">{STATUT_LABELS[item.statut]}</span>
              </div>
              {item.message && <p className="th-work-message">{item.message}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
