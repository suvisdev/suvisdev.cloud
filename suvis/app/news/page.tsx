import type { Metadata } from "next"

import {
  getNewsArticles,
  getNewsHot,
  getNewsSections,
  getNewsTopics,
  type NewsArticle,
  type NewsSection,
} from "@/lib/news-api"
import { ArticleItem } from "./_components/article-item"
import { HotSection } from "./_components/hot-section"
import { newsHref, type NewsView } from "./_components/news-href"
import { GroupTabs, SearchForm, SectionSwitch, TopicTabs } from "./_components/news-nav"

// news.suvisdev.cloud — 새 AI 기술·아키텍처 변화를 공부하려고 모은다(2026-11-05). 메인 AI, 부록 경제.
// 호스트 연결: next.config.mjs rewrites 가 news.suvisdev.cloud 의 "/" 를 이 페이지로 보낸다.

const PAGE_SIZE = 30

const INTRO: Record<NewsSection, { title: string; desc: string }> = {
  ai: {
    title: "AI 기술 소식",
    desc: "연구소 블로그 · 논문 · 오픈소스 릴리스 · 해설에서 새 AI 기술과 아키텍처 변화를 모읍니다.",
  },
  economy: {
    title: "경제 뉴스",
    desc: "부록 — 경제 언론 기사를 모아 두고 찾아봅니다.",
  },
}

type SearchParams = Promise<Record<string, string | string[] | undefined>>

function pick(value: string | string[] | undefined): string {
  const v = Array.isArray(value) ? value[0] : value
  return (v ?? "").trim()
}

/** 주소 쿼리 → 화면 상태. 검색어가 있으면 탭·묶음은 무시하고, 탭이 있으면 묶음은 무시한다. */
function parseView(sp: Record<string, string | string[] | undefined>): NewsView {
  const section: NewsSection = pick(sp.section) === "economy" ? "economy" : "ai"
  const q = pick(sp.q).slice(0, 50)
  const topicRaw = pick(sp.topic)
  const groupRaw = pick(sp.group)
  const beforeRaw = pick(sp.before)
  const view: NewsView = { section, hideAi: pick(sp.hide_ai) === "1" }
  if (/^[0-9T:.+\-Z]{10,40}$/.test(beforeRaw)) view.before = beforeRaw
  if (q) return { ...view, q }
  if (/^\d{1,9}$/.test(topicRaw)) return { ...view, topic: Number(topicRaw) }
  if (/^[a-z_]{1,16}$/.test(groupRaw)) return { ...view, group: groupRaw }
  return view
}

export async function generateMetadata({
  searchParams,
}: {
  searchParams: SearchParams
}): Promise<Metadata> {
  const { section } = parseView(await searchParams)
  return { title: `${INTRO[section].title} — Suvisdev News` }
}

/** 핫한 소식은 AI 섹션 첫 화면에만 — 검색·탭·묶음을 고르면 그 목록에 집중한다. */
function isFrontPage(view: NewsView): boolean {
  return view.section === "ai" && !view.q && view.topic === undefined && !view.group && !view.before
}

export default async function NewsPage({ searchParams }: { searchParams: SearchParams }) {
  const view = parseView(await searchParams)
  const [sections, topics, articles, hot] = await Promise.all([
    getNewsSections(),
    getNewsTopics(view.section),
    getNewsArticles({
      section: view.section,
      group: view.group,
      topicId: view.topic,
      q: view.q,
      before: view.before,
      limit: PAGE_SIZE,
    }),
    isFrontPage(view) ? getNewsHot() : null,
  ])
  const groups = sections.ok
    ? (sections.data.find((s) => s.code === view.section)?.groups ?? [])
    : []
  const groupLabels = new Map(groups.map((g) => [g.code, g.label]))
  const intro = INTRO[view.section]

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 md:py-12 lg:max-w-5xl">
      {/* 넓은 화면의 오른쪽 칸(17rem + 간격)은 글마다 그 글의 용어가 차지한다 */}
      <div className="lg:pr-[19rem]">
        <header>
          <p className="text-muted-foreground text-xs font-medium tracking-[0.2em] uppercase">
            Suvisdev News
          </p>
          <h1 className="text-foreground mt-2 text-2xl font-bold tracking-tight md:text-3xl">
            {intro.title}
          </h1>
          <p className="text-muted-foreground mt-2 text-sm [word-break:keep-all]">{intro.desc}</p>
        </header>

        <div className="mt-6 space-y-4">
          <SectionSwitch current={view.section} />
          <SearchForm section={view.section} q={view.q} />
          <GroupTabs view={view} groups={groups} />
          {topics.ok && <TopicTabs view={view} topics={topics.data} />}
        </div>
      </div>

      {/* 실패하면 조용히 뺀다 — 아래 최신 목록이 본 화면이다 */}
      {hot?.ok && <HotSection hot={hot.data} groupLabels={groupLabels} />}

      <ArticleSection view={view} result={articles} groupLabels={groupLabels} />

      <footer className="border-border text-muted-foreground mt-12 border-t pt-6 text-xs leading-relaxed [word-break:keep-all]">
        <p>제목·요약·원문 링크만 보여 줍니다. 기사 전문은 각 매체에서 읽어 주세요.</p>
        <p className="mt-1">
          <strong className="text-foreground font-medium">AI 작성</strong>은 매체가 AI로 썼다고 밝힌
          기사, <strong className="text-foreground font-medium">AI 생성 의심</strong>은 규칙으로
          추정한 기사입니다. 한국어 뉴스 기사만 판정하고, 숨기지 않으며, 기사 내용이 사실인지는
          판정하지 않습니다.
        </p>
        <p className="mt-1">
          <strong className="text-foreground font-medium">AI 요약</strong>과 영어 제목 번역은 LG
          EXAONE 3.5 모델이 자동으로 만든 것이라 틀릴 수 있습니다. 중요한 내용은 원문에서 확인해
          주세요.
        </p>
        <p className="mt-1">
          <strong className="text-foreground font-medium">용어</strong> 설명은 미리 써 둔 용어
          사전에서 글에 나오는 말을 찾아 보여 줍니다. 사전에 없는 용어는 나오지 않습니다.
        </p>
      </footer>
    </main>
  )
}

function ArticleSection({
  view,
  result,
  groupLabels,
}: {
  view: NewsView
  result: Awaited<ReturnType<typeof getNewsArticles>>
  groupLabels: Map<string, string>
}) {
  if (!result.ok) {
    return (
      <p className="border-border bg-muted text-muted-foreground mt-8 rounded-md border px-4 py-3 text-sm">
        {result.message}
      </p>
    )
  }
  const rows = result.data
  const shown = view.hideAi ? rows.filter((a) => a.badge === "none") : rows
  return (
    <section className="mt-6" aria-label="글 목록">
      {/* 양 끝으로 벌리면 넓은 화면에서 링크가 용어 칸 위에 혼자 뜬다 — 왼쪽에 붙여 둔다 */}
      <div className="text-muted-foreground flex flex-wrap items-center gap-x-1.5 text-xs">
        <ListCaption view={view} />
        <span aria-hidden>·</span>
        <a
          href={newsHref({ ...view, before: undefined, hideAi: !view.hideAi })}
          className="underline-offset-2 hover:underline"
        >
          {view.hideAi ? "AI 배지 글 보이기" : "AI 배지 글 숨기기"}
        </a>
      </div>
      <EmptyOrList view={view} rows={shown} groupLabels={groupLabels} />
      <MoreLink view={view} rows={rows} />
    </section>
  )
}

function ListCaption({ view }: { view: NewsView }) {
  if (view.q) return <span>&lsquo;{view.q}&rsquo; 검색 결과</span>
  if (view.before) return <span>이전 글</span>
  return <span>최신순</span>
}

function EmptyOrList({
  view,
  rows,
  groupLabels,
}: {
  view: NewsView
  rows: NewsArticle[]
  groupLabels: Map<string, string>
}) {
  if (rows.length === 0) {
    const text = view.q ? "찾는 단어가 모두 들어간 글이 없습니다." : "아직 모인 글이 없습니다."
    return <p className="text-muted-foreground mt-6 text-sm">{text}</p>
  }
  return (
    <ul className="mt-2">
      {rows.map((a) => (
        <ArticleItem key={a.id} article={a} groupLabel={groupLabels.get(a.group) ?? ""} />
      ))}
    </ul>
  )
}

/** 한 쪽이 꽉 찼을 때만 — 마지막 글의 정렬 시각(sort_at)보다 오래된 글을 다음 쪽으로 받는다. */
function MoreLink({ view, rows }: { view: NewsView; rows: NewsArticle[] }) {
  const cursor = rows.at(-1)?.sort_at
  if (rows.length < PAGE_SIZE || !cursor) return null
  return (
    <div className="mt-6 text-center">
      <a
        href={newsHref({ ...view, before: cursor })}
        className="border-border text-foreground hover:bg-muted inline-flex items-center rounded-md border px-4 py-2 text-sm"
      >
        더 보기
      </a>
    </div>
  )
}
