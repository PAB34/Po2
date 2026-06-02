import { Link, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./providers/AuthProvider";

import { AccountPage } from "./pages/AccountPage";
import { BuildingCreateEditPage } from "./pages/BuildingCreateEditPage";
import { BuildingDetailPage } from "./pages/BuildingDetailPage";
import { BuildingsListPage } from "./pages/BuildingsListPage";
import { BuildingsLandingPage } from "./pages/BuildingsLandingPage";
import { BuildingTechniquePage } from "./pages/BuildingTechniquePage";
import { CvcImportPage } from "./pages/CvcImportPage";
import { EnergieBillingPage } from "./pages/EnergieBillingPage";
import CpeDalkiaPage from "./pages/CpeDalkiaPage";
import { CpeDalkiaImportPage } from "./pages/CpeDalkiaImportPage";
import CpeSiteDetailPage from "./pages/CpeSiteDetailPage";
import EnergieBpuPage from "./pages/EnergieBpuPage";
import { EnergieDetailPage } from "./pages/EnergieDetailPage";
import { EnergieInvoiceDetailPage } from "./pages/EnergieInvoiceDetailPage";
import { EnergieInvoicesPage } from "./pages/EnergieInvoicesPage";
import { EnergiePage } from "./pages/EnergiePage";
import { EnergieRecommendationsPage } from "./pages/EnergieRecommendationsPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";

function RequireAuth() {
  const { isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <p>Chargement de la session...</p>;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export default function App() {
  const { logout, user } = useAuth();

  return (
    <div className="app-shell">
      {user && (
        <aside className="sidebar">
          <div>
            <p className="eyebrow">PatrimoineOp</p>
            <h1>Socle MVP</h1>
          </div>
          <div className="session-card">
            <strong>{`${user.prenom} ${user.nom}`}</strong>
            <span>{user.email}</span>
            <button type="button" className="secondary-button" onClick={logout}>
              Se déconnecter
            </button>
          </div>
          <nav>
            <Link to="/">Accueil</Link>
            <Link to="/buildings">Bâtiments</Link>
            <Link to="/buildings/technique">Gestion Technique</Link>
            <Link to="/buildings/cvc-import">Import CVC terrain</Link>
            <Link to="/energie">Énergie</Link>
            <Link to="/energie/preconisations">Preconisations</Link>
            <Link to="/energie/factures">Factures</Link>
            <Link to="/energie/facturation">Facturation</Link>
            <Link to="/energie/bpu">Historique BPU</Link>
            <Link to="/cpe">CPE DALKIA</Link>
            <Link to="/cpe/dalkia-import">Import référentiel DALKIA</Link>
            <Link to="/account">Compte</Link>
          </nav>
        </aside>
      )}
      <main className="content">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<RequireAuth />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/buildings" element={<BuildingsLandingPage />} />
            <Route path="/buildings/list" element={<BuildingsListPage />} />
            <Route path="/buildings/create-edit" element={<BuildingCreateEditPage />} />
            <Route path="/buildings/technique" element={<BuildingTechniquePage />} />
            <Route path="/buildings/cvc-import" element={<CvcImportPage />} />
            <Route path="/buildings/:buildingId" element={<BuildingDetailPage />} />
            <Route path="/energie" element={<EnergiePage />} />
            <Route path="/energie/preconisations" element={<EnergieRecommendationsPage />} />
            <Route path="/energie/factures" element={<EnergieInvoicesPage />} />
            <Route path="/energie/factures/:invoiceImportId" element={<EnergieInvoiceDetailPage />} />
            <Route path="/energie/facturation" element={<EnergieBillingPage />} />
            <Route path="/energie/bpu" element={<EnergieBpuPage />} />
            <Route path="/energie/:prmId" element={<EnergieDetailPage />} />
            <Route path="/cpe" element={<CpeDalkiaPage />} />
            <Route path="/cpe/sites/:siteId" element={<CpeSiteDetailPage />} />
            <Route path="/cpe/dalkia-import" element={<CpeDalkiaImportPage />} />
            <Route path="/account" element={<AccountPage />} />
          </Route>
          <Route path="*" element={<Navigate to={user ? "/" : "/login"} replace />} />
        </Routes>
      </main>
    </div>
  );
}
