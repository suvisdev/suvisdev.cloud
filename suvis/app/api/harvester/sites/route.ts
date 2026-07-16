import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function GET() {
  try {
    const res = await backendFetch("/api/ontology/harvester/sites")
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
