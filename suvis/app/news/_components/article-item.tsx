import type { NewsArticle } from "@/lib/news-api"

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

export function ArticleItem({ article, groupLabel }: { article: NewsArticle; groupLabel: string }) {
  const date = formatDate(article.published_at)
  return (
    <li className="border-border border-b py-4 last:border-b-0">
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-foreground text-base leading-snug font-semibold break-words [word-break:keep-all] hover:underline"
      >
        {article.title}
      </a>
      <p className="text-muted-foreground mt-1 flex flex-wrap gap-x-1.5 text-xs">
        <span>{article.source_name ?? article.source_domain}</span>
        {groupLabel && <span aria-hidden>·</span>}
        {groupLabel && <span>{groupLabel}</span>}
        {date && <span aria-hidden>·</span>}
        {date && <time dateTime={article.published_at ?? undefined}>{date}</time>}
      </p>
      {article.summary && (
        <p className="text-muted-foreground mt-1.5 line-clamp-3 text-sm leading-relaxed break-words [word-break:keep-all]">
          {article.summary}
        </p>
      )}
      <AiBadge article={article} />
    </li>
  )
}
