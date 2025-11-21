import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
// Updated: Using relative paths for proper resolution in all environments
export default defineConfig({
  base: "./",
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    extensions: [".mjs", ".js", ".mts", ".ts", ".jsx", ".tsx", ".json"],
  },
});
