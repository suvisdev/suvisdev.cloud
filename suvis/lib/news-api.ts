import { backendFetch } from "@/lib/backend-client"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

/** news.suvisdev.cloud 공개 읽기 API (`suvisdev/apps/news`, 로그인 없음).
 *  서버 컴포넌트(`app/news/page.tsx`)에서만 부른다 — 화면은 서버에서 그리고 클라이언트 fetch 는 없다.
 *  메인은 AI 섹션(section=ai), 경제는 부록(section=economy). 본문은 API 가 내보내지 않는다(제목·요약·링크만). */

type ApiErrorBody = { detail?: unknown }

export type NewsSection = "ai" | "economy"

export type NewsGroup = { code: string; label: string; feeds: string[] }

export type NewsSectionInfo = { code: NewsSection; label: string; groups: NewsGroup[] }

export type NewsTopic = { id: number; label: string; query: string; section: NewsSection }

export type NewsBadge = "none" | "ai_disclosed" | "ai_suspected"

export type NewsTerm = { term: string; desc: string }

export type NewsArticle = {
  id: number
  title: string
  url: string
  summary: string
  source_domain: string
  source_name: string | null
  published_at: string | null
  badge: NewsBadge
  reasons_ko: string[]
  section: NewsSection
  group: string
  /** 목록 정렬 시각(날짜 없는 글은 수집 시각) — 다음 쪽은 마지막 글의 이 값을 before 로 넘긴다 */
  sort_at: string | null
  /** 노트북 EXAONE 이 만든 한국어 제목(영어 글만 번역)·2~3문장 요약. 아직 안 만들었으면 null */
  title_ko: string | null
  summary_ko: string | null
  /** 글에 나오는 전문 용어와 뜻(백엔드 고정 사전). 백엔드 배포가 Vercel 보다 늦는 동안에는 없을 수 있다 */
  terms?: NewsTerm[]
}

export type NewsResult<T> = { ok: true; data: T } | { ok: false; message: string }

const LOAD_FAILED = "뉴스를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요."

async function newsFetch<T>(path: string, revalidate: number): Promise<NewsResult<T>> {
  try {
    const res = await backendFetch(`/api/v1/news${path}`, { next: { revalidate } })
    const data = (await res.json()) as T & ApiErrorBody
    if (!res.ok)
      return { ok: false, message: safeApiErrorMessage(data.detail, LOAD_FAILED, res.status) }
    return { ok: true, data }
  } catch {
    return { ok: false, message: LOAD_FAILED }
  }
}

export function getNewsSections(): Promise<NewsResult<NewsSectionInfo[]>> {
  return newsFetch<NewsSectionInfo[]>("/sections", 3600)
}

export function getNewsTopics(section: NewsSection): Promise<NewsResult<NewsTopic[]>> {
  return newsFetch<NewsTopic[]>(`/topics?section=${section}`, 300)
}

export type ArticleQuery = {
  section: NewsSection
  group?: string
  topicId?: number
  q?: string
  before?: string
  limit: number
}

/** 검색어(q) → 탭(topicId) → 섹션 최신(group) 순으로 하나만 고른다. */
export function getNewsArticles(query: ArticleQuery): Promise<NewsResult<NewsArticle[]>> {
  const params = new URLSearchParams({ limit: String(query.limit) })
  if (query.before) params.set("before", query.before)
  if (query.q) {
    params.set("q", query.q)
    params.set("section", query.section)
    return newsFetch<NewsArticle[]>(`/search?${params}`, 60)
  }
  if (query.topicId !== undefined) {
    return newsFetch<NewsArticle[]>(`/topics/${query.topicId}/articles?${params}`, 120)
  }
  params.set("section", query.section)
  if (query.group) params.set("group", query.group)
  return newsFetch<NewsArticle[]>(`/latest?${params}`, 120)
}
