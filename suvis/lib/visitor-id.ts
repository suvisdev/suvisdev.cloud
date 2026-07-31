const COOKIE_NAME = "suvis_vid"
const MAX_AGE_SECONDS = 60 * 60 * 24 * 365 * 2 // 2년

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

/** 익명 방문자 식별용 쿠키 UUID를 가져오거나 없으면 새로 만든다. PII 없음. */
export function getOrCreateVisitorId(): string {
  const existing = readCookie(COOKIE_NAME)
  if (existing) return existing

  const id = crypto.randomUUID()
  const secure = location.protocol === "https:" ? "; Secure" : ""
  document.cookie = `${COOKIE_NAME}=${encodeURIComponent(id)}; Max-Age=${MAX_AGE_SECONDS}; Path=/; SameSite=Lax${secure}`
  return id
}
