import { useState, type ReactNode } from "react";
import { AppShellV1 } from "../app/AppShellV1";
import type { AppProfileV1 } from "../app/navigationV1";
import { FluidsPortfolioPageV1 } from "../features/fluids/FluidsPortfolioPageV1";
import { FluidWaterComingSoonV1 } from "../features/fluids/FluidWaterComingSoonV1";
import { EnergiePage, EnergieDataOpsPage } from "./EnergiePage";
import { EnergieGazPage } from "./EnergieGazPage";
import { useAuth } from "../providers/AuthProvider";

function FluidShell({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth();
  const [profile, setProfile] = useState<AppProfileV1>("fluides");
  const userLabel = user ? `${user.prenom} ${user.nom}` : undefined;
  return (
    <AppShellV1 profile={profile} userLabel={userLabel} onProfileChange={setProfile} onLogout={logout} routePrefix="/refonte-v1">
      {children}
    </AppShellV1>
  );
}

export function RefonteV1FluidsPage() {
  return <FluidShell><FluidsPortfolioPageV1 /></FluidShell>;
}

// Sous-routes « détail par distributeur » : on embarque les pages legacy réelles (Option A, pas de réécriture).
export function RefonteV1FluidElectricitePage() {
  return <FluidShell><EnergiePage /></FluidShell>;
}

// Fenêtre de collecte ENEDIS (acquisition) ré-hébergée dans le shell refonte.
export function RefonteV1FluidElectriciteCollectePage() {
  return <FluidShell><EnergieDataOpsPage /></FluidShell>;
}

export function RefonteV1FluidGazPage() {
  return <FluidShell><EnergieGazPage /></FluidShell>;
}

export function RefonteV1FluidEauPage() {
  return <FluidShell><FluidWaterComingSoonV1 /></FluidShell>;
}
