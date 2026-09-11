import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "../providers/AuthProvider";
import { ThermiqueApp } from "./ThermiqueApp";
import "../design-system/tokens.css";
import "./thermique.css";

// Sur thermique.* l'outil est à la racine ; ailleurs (site principal, staging, dev) sous /thermique/.
const basename = window.location.hostname.startsWith("thermique.") ? "/" : "/thermique";
const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false } } });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter basename={basename}>
          <ThermiqueApp />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
