import { Search } from "lucide-react"

import { cn } from "@/lib/utils"
import type { NewsGroup, NewsSection, NewsTopic } from "@/lib/news-api"
import { newsHref, type NewsView } from "./news-href"

const SECTION_TABS: { code: NewsSection; label: string }[] = [
  { code: "ai", label: "AI 기술" },
  { code: "economy", label: "경제 · 부록" },
]

const pillClass = (active: boolean) =>
  cn(
    "inline-flex items-center rounded-full border px-3 py-1 text-sm whitespace-nowrap transition-colors",
    active
      ? "border-primary bg-primary text-primary-foreground"
      : "border-border bg-background text-muted-foreground hover:text-foreground"
  )

/** 섹션 전환 — 메인 AI, 부록 경제. 필터는 전부 링크(서버에서 다시 그림)라 클라이언트 JS 가 필요 없다. */
export function SectionSwitch({ current }: { current: NewsSection }) {
  return (
    <nav aria-label="섹션" className="flex gap-2">
      {SECTION_TABS.map((tab) => (
        <a
          key={tab.code}
          href={newsHref({ section: tab.code })}
          aria-current={tab.code === current ? "page" : undefined}
          className={pillClass(tab.code === current)}
        >
          {tab.label}
        </a>
      ))}
    </nav>
  )
}

export function SearchForm({ section, q }: { section: NewsSection; q?: string }) {
  return (
    <form method="get" role="search" className="flex gap-2">
      {section !== "ai" && <input type="hidden" name="section" value={section} />}
      <label htmlFor="news-q" className="sr-only">
        모아 둔 글에서 찾기
      </label>
      <input
        id="news-q"
        name="q"
        type="search"
        defaultValue={q}
        maxLength={50}
        placeholder={section === "ai" ? "예: mixture of experts, agent" : "예: 금리, 환율"}
        className="border-input bg-background text-foreground placeholder:text-muted-foreground focus-visible:ring-ring h-10 min-w-0 flex-1 rounded-md border px-3 text-sm focus-visible:ring-2 focus-visible:outline-none"
      />
      <button
        type="submit"
        className="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex h-10 shrink-0 items-center gap-1.5 rounded-md px-4 text-sm font-medium"
      >
        <Search className="h-4 w-4" aria-hidden />
        찾기
      </button>
    </form>
  )
}

/** 출처 묶음 탭(전체·연구소 블로그·논문…) — 피드가 있는 묶음만. */
export function GroupTabs({ view, groups }: { view: NewsView; groups: NewsGroup[] }) {
  const shown = groups.filter((g) => g.feeds.length > 0)
  if (shown.length < 2) return null
  const active = view.topic === undefined && !view.q
  return (
    <nav aria-label="출처 묶음" className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
      <a
        href={newsHref({ section: view.section, hideAi: view.hideAi })}
        className={pillClass(active && !view.group)}
      >
        전체
      </a>
      {shown.map((g) => (
        <a
          key={g.code}
          href={newsHref({ section: view.section, group: g.code, hideAi: view.hideAi })}
          title={g.feeds.join(", ")}
          className={pillClass(active && view.group === g.code)}
        >
          {g.label}
        </a>
      ))}
    </nav>
  )
}

/** 운영자가 저장한 검색어 탭 — 그 섹션 글 중 관련 있는 것만 모인다. */
export function TopicTabs({ view, topics }: { view: NewsView; topics: NewsTopic[] }) {
  if (topics.length === 0) return null
  return (
    <nav aria-label="저장 검색어" className="flex flex-wrap items-center gap-2">
      <span className="text-muted-foreground text-xs">주제</span>
      {topics.map((t) => (
        <a
          key={t.id}
          href={newsHref({ section: view.section, topic: t.id, hideAi: view.hideAi })}
          title={t.query}
          className={pillClass(view.topic === t.id)}
        >
          {t.label}
        </a>
      ))}
    </nav>
  )
}
