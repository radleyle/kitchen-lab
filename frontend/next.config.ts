import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Emits a minimal Node server under .next/standalone for the prod image.
  output: "standalone",
  // Monorepo: avoid Next picking the repo-root lockfile as the workspace root.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
