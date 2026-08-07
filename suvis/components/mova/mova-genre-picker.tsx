"use client"

import { cn } from "@/lib/utils"

/** 실 DB `tags`(tag_kind='genre') 라벨 기준 — 추천 후보와 실제로 매칭되는 값만 둔다. */
export const PREFERRED_GENRE_OPTIONS = [
  "액션", "드라마", "코미디", "모험", "스릴러", "SF", "판타지", "가족",
  "로맨스", "공포", "범죄", "애니메이션", "미스터리", "역사", "전쟁", "음악",
] as const

type MovaGenrePickerProps = {
  value: string[]
  onChange: (next: string[]) => void
}

/** 선호 장르 토글 칩. 저장은 쓰는 쪽이 한다(마이페이지 편집 · 온보딩 공용). */
export function MovaGenrePicker({ value, onChange }: MovaGenrePickerProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {PREFERRED_GENRE_OPTIONS.map((g) => {
        const selected = value.includes(g)
        return (
          <button
            key={g}
            type="button"
            aria-pressed={selected}
            onClick={() =>
              onChange(selected ? value.filter((x) => x !== g) : [...value, g])
            }
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition",
              selected
                ? "border-mova-accent bg-mova-accent-soft text-mova-accent"
                : "border-mova-border text-neutral-400 hover:border-mova-accent/40",
            )}
          >
            {g}
          </button>
        )
      })}
    </div>
  )
}
