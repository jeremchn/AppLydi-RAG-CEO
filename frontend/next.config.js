/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  // L'URL sera définie via les variables d'environnement Cloud Run
}

module.exports = nextConfig