/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export: `next build` emits a fully static site to `out/`, which the Tauri
  // desktop shell (Phase B) bundles and serves from the WebView. All pages are client
  // components that talk to the FastAPI backend at runtime, and dynamic screens use
  // query params (/jobs?id=, /results?id=) so no server is required.
  output: "export",
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000",
  },
};

export default nextConfig;
