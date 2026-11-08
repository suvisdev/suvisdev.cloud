// 덜미(매크로 탐지) 데모 — SDK는 백엔드가 서빙하는 sdk.js를 그대로 쓴다(고객 사이트와 같은 경로).
const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) || "http://127.0.0.1:8000"

// 데모 사이트의 공개 키(pk_) — 브라우저에 두는 값이라 비밀이 아니다. 비밀 키는 백엔드 .env(DEOLMI_DEMO_SECRET).
const DEMO_SITE_KEY = "pk_be48a7b738c379e04c1ac367cbe93f04"

export type Verdict = "allow" | "challenge" | "block"

export type DeolmiSignals = Record<string, number>

export type DeolmiResult = {
  score: number
  verdict: Verdict
  rule_score: number
  model_score: number | null
  decided_by: "rule" | "model"
  reasons: string[]
}

export type DeolmiSession = {
  score(): Promise<{ token: string; verdict: Verdict }>
  features(): DeolmiSignals
  /** 이벤트 수집을 멈춘다(리스너 해제). */
  stop(): void
}

type DeolmiSdk = { init(opts: { endpoint: string; siteKey: string }): DeolmiSession }

declare global {
  interface Window {
    Deolmi?: DeolmiSdk
  }
}

type ApiErrorBody = { detail?: string | unknown }

let sdkLoading: Promise<DeolmiSdk> | null = null

function loadSdk(): Promise<DeolmiSdk> {
  sdkLoading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script")
    script.src = `${API_BASE}/api/deolmi/sdk.js`
    script.onload = () =>
      window.Deolmi ? resolve(window.Deolmi) : reject(new Error("SDK가 비어 있습니다."))
    script.onerror = () => {
      sdkLoading = null
      reject(new Error("덜미 SDK를 불러오지 못했습니다."))
    }
    document.head.appendChild(script)
  })
  return sdkLoading
}

/** 새 측정 세션 — 이 시점부터의 마우스·키·클릭만 센다. */
export async function startSession(): Promise<DeolmiSession> {
  const sdk = await loadSdk()
  return sdk.init({ endpoint: API_BASE, siteKey: DEMO_SITE_KEY })
}

async function deolmiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/deolmi${path}`, init)
  const data = (await res.json()) as T & ApiErrorBody
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : ""
    throw new Error(`판정을 확인하지 못했습니다(${res.status}${detail ? `, ${detail}` : ""}).`)
  }
  return data
}

/** 고객 서버가 하는 /verify를 백엔드가 데모 비밀 키로 대신 해 준다 — 판정 이유까지 받는다. */
export function demoVerify(token: string): Promise<DeolmiResult> {
  return deolmiFetch<DeolmiResult>("/demo/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  })
}
