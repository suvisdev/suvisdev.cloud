/** Mova AI 채팅 빠른 추천 문구 풀 — 3시간 단위로 로테이션(하루 8번).
 * 2026-10-07 운영 API로 문구마다 실제 답을 받아 보고 잘 답하는 것만 남겼다. 뺀 것: 넷플릭스·시리즈·러닝타임처럼
 * 데이터에 없는 조건, "공포는 싫고…"(공포물 추천), "비 오는 날…"(제목 낱말만 맞춤), "우울할 때…"(재난물 섞임).
 * 문구를 바꾸면 같은 방식으로 실제 답을 확인할 것. */
const SUGGESTION_POOL = [
  "오늘 밤 가볍게 볼 한국 영화",
  "SF 영화 추천해줘",
  "가족이랑 같이 볼 코미디",
  "실화 바탕 감동 영화 추천",
  "배우 송강호 나오는 작품",
  "마블 이후에 볼 슈퍼히어로 영화",
  "일본 애니메이션 영화 추천",
  "여행 가기 전에 보기 좋은 영화",
  "운동 후 가볍게 볼 액션",
  "클래식 명작 처음 보는 사람용",
  "로맨스 말고 설레는 영화",
  "봉준호 감독 영화 추천",
  "마동석 나오는 액션 영화",
  "디즈니 애니메이션 추천",
  "혼자 보기 좋은 잔잔한 영화",
  "라라랜드 줄거리 알려줘",
] as const

/** 3시간 단위 버킷 키 — 같은 버킷 안에서는 항상 같은 3개(SSR·CSR 일관성). */
const ROTATION_HOURS = 3

function bucketKey(date = new Date()): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, "0")
  const d = String(date.getDate()).padStart(2, "0")
  const bucket = Math.floor(date.getHours() / ROTATION_HOURS)
  return `${y}-${m}-${d}-${bucket}`
}

function hashString(value: string): number {
  let hash = 2166136261
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

/** 3시간 로테이션으로 풀에서 count개를 결정적으로 선택(하루 8번 갱신). */
export function getRotatingMovaChatSuggestions(count = 3, date = new Date()): string[] {
  const key = bucketKey(date)
  const limit = Math.min(count, SUGGESTION_POOL.length)
  const ranked = SUGGESTION_POOL.map((text, index) => ({
    text,
    rank: hashString(`${key}:${index}:${text}`),
  }))
  ranked.sort((a, b) => a.rank - b.rank)
  return ranked.slice(0, limit).map((item) => item.text)
}

