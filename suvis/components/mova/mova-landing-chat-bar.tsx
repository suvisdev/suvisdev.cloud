"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { ArrowUp, Loader2 } from "lucide-react"
import { getDailyMovaChatSuggestions } from "@/lib/mova-chat-suggestions"
import { cn } from "@/lib/utils"

type ChatFormProps = { message: string }

export function MovaLandingChatBar() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [value, setValue] = useState("")
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const seededRef = useRef(false)
  const dailyHints = useMemo(() => getDailyMovaChatSuggestions(3), [])

  const goMain = useCallback(
    (text: string) => {
      const trimmed = text.trim()
      if (!trimmed) return
      setLoading(true)
      const href = `/mova/main?q=${encodeURIComponent(trimmed)}`
      const d = document as Document & {
        startViewTransition?: (cb: () => void) => void
      }
      if (typeof d.startViewTransition === "function") {
        d.startViewTransition(() => router.push(href))
        return
      }
      router.push(href)
    },
    [router],
  )

  useEffect(() => {
    const q = searchParams.get("q")?.trim()
    if (!q || seededRef.current) return
    seededRef.current = true
    setValue(q)
    inputRef.current?.focus()
  }, [searchParams])

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const formProps = Object.fromEntries(formData.entries()) as ChatFormProps
    goMain(formProps.message)
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Enter" || e.shiftKey || e.nativeEvent.isComposing) return
    e.preventDefault()
    e.currentTarget.form?.requestSubmit()
  }

  return (
    <div className="w-full">
      <form
        onSubmit={onSubmit}
        className="relative rounded-2xl border border-[var(--mova-border)] bg-[var(--mova-surface)] shadow-[0_8px_40px_rgba(0,0,0,0.45)] transition-shadow focus-within:border-[var(--mova-accent)]/40 focus-within:shadow-[0_8px_48px_rgba(190,24,93,0.15)]"
      >
        <textarea
          ref={inputRef}
          name="message"
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
          placeholder="장르, 분위기, 배우를 알려주세요…"
          className="max-h-32 min-h-[3.25rem] w-full resize-none bg-transparent px-4 py-3.5 pr-12 text-base leading-relaxed text-[var(--mova-text)] placeholder:text-neutral-500 outline-none disabled:opacity-60 sm:px-5 sm:py-4 sm:pr-14"
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          aria-label="AI 추천 받기"
          className={cn(
            "absolute right-3 bottom-3 flex h-9 w-9 items-center justify-center rounded-lg transition-all",
            value.trim()
              ? "bg-[var(--mova-accent)] text-white shadow-md hover:brightness-110"
              : "bg-[var(--mova-surface-2)] text-[var(--mova-muted)]",
            "disabled:opacity-40",
          )}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
          )}
        </button>
      </form>

      <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5 px-1 sm:mt-4 sm:gap-2">
        {dailyHints.map((hint) => (
          <button
            key={hint}
            type="button"
            disabled={loading}
            onClick={() => goMain(hint)}
            className="rounded-full border border-[var(--mova-border)] bg-[var(--mova-surface)] px-3 py-1.5 text-xs text-[var(--mova-muted)] transition-colors hover:border-[var(--mova-accent)]/30 hover:bg-[var(--mova-accent-soft)] hover:text-[var(--mova-text)] disabled:opacity-50"
          >
            {hint}
          </button>
        ))}
      </div>
    </div>
  )
}
