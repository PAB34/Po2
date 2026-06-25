import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { navigationV1, profilesV1, type AppProfileV1 } from "./navigationV1";

type AppShellV1Props = { children: ReactNode; profile?: AppProfileV1; userLabel?: string; onProfileChange?: (profile: AppProfileV1) => void; onLogout?: () => void; routePrefix?: string; };
function isActive(pathname: string, to: string) { return pathname === to || (to !== "/" && pathname.startsWith(to + "/")); }

export function AppShellV1({ children, profile = "direction", userLabel, onProfileChange, onLogout, routePrefix = "" }: AppShellV1Props) {
  const location = useLocation();
  const labTo = (key: string, to: string) => {
    if (!routePrefix) return to;
    const mapped: Record<string, string> = { cockpit: routePrefix, invoices: `${routePrefix}/factures`, fluids: `${routePrefix}/fluides`, sites: `${routePrefix}/sites` };
    return mapped[key] ?? to;
  };
  return (
    <div className="po2-shell-v1">
      <aside className="po2-shell-v1__sidebar"><Link to="/" className="po2-shell-v1__brand" aria-label="Accueil Po2"><span className="po2-shell-v1__logo">PO²</span><span><strong>Patrimoine au carré</strong><small>Gérer aujourd’hui, bâtir demain</small></span></Link><nav className="po2-shell-v1__nav" aria-label="Navigation V1">{navigationV1.map((section) => <div key={section.label} className="po2-shell-v1__nav-section"><span>{section.label}</span>{section.items.map((item) => <Link key={item.key} to={labTo(item.key, item.to)} className={isActive(location.pathname, labTo(item.key, item.to)) ? "po2-shell-v1__nav-link po2-shell-v1__nav-link--active" : "po2-shell-v1__nav-link"}><span>{item.label}</span>{item.badge ? <b>{item.badge}</b> : null}</Link>)}</div>)}</nav></aside>
      <div className="po2-shell-v1__main"><header className="po2-shell-v1__topbar"><button type="button" className="po2-shell-v1__search">⌕ Rechercher un site, une facture, un compteur</button><label className="po2-shell-v1__profile"><span>Voir comme</span><select value={profile} onChange={(event) => onProfileChange?.(event.target.value as AppProfileV1)}>{Object.entries(profilesV1).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>{userLabel ? <span className="po2-shell-v1__user">{userLabel}</span> : null}{onLogout ? <button type="button" className="po2-shell-v1__logout" onClick={onLogout}>Se déconnecter</button> : null}</header><main className="po2-shell-v1__content">{children}</main></div>
    </div>
  );
}
