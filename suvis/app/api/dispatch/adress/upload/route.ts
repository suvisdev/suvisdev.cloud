import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"
import { cookieBearer } from "@/lib/auth-bff"

export async function POST(request: Request) {
  try {
    const formData = await request.formData()
    const auth = await cookieBearer()
    const res = await backendFetch("/api/v1/dispatch/adress/upload", {
      method: "POST",
      headers: auth ? { Authorization: auth } : {},
      body: formData,
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
