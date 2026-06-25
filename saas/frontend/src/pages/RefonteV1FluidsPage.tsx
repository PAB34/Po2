import { useState } from "react";
import { AppShellV1 } from "../app/AppShellV1";
import type { AppProfileV1 } from "../app/navigationV1";
import { FluidsPortfolioPageV1 } from "../features/fluids/FluidsPortfolioPageV1";
import { useAuth } from "../providers/AuthProvider";
export function RefonteV1FluidsPage() { const { logout, user } = useAuth(); const [profile, setProfile] = useState<AppProfileV1>("fluides"); const userLabel = user ? `${user.prenom} ${user.nom}` : undefined; return <AppShellV1 profile={profile} userLabel={userLabel} onProfileChange={setProfile} onLogout={logout} routePrefix="/refonte-v1"><FluidsPortfolioPageV1 /></AppShellV1>; }
