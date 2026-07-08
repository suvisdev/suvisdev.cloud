/** 채팅·검색 API에서 poster가 "", null, {} 등으로 올 때 Next/Image 오류 방지 */

export function coercePosterUrl(value: unknown): string | null {
  if (value == null) return null
  if (typeof value === "string") {
    const trimmed = value.trim()
    if (!trimmed) return null
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://") || trimmed.startsWith("/")) {
      return trimmed
    }
    return null
  }
  if (typeof value === "object") {
    const o = value as Record<string, unknown>
    for (const key of ["url", "src", "href", "poster"]) {
      const nested = coercePosterUrl(o[key])
      if (nested) return nested
    }
  }
  return null
}
