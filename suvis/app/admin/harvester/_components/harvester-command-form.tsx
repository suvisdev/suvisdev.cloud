"use client"

import { useEffect, useState } from "react"
import { Link2, Loader2, Radar } from "lucide-react"
import { patchState } from "@/lib/form-status"
import { safeApiErrorMessage } from "@/lib/user-facing-error"
import { cn } from "@/lib/utils"

type HarvesterSite = { site_id: string; fetcher_kind: string }

type RunResult = {
  recordCount: number
  path: string
  parsedKeyword: string
  parsedLimit: number
}

type FormState = {
  submitting: boolean
  error: string | null
  result: RunResult | null
}

type UiState = {
  inputMode: "site" | "url"
}

type SiteFormProps = { site_id: string; command_text: string }
type UrlFormProps = { url: string; command_text: string }

const COPY = {
  scrape: {
    title: "스크래퍼 — 지금 1회 수집",
    hint: "명령을 해석해 한 번만 수집하고 파일에 새로 저장합니다.",
    sitePlaceholder: "예: 패터슨이란 영화 5개만 가져와줘",
    urlPlaceholder: "예: 이 페이지에서 가격이랑 상품명만 뽑아줘",
    button: "수집 실행",
    endpoint: "/api/harvester/scrape",
  },
  crawl: {
    title: "크롤러 — 지금 1회 크롤링",
    hint: "명령을 해석해 한 번만 크롤링하고, 그날 파일에 이어붙입니다(중복 자동 제외).",
    sitePlaceholder: "예: 박스오피스 관련 뉴스 20개 모아줘",
    urlPlaceholder: "예: 이 페이지 본문 요약해서 정리해줘",
    button: "크롤링 실행",
    endpoint: "/api/harvester/crawl",
  },
} as const

const initialState: FormState = { submitting: false, error: null, result: null }

function isLikelyUrl(value: string): boolean {
  try {
    const u = new URL(value)
    return u.protocol === "http:" || u.protocol === "https:"
  } catch {
    return false
  }
}

export function HarvesterCommandForm({ mode }: { mode: keyof typeof COPY }) {
  const copy = COPY[mode]
  const [sites, setSites] = useState<HarvesterSite[]>([])
  const [ui, setUi] = useState<UiState>({ inputMode: "site" })
  const [state, setState] = useState<FormState>(initialState)
  const patch = (p: Partial<FormState>) => patchState(setState, p)

  useEffect(() => {
    let cancelled = false
    fetch("/api/harvester/sites")
      .then((res) => res.json())
      .then((data: unknown) => {
        if (!cancelled && Array.isArray(data)) setSites(data as HarvesterSite[])
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (state.submitting) return
    const formData = new FormData(e.currentTarget)

    const body: Record<string, string> =
      ui.inputMode === "site"
        ? (() => {
            const p = Object.fromEntries(formData.entries()) as SiteFormProps
            return { site_id: p.site_id, command_text: p.command_text }
          })()
        : (() => {
            const p = Object.fromEntries(formData.entries()) as UrlFormProps
            return { url: p.url, command_text: p.command_text }
          })()

    if (ui.inputMode === "site" && !body.site_id) {
      patch({ error: "사이트를 선택해 주세요.", result: null })
      return
    }
    if (ui.inputMode === "url" && !isLikelyUrl(body.url ?? "")) {
      patch({ error: "http:// 또는 https://로 시작하는 URL을 입력해 주세요.", result: null })
      return
    }
    if (!body.command_text?.trim()) {
      patch({ error: "명령을 입력해 주세요.", result: null })
      return
    }

    patch({ submitting: true, error: null, result: null })
    try {
      const res = await fetch(copy.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      const data = await res.json().catch(() => ({})) as Record<string, unknown>
      if (!res.ok) {
        patch({
          error: safeApiErrorMessage(data.detail, "실행에 실패했습니다.", res.status),
          submitting: false,
        })
        return
      }
      patch({
        result: {
          recordCount: typeof data.record_count === "number" ? data.record_count : 0,
          path: typeof data.path === "string" ? data.path : "",
          parsedKeyword: typeof data.parsed_keyword === "string" ? data.parsed_keyword : "",
          parsedLimit: typeof data.parsed_limit === "number" ? data.parsed_limit : 0,
        },
        submitting: false,
      })
    } catch {
      patch({ error: "네트워크 오류가 발생했습니다.", submitting: false })
    }
  }

  return (
    <div className="max-w-xl rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-base font-semibold text-slate-800">{copy.title}</h2>
      <p className="mt-1 text-xs text-slate-500">{copy.hint}</p>

      <div className="mt-4 flex gap-1 rounded-lg bg-slate-100 p-1 text-xs font-medium">
        {(["site", "url"] as const).map((m) => (
          <button
            key={m}
            type="button"
            disabled={state.submitting}
            onClick={() => setUi({ inputMode: m })}
            className={cn(
              "flex-1 rounded-md py-1.5 transition-colors",
              ui.inputMode === m ? "bg-white text-indigo-700 shadow-sm" : "text-slate-500 hover:text-slate-700",
            )}
          >
            {m === "site" ? "등록된 사이트" : "URL 직접 입력"}
          </button>
        ))}
      </div>

      <form onSubmit={(e) => void handleSubmit(e)} className="mt-4 space-y-4">
        {ui.inputMode === "site" ? (
          <div>
            <label htmlFor={`${mode}-site`} className="block text-xs font-semibold text-slate-700">
              사이트 <span className="text-rose-500">*</span>
            </label>
            <select
              id={`${mode}-site`}
              name="site_id"
              defaultValue=""
              disabled={state.submitting}
              className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-200 disabled:opacity-50"
            >
              <option value="" disabled>
                {sites.length ? "사이트를 선택하세요" : "불러오는 중…"}
              </option>
              {sites.map((s) => (
                <option key={s.site_id} value={s.site_id}>
                  {s.site_id} ({s.fetcher_kind})
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div>
            <label htmlFor={`${mode}-url`} className="block text-xs font-semibold text-slate-700">
              URL <span className="text-rose-500">*</span>
            </label>
            <div className="relative mt-1.5">
              <Link2 className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
              <input
                id={`${mode}-url`}
                name="url"
                type="url"
                placeholder="https://example.com/article/123"
                disabled={state.submitting}
                className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-200 disabled:opacity-50"
              />
            </div>
            <p className="mt-1 text-[11px] text-slate-400">
              robots.txt로 수집이 막힌 페이지는 자동으로 거부됩니다.
            </p>
          </div>
        )}

        <div>
          <label htmlFor={`${mode}-command`} className="block text-xs font-semibold text-slate-700">
            명령 <span className="text-rose-500">*</span>
          </label>
          <textarea
            id={`${mode}-command`}
            name="command_text"
            rows={3}
            placeholder={ui.inputMode === "site" ? copy.sitePlaceholder : copy.urlPlaceholder}
            disabled={state.submitting}
            className="mt-1.5 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-200 disabled:opacity-50"
          />
        </div>

        <button
          type="submit"
          disabled={state.submitting}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
        >
          {state.submitting ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              실행 중…
            </>
          ) : (
            <>
              <Radar className="size-4" />
              {copy.button}
            </>
          )}
        </button>
      </form>

      {state.error && (
        <p role="alert" className="mt-4 text-xs text-rose-700">
          {state.error}
        </p>
      )}
      {state.result && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">
          <p>
            해석된 명령: <b>{state.result.parsedKeyword}</b>
            {ui.inputMode === "site" ? ` · ${state.result.parsedLimit}건 요청` : ""}
          </p>
          <p className="mt-1">
            결과: <b>{state.result.recordCount}건</b> 수집 → {state.result.path}
          </p>
        </div>
      )}
    </div>
  )
}
