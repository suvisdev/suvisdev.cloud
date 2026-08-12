import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

type Params = { params: Promise<{ id: string }> }

export async function GET(request: Request, { params }: Params) {
  const { id } = await params
  const auth = request.headers.get("authorization")
  try {
    const res = await backendFetch(`/mova/conversations/${id}`, {
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

export async function DELETE(request: Request, { params }: Params) {
  const { id } = await params
  const auth = request.headers.get("authorization")
  try {
    const res = await backendFetch(`/mova/conversations/${id}`, {
      method: "DELETE",
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
