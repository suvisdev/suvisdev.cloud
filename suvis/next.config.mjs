// 서브도메인 서빙(2026-09-03): mova/gildle.suvisdev.cloud가 각 섹션을 루트처럼
// 서빙한다. Next API 프록시(/api)·에셋(/_next, 확장자 있는 파일)·이미 접두된
// 경로는 리라이트하지 않는다 — 기존 suvisdev.cloud/mova 경로도 그대로 산다.
const SUBDOMAIN_APPS = [
  { host: "mova.suvisdev.cloud", prefix: "mova" },
  { host: "gildle.suvisdev.cloud", prefix: "gildle" },
]

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return {
      beforeFiles: SUBDOMAIN_APPS.flatMap(({ host, prefix }) => [
        {
          source: "/",
          has: [{ type: "host", value: host }],
          destination: `/${prefix}`,
        },
        {
          source: `/:path((?!${prefix}/|api/|_next/|.*\\..*).*)`,
          has: [{ type: "host", value: host }],
          destination: `/${prefix}/:path`,
        },
      ]),
    }
  },
  images: {
    unoptimized: true,
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com", pathname: "/**" },
      { protocol: "https", hostname: "image.tmdb.org", pathname: "/**" },
    ],
  },
}

export default nextConfig
