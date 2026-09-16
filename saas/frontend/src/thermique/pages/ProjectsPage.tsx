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
  const [erasing, setErasing] = useState(false);
  const [confirmation, setConfirmation] = useState("");

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

  // Efface tous les projets du compte ; la bibliothèque de modèles réutilisables est gardée.
  const eraseAll = useMutation({
    mutationFn: () => thermiqueApi.eraseAllProjects(token!, confirmation),
    onSuccess: async () => {
      setErasing(false);
      setConfirmation("");
      // Plus aucun projet : on oublie tout ce qui était en cache pour eux, sauf la liste elle-même, rechargée.
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] === "thermique" && query.queryKey[1] !== projectsQueryKey[1] });
      await queryClient.invalidateQueries({ queryKey: projectsQueryKey });
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

      {projects.data && (projects.data.length > 0 || eraseAll.isSuccess) && (
        <section className="po2-card th-section th-danger-zone">
          <div className="po2-card__body">
            <h2>Tout effacer</h2>
            {eraseAll.isSuccess && (
              <p className="th-alert th-alert--ok">
                {eraseAll.data.projets_effaces} projet{eraseAll.data.projets_effaces > 1 ? "s effacés" : " effacé"} avec leurs documents et leurs
                tracés.
              </p>
            )}
            {projects.data.length > 0 && !erasing && (
              <>
                <p className="th-muted">
                  Supprime définitivement vos {projects.data.length} projet{projects.data.length > 1 ? "s" : ""} : plans, coupes, niveaux, tracés et
                  composants de projet. Votre bibliothèque de modèles réutilisables est gardée.
                </p>
                <button type="button" className="po2-button po2-button--secondary th-button-danger" onClick={() => setErasing(true)}>
                  Effacer tous mes projets…
                </button>
              </>
            )}
            {projects.data.length > 0 && erasing && (
              <form
                className="th-inline-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (confirmation.trim().toUpperCase() === "EFFACER") {
                    eraseAll.mutate();
                  }
                }}
              >
                <label className="th-field th-field--grow">
                  <span>Tapez EFFACER pour confirmer (action irréversible)</span>
                  <input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoFocus maxLength={20} />
                </label>
                <button
                  type="submit"
                  className="po2-button po2-button--primary th-button-danger"
                  disabled={confirmation.trim().toUpperCase() !== "EFFACER" || eraseAll.isPending}
                >
                  {eraseAll.isPending ? "Effacement…" : `Effacer ${projects.data.length} projet${projects.data.length > 1 ? "s" : ""}`}
                </button>
                <button
                  type="button"
                  className="po2-button po2-button--ghost"
                  onClick={() => {
                    setErasing(false);
                    setConfirmation("");
                  }}
                >
                  Annuler
                </button>
              </form>
            )}
            {eraseAll.error && <p className="th-alert th-alert--error">{eraseAll.error.message}</p>}
          </div>
        </section>
      )}
    </>
  );
}
