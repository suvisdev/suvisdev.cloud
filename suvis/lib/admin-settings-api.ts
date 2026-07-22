export type AdminSettings = {
  siteName: string
  siteDescription: string
  defaultModel: string
  responseTimeoutSec: number
  autoRetry: boolean
  ollamaBaseUrl: string
  webhookUrl: string
}

const DEFAULT_SETTINGS: AdminSettings = {
  siteName: "Suvisdev",
  siteDescription: "영화 추천부터 실험 기능까지, Suvisdev 앱을 한곳에서 만나보세요.",
  defaultModel: "EXAONE-3.5-2.4B-Instruct",
  responseTimeoutSec: 60,
  autoRetry: true,
  ollamaBaseUrl: "http://host.docker.internal:11434",
  webhookUrl: "",
}

/** TODO: 설정 저장 API 연동 전까지 mock — 항상 기본값 반환. */
export async function getSettings(): Promise<AdminSettings> {
  return DEFAULT_SETTINGS
}

/** TODO: 실제 저장 로직 미구현. 지금은 호출만 흉내낸다. */
export async function saveSettings(_settings: AdminSettings): Promise<{ ok: true }> {
  await new Promise((r) => setTimeout(r, 400))
  return { ok: true }
}
