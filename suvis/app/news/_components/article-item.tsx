import type { NewsArticle, NewsTerm } from "@/lib/news-api"

const DATE_FORMAT = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
})

const BADGE_LABEL = { ai_disclosed: "AI 작성", ai_suspected: "AI 생성 의심" } as const

function formatDate(iso: string | null): string {
  if (!iso) return ""
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? "" : DATE_FORMAT.format(d)
}

/** 배지는 숨기지 않고 단다. 누르면 이유(reasons_ko)를 보여 준다 — 단정하지 않는 문구만(rubric.md §3). */
function AiBadge({ article }: { article: NewsArticle }) {
  if (article.badge === "none") return null
  return (
    <details className="mt-2 text-xs">
      <summary className="border-border bg-muted text-foreground inline-flex cursor-pointer list-none items-center rounded-full border px-2 py-0.5 font-medium select-none">
        {BADGE_LABEL[article.badge]}
      </summary>
      {article.reasons_ko.length > 0 && (
        <ul className="text-muted-foreground mt-2 list-disc space-y-0.5 pl-5">
          {article.reasons_ko.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      <p className="text-muted-foreground mt-1.5">
        자동 판정이라 틀릴 수 있습니다. 기사 내용이 사실인지는 판정하지 않습니다.
      </p>
    </details>
  )
}

/** 요약: 한국어 AI 요약이 있으면 그것(앞에 'AI 요약' 표시), 없으면 피드가 준 요약. */
function Summary({ article }: { article: NewsArticle }) {
  if (article.summary_ko) {
    return (
      <p className="text-muted-foreground mt-1.5 text-sm leading-relaxed break-words [word-break:keep-all]">
        <span className="border-border text-foreground mr-1.5 inline-block rounded border px-1 align-[1px] text-[10px] leading-4 font-medium">
          AI 요약
        </span>
        {article.summary_ko}
      </p>
    )
  }
  if (!article.summary) return null
  return (
    <p className="text-muted-foreground mt-1.5 line-clamp-3 text-sm leading-relaxed break-words [word-break:keep-all]">
      {article.summary}
    </p>
  )
}

/** 그 글에 나오는 전문 용어와 뜻 — 넓은 화면은 글 오른쪽 칸, 좁은 화면은 글 아래. */
function Terms({ terms }: { terms: NewsTerm[] }) {
  if (terms.length === 0) return null
  return (
    <aside
      aria-label="용어 정리"
      className="bg-muted/50 mt-3 rounded-md p-3 lg:mt-0.5 lg:rounded-none lg:bg-transparent lg:p-0"
    >
      <p className="text-muted-foreground text-[11px] font-medium">용어</p>
      <dl className="mt-1.5 space-y-2.5">
        {terms.map((t) => (
          <div key={t.term}>
            <dt className="text-foreground text-xs font-semibold">{t.term}</dt>
            <dd className="text-muted-foreground mt-0.5 text-xs leading-relaxed [word-break:keep-all]">
              {t.desc}
            </dd>
          </div>
        ))}
      </dl>
    </aside>
  )
}

export function ArticleItem({
  article,
  groupLabel,
  showHot = false,
}: {
  article: NewsArticle
  groupLabel: string
  /** 핫한 소식 칸에서만 반응 수치를 보여 준다 — 일반 목록의 수치는 오래됐을 수 있다 */
  showHot?: boolean
}) {
  const date = formatDate(article.published_at)
  const title = article.title_ko || article.title
  const translated = title !== article.title
  return (
    <li className="border-border border-b py-4 last:border-b-0 lg:grid lg:grid-cols-[minmax(0,1fr)_17rem] lg:gap-8">
      <div className="min-w-0">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-foreground text-base leading-snug font-semibold break-words [word-break:keep-all] hover:underline"
        >
          {title}
        </a>
        {translated && (
          <p className="text-muted-foreground mt-0.5 text-xs break-words" lang="en">
            {article.title}
          </p>
        )}
        <p className="text-muted-foreground mt-1 flex flex-wrap gap-x-1.5 text-xs">
          <span>{article.source_name ?? article.source_domain}</span>
          {groupLabel && <span aria-hidden>·</span>}
          {groupLabel && <span>{groupLabel}</span>}
          {date && <span aria-hidden>·</span>}
          {date && <time dateTime={article.published_at ?? undefined}>{date}</time>}
          {showHot && article.hot_label && <span aria-hidden>·</span>}
          {showHot && article.hot_label && (
            <span className="text-foreground font-medium">{article.hot_label}</span>
          )}
        </p>
        <Summary article={article} />
        <AiBadge article={article} />
      </div>
      <Terms terms={article.terms ?? []} />
    </li>
  )
}
