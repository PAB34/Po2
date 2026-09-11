import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi } from "../api";
import { formatDate, projectsQueryKey } from "../projectCache";

export function ProjectsPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const projects = useQuery({
    queryKey: projectsQueryKey,
    queryFn: () => thermiqueApi.listProjects(token!),
    enabled: Boolean(token),
  });

  const create = useMutation({
    mutationFn: () => thermiqueApi.createProject(token!, { name, description: description || undefined }),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      navigate(`/projets/${project.id}`);
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (name.trim()) {
      create.mutate();
    }
  }

  return (
    <>
      <div className="th-page-head">
        <div>
          <p className="po2-eyebrow">Métré thermique</p>
          <h1>Projets</h1>
          <p className="th-muted">Un projet regroupe les plans, coupes et façades d'un bâtiment à métrer.</p>
        </div>
      </div>

      <section className="po2-card th-section">
        <div className="po2-card__body">
          <form className="th-inline-form" onSubmit={handleSubmit}>
            <label className="th-field th-field--grow">
              <span>Nouveau projet</span>
              <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex. Médiathèque de Frontignan" maxLength={200} />
            </label>
            <label className="th-field th-field--grow">
              <span>Description (facultatif)</span>
              <input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Ex. Dossier PC, lot E1" maxLength={2000} />
            </label>
            <button type="submit" className="po2-button po2-button--primary" disabled={!name.trim() || create.isPending}>
              {create.isPending ? "Création…" : "Créer le projet"}
            </button>
          </form>
          {create.error && <p className="th-alert th-alert--error">{create.error.message}</p>}
        </div>
      </section>

      {projects.isLoading && <p className="th-muted">Chargement des projets…</p>}
      {projects.error && <p className="th-alert th-alert--error">{projects.error.message}</p>}
      {projects.data && projects.data.length === 0 && (
        <p className="th-empty">Aucun projet pour l'instant. Créez-en un pour importer vos plans et vos coupes.</p>
      )}

      <div className="th-grid">
        {projects.data?.map((project) => (
          <Link key={project.id} to={`/projets/${project.id}`} className="po2-card th-project-card">
            <strong>{project.name}</strong>
            {project.description && <span className="th-muted">{project.description}</span>}
            <span>
              {project.sheet_count} planche{project.sheet_count > 1 ? "s" : ""} · {project.sheets_ready} prête
              {project.sheets_ready > 1 ? "s" : ""}
            </span>
            <small className="th-muted">Modifié le {formatDate(project.updated_at)}</small>
          </Link>
        ))}
      </div>
    </>
  );
}
