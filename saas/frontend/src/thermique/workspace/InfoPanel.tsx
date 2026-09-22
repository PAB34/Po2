import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type ProjectDetail } from "../api";
import { allSheets, projectQueryKey, projectsQueryKey } from "../projectCache";
import { groupSheets, sheetTitle } from "./levels";

type Props = {
  project: ProjectDetail;
  referenceId: number | null;
  onReference: (sheetId: number) => void;
};

// Panneau « Infos du projet » : nom, description, plan de référence, contenu du dossier.
export function InfoPanel({ project, referenceId, onReference }: Props) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description ?? "");
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const sheets = allSheets(project);
  const groups = groupSheets(sheets);
  const changed = name.trim() !== project.name || (description.trim() || null) !== project.description;

  const save = async () => {
    if (!name.trim()) {
      setMessage({ tone: "error", text: "Le projet doit avoir un nom." });
      return;
    }
    try {
      await thermiqueApi.updateProject(token!, project.id, { name: name.trim(), description: description.trim() || null });
      await queryClient.invalidateQueries({ queryKey: projectQueryKey(project.id) });
      void queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      setMessage({ tone: "ok", text: "Enregistré." });
    } catch (failure) {
      setMessage({ tone: "error", text: failure instanceof Error ? failure.message : "Enregistrement impossible." });
    }
  };

  return (
    <>
      <section className="th-form">
        <h2>Projet</h2>
        <label className="th-field">
          <span>Nom</span>
          <input value={name} maxLength={200} onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="th-field">
          <span>Description</span>
          <textarea rows={3} value={description} onChange={(event) => setDescription(event.target.value)} />
        </label>
        <div className="th-inline">
          <button type="button" className="po2-button po2-button--primary" disabled={!changed} onClick={() => void save()}>
            Enregistrer
          </button>
          {message && <span className={message.tone === "ok" ? "th-muted" : "th-alert th-alert--error"}>{message.text}</span>}
        </div>
      </section>

      <section>
        <h2>Plan de référence</h2>
        <p className="th-muted">Le plan qui s'ouvre en premier. Par défaut, le RDC.</p>
        <select
          value={referenceId ?? ""}
          disabled={groups.levels.length === 0}
          onChange={(event) => event.target.value && onReference(Number(event.target.value))}
        >
          {groups.levels.map((sheet) => (
            <option key={sheet.id} value={sheet.id}>
              {sheetTitle(sheet)}
            </option>
          ))}
        </select>
        {groups.levels.length === 0 && <p className="th-muted">Classez au moins une planche en « plan » pour choisir le plan de référence.</p>}
      </section>

      <section>
        <h2>Contenu du dossier</h2>
        <ul className="th-ws-facts">
          <li>
            <span>Plans de niveau</span>
            <strong>{groups.levels.length}</strong>
          </li>
          <li>
            <span>Coupes</span>
            <strong>{groups.sections.length}</strong>
          </li>
          <li>
            <span>Façades</span>
            <strong>{groups.elevations.length}</strong>
          </li>
          <li>
            <span>Autres planches</span>
            <strong>{groups.others.length}</strong>
          </li>
          <li>
            <span>Planches prêtes (classées et à l'échelle)</span>
            <strong>
              {sheets.filter((sheet) => sheet.status === "prete").length} / {sheets.length}
            </strong>
          </li>
          <li>
            <span>Fichiers PDF</span>
            <strong>{project.documents.length}</strong>
          </li>
        </ul>
      </section>
    </>
  );
}
