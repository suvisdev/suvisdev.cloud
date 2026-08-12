"use client"

import { useCallback, useEffect, useState } from "react"
import { MessageSquarePlus, Trash2, X } from "lucide-react"
import {
  deleteConversation,
  listConversations,
  type ConversationSummary,
} from "@/lib/mova-conversations-api"
import { cn } from "@/lib/utils"

type MovaChatSidebarProps = {
  activeId: number | null
  refreshKey: number
  onSelect: (id: number) => void
  onNewChat: () => void
  onDeleted: (id: number) => void
  onClose?: () => void
}

export function MovaChatSidebar({
  activeId,
  refreshKey,
  onSelect,
  onNewChat,
  onDeleted,
  onClose,
}: MovaChatSidebarProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      const rows = await listConversations()
      setConversations(rows)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "대화 목록을 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload, refreshKey])

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm("이 대화를 삭제할까요? 되돌릴 수 없습니다.")) return
    try {
      await deleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      onDeleted(id)
    } catch (e) {
      setError(e instanceof Error ? e.message : "삭제에 실패했습니다.")
    }
  }

  return (
    <aside className="flex h-full w-full flex-col border-r border-mova-border bg-mova-surface/95 backdrop-blur-md md:w-64">
      <div className="flex items-center justify-between border-b border-mova-border px-3 py-3">
        <button
          type="button"
          onClick={onNewChat}
          className="flex flex-1 items-center gap-2 rounded-lg border border-mova-border bg-mova-surface-2 px-3 py-2 text-sm text-mova-text transition-colors hover:border-mova-accent/40 hover:bg-mova-accent-soft"
        >
          <MessageSquarePlus className="h-4 w-4" />
          <span>새 대화</span>
        </button>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="사이드바 닫기"
            className="ml-2 flex h-9 w-9 items-center justify-center rounded-lg text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text md:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-2">
        {loading && (
          <p className="px-3 py-2 text-xs text-mova-muted">불러오는 중…</p>
        )}
        {error && (
          <p className="px-3 py-2 text-xs text-red-500 dark:text-red-400">{error}</p>
        )}
        {!loading && !error && conversations.length === 0 && (
          <p className="px-3 py-4 text-xs text-mova-muted">
            아직 저장된 대화가 없어요. 첫 메시지를 보내면 여기에 쌓입니다.
          </p>
        )}
        <ul className="space-y-0.5 px-2">
          {conversations.map((c) => {
            const active = c.id === activeId
            return (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  className={cn(
                    "group flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors",
                    active
                      ? "bg-mova-accent-soft text-mova-text"
                      : "text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text",
                  )}
                >
                  <span className="min-w-0 flex-1 truncate">{c.title}</span>
                  <button
                    type="button"
                    onClick={(e) => void handleDelete(c.id, e)}
                    aria-label="대화 삭제"
                    className="opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-mova-muted hover:text-red-500" />
                  </button>
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    </aside>
  )
}
