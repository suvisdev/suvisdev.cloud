"use client"

import { useEffect, useRef } from "react"
import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import type { PortfolioChatTurn } from "@/lib/portfolio-api"

type PortfolioChatPanelProps = {
  messages: PortfolioChatTurn[]
  loading: boolean
  error: string | null
}

export function PortfolioChatPanel({ messages, loading, error }: PortfolioChatPanelProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
  }, [messages, loading])

  return (
    <section
      role="log"
      aria-live="polite"
      className="w-full max-w-2xl rounded-2xl border border-neutral-300 bg-white p-4 shadow-sm dark:border-neutral-700 dark:bg-[#161a24]"
    >
      <div className="max-h-[min(50vh,420px)] space-y-3 overflow-y-auto overscroll-contain pr-1">
        {messages.map((m, i) => (
          <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <p
              className={cn(
                "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed break-words whitespace-pre-wrap",
                m.role === "user"
                  ? "bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900"
                  : "bg-neutral-100 text-neutral-900 dark:bg-[#0d0f14] dark:text-neutral-100"
              )}
            >
              {m.content}
            </p>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            답변을 준비하고 있어요…
          </div>
        )}
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <div ref={endRef} />
      </div>
    </section>
  )
}
