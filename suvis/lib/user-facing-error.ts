/** @see suvis/_claude/REACT_RULES.md §7 — 입력값·원시 payload를 UI에 노출하지 않음 */

const MAX_LEN = 200

/**
 * API `detail`을 사용자에게 보여줄 짧은 문장으로만 변환한다.
 * 객체 전체 JSON.stringify, formProps, 비밀번호 필드 값은 넣지 않는다.
 */
export function safeApiErrorMessage(
  detail: unknown,
  fallback: string,
  status?: number,
): string {
  if (typeof detail === "string") {
    const t = detail.trim()
    if (!t) return fallback
    return t.length > MAX_LEN ? `${t.slice(0, MAX_LEN)}…` : t
  }

  if (Array.isArray(detail)) {
    const parts: string[] = []
    for (const item of detail) {
      if (typeof item === "object" && item && "msg" in item) {
        const msg = (item as { msg?: unknown }).msg
        if (typeof msg === "string" && msg.trim()) parts.push(msg.trim())
      }
    }
    if (parts.length) {
      const joined = parts.join(" ")
      return joined.length > MAX_LEN ? `${joined.slice(0, MAX_LEN)}…` : joined
    }
  }

  if (status === 404) return fallback
  return fallback
}
