/** 길들 표기 규칙 — 앱 `gildle/lib/features/gildle/presentation/format.dart`와 같은 결과를 낸다
 *  (2026-09-30 웹·앱 통일). 한쪽을 바꾸면 다른 쪽도 같이 바꾼다. */

/** 기록·산책 중 거리(소수 둘째 자리). 1km 미만은 m. */
export function formatKm(m: number): string {
  return m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${Math.round(m)} m`
}

/** 지도 경로 요약용 거리(소수 첫째 자리). */
export function formatKmShort(m: number): string {
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`
}

/** 초 → `mm:ss`, 한 시간 이상이면 `h:mm:ss`. */
export function formatDuration(totalS: number): string {
  const h = Math.floor(totalS / 3600)
  const mm = String(Math.floor((totalS % 3600) / 60)).padStart(2, "0")
  const ss = String(Math.floor(totalS % 60)).padStart(2, "0")
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

/** ISO 시각 → `2026.09.30 14:05`(보는 사람의 현지 시각). */
export function formatDate(iso: string): string {
  const t = new Date(iso)
  const two = (n: number) => String(n).padStart(2, "0")
  return `${t.getFullYear()}.${two(t.getMonth() + 1)}.${two(t.getDate())} ${two(t.getHours())}:${two(t.getMinutes())}`
}

/** 분/km. 100m 미만이면 의미가 없어 `—`. */
export function formatPace(distanceM: number, elapsedS: number): string {
  if (distanceM < 100) return "—"
  return `${(elapsedS / 60 / (distanceM / 1000)).toFixed(1)}분/km`
}

export const SEASON_LABEL: Record<string, string> = {
  spring_autumn: "봄·가을",
  summer_shade: "그늘 모드",
  winter_safety: "겨울 안전",
  summer: "여름", // 구 기록
}
