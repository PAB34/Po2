import { Link, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../providers/AuthProvider";
import { ThermiqueLoginPage } from "./pages/ThermiqueLoginPage";
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
        </Route>
        <Route element={<Shell fullWidth />}>
          <Route path="projets/:projectId/planches/:sheetId" element={<SheetPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
