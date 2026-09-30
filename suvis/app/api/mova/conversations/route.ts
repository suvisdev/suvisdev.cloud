import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"
import { cookieBearer } from "@/lib/auth-bff"

export async function GET(_request: Request) {
  const auth = await cookieBearer()
  try {
    const res = await backendFetch("/mova/conversations", {
      method: "GET",
      headers: {
        ...(auth ? { Authorization: auth } : {}),
      },
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
