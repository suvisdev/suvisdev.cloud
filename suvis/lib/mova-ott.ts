/**
 * OTT 프로바이더 메타데이터 — TMDB가 주는 provider slug를 브랜드 표기와 각 사이트
 * 검색 URL로 매핑한다. 현재 백엔드는 platforms[].url을 TMDB watch aggregator
 * 페이지로 채우고 있어서(예: themoviedb.org/movie/278/watch?locale=KR) 사용자가
 * 클릭해도 TMDB로 튕겨나감. 그래서 실제 각 OTT 사이트의 검색 URL을 프론트에서
 * 구성한다.
 */

type OttProviderInfo = {
  label: string
  /** Tailwind: bg + text + border. 사이트별 아이덴티티 컬러. */
  colors: string
  searchUrl: (title: string) => string
  /** 이 slug를 다른 slug로 병합해서 표시(예: 광고형 요금제를 본 요금제로). */
  mergeInto?: string
}

const OTT_PROVIDERS: Record<string, OttProviderInfo> = {
  netflix: {
    label: "Netflix",
    colors: "bg-black text-[#e50914] border-[#e50914]/50 hover:bg-[#e50914]/10",
    searchUrl: (t) => `https://www.netflix.com/search?q=${encodeURIComponent(t)}`,
  },
  netflixstandardwithads: { label: "Netflix", colors: "", searchUrl: () => "", mergeInto: "netflix" },
  netflixkids: { label: "Netflix", colors: "", searchUrl: () => "", mergeInto: "netflix" },
  wavve: {
    label: "Wavve",
    colors: "bg-black text-[#3fadff] border-[#3fadff]/50 hover:bg-[#3fadff]/10",
    searchUrl: (t) => `https://www.wavve.com/search/search?searchWord=${encodeURIComponent(t)}`,
  },
  tving: {
    label: "TVING",
    colors: "bg-black text-[#ff153c] border-[#ff153c]/50 hover:bg-[#ff153c]/10",
    searchUrl: (t) => `https://www.tving.com/search?keyword=${encodeURIComponent(t)}`,
  },
  watcha: {
    label: "WATCHA",
    colors: "bg-black text-[#ff0558] border-[#ff0558]/50 hover:bg-[#ff0558]/10",
    searchUrl: (t) => `https://watcha.com/search?query=${encodeURIComponent(t)}`,
  },
  disneyplus: {
    label: "Disney+",
    colors: "bg-[#0a1e3d] text-[#8fc6ff] border-[#8fc6ff]/50 hover:bg-[#8fc6ff]/10",
    searchUrl: (t) => `https://www.disneyplus.com/search?q=${encodeURIComponent(t)}`,
  },
  coupangplay: {
    label: "쿠팡플레이",
    colors: "bg-black text-[#ff6f22] border-[#ff6f22]/50 hover:bg-[#ff6f22]/10",
    searchUrl: (t) => `https://www.coupangplay.com/search?keyword=${encodeURIComponent(t)}`,
  },
  appletvplus: {
    label: "Apple TV+",
    colors: "bg-black text-white border-white/40 hover:bg-white/10",
    searchUrl: (t) => `https://tv.apple.com/search?term=${encodeURIComponent(t)}`,
  },
  amazonprimevideo: {
    label: "Prime Video",
    colors: "bg-black text-[#00a8e1] border-[#00a8e1]/50 hover:bg-[#00a8e1]/10",
    searchUrl: (t) => `https://www.primevideo.com/search?phrase=${encodeURIComponent(t)}`,
  },
  googleplaymovies: {
    label: "Google Play",
    colors: "bg-black text-[#5f6368] border-[#5f6368]/50 hover:bg-[#5f6368]/10",
    searchUrl: (t) => `https://play.google.com/store/search?q=${encodeURIComponent(t)}&c=movies`,
  },
  youtube: {
    label: "YouTube",
    colors: "bg-black text-[#ff0000] border-[#ff0000]/50 hover:bg-[#ff0000]/10",
    searchUrl: (t) => `https://www.youtube.com/results?search_query=${encodeURIComponent(t + " 영화")}`,
  },
  paramountplus: {
    label: "Paramount+",
    colors: "bg-black text-[#0064ff] border-[#0064ff]/50 hover:bg-[#0064ff]/10",
    searchUrl: (t) => `https://www.paramountplus.com/search/?q=${encodeURIComponent(t)}`,
  },
  seezn: {
    label: "Seezn",
    colors: "bg-black text-[#8a56ff] border-[#8a56ff]/50 hover:bg-[#8a56ff]/10",
    searchUrl: (t) => `https://www.seezn.com/search?keyword=${encodeURIComponent(t)}`,
  },
}

export type NormalizedOttBadge = {
  provider: string
  label: string
  colors: string
  href: string
}

/** TMDB가 준 platforms 목록을 화면 표시용으로 정규화 — 중복 병합, 알려진 것만
 * 반환. 링크는 각 OTT의 검색 URL(제목 쿼리)로 구성한다. */
export function normalizeOttPlatforms(
  platforms: { provider: string; url: string | null }[] | null | undefined,
  title: string,
): NormalizedOttBadge[] {
  if (!platforms || platforms.length === 0) return []
  const seen = new Set<string>()
  const out: NormalizedOttBadge[] = []
  for (const p of platforms) {
    const key = String(p.provider).toLowerCase().replace(/\s+/g, "")
    const info = OTT_PROVIDERS[key]
    if (!info) continue
    const canonical = info.mergeInto ?? key
    if (seen.has(canonical)) continue
    seen.add(canonical)
    const display = info.mergeInto ? OTT_PROVIDERS[info.mergeInto] : info
    if (!display) continue
    out.push({
      provider: canonical,
      label: display.label,
      colors: display.colors,
      href: display.searchUrl(title),
    })
  }
  return out
}
