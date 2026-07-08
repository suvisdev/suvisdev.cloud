"use client"

import { useCallback, useEffect, useState } from "react"
import { Inbox, Loader2, RefreshCw, Trash2 } from "lucide-react"

type ReceiveItem = {
  id: number
  sender: string
  subject: string
  body: string
  received_at: string
}

export default function AdminReceivePage() {
  const [items, setItems] = useState<ReceiveItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<ReceiveItem | null>(null)
  const [deleting, setDeleting] = useState<number | null>(null)

  const fetchReceive = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/dispatch/receive")
      if (!res.ok) throw new Error(`오류 (${res.status})`)
      const data = (await res.json()) as ReceiveItem[]
      setItems(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "불러오기 실패")
    } finally {
      setLoading(false)
    }
  }, [])

  const handleDelete = useCallback(
    async (item: ReceiveItem, e: React.MouseEvent) => {
      e.stopPropagation()
      setDeleting(item.id)
      try {
        const res = await fetch(`/api/dispatch/receive?id=${item.id}`, { method: "DELETE" })
        if (!res.ok) throw new Error()
        setItems((prev) => prev.filter((i) => i.id !== item.id))
        if (selected?.id === item.id) setSelected(null)
      } finally {
        setDeleting(null)
      }
    },
    [selected]
  )

  useEffect(() => {
    void fetchReceive()
  }, [fetchReceive])

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      {/* 목록 */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <p className="text-sm font-semibold text-slate-800">수신함 ({items.length})</p>
          <button
            type="button"
            onClick={() => void fetchReceive()}
            disabled={loading}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 disabled:opacity-50"
            aria-label="새로고침"
          >
            <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="size-6 animate-spin text-slate-400" />
          </div>
        )}
        {error && <p className="px-4 py-8 text-center text-xs text-rose-500">{error}</p>}
        {!loading && !error && items.length === 0 && (
          <div className="px-4 py-16 text-center text-slate-400">
            <Inbox className="mx-auto mb-3 size-10 opacity-30" />
            <p className="text-sm">수신된 메일이 없습니다.</p>
            <p className="mt-1 text-xs">n8n 워크플로우가 활성화되면 자동으로 쌓여요.</p>
          </div>
        )}
        <ul className="divide-y divide-slate-100">
          {items.map((item) => (
            <li key={item.id} className="group relative">
              <button
                type="button"
                onClick={() => setSelected(item)}
                className={`w-full px-4 py-3 text-left transition-colors hover:bg-slate-50 ${selected?.id === item.id ? "bg-indigo-50" : ""}`}
              >
                <p className="truncate pr-6 text-sm font-semibold text-slate-800">
                  {item.subject || "(제목 없음)"}
                </p>
                <p className="truncate text-xs text-slate-500">{item.sender}</p>
                <p className="mt-0.5 text-[10px] text-slate-400">
                  {new Date(item.received_at).toLocaleString("ko-KR")}
                </p>
              </button>
              <button
                type="button"
                onClick={(e) => void handleDelete(item, e)}
                disabled={deleting === item.id}
                className="absolute top-1/2 right-2 -translate-y-1/2 rounded p-1 text-slate-300 opacity-0 transition-opacity group-hover:opacity-100 hover:text-rose-500 disabled:opacity-50"
                aria-label="삭제"
              >
                {deleting === item.id ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4" />
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* 본문 */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        {selected ? (
          <>
            <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
              <div>
                <p className="text-xs text-slate-500">{selected.sender}</p>
                <h2 className="mt-1 text-lg font-bold text-slate-800">
                  {selected.subject || "(제목 없음)"}
                </h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  {new Date(selected.received_at).toLocaleString("ko-KR")}
                </p>
              </div>
              <button
                type="button"
                onClick={(e) => void handleDelete(selected, e)}
                disabled={deleting === selected.id}
                className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-500 disabled:opacity-50"
                aria-label="삭제"
              >
                {deleting === selected.id ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4" />
                )}
              </button>
            </div>
            <div className="p-6">
              <pre className="font-sans text-sm leading-relaxed whitespace-pre-wrap text-slate-700">
                {selected.body}
              </pre>
            </div>
          </>
        ) : (
          <div className="flex h-full items-center justify-center py-32 text-slate-400">
            <div className="text-center">
              <Inbox className="mx-auto mb-3 size-10 opacity-30" />
              <p className="text-sm">메일을 선택하면 본문이 표시됩니다.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
