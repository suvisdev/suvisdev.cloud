import type { NewsSection } from "@/lib/news-api"

/** 화면 상태 = 주소의 쿼리. news.suvisdev.cloud(경로 "/")와 suvisdev.cloud/news 양쪽에서 같은 링크가 동작하도록
 *  경로 없이 쿼리만 만든다("?section=economy" — 브라우저가 지금 경로에 붙인다). */
export type NewsView = {
  section: NewsSection
  group?: string
  topic?: number
  q?: string
  before?: string
  hideAi?: boolean
}

export function newsHref(view: NewsView): string {
  const params = new URLSearchParams()
  if (view.section !== "ai") params.set("section", view.section)
  if (view.q) params.set("q", view.q)
  if (view.topic !== undefined) params.set("topic", String(view.topic))
  if (view.group) params.set("group", view.group)
  if (view.before) params.set("before", view.before)
  if (view.hideAi) params.set("hide_ai", "1")
  return `?${params.toString()}`
}
