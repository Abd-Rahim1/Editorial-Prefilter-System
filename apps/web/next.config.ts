import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Proxy all /api/* requests to the FastAPI backend.
  // This routes them through the same origin (localhost:3000 → localhost:8000)
  // so the browser never sees a cross-origin request — CORS is bypassed entirely.
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
  allowedDevOrigins: ['172.21.144.1', '192.168.56.1', 'localhost', '127.0.0.1'],
};

export default nextConfig;