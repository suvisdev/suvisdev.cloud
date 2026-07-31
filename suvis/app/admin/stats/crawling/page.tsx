"use client"

import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { getCrawlPolicies, type CrawlPolicy } from "@/lib/harvester-api"

function formatInterval(minutes: number): string {
  if (minutes % 1440 === 0) return `${minutes / 1440}일`
  if (minutes % 60 === 0) return `${minutes / 60}시간`
  return `${minutes}분`
}

function formatLastRun(iso: string | null): string {
  if (!iso) return "실행 이력 없음"
  const diffMs = Date.now() - new Date(iso).getTime()
  const hours = Math.floor(diffMs / (1000 * 60 * 60))
  if (hours < 1) return "1시간 이내"
  if (hours < 24) return `${hours}시간 전`
  return `${Math.floor(hours / 24)}일 전`
}

export default function AdminStatsCrawlingPage() {
  const [policies, setPolicies] = useState<CrawlPolicy[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getCrawlPolicies()
      .then(setPolicies)
      .catch((e: Error) => setError(e.message))
  }, [])

  if (error) {
    return (
      <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>
    )
  }

  if (!policies) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-slate-400">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        불러오는 중...
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-400">
        crawl_config.yaml에 등록된 재수집 정책 현황입니다. 마지막 실행 시각은 사이트 단위로
        기록되어, 같은 사이트에 정책이 여러 개면 값이 동일하게 표시될 수 있습니다.
      </p>

      {policies.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-400">
          등록된 크롤링 정책이 없습니다.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs text-slate-500">
                <th className="px-4 py-3 font-medium">사이트</th>
                <th className="px-4 py-3 font-medium">키워드</th>
                <th className="px-4 py-3 font-medium">주기</th>
                <th className="px-4 py-3 font-medium">마지막 실행</th>
                <th className="px-4 py-3 font-medium">상태</th>
              </tr>
            </thead>
            <tbody>
              {policies.map((p, i) => (
                <tr key={`${p.site_id}-${i}`} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3 font-medium text-slate-800">{p.site_id}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {p.keyword_source ? (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        동적: {p.keyword_source}
                      </span>
                    ) : (
                      p.keywords.join(", ")
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatInterval(p.interval_minutes)}</td>
                  <td className="px-4 py-3 text-slate-600">{formatLastRun(p.last_run_at)}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        p.is_due ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {p.is_due ? "실행 예정" : "대기 중"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
