/** @type {import('next').NextConfig} */

const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
  runtimeCaching: [
    {
      urlPattern: /^https?.*/,
      handler: "NetworkFirst",
      options: {
        cacheName: "offlineCache",
        expiration: {
          maxEntries: 200,
          maxAgeSeconds: 7 * 24 * 60 * 60, // 7 days
        },
      },
    },
    {
      urlPattern: /\/api\/v1\/news\/posts/,
      handler: "StaleWhileRevalidate",
      options: {
        cacheName: "news-cache",
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 60 * 60, // 1 hour
        },
      },
    },
    {
      urlPattern: /\/api\/v1\/alerts/,
      handler: "NetworkFirst",
      options: {
        cacheName: "alerts-cache",
        networkTimeoutSeconds: 3,
        expiration: {
          maxEntries: 50,
          maxAgeSeconds: 5 * 60, // 5 minutes
        },
      },
    },
    {
      urlPattern: /https:\/\/tile\.openstreetmap\.org\/.*/,
      handler: "CacheFirst",
      options: {
        cacheName: "map-tiles",
        expiration: {
          maxEntries: 5000,
          maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
        },
      },
    },
  ],
});

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,

  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: process.env.NEXT_PUBLIC_MINIO_HOST || "localhost",
        port: process.env.NEXT_PUBLIC_MINIO_PORT || "9000",
        pathname: "/**",
      },
    ],
    formats: ["image/avif", "image/webp"],
  },

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(self), geolocation=(self)",
          },
        ],
      },
    ];
  },

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },

  webpack(config) {
    config.resolve.fallback = { fs: false, net: false, tls: false };
    return config;
  },
};

module.exports = withPWA(nextConfig);
