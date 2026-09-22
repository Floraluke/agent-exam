import type { NextConfig } from "next";

const apiOrigin = process.env.AGENTEXAM_API_ORIGIN ?? "http://127.0.0.1:8000";
const target = new URL(apiOrigin);
if (
  target.protocol !== "http:" || target.hostname !== "127.0.0.1" ||
  target.username || target.password || target.pathname !== "/" ||
  target.search || target.hash
) {
  throw new Error("FastAPI 转发目标必须为本机回环 HTTP 地址");
}

const scriptSources = process.env.NODE_ENV === "production"
  ? "script-src 'self' 'unsafe-inline'"
  : "script-src 'self' 'unsafe-inline' 'unsafe-eval'";
const securityHeaders = [
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'", "base-uri 'self'", "object-src 'none'",
      "frame-ancestors 'none'", "form-action 'self'", scriptSources,
      "style-src 'self' 'unsafe-inline'", "img-src 'self' data:",
      "font-src 'self'", "connect-src 'self'",
    ].join("; "),
  },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
];

const config: NextConfig = {
  distDir: process.env.AGENTEXAM_NEXT_DIST_DIR || ".next",
  poweredByHeader: false,
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${target.origin}/api/v1/:path*` }];
  },
};

export default config;
