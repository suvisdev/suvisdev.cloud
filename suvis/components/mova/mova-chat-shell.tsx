"use client"

import { useCallback, useEffect, useState } from "react"
import { BarChart3, PanelLeft, PanelLeftClose } from "lucide-react"
import { MovaAiChatBar } from "@/components/mova/mova-ai-chat-bar"
import { MovaChatRail } from "@/components/mova/mova-chat-rail"
import { MovaChatSidebar } from "@/components/mova/mova-chat-sidebar"
import { getSuvisSession, SUVIS_SESSION_CHANGED_EVENT } from "@/lib/suvis-session"

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
const RAIL_HIDDEN_KEY = "mova-rail-hidden"

export function MovaChatShell() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [desktopCollapsed, setDesktopCollapsed] = useState(false)
  const [railHidden, setRailHidden] = useState(true)
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

    // 랭킹 레일 숨김 상태 복원. 값이 없으면 디폴트 숨김("1"). 사용자가 명시적으로
    // "0"으로 저장한 경우에만 노출한다.
    try {
      const raw = window.localStorage.getItem(RAIL_HIDDEN_KEY)
      setRailHidden(raw === null ? true : raw === "1")
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

  // 랭킹 레일 숨김 저장
  useEffect(() => {
    if (!hydrated) return
    try {
      window.localStorage.setItem(RAIL_HIDDEN_KEY, railHidden ? "1" : "0")
    } catch {
      // ignore
    }
  }, [railHidden, hydrated])

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
    [conversationId]
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
    // min-h-0 + overflow-hidden이 없으면 리스트가 콘텐츠만큼 자라 입력창이 페이지 밖으로
    // 밀린다(2026-09-28 실측: 스페이서와 되먹임해 리스트가 15만 px까지 커짐).
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
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

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {/* 사이드바 토글 바 — 모바일: 항상 노출 / 데스크톱: 접혔을 때만 노출 */}
        <div className="border-mova-border flex items-center gap-2 border-b px-3 py-1 md:px-4">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="대화 목록 열기"
            className="text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text flex h-9 w-9 items-center justify-center rounded-lg md:hidden"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
          {desktopCollapsed && (
            <button
              type="button"
              onClick={() => setDesktopCollapsed(false)}
              aria-label="대화 목록 펼치기"
              className="text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text hidden h-9 w-9 items-center justify-center rounded-lg md:flex"
            >
              <PanelLeft className="h-4 w-4" />
            </button>
          )}
          {!desktopCollapsed && (
            <button
              type="button"
              onClick={() => setDesktopCollapsed(true)}
              aria-label="대화 목록 접기"
              className="text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text hidden h-9 w-9 items-center justify-center rounded-lg md:flex"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
          <span className="text-mova-muted text-xs">대화 목록</span>

          {/* 랭킹 레일 토글 — lg+에서만. 디폴트 숨김. */}
          <button
            type="button"
            onClick={() => setRailHidden((v) => !v)}
            aria-label={railHidden ? "랭킹 열기" : "랭킹 숨기기"}
            aria-pressed={!railHidden}
            className="text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text ml-auto hidden h-9 items-center gap-1.5 rounded-lg px-2 text-xs lg:flex"
          >
            <BarChart3 className="h-4 w-4" />
            <span>{railHidden ? "랭킹 보기" : "랭킹 숨기기"}</span>
          </button>
        </div>

        <MovaAiChatBar
          conversationId={conversationId}
          onConversationChanged={handleConversationChanged}
        />
      </div>

      {/* 우측 랭킹 레일 — 데스크톱(lg+)만. 디폴트 숨김, 토글로 노출. */}
      {!railHidden && <MovaChatRail />}
    </div>
  )
}
