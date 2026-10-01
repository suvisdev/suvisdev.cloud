"use client"

import { useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { BookOpen, FileText, Sparkles, UserRound, Users } from "lucide-react"
import { cn } from "@/lib/utils"
import type { AppCatalogItem } from "@/lib/apps-catalog"
import { sendPortfolioChat, type PortfolioChatTurn } from "@/lib/portfolio-api"
import { PortfolioChatPanel } from "@/components/home/portfolio-chat-panel"

type AppLauncherProps = {
  apps: AppCatalogItem[]
}

type ChatState = { messages: PortfolioChatTurn[]; loading: boolean; error: string | null }

// 상단 메뉴 대신 채팅창 바로 아래에 둔다(2026-10-01 사용자) — 지킬 주소는 /blog 페이지와 같다.
// About은 #contact 없이 — 앵커가 있으면 소개를 건너뛰고 연락처로 내려간다.
const HOME_LINKS = [
  { label: "개인 프로젝트 지킬", href: "https://jk.suvisdev.cloud", icon: BookOpen },
  { label: "팀 프로젝트 지킬", href: "https://ats.suvisdev.cloud", icon: Users },
  { label: "Resume", href: "/resume", icon: FileText },
  { label: "About", href: "/contact", icon: UserRound },
]

const homeLinkClass =
  "inline-flex items-center gap-1.5 rounded-full border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:border-[#f0dc3a] hover:text-neutral-900 dark:border-neutral-700 dark:bg-[#161a24] dark:text-neutral-300 dark:hover:text-neutral-100"

export function AppLauncher({ apps }: AppLauncherProps) {
  const [input, setInput] = useState("")
  const [chat, setChat] = useState<ChatState>({ messages: [], loading: false, error: null })

  async function submit() {
    const text = input.trim()
    if (!text || chat.loading) return
    const history = chat.messages
    setInput("")
    setChat({ messages: [...history, { role: "user", content: text }], loading: true, error: null })
    try {
      const res = await sendPortfolioChat(text, history)
      setChat((prev) => ({
        messages: [...prev.messages, { role: "assistant", content: res.reply }],
        loading: false,
        error: null,
      }))
    } catch (e) {
      // 실패한 사용자 메시지는 되돌리고 입력을 복원한다
      setChat({
        messages: history,
        loading: false,
        error: e instanceof Error ? e.message : "답변을 가져오지 못했어요.",
      })
      setInput(text)
    }
  }

  return (
    <div className="flex w-full flex-col items-center gap-8">
      {/* 대화는 입력창 위에 쌓인다 — 채팅 UI 관례(메시지 위, 입력 아래). 2026-09-28 사용자 제안 */}
      {(chat.messages.length > 0 || chat.error) && (
        <PortfolioChatPanel messages={chat.messages} loading={chat.loading} error={chat.error} />
      )}

      <div className="flex w-full flex-col items-center gap-4">
        <form
          className="flex w-full max-w-2xl items-center gap-3 rounded-full border border-neutral-300 bg-white px-5 py-3.5 shadow-sm transition-shadow focus-within:border-[#f0dc3a] focus-within:shadow-md dark:border-neutral-700 dark:bg-[#161a24]"
          onSubmit={(e) => {
            e.preventDefault()
            void submit()
          }}
        >
          <Sparkles className="h-5 w-5 shrink-0 text-neutral-500" aria-hidden />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.nativeEvent.isComposing) e.preventDefault()
            }}
            placeholder="Suvisdev에게 물어보세요 — 진수택과 그의 앱에 대해"
            aria-label="Suvisdev에게 질문"
            autoComplete="off"
            disabled={chat.loading}
            className="w-full bg-transparent text-base text-neutral-900 outline-none placeholder:text-neutral-500 disabled:opacity-60 dark:text-neutral-100"
          />
        </form>

        <nav aria-label="바로가기" className="flex flex-wrap justify-center gap-3">
          {HOME_LINKS.map(({ label, href, icon: Icon }) =>
            href.startsWith("http") ? (
              <a
                key={href}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className={homeLinkClass}
              >
                <Icon className="h-4 w-4" aria-hidden />
                {label}
              </a>
            ) : (
              <Link key={href} href={href} className={homeLinkClass}>
                <Icon className="h-4 w-4" aria-hidden />
                {label}
              </Link>
            )
          )}
        </nav>
      </div>

      <ul className="flex flex-wrap justify-center gap-6 sm:gap-8">
        {apps.map((app) => (
          <li key={app.id}>
            <AppTile app={app} />
          </li>
        ))}
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
          app.gradient
        )}
      >
        {app.image && <Image src={app.image} alt="" fill sizes="72px" className="object-cover" />}
      </div>
      <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
        {app.titleKo}
      </span>
      <span className="text-xs text-neutral-500">{app.kind}</span>
      {!app.available && <span className="text-[11px] text-neutral-400">준비 중</span>}
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
