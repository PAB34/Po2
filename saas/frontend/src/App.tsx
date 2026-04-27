import { Link, Route, Routes } from "react-router-dom";
import { useAuth } from "./providers/AuthProvider";

import { AccountPage } from "./pages/AccountPage";
import { BuildingDetailPage } from "./pages/BuildingDetailPage";
import { BuildingHubPage } from "./pages/BuildingHubPage";
import { BuildingImportPage } from "./pages/BuildingImportPage";
import { BuildingsPage } from "./pages/BuildingsPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";

export default function App() {
  const { logout, user } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">PatrimoineOp</p>
          <h1>Socle MVP</h1>
        </div>
        <div className="session-card">
          <strong>{user ? `${user.prenom} ${user.nom}` : "Session non connectée"}</strong>
          <span>{user ? user.email : "Connecte-toi pour accéder au compte"}</span>
          {user && (
            <button type="button" className="secondary-button" onClick={logout}>
              Se déconnecter
            </button>
          )}
        </div>
        <nav>
          <Link to="/">Accueil</Link>
          <Link to="/buildings">Bâtiments</Link>
          <Link to="/login">Connexion</Link>
          <Link to="/register">Inscription</Link>
          <Link to="/account">Compte</Link>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/buildings" element={<BuildingHubPage />} />
          <Route path="/buildings/manual" element={<BuildingsPage />} />
          <Route path="/buildings/import" element={<BuildingImportPage />} />
          <Route path="/buildings/:buildingId" element={<BuildingDetailPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/account" element={<AccountPage />} />
        </Routes>
      </main>
    </div>
  );
}
