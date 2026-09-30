import { cookies } from "next/headers"
import { NextResponse } from "next/server"

import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  clearAuthCookies,
  gatewayPost,
  parseTokenPair,
  setAuthCookies,
  type TokenPair,
} from "@/lib/auth-bff"

// catch-all BFF 프록시 — 브라우저의 모든 백엔드 호출을 여기서 대행한다.
// httpOnly access 쿠키를 읽어 Bearer로 붙여 백엔드에 전달하고, 401이면 refresh 쿠키로 한 번 회전 후 재시도한다.
// 클라이언트는 토큰을 갖지 않는다(localStorage 폐기) — 인증은 쿠키가 진다.
const API_BASE =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

const BODYLESS = new Set(["GET", "HEAD", "DELETE"])
// 백엔드로 넘길 요청 헤더 화이트리스트(host·cookie·connection 등은 넘기지 않는다).
const FORWARD_HEADERS = ["content-type", "accept"]

async function proxy(
  request: Request,
  ctx: { params: Promise<{ path: string[] }> },
  method: string,
): Promise<NextResponse> {
  const { path } = await ctx.params
  const url = `${API_BASE}/${path.join("/")}${new URL(request.url).search}`
  const body = BODYLESS.has(method) ? undefined : await request.arrayBuffer()

  const baseHeaders: Record<string, string> = {}
  for (const h of FORWARD_HEADERS) {
    const v = request.headers.get(h)
    if (v) baseHeaders[h] = v
  }

  const store = await cookies()
  const access = store.get(ACCESS_COOKIE)?.value
  const refresh = store.get(REFRESH_COOKIE)?.value

  const call = (token: string | undefined): Promise<Response> =>
    fetch(url, {
      method,
      headers: token ? { ...baseHeaders, authorization: `Bearer ${token}` } : baseHeaders,
      body,
      redirect: "manual",
    })

  let backendRes = await call(access)
  let rotated: TokenPair | null = null
  if (backendRes.status === 401 && refresh) {
    const r = await gatewayPost("/auth/refresh", { refresh_token: refresh })
    rotated = r.ok ? parseTokenPair(await r.json().catch(() => ({}))) : null
    if (rotated) backendRes = await call(rotated.access_token)
  }

  const buf = await backendRes.arrayBuffer()
  const response = new NextResponse(buf, {
    status: backendRes.status,
    headers: { "content-type": backendRes.headers.get("content-type") ?? "application/json" },
  })
  if (rotated) setAuthCookies(response, rotated)
  else if (backendRes.status === 401 && refresh) clearAuthCookies(response) // 리프레시도 실패 → 쿠키 정리
  return response
}

type Ctx = { params: Promise<{ path: string[] }> }
export const GET = (req: Request, ctx: Ctx) => proxy(req, ctx, "GET")
export const POST = (req: Request, ctx: Ctx) => proxy(req, ctx, "POST")
export const PUT = (req: Request, ctx: Ctx) => proxy(req, ctx, "PUT")
export const PATCH = (req: Request, ctx: Ctx) => proxy(req, ctx, "PATCH")
export const DELETE = (req: Request, ctx: Ctx) => proxy(req, ctx, "DELETE")
