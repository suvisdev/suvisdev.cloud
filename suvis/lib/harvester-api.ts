import { safeApiErrorMessage } from "@/lib/user-facing-error"

export type CrawlPolicy = {
  site_id: string
  keywords: string[]
  keyword_source: string | null
  interval_minutes: number
  limit_per_keyword: number | null
  last_run_at: string | null
  is_due: boolean
}

type ApiErrorBody = { detail?: string | unknown }

export async function getCrawlPolicies(): Promise<CrawlPolicy[]> {
  const res = await fetch("/api/harvester/policies")
  const data = (await res.json()) as CrawlPolicy[] & ApiErrorBody
  if (!res.ok) {
    throw new Error(safeApiErrorMessage(data.detail, "크롤링 정책을 가져오지 못했습니다.", res.status))
  }
  return data
}
