import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// Outil de métré thermique : second point d'entrée (thermique.html), servi sur le
// sous-domaine thermique.* ou sous /thermique/ (même règle que nginx.conf).
function thermiqueDevEntry(): Plugin {
  return {
    name: "thermique-dev-entry",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const host = req.headers.host ?? "";
        const url = req.url ?? "/";
        const wantsHtml = (req.headers.accept ?? "").includes("text/html");
        const isThermique = host.startsWith("thermique.") || url === "/thermique" || url.startsWith("/thermique/");
        if (wantsHtml && !url.startsWith("/api") && isThermique) {
          req.url = "/thermique.html";
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), thermiqueDevEntry()],
  build: {
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL("./index.html", import.meta.url)),
        thermique: fileURLToPath(new URL("./thermique.html", import.meta.url)),
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
