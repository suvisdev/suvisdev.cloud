"use client"

import { useEffect, useState } from "react"
import { Loader2, Radar } from "lucide-react"
import { patchState } from "@/lib/form-status"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

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

type CommandFormProps = { site_id: string; command_text: string }

const COPY = {
  scrape: {
    title: "스크래퍼 — 지금 1회 수집",
    hint: "선택한 사이트에서 명령을 해석해 한 번만 수집하고 파일에 새로 저장합니다.",
    placeholder: "예: 패터슨이란 영화 5개만 가져와줘",
    button: "수집 실행",
    endpoint: "/api/harvester/scrape",
  },
  crawl: {
    title: "크롤러 — 지금 1회 크롤링",
    hint: "선택한 사이트에서 명령을 해석해 한 번만 크롤링하고, 그날 파일에 이어붙입니다(중복 자동 제외).",
    placeholder: "예: 박스오피스 관련 뉴스 20개 모아줘",
    button: "크롤링 실행",
    endpoint: "/api/harvester/crawl",
  },
} as const

const initialState: FormState = { submitting: false, error: null, result: null }

export function HarvesterCommandForm({ mode }: { mode: keyof typeof COPY }) {
  const copy = COPY[mode]
  const [sites, setSites] = useState<HarvesterSite[]>([])
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
    const formProps = Object.fromEntries(formData.entries()) as CommandFormProps

    if (!formProps.site_id) {
      patch({ error: "사이트를 선택해 주세요.", result: null })
      return
    }
    if (!formProps.command_text?.trim()) {
      patch({ error: "명령을 입력해 주세요.", result: null })
      return
    }

    patch({ submitting: true, error: null, result: null })
    try {
      const res = await fetch(copy.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formProps),
      })
      const body = await res.json().catch(() => ({})) as Record<string, unknown>
      if (!res.ok) {
        patch({
          error: safeApiErrorMessage(body.detail, "실행에 실패했습니다.", res.status),
          submitting: false,
        })
        return
      }
      patch({
        result: {
          recordCount: typeof body.record_count === "number" ? body.record_count : 0,
          path: typeof body.path === "string" ? body.path : "",
          parsedKeyword: typeof body.parsed_keyword === "string" ? body.parsed_keyword : "",
          parsedLimit: typeof body.parsed_limit === "number" ? body.parsed_limit : 0,
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

      <form onSubmit={(e) => void handleSubmit(e)} className="mt-4 space-y-4">
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

        <div>
          <label htmlFor={`${mode}-command`} className="block text-xs font-semibold text-slate-700">
            명령 <span className="text-rose-500">*</span>
          </label>
          <textarea
            id={`${mode}-command`}
            name="command_text"
            rows={3}
            placeholder={copy.placeholder}
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
            해석된 명령: <b>{state.result.parsedKeyword}</b> · {state.result.parsedLimit}건 요청
          </p>
          <p className="mt-1">
            결과: <b>{state.result.recordCount}건</b> 수집 → {state.result.path}
          </p>
        </div>
      )}
    </div>
  )
}
