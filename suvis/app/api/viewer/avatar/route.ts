import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"
import { cookieBearer } from "@/lib/auth-bff"

export async function POST(request: Request) {
  const auth = await cookieBearer()
  // FormData를 다시 넘긴다 — Content-Type을 직접 넣으면 boundary가 달라져 깨진다.
  const form = await request.formData()
  try {
    const res = await backendFetch("/viewer/avatar/upload", {
      method: "POST",
      headers: auth ? { Authorization: auth } : {},
      body: form,
    })
    let data: unknown
    try {
      data = await res.json()
    } catch {
      data = { detail: `Backend response error (${res.status})` }
    }
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 502 })
  }
}
