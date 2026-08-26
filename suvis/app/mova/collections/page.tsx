import type { Metadata } from "next"
import Link from "next/link"
import { Layers } from "lucide-react"
import { fetchMovaCollections } from "@/lib/mova-api"

export const metadata: Metadata = { title: "컬렉션 — Mova" }

export default async function MovaCollectionsPage() {
  let collections: Awaited<ReturnType<typeof fetchMovaCollections>> | null = null
  try {
    collections = await fetchMovaCollections(40, 0)
  } catch {
    // API 미연결 시 빈 상태 표시
  }

  const items = collections?.items ?? []

  return (
    <>
      <main className="mx-auto max-w-[1400px] px-4 py-6 md:px-6 md:py-8">
        <div className="mb-6 flex items-center gap-2">
          <Layers className="h-5 w-5 text-mova-accent" />
          <h1 className="text-xl font-semibold text-mova-text">컬렉션</h1>
          {items.length > 0 && (
            <span className="text-sm text-neutral-500">{items.length}개</span>
          )}
        </div>

        {items.length === 0 ? (
          <p className="text-sm text-neutral-400">등록된 컬렉션이 없습니다.</p>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {items.map((col) => (
              <li key={col.slug}>
                <Link
                  href={`/mova/collections/${col.slug}`}
                  className="group flex h-full flex-col gap-3 rounded-xl border border-mova-border bg-mova-surface p-5 transition hover:border-mova-accent/40 hover:bg-mova-surface-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="text-base font-semibold text-mova-text group-hover:text-mova-accent-bright">
                      {col.name}
                    </h2>
                    <span className="shrink-0 rounded-full bg-mova-surface-2 px-2.5 py-0.5 text-xs text-neutral-400">
                      {col.movie_count}편
                    </span>
                  </div>
                  {col.description && (
                    <p className="line-clamp-2 text-sm leading-relaxed text-mova-muted">
                      {col.description}
                    </p>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  )
}
