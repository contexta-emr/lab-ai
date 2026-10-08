/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The API is a separate service. In development it runs on :8000; in
  // production NEXT_PUBLIC_API_URL points at wherever it is deployed.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;
