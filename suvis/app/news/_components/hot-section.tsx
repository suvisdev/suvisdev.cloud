import type { NewsArticle, NewsHot } from "@/lib/news-api"
import { ArticleItem } from "./article-item"

/** 화제 정도는 모델이 판단하지 않고 사람들의 반응 수치로 정한다. 단위가 달라 출처별로 따로 보여 준다. */
function HotList({
  title,
  rows,
  groupLabels,
}: {
  title: string
  rows: NewsArticle[]
  groupLabels: Map<string, string>
}) {
  if (rows.length === 0) return null
  return (
    <div className="mt-4">
      <h3 className="text-foreground text-sm font-semibold">{title}</h3>
      <ul className="mt-1">
        {rows.map((a) => (
          <ArticleItem key={a.id} article={a} groupLabel={groupLabels.get(a.group) ?? ""} showHot />
        ))}
      </ul>
    </div>
  )
}

export function HotSection({
  hot,
  groupLabels,
}: {
  hot: NewsHot
  groupLabels: Map<string, string>
}) {
  if (hot.papers.length === 0 && hot.community.length === 0) return null
  return (
    <section
      aria-label="오늘의 핫한 소식"
      className="border-border mt-8 border-b pb-2 [word-break:keep-all]"
    >
      <h2 className="text-foreground text-lg font-bold tracking-tight">오늘의 핫한 소식</h2>
      <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
        사람들의 반응이 많은 순서입니다. 논문은 Hugging Face 추천 수, 커뮤니티 글은 Hacker News
        점수로 매기며 30분마다 새로 받습니다.
      </p>
      <HotList title="화제의 논문" rows={hot.papers} groupLabels={groupLabels} />
      <HotList title="커뮤니티 화제" rows={hot.community} groupLabels={groupLabels} />
    </section>
  )
}
