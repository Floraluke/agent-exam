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

const config: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${target.origin}/api/v1/:path*` }];
  },
};

export default config;
