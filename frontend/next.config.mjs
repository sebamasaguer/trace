/** @type {import('next').NextConfig} */
// URL interna del backend. Next la resuelve en el BUILD (queda fija en routes-manifest),
// por eso se pasa como build arg. En Dokploy: http://<nombre-app-backend>:8100
const backendUrl = (process.env.BACKEND_URL || "http://backend:8100").replace(/\/$/, "");

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`
      }
    ];
  }
};

export default nextConfig;
