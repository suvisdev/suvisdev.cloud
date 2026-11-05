/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com", pathname: "/**" },
      { protocol: "https", hostname: "image.tmdb.org", pathname: "/**" },
    ],
  },
  // news.suvisdev.cloud(같은 Vercel 프로젝트에 붙인 서브도메인)의 첫 화면을 /news 로 보여 준다(2026-11-05).
  // "/" 만 바꾼다 — 화면 안 링크는 쿼리만 쓰고("?section=economy"), /_next·/api·정적 파일은 그대로 둔다.
  // suvisdev.cloud/news 도 같은 페이지라 도메인 연결 전에도 열린다.
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/",
          has: [{ type: "host", value: "news.suvisdev.cloud" }],
          destination: "/news",
        },
      ],
    }
  },
}

export default nextConfig
