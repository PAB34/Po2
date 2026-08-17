import { useState, type ReactNode } from "react";
import { AppShellV1 } from "../app/AppShellV1";
import type { AppProfileV1 } from "../app/navigationV1";
import { TechniqueParcDetailV1 } from "../features/technique/TechniqueParcDetailV1";
import { useAuth } from "../providers/AuthProvider";

function TechniqueShell({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth();
  const [profile, setProfile] = useState<AppProfileV1>("technique");
  const userLabel = user ? `${user.prenom} ${user.nom}` : undefined;
  return (
    <AppShellV1 profile={profile} userLabel={userLabel} onProfileChange={setProfile} onLogout={logout} routePrefix="/refonte-v1">
      {children}
    </AppShellV1>
  );
}

// État du parc technique CVC. Les écrans d'acquisition (import, rattachements,
// fluides frigorigènes) restent sur leurs routes legacy `/buildings/cvc-*`,
// accessibles depuis l'en-tête de la page.
export function RefonteV1TechniquePage() {
  return <TechniqueShell><TechniqueParcDetailV1 /></TechniqueShell>;
}
