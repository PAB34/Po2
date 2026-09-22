import { useQuery } from "@tanstack/react-query";
import { Link, NavLink, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi } from "../api";
import { ComponentLibrary } from "../library/ComponentLibrary";
import { projectQueryKey } from "../projectCache";

const tabClass = ({ isActive }: { isActive: boolean }) => (isActive ? "is-active" : undefined);

// Onglets d'un projet : ses plans et planches, sa bibliothèque de composants.
export function ProjectTabs({ projectId }: { projectId: number }) {
  return (
    <nav className="th-segmented th-section" aria-label="Sections du projet">
      <NavLink to={`/projets/${projectId}`} end className={tabClass}>
        Plans et planches
      </NavLink>
      <NavLink to={`/projets/${projectId}/bibliotheque`} className={tabClass}>
        Bibliothèque
      </NavLink>
    </nav>
  );
}

export function ProjectLibraryPage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const { data: project, error } = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled: Boolean(token) && Number.isFinite(projectId),
  });

  if (error) {
    return <p className="th-alert th-alert--error">{error.message}</p>;
  }
  return (
    <>
      <div className="th-page-head">
        <div>
          <p className="po2-eyebrow">
            <Link to="/">Projets</Link>
          </p>
          <h1>{project?.name ?? "…"}</h1>
          <p className="th-muted">
            Les composants du bâtiment, par catégorie : créez-les, dupliquez-les ou importez vos modèles. Chaque carte se déplie pour voir et
            modifier sa composition.
          </p>
        </div>
      </div>
      <ProjectTabs projectId={projectId} />
      <ComponentLibrary scope={{ kind: "projet", projectId }} />
    </>
  );
}
