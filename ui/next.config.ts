import type { NextConfig } from "next";

const BACKEND_URL = process.env.NOVA_BACKEND_URL ?? "http://localhost:8765";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
