import { NextRequest, NextResponse } from "next/server"

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q") ?? ""
  if (!q) return NextResponse.json([])

  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000"
  try {
    const res = await fetch(
      `${backendUrl}/api/v1/dispatch/adress/search?q=${encodeURIComponent(q)}`,
      { cache: "no-store" },
    )
    if (!res.ok) return NextResponse.json([])
    const data = await res.json() as unknown
    return NextResponse.json(data)
  } catch {
    return NextResponse.json([])
  }
}
