"use client"

import { useCallback, useEffect, useState } from "react"
import { PanelLeft, PanelLeftClose } from "lucide-react"
import { MovaAiChatBar } from "@/components/mova/mova-ai-chat-bar"
import { MovaChatSidebar } from "@/components/mova/mova-chat-sidebar"
import {
  getSuvisSession,
  SUVIS_SESSION_CHANGED_EVENT,
} from "@/lib/suvis-session"

/**
 * mova/main 클라이언트 셸 — 로그인 상태 감지·conversationId 공유·사이드바 토글.
 *
 * - 로그인 O: 사이드바(데스크톱 상시/접기 가능, 모바일 오버레이) + 챗바(DB 모드)
 * - 로그인 X: 챗바만(sessionStorage 모드), 사이드바 없음
 * - 활성 conversationId는 sessionStorage로 유지 → 영화 상세를 다녀와도 이어서.
 * - 사이드바 접힘 상태는 localStorage로 유지(세션 넘어서도 사용자 선호 기억).
 */

const ACTIVE_CONV_KEY = "mova-active-conversation-id"
const SIDEBAR_COLLAPSED_KEY = "mova-sidebar-collapsed"

export function MovaChatShell() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [desktopCollapsed, setDesktopCollapsed] = useState(false)
  const [hydrated, setHydrated] = useState(false)

  // 로그인 상태 감지 + sessionStorage에서 활성 대화 복원
  useEffect(() => {
    const check = () => setLoggedIn(getSuvisSession() !== null)
    check()
    window.addEventListener(SUVIS_SESSION_CHANGED_EVENT, check)

    // 활성 conversationId 복원(remount에도 이어서 보이도록)
    try {
      const raw = window.sessionStorage.getItem(ACTIVE_CONV_KEY)
      const n = raw ? Number(raw) : NaN
      if (Number.isFinite(n) && n > 0) setConversationId(n)
    } catch {
      // ignore
    }

    // 사이드바 접힘 상태 복원(세션 넘어서도 사용자 선호 기억)
    try {
      const collapsed = window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1"
      setDesktopCollapsed(collapsed)
    } catch {
      // ignore
    }

    setHydrated(true)
    return () => window.removeEventListener(SUVIS_SESSION_CHANGED_EVENT, check)
  }, [])

  // 활성 대화 저장(sessionStorage: 브라우저 탭 세션 동안 유지)
  useEffect(() => {
    if (!hydrated) return
    try {
      if (conversationId === null) window.sessionStorage.removeItem(ACTIVE_CONV_KEY)
      else window.sessionStorage.setItem(ACTIVE_CONV_KEY, String(conversationId))
    } catch {
      // ignore
    }
  }, [conversationId, hydrated])

  // 사이드바 접힘 저장
  useEffect(() => {
    if (!hydrated) return
    try {
      window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, desktopCollapsed ? "1" : "0")
    } catch {
      // ignore
    }
  }, [desktopCollapsed, hydrated])

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
    setSidebarRefreshKey((k) => k + 1)
  }, [])

  // 하이드레이션 완료 전 잠깐 익명으로 렌더되는 flash + 잘못된 auto-send 방지.
  if (!hydrated) {
    return <div className="flex-1" aria-hidden />
  }

  if (!loggedIn) {
    // 익명: 사이드바 없이 챗바만(sessionStorage 모드).
    return (
      <div className="flex flex-1 flex-col">
        <MovaAiChatBar />
      </div>
    )
  }

  return (
    <div className="relative flex flex-1 overflow-hidden">
      {/* 데스크톱 사이드바 — desktopCollapsed=false일 때만 노출 */}
      {!desktopCollapsed && (
        <div className="hidden md:block">
          <MovaChatSidebar
            activeId={conversationId}
            refreshKey={sidebarRefreshKey}
            onSelect={handleSelect}
            onNewChat={handleNewChat}
            onDeleted={handleDeleted}
            onClose={() => setDesktopCollapsed(true)}
          />
        </div>
      )}

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
        {/* 사이드바 토글 바 — 모바일: 항상 노출 / 데스크톱: 접혔을 때만 노출 */}
        <div className="flex items-center gap-2 border-b border-mova-border px-3 py-2 md:px-4">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="대화 목록 열기"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text md:hidden"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
          {desktopCollapsed && (
            <button
              type="button"
              onClick={() => setDesktopCollapsed(false)}
              aria-label="대화 목록 펼치기"
              className="hidden h-9 w-9 items-center justify-center rounded-lg text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text md:flex"
            >
              <PanelLeft className="h-4 w-4" />
            </button>
          )}
          {!desktopCollapsed && (
            <button
              type="button"
              onClick={() => setDesktopCollapsed(true)}
              aria-label="대화 목록 접기"
              className="hidden h-9 w-9 items-center justify-center rounded-lg text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text md:flex"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
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
