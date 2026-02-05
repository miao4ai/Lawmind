/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Enable standalone output for Docker
  output: 'standalone',

  // Environment variables
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  },

  // Disable image optimization for Cloud Run
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
