import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 允许通过 127.0.0.1 访问开发服务器（避免 HMR 跨域阻断）
  allowedDevOrigins: ["127.0.0.1"],
  // 本地开发：把 /api 代理到后端（阶段 4 上线时换成 proxy.ts 运行时转发）
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
    ];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
