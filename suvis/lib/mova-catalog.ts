/** 정적 카탈로그(`mova-movies`)의 한글 제목 → 목업 slug. DB 작품에는 쓰지 않는다. */

const MOVA_TITLE_TO_SLUG: Record<string, string> = {
  원더풀스: "wonderfuls",
  인터스텔라: "interstellar",
  "듄: 파트2": "dune-2",
  오펜하이머: "oppenheimer",
  기생충: "parasite",
  "블레이드 러너 2049": "blade-runner-2049",
  라라랜드: "lalaland",
  매트릭스: "matrix",
  인셉션: "inception",
  "다크 나이트": "dark-knight",
  "오징어 게임": "squid-game",
}

/** URL에 쓸 작품 id. DB slug가 오면 그대로 쓴다 — 제목으로 목업 slug("parasite")에 덮어쓰면
 *  실제 DB slug(`tmdb-496243`)를 잃어 상세 조회가 404가 되고 목업 데이터가 보인다(2026-09-30 실사용:
 *  기생충·인셉션 등 8편). 첫 인자가 한글 제목 자체일 때만 정적 카탈로그 slug로 바꾼다. */
export function resolveMovaCatalogSlug(idOrTitle: string, _title?: string): string {
  const key = idOrTitle.trim()
  return MOVA_TITLE_TO_SLUG[key] ?? key
}
