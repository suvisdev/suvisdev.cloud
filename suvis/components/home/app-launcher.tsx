"use client"

import { useMemo, useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Search } from "lucide-react"
import { cn } from "@/lib/utils"
import type { AppCatalogItem } from "@/lib/apps-catalog"

type AppLauncherProps = {
  apps: AppCatalogItem[]
}

function matches(app: AppCatalogItem, q: string) {
  const s = q.trim().toLowerCase()
  if (!s) return true
  return (
    app.titleKo.toLowerCase().includes(s) ||
    app.titleEn.toLowerCase().includes(s) ||
    (app.team ?? "").toLowerCase().includes(s)
  )
}

export function AppLauncher({ apps }: AppLauncherProps) {
  const router = useRouter()
  const [query, setQuery] = useState("")
  const visible = useMemo(() => apps.filter((a) => matches(a, query)), [apps, query])

  function open(app: AppCatalogItem) {
    if (!app.href) return
    if (app.href.startsWith("http")) window.open(app.href, "_blank", "noopener,noreferrer")
    else router.push(app.href)
  }

  return (
    <div className="flex w-full flex-col items-center gap-12">
      <form
        className="flex w-full max-w-2xl items-center gap-3 rounded-full border border-neutral-300 bg-white px-5 py-3.5 shadow-sm transition-shadow focus-within:shadow-md dark:border-neutral-700 dark:bg-[#161a24]"
        onSubmit={(e) => {
          e.preventDefault()
          if (visible[0]) open(visible[0])
        }}
      >
        <Search className="h-5 w-5 shrink-0 text-neutral-500" aria-hidden />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="앱 이름을 입력하세요"
          aria-label="앱 검색"
          autoComplete="off"
          className="w-full bg-transparent text-base text-neutral-900 outline-none placeholder:text-neutral-500 dark:text-neutral-100"
        />
      </form>

      <ul className="flex flex-wrap justify-center gap-6 sm:gap-8">
        {visible.map((app) => (
          <li key={app.id}>
            <AppTile app={app} />
          </li>
        ))}
        {visible.length === 0 && (
          <li className="text-sm text-neutral-500">일치하는 앱이 없습니다.</li>
        )}
      </ul>
    </div>
  )
}

function AppTile({ app }: { app: AppCatalogItem }) {
  const body = (
    <>
      <div
        className={cn(
          "relative h-16 w-16 overflow-hidden rounded-full bg-gradient-to-br shadow-sm transition-transform group-hover:scale-105 sm:h-[4.5rem] sm:w-[4.5rem]",
          app.gradient,
        )}
      >
        {app.image && (
          <Image src={app.image} alt="" fill sizes="72px" className="object-cover" />
        )}
      </div>
      <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
        {app.titleKo}
      </span>
      <span className="text-xs text-neutral-500">
        {app.available ? app.titleEn : "준비 중"}
      </span>
    </>
  )
  const className = "group flex w-24 flex-col items-center gap-2 text-center sm:w-28"

  if (!app.href) return <div className={className}>{body}</div>
  if (app.href.startsWith("http")) {
    return (
      <a href={app.href} target="_blank" rel="noopener noreferrer" className={className}>
        {body}
      </a>
    )
  }
  return (
    <Link href={app.href} className={className}>
      {body}
    </Link>
  )
}
