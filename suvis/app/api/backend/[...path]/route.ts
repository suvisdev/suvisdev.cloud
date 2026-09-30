import { forwardToBackend } from "@/lib/auth-bff"

// catch-all BFF 프록시 — 브라우저의 모든 백엔드 호출을 여기서 대행한다.
// httpOnly 쿠키를 Bearer로 붙여 백엔드에 전달하고 401이면 리프레시(공용 forwardToBackend가 처리).
// 클라이언트는 토큰을 갖지 않는다 — 인증은 쿠키가 진다.
const API_BASE =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

type Ctx = { params: Promise<{ path: string[] }> }

async function proxy(request: Request, ctx: Ctx, method: string) {
  const { path } = await ctx.params
  const url = `${API_BASE}/${path.join("/")}${new URL(request.url).search}`
  return forwardToBackend(request, url, method)
}

export const GET = (req: Request, ctx: Ctx) => proxy(req, ctx, "GET")
export const POST = (req: Request, ctx: Ctx) => proxy(req, ctx, "POST")
export const PUT = (req: Request, ctx: Ctx) => proxy(req, ctx, "PUT")
export const PATCH = (req: Request, ctx: Ctx) => proxy(req, ctx, "PATCH")
export const DELETE = (req: Request, ctx: Ctx) => proxy(req, ctx, "DELETE")
