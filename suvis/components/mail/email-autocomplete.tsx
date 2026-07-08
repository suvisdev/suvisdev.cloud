"use client"

import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

type Contact = { name: string; email: string }

type Props = {
  value: string
  onChange: (v: string) => void
  disabled?: boolean
}

export function EmailAutocomplete({ value, onChange, disabled }: Props) {
  const [suggestions, setSuggestions] = useState<Contact[]>([])
  const [open, setOpen] = useState(false)
  const [activeIdx, setActiveIdx] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!value.trim()) {
      setSuggestions([])
      setOpen(false)
      return
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/dispatch/adress/search?q=${encodeURIComponent(value)}`)
        if (!res.ok) return
        const data = await res.json() as Contact[]
        setSuggestions(data)
        setOpen(data.length > 0)
        setActiveIdx(-1)
      } catch {
        // 네트워크 오류 시 드롭다운 닫기
        setOpen(false)
      }
    }, 150)
    return () => clearTimeout(timer)
  }, [value])

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", onClickOutside)
    return () => document.removeEventListener("mousedown", onClickOutside)
  }, [])

  const select = (contact: Contact) => {
    onChange(contact.email)
    setOpen(false)
    setActiveIdx(-1)
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open) return
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setActiveIdx((i) => Math.max(i - 1, 0))
    } else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault()
      select(suggestions[activeIdx])
    } else if (e.key === "Escape") {
      setOpen(false)
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        id="mail-to"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        onFocus={() => { if (suggestions.length > 0) setOpen(true) }}
        disabled={disabled}
        placeholder="example@email.com"
        autoComplete="off"
        className={cn(
          "mt-1.5 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900",
          "placeholder:text-neutral-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-200",
          "disabled:opacity-50 dark:border-[#252b3b] dark:bg-[#161a24] dark:text-neutral-100 dark:placeholder:text-neutral-600",
        )}
      />

      {open && (
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-lg dark:border-[#252b3b] dark:bg-[#161a24]">
          {suggestions.map((c, i) => (
            <li
              key={`${c.email}-${i}`}
              onMouseDown={(e) => { e.preventDefault(); select(c) }}
              className={cn(
                "flex cursor-pointer flex-col px-3 py-2 text-sm transition-colors",
                i === activeIdx
                  ? "bg-indigo-50 dark:bg-indigo-950/40"
                  : "hover:bg-neutral-50 dark:hover:bg-[#252b3b]",
              )}
            >
              <span className="font-medium text-neutral-900 dark:text-neutral-100">{c.name}</span>
              <span className="text-xs text-neutral-500 dark:text-neutral-400">{c.email}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
