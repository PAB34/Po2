import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../providers/AuthProvider";
import { CalquesPage } from "./pages/CalquesPage";
import { SuperpositionPage } from "./pages/SuperpositionPage";
import { PiecesPage } from "./pages/PiecesPage";
import { EnveloppePage } from "./pages/EnveloppePage";
import { LibraryPage } from "./pages/LibraryHomePage";
import { MetrePage } from "./pages/MetrePage";
import { ThermiqueLoginPage } from "./pages/ThermiqueLoginPage";
import { ProjectLibraryPage } from "./pages/ProjectLibraryPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SheetPage } from "./pages/SheetPage";

function RequireAuth() {
  const { isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <p className="th-main th-muted">Chargement de la session…</p>;
  }
  if (!user) {
    return <Navigate to="/connexion" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  fontWeight: 750,
  textDecoration: isActive ? "underline" : "none",
  textUnderlineOffset: "0.35em",
});

function Shell({ fullWidth = false }: { fullWidth?: boolean }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="th-app">
      <header className="th-header">
        <Link to="/" className="th-brand">
          <strong>Métré thermique</strong>
          <span>patrimoine au carré</span>
        </Link>
        <nav className="th-inline" style={{ gap: "1.2rem" }} aria-label="Navigation principale">
          <NavLink to="/" end style={navLinkStyle}>
            Projets
          </NavLink>
          <NavLink to="/bibliotheque" style={navLinkStyle}>
            Bibliothèque
          </NavLink>
        </nav>
        <div className="th-header__user">
          <span>
            {user?.prenom} {user?.nom}
          </span>
          <button
            type="button"
            className="po2-button po2-button--ghost"
            onClick={() => {
              logout();
              navigate("/connexion");
            }}
          >
            Déconnexion
          </button>
        </div>
      </header>
      <main className={fullWidth ? "th-main th-main--full" : "th-main"}>
        <Outlet />
      </main>
    </div>
  );
}

export function ThermiqueApp() {
  return (
    <Routes>
      <Route path="/connexion" element={<ThermiqueLoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<Shell />}>
          <Route index element={<ProjectsPage />} />
          <Route path="projets/:projectId" element={<ProjectPage />} />
          <Route path="projets/:projectId/bibliotheque" element={<ProjectLibraryPage />} />
          <Route path="bibliotheque" element={<LibraryPage />} />
        </Route>
        <Route element={<Shell fullWidth />}>
          <Route path="projets/:projectId/planches/:sheetId" element={<SheetPage />} />
          <Route path="projets/:projectId/metre" element={<MetrePage />} />
          <Route path="projets/:projectId/calques" element={<CalquesPage />} />
          <Route path="projets/:projectId/superposition" element={<SuperpositionPage />} />
          <Route path="projets/:projectId/enveloppe" element={<EnveloppePage />} />
          <Route path="projets/:projectId/pieces" element={<PiecesPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
