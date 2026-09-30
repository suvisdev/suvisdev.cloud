import type { NextRequest} from "next/server";
import { NextResponse } from "next/server"
import { backendFetch } from "@/lib/backend-client"
import { cookieBearer } from "@/lib/auth-bff"

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q") ?? ""
  if (!q) return NextResponse.json([])

  const auth = await cookieBearer()
  try {
    const res = await backendFetch(
      `/api/v1/dispatch/adress/search?q=${encodeURIComponent(q)}`,
      { cache: "no-store", headers: auth ? { Authorization: auth } : {} },
    )
    if (!res.ok) return NextResponse.json([])
    const data = await res.json() as unknown
    return NextResponse.json(data)
  } catch {
    return NextResponse.json([])
  }
}
