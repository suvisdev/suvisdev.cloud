/** 정적 카탈로그(`mova-movies`)와 DB slug 불일치 시 URL용 canonical id */

export const MOVA_TITLE_TO_SLUG: Record<string, string> = {
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

export function resolveMovaCatalogSlug(idOrTitle: string, title?: string): string {
  const key = idOrTitle.trim()
  if (MOVA_TITLE_TO_SLUG[key]) return MOVA_TITLE_TO_SLUG[key]
  if (title) {
    const fromTitle = MOVA_TITLE_TO_SLUG[title.trim()]
    if (fromTitle) return fromTitle
  }
  return key
}
