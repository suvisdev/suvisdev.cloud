import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

const FORWARD_PARAMS = [
  "genre",
  "actor",
  "release_year",
  "min_rating",
  "age_rating",
  "platform",
  "sort",
  "limit",
  "offset",
] as const

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const query = new URLSearchParams()

  for (const key of FORWARD_PARAMS) {
    const value = searchParams.get(key)
    if (value !== null && value !== "") {
      query.set(key, value)
    }
  }

  if (!query.has("limit")) query.set("limit", "24")
  if (!query.has("offset")) query.set("offset", "0")

  try {
    const res = await backendFetch(`/mova/movies?${query.toString()}`, {
      cache: "no-store",
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
