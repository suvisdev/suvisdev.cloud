import { NextResponse, type NextRequest } from "next/server"

import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  clearTokens,
  isExpired,
  refreshOnce,
  retryLaterResponse,
  writeTokens,
} from "@/lib/auth-bff"

// 인증을 쓰는 개별 프록시(cookieBearer 사용 라우트) 앞에서 access 쿠키를 한 번에 갱신한다 — 라우트마다
// 갱신 코드를 두지 않게. access가 없거나 만료 직전이고 refresh가 있으면 회전한다.
// - 성공: 새 토큰을 이 요청의 쿠키로 바꿔 라우트에 넘기고, 응답 쿠키에도 심는다.
// - 무효(401/403): 쿠키를 지우고 비로그인으로 넘긴다(세션이 실제로 끝났다).
// - 인증 서버 장애·5초 초과: 라우트로 보내지 않고 503 — 만료 토큰으로 401이 나거나 /mova/chat이 익명으로
//   강등되지 않게 한다. 쿠키는 그대로 두니 클라가 재시도하면 된다.
// - 회전 경합(409 refresh_superseded): 쿠키를 지우지 않고 409 — 다른 요청이 심은 새 쿠키로 재시도하면 된다.
// 공개 API·catch-all(/api/backend)은 matcher에 넣지 않는다 — 인증 서버 장애와 무관하게 동작해야 한다
// (catch-all은 forwardToBackend가 401일 때만 503으로 바꾼다).
export async function proxy(request: NextRequest) {
  if (isPublicMethod(request)) return NextResponse.next()
  const access = request.cookies.get(ACCESS_COOKIE)?.value
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value
  if (!refresh || (access && !isExpired(access))) return NextResponse.next()

  const result = await refreshOnce(refresh)
  const retry = retryLaterResponse(result)
  if (retry) return retry
  if (result.kind === "ok") {
    request.cookies.set(ACCESS_COOKIE, result.tokens.access_token)
    request.cookies.set(REFRESH_COOKIE, result.tokens.refresh_token)
  } else {
    request.cookies.delete(ACCESS_COOKIE)
    request.cookies.delete(REFRESH_COOKIE)
  }
  const headers = new Headers(request.headers)
  headers.set("cookie", request.cookies.toString())
  const response = NextResponse.next({ request: { headers } })
  if (result.kind === "ok") writeTokens(response.cookies, result.tokens)
  else clearTokens(response.cookies)
  return response
}

// 같은 파일 안에서 인증을 안 쓰는 메서드 — 리뷰 댓글 조회, 외부 시스템 수신(dispatch receive POST).
function isPublicMethod(request: NextRequest): boolean {
  const path = request.nextUrl.pathname
  if (request.method === "GET" && /^\/api\/mova\/reviews\/[^/]+\/comments$/.test(path)) return true
  return request.method === "POST" && path === "/api/dispatch/receive"
}

// multipart 업로드(아바타·주소록)는 제외한다 — Vercel 미들웨어 본문 한도(4MB)가 함수 한도(4.5MB)보다 작다.
// 그 라우트는 cookieBearerOr503()으로 직접 갱신한다. 새 인증 라우트를 만들면 이 목록에 추가한다.
// matcher는 빌드 때 정적으로 읽히므로 리터럴로 적는다(변수·map 불가).
export const config = {
  matcher: [
    { source: "/api/mova/chat", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/mova/conversations/:path*", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/mova/mypage/:path*", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/mova/watchlist/:path*", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/mova/rankings/refresh", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/mova/reviews", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/mova/reviews/activity", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/mova/reviews/comments/:path*", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/mova/reviews/:reviewId", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/mova/reviews/:reviewId/comments", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/viewer/profile", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/dispatch/:path*", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/harvester/:path*", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/analytics/visitors/summary", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/titanic/smith/chat", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/v1/langchain/chat", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/v1/contents/soccer/chat", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
    { source: "/api/media/photos/ocr", missing: [{ type: "header", key: "content-type", value: "multipart/form-data.*" }] },
  ],
}
