"use client"

import { useEffect } from "react"
import { syncSessionWithCookie } from "@/lib/suvis-session"

/** 페이지를 열 때 한 번, 로그인 표시(localStorage)와 실제 인증(httpOnly 쿠키)을 맞춘다 —
 *  쿠키가 없거나 만료됐는데 표시만 남아 "로그인돼 보이지만 401"이 되는 상태를 막는다. */
export function SessionSync() {
  useEffect(() => {
    void syncSessionWithCookie()
  }, [])
  return null
}
