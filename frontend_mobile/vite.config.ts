// frontend_mobile/vite.config.ts

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tsconfigPaths from 'vite-tsconfig-paths';
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  // SE siamo in produzione (build per il server Python), la base è /mobile/
  // SE siamo in sviluppo (npm run dev), la base è la root /
  base: mode === 'production' ? '/mobile/' : '/',
  server: {
    host: "0.0.0.0",
    port: 3000,
  },
  plugins: [
    react(), 
    tsconfigPaths(),
    mode === "development" && componentTagger()
  ].filter(Boolean),
}));