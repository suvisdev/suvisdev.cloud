// mova·길들 점검 모드 상태 — 관리자 "운영 제어"에서 켜고 끈다(백엔드 site_maintenance).
// 레이아웃(서버)이 읽어 점검 안내를 띄울지 정한다. 10초 캐시, 못 읽으면 점검 아님으로 본다.
const API_BASE =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

export type MaintenanceState = { mova: boolean; gildle: boolean }

const OFF: MaintenanceState = { mova: false, gildle: false }

export async function getMaintenance(): Promise<MaintenanceState> {
  try {
    const res = await fetch(`${API_BASE}/viewer/maintenance`, {
      next: { revalidate: 10 },
      signal: AbortSignal.timeout(3_000),
    })
    if (!res.ok) return OFF
    const data = (await res.json()) as Partial<MaintenanceState>
    return { mova: data.mova === true, gildle: data.gildle === true }
  } catch {
    return OFF
  }
}
