import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
// CRITICAL: root must be absolute path for Vercel builds
// Using path.resolve to ensure absolute path even if __dirname is relative
const rootPath = path.resolve(__dirname);

export default defineConfig({
  root: rootPath,
  base: "./",
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(rootPath, "./src"),
    },
    extensions: [".mjs", ".js", ".mts", ".ts", ".jsx", ".tsx", ".json"],
  },
  build: {
    rollupOptions: {
      input: path.resolve(rootPath, "index.html"),
    },
  },
});
