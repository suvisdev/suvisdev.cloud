import { safeApiErrorMessage } from "@/lib/user-facing-error"

// 토큰은 응답 본문에 없다 — BFF 프록시가 httpOnly 쿠키로 심는다(2026-09-30).
export type OAuthSessionResult = {
  id: number
  username: string
  nickname: string
  role: "admin" | "user"
}

type OAuthApiErrorBody = { detail?: string | unknown }

async function postOAuth(
  path: string,
  body: Record<string, unknown>,
): Promise<OAuthSessionResult> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const data = (await res.json()) as OAuthSessionResult & OAuthApiErrorBody
  if (!res.ok) {
    throw new Error(
      safeApiErrorMessage(data.detail, "요청을 처리하지 못했습니다.", res.status),
    )
  }
  return data
}

export function exchangeOAuthCode(code: string): Promise<OAuthSessionResult> {
  return postOAuth("/api/auth/oauth-exchange", { code })
}

export function submitOAuthConsent(
  code: string,
  agreed: boolean,
): Promise<OAuthSessionResult> {
  return postOAuth("/api/auth/oauth-consent", { code, agreed })
}
