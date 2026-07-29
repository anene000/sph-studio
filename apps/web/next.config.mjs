/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Phase B (Tauri) serves a static export; enable when bundling into the desktop app.
  // output: 'export',
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000',
  },
};

export default nextConfig;
