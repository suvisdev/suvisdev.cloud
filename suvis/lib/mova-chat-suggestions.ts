/** Mova AI 채팅 빠른 추천 문구 풀 — 날짜별로 3개씩 로테이션 */
const SUGGESTION_POOL = [
  "오늘 밤 가볍게 볼 한국 영화",
  "SF 영화 추천해줘",
  "우울할 때 위로되는 영화",
  "넷플릭스에서 볼 만한 스릴러",
  "가족이랑 같이 볼 코미디",
  "비 오는 날 어울리는 영화",
  "90년대 향수 나는 한국 영화",
  "마블 이후에 볼 슈퍼히어로 영화",
  "실화 바탕 감동 영화 추천",
  "짧게 끝나는 러닝타임 영화",
  "일본 애니메이션 영화 추천",
  "로맨스 말고 설레는 영화",
  "공포는 싫고 긴장감 있는 영화",
  "주말에 몰아볼 시리즈 느낌 영화",
  "배우 송강호 나오는 작품",
  "여행 가기 전에 보기 좋은 영화",
  "운동 후 가볍게 볼 액션",
  "클래식 명작 처음 보는 사람용",
] as const

function localDateKey(date = new Date()): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, "0")
  const d = String(date.getDate()).padStart(2, "0")
  return `${y}-${m}-${d}`
}

function hashString(value: string): number {
  let hash = 2166136261
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

/** 로컬 날짜 기준으로 풀에서 count개를 결정적으로 선택 */
export function getDailyMovaChatSuggestions(count = 3, date = new Date()): string[] {
  const dayKey = localDateKey(date)
  const limit = Math.min(count, SUGGESTION_POOL.length)
  const ranked = SUGGESTION_POOL.map((text, index) => ({
    text,
    rank: hashString(`${dayKey}:${index}:${text}`),
  }))
  ranked.sort((a, b) => a.rank - b.rank)
  return ranked.slice(0, limit).map((item) => item.text)
}
