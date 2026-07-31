"use client"

import { useEffect } from "react"
import { getOrCreateVisitorId } from "@/lib/visitor-id"
import { pingVisitor } from "@/lib/visitor-analytics-api"

const HEARTBEAT_MS = 60_000

/** 익명 방문자를 60초 간격으로 heartbeat — 백그라운드 탭에서는 멈춘다. UI 없음. */
export function VisitorTracker() {
  useEffect(() => {
    const visitorId = getOrCreateVisitorId()

    const sendIfVisible = () => {
      if (document.visibilityState === "visible") {
        void pingVisitor(visitorId)
      }
    }

    sendIfVisible()
    const interval = window.setInterval(sendIfVisible, HEARTBEAT_MS)
    document.addEventListener("visibilitychange", sendIfVisible)

    return () => {
      window.clearInterval(interval)
      document.removeEventListener("visibilitychange", sendIfVisible)
    }
  }, [])

  return null
}
