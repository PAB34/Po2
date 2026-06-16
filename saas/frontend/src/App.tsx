import { Link, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./providers/AuthProvider";

import { AccountPage } from "./pages/AccountPage";
import { BuildingCreateEditPage } from "./pages/BuildingCreateEditPage";
import { BuildingDetailPage } from "./pages/BuildingDetailPage";
import { BuildingsListPage } from "./pages/BuildingsListPage";
import { BuildingsLandingPage } from "./pages/BuildingsLandingPage";
import { BuildingTechniquePage } from "./pages/BuildingTechniquePage";
import { CvcImportPage } from "./pages/CvcImportPage";
import { CvcRefrigerantsPage } from "./pages/CvcRefrigerantsPage";
import { CvcSiteMappingPage } from "./pages/CvcSiteMappingPage";
import { CvcTechnicalReportPage } from "./pages/CvcTechnicalReportPage";
import MeterMatchingPage from "./pages/MeterMatchingPage";
import { EnergieBillingPage } from "./pages/EnergieBillingPage";
import CpeDalkiaPage from "./pages/CpeDalkiaPage";
import { CpeDalkiaImportPage } from "./pages/CpeDalkiaImportPage";
import CpeSiteDetailPage from "./pages/CpeSiteDetailPage";
import EnergieBpuPage from "./pages/EnergieBpuPage";
import { EnergieDetailPage } from "./pages/EnergieDetailPage";
import { EnergieGazPage } from "./pages/EnergieGazPage";
import { EnergieInvoiceDetailPage } from "./pages/EnergieInvoiceDetailPage";
import FacturesPage from "./pages/FacturesPage";
import { EnergieDataOpsPage, EnergiePage } from "./pages/EnergiePage";
import { EnergieRecommendationsPage } from "./pages/EnergieRecommendationsPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { ProductDomainPage } from "./pages/ProductDomainPage";
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

type NavLink = { to: string; label: string };
type Pillar = "energie" | "maintenance" | "patrimoine";
type NavDomain = {
  key: string;
  label: string;
  primaryTo: string;
  pillar?: Pillar;
  prefixes: string[];
  links: NavLink[];
};

const DOMAINS: NavDomain[] = [
  { key: "dashboard", label: "Tableau de bord", primaryTo: "/", prefixes: [], links: [] },
  {
    key: "patrimoine",
    label: "Patrimoine",
    primaryTo: "/patrimoine",
    pillar: "patrimoine",
    prefixes: ["/patrimoine", "/buildings/list", "/buildings/compteurs", "/buildings/create-edit", "/buildings"],
    links: [
      { to: "/patrimoine", label: "Vue d'ensemble" },
      { to: "/buildings/list", label: "Sites et bâtiments" },
      { to: "/buildings/compteurs", label: "Rapprochement compteurs" },
      { to: "/buildings/create-edit", label: "Import patrimoine" },
    ],
  },
  {
    key: "energie",
    label: "Fluides & consommations",
    primaryTo: "/energie",
    pillar: "energie",
    prefixes: ["/energie"],
    links: [
      { to: "/energie", label: "Vue d'ensemble" },
      { to: "/energie/donnees", label: "Acquisition & données" },
      { to: "/energie/preconisations", label: "Préconisations" },
      { to: "/energie/bpu", label: "Prix et TURPE" },
      { to: "/energie/gaz", label: "Gaz GRDF" },
    ],
  },
  {
    key: "marches",
    label: "Marchés & contrats",
    primaryTo: "/marches",
    pillar: "maintenance",
    prefixes: ["/marches", "/factures", "/cpe"],
    links: [
      { to: "/marches", label: "Vue d'ensemble" },
      { to: "/factures", label: "Factures marché" },
      { to: "/cpe", label: "CPE DALKIA" },
      { to: "/cpe/dalkia-import", label: "Référentiel DALKIA" },
    ],
  },
  {
    key: "technique",
    label: "Technique",
    primaryTo: "/technique",
    pillar: "maintenance",
    prefixes: [
      "/technique",
      "/buildings/technique",
      "/buildings/cvc-fluides",
      "/buildings/cvc-rapport-technique",
      "/buildings/cvc-import",
    ],
    links: [
      { to: "/technique", label: "Vue d'ensemble" },
      { to: "/buildings/technique", label: "Inventaire & CVC" },
      { to: "/buildings/cvc-fluides", label: "Fluides frigorigènes & ESP" },
      { to: "/buildings/cvc-rapport-technique", label: "Rapport technique CVC" },
    ],
  },
  {
    key: "admin",
    label: "Administration",
    primaryTo: "/administration",
    prefixes: ["/administration", "/cpe/dalkia-import", "/buildings/cvc-import", "/energie/facturation", "/account"],
    links: [
      { to: "/administration", label: "Vue d'ensemble" },
      { to: "/cpe/dalkia-import", label: "Import référentiel DALKIA" },
      { to: "/buildings/cvc-import", label: "Import CVC terrain" },
      { to: "/buildings/cvc-import/batiments", label: "Matching bâtiment CVC" },
      { to: "/energie/facturation", label: "Configuration tarifaire" },
      { to: "/account", label: "Mon compte" },
    ],
  },
];

const PILLARS: { key: Pillar; label: string; to: string }[] = [
  { key: "energie", label: "Fluides", to: "/energie" },
  { key: "maintenance", label: "Maintenance", to: "/marches" },
  { key: "patrimoine", label: "Patrimoine", to: "/patrimoine" },
];

function matchesPrefix(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`);
}

function activeDomain(path: string): NavDomain {
  if (path === "/") return DOMAINS[0];
  let best: NavDomain = DOMAINS[0];
  let bestLen = -1;
  for (const domain of DOMAINS) {
    for (const prefix of domain.prefixes) {
      if (matchesPrefix(path, prefix) && prefix.length > bestLen) {
        best = domain;
        bestLen = prefix.length;
      }
    }
  }
  return best;
}

function activeLinkTo(path: string, links: NavLink[]): string | null {
  let best: string | null = null;
  let bestLen = -1;
  for (const link of links) {
    if (matchesPrefix(path, link.to) && link.to.length > bestLen) {
      best = link.to;
      bestLen = link.to.length;
    }
  }
  return best;
}

export default function App() {
  const { logout, user } = useAuth();
  const location = useLocation();
  const current = activeDomain(location.pathname);
  const currentLink = activeLinkTo(location.pathname, current.links);

  return (
    <div className="app-shell">
      {user && (
        <>
          <header className="topbar">
            <Link to="/" className="topbar-brand">
              <span className="topbar-brand-eyebrow">Patrimoineaucarré</span>
              <strong>Po2</strong>
            </Link>
            <div className="topbar-pills">
              {PILLARS.map((pillar) => (
                <Link key={pillar.key} to={pillar.to} className={`topbar-pill topbar-pill--${pillar.key}`}>
                  {pillar.label}
                </Link>
              ))}
            </div>
            <div className="topbar-session">
              <span className="topbar-user">{`${user.prenom} ${user.nom}`}</span>
              <button type="button" className="secondary-button" onClick={logout}>
                Se déconnecter
              </button>
            </div>
          </header>

          <nav className="topnav" aria-label="Navigation principale">
            {DOMAINS.map((domain) => (
              <Link
                key={domain.key}
                to={domain.primaryTo}
                className={`topnav-tab${domain.key === current.key ? " topnav-tab--active" : ""}`}
              >
                {domain.label}
              </Link>
            ))}
          </nav>

          {current.links.length > 0 && (
            <nav className="subnav" aria-label={`Navigation ${current.label}`}>
              {current.links.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`subnav-link${link.to === currentLink ? " subnav-link--active" : ""}`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          )}
        </>
      )}

      <main className="content">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<RequireAuth />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/patrimoine" element={<ProductDomainPage domain="patrimoine" />} />
            <Route path="/patrimoine/sites" element={<Navigate to="/buildings/list" replace />} />
            <Route path="/patrimoine/rattachements" element={<Navigate to="/buildings/compteurs" replace />} />
            <Route path="/patrimoine/imports" element={<Navigate to="/buildings/create-edit" replace />} />
            <Route path="/buildings" element={<BuildingsLandingPage />} />
            <Route path="/buildings/list" element={<BuildingsListPage />} />
            <Route path="/buildings/create-edit" element={<BuildingCreateEditPage />} />
            <Route path="/buildings/technique" element={<BuildingTechniquePage />} />
            <Route path="/buildings/cvc-import" element={<CvcImportPage />} />
            <Route path="/buildings/cvc-fluides" element={<CvcRefrigerantsPage />} />
            <Route path="/buildings/cvc-rapport-technique" element={<CvcTechnicalReportPage />} />
            <Route path="/buildings/cvc-import/batiments" element={<CvcSiteMappingPage />} />
            <Route path="/buildings/compteurs" element={<MeterMatchingPage />} />
            <Route path="/buildings/:buildingId" element={<BuildingDetailPage />} />
            <Route path="/energie" element={<EnergiePage />} />
            <Route path="/energie/donnees" element={<EnergieDataOpsPage />} />
            <Route path="/energie/preconisations" element={<EnergieRecommendationsPage />} />
            <Route path="/factures" element={<FacturesPage />} />
            <Route path="/factures/:invoiceImportId" element={<EnergieInvoiceDetailPage />} />
            <Route path="/energie/factures" element={<Navigate to="/factures" replace />} />
            <Route
              path="/energie/factures/:invoiceImportId"
              element={<LegacyInvoiceRedirect />}
            />
            <Route path="/energie/facturation" element={<EnergieBillingPage />} />
            <Route path="/energie/bpu" element={<EnergieBpuPage />} />
            <Route path="/energie/gaz" element={<EnergieGazPage />} />
            <Route path="/energie/:prmId" element={<EnergieDetailPage />} />
            <Route path="/marches" element={<ProductDomainPage domain="marches" />} />
            <Route path="/marches/cpe-dalkia" element={<Navigate to="/cpe" replace />} />
            <Route path="/cpe" element={<CpeDalkiaPage />} />
            <Route path="/cpe/sites/:siteId" element={<CpeSiteDetailPage />} />
            <Route path="/cpe/dalkia-import" element={<CpeDalkiaImportPage />} />
            <Route path="/technique" element={<ProductDomainPage domain="technique" />} />
            <Route path="/technique/cvc" element={<Navigate to="/buildings/technique" replace />} />
            <Route path="/technique/fluides" element={<Navigate to="/buildings/cvc-fluides" replace />} />
            <Route path="/technique/rapport" element={<Navigate to="/buildings/cvc-rapport-technique" replace />} />
            <Route path="/administration" element={<ProductDomainPage domain="administration" />} />
            <Route path="/account" element={<AccountPage />} />
          </Route>
          <Route path="*" element={<Navigate to={user ? "/" : "/login"} replace />} />
        </Routes>
      </main>
    </div>
  );
}

function LegacyInvoiceRedirect() {
  const location = useLocation();
  const target = location.pathname.replace("/energie/factures", "/factures");
  return <Navigate to={target} replace />;
}
