import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Proxy all /api/* requests to the FastAPI backend.
  // This routes them through the same origin (localhost:3000 → localhost:8000)
  // so the browser never sees a cross-origin request — CORS is bypassed entirely.
  async rewrites() {
    const apiUrl = process.env.API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
  allowedDevOrigins: ['172.21.144.1', '192.168.56.1', 'localhost', '127.0.0.1'],
};

export default nextConfig;