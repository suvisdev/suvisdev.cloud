import type { MetadataRoute } from "next"

/** AI 학습·대량 수집 크롤러 차단. 검색엔진(구글·네이버 등) 색인은 허용 —
 *  전부 막으면 검색 노출까지 사라진다. robots.txt는 신사협정이라 악성
 *  스크레이퍼는 안 지키지만, 주요 AI 크롤러는 준수한다. */
const SCRAPER_BOTS = [
  "GPTBot",
  "ChatGPT-User",
  "CCBot",
  "anthropic-ai",
  "ClaudeBot",
  "Claude-Web",
  "Google-Extended",
  "Applebot-Extended",
  "Bytespider",
  "PerplexityBot",
  "Amazonbot",
  "FacebookBot",
  "meta-externalagent",
  "Diffbot",
  "Scrapy",
  "ImagesiftBot",
  "Omgilibot",
]

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      ...SCRAPER_BOTS.map((userAgent) => ({ userAgent, disallow: "/" })),
      { userAgent: "*", allow: "/", disallow: ["/admin/", "/api/"] },
    ],
  }
}
