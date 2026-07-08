const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000"

export const BACKEND_DOWN =
  "Backend unreachable. Start API in suvisdev: uvicorn main:app --reload"

export function backendFetch(path: string, init?: RequestInit): Promise<Response> {
  const creds = process.env.BACKEND_CREDENTIALS
  const authHeaders: Record<string, string> = creds
    ? { Authorization: `Basic ${Buffer.from(creds).toString("base64")}` }
    : {}
  const existingHeaders = (init?.headers ?? {}) as Record<string, string>
  return fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers: { ...authHeaders, ...existingHeaders },
  })
}
