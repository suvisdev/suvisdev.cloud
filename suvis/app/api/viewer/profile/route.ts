import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function GET(request: Request) {
  const id = new URL(request.url).searchParams.get("id")
  if (!id) {
    return NextResponse.json({ detail: "id가 필요합니다." }, { status: 400 })
  }
  try {
    const res = await backendFetch(`/viewer/profile/${id}`, { cache: "no-store" })
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

export async function PATCH(request: Request) {
  const id = new URL(request.url).searchParams.get("id")
  if (!id) {
    return NextResponse.json({ detail: "id가 필요합니다." }, { status: 400 })
  }
  const auth = request.headers.get("authorization")
  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ detail: "잘못된 요청 본문입니다." }, { status: 400 })
  }
  try {
    const res = await backendFetch(`/viewer/profile/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...(auth ? { Authorization: auth } : {}),
      },
      body: JSON.stringify(body),
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
