/** @type {import('next').NextConfig} */
const nextConfig = {
  ...(process.env.DOCKER_BUILD === "true" ? { output: "standalone" } : {}),
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
  // F4 Content Hub (2026-05-19) · redirects 308 de las 4 rutas viejas al
  // workspace unificado /dashboard/hub. Rollback: remover este bloque + las
  // rutas viejas siguen funcionando (NO se eliminaron del codebase).
  async redirects() {
    return [
      {
        source: "/dashboard/social",
        destination: "/dashboard/hub?tab=feed",
        permanent: true,
      },
      {
        source: "/dashboard/social/comentarios",
        destination: "/dashboard/hub?tab=comentarios",
        permanent: true,
      },
      {
        source: "/dashboard/content/top",
        destination: "/dashboard/hub?tab=top",
        permanent: true,
      },
      {
        source: "/dashboard/aceptacion/fans",
        destination: "/dashboard/hub?tab=fans",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
