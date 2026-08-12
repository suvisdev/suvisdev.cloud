"use client"

import { useCallback, useEffect, useState } from "react"
import { PanelLeft } from "lucide-react"
import { MovaAiChatBar } from "@/components/mova/mova-ai-chat-bar"
import { MovaChatSidebar } from "@/components/mova/mova-chat-sidebar"
import {
  getSuvisSession,
  SUVIS_SESSION_CHANGED_EVENT,
} from "@/lib/suvis-session"

/**
 * mova/main 클라이언트 셸 — 로그인 상태를 감지해서 사이드바 표시 여부를 결정하고,
 * conversationId 상태를 사이드바·챗바 사이에 공유한다.
 *
 * - 로그인 O: 좌측 사이드바(데스크톱 상시, 모바일 오버레이) + 챗바(DB 모드)
 * - 로그인 X: 챗바만(sessionStorage 모드), 사이드바 없음
 */
export function MovaChatShell() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const check = () => setLoggedIn(getSuvisSession() !== null)
    check()
    window.addEventListener(SUVIS_SESSION_CHANGED_EVENT, check)
    return () => window.removeEventListener(SUVIS_SESSION_CHANGED_EVENT, check)
  }, [])

  const handleSelect = useCallback((id: number) => {
    setConversationId(id)
    setMobileOpen(false)
  }, [])

  const handleNewChat = useCallback(() => {
    setConversationId(null)
    setMobileOpen(false)
  }, [])

  const handleDeleted = useCallback(
    (id: number) => {
      if (id === conversationId) setConversationId(null)
      setSidebarRefreshKey((k) => k + 1)
    },
    [conversationId],
  )

  const handleConversationChanged = useCallback((id: number | null) => {
    setConversationId(id)
    // 새로 만들어졌거나 append됐거나 — 어느 쪽이든 사이드바 목록(updated_at 순서·
    // message_count)이 갱신돼야 한다.
    setSidebarRefreshKey((k) => k + 1)
  }, [])

  if (!loggedIn) {
    // 익명: 지금까지의 UX 그대로. 사이드바·conversation prop 없이 sessionStorage 모드.
    return (
      <div className="flex flex-1 flex-col">
        <MovaAiChatBar />
      </div>
    )
  }

  return (
    <div className="relative flex flex-1 overflow-hidden">
      {/* 데스크톱 상시 사이드바 */}
      <div className="hidden md:block">
        <MovaChatSidebar
          activeId={conversationId}
          refreshKey={sidebarRefreshKey}
          onSelect={handleSelect}
          onNewChat={handleNewChat}
          onDeleted={handleDeleted}
        />
      </div>

      {/* 모바일 오버레이 사이드바 */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 md:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden
          />
          <div className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] md:hidden">
            <MovaChatSidebar
              activeId={conversationId}
              refreshKey={sidebarRefreshKey}
              onSelect={handleSelect}
              onNewChat={handleNewChat}
              onDeleted={handleDeleted}
              onClose={() => setMobileOpen(false)}
            />
          </div>
        </>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* 모바일 사이드바 토글 */}
        <div className="flex items-center gap-2 border-b border-mova-border px-3 py-2 md:hidden">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="대화 목록 열기"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-mova-muted">대화 목록</span>
        </div>

        <MovaAiChatBar
          conversationId={conversationId}
          onConversationChanged={handleConversationChanged}
        />
      </div>
    </div>
  )
}
