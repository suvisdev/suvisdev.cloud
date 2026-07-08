'use client'
import { Sun, Moon } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  if (!mounted) return <div className="h-6 w-11" aria-hidden />

  const isDark = theme === 'dark'

  return (
    <button
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      aria-label="테마 전환"
      role="switch"
      aria-checked={isDark}
      className="relative h-6 w-11 shrink-0 rounded-full bg-neutral-200 transition-colors duration-300 hover:bg-neutral-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 dark:bg-indigo-500/80 dark:hover:bg-indigo-500"
    >
      <span className={`absolute left-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-300 ${isDark ? 'translate-x-5' : 'translate-x-0'}`}>
        {isDark
          ? <Moon className="h-3 w-3 text-indigo-500" aria-hidden />
          : <Sun className="h-3 w-3 text-amber-500" aria-hidden />}
      </span>
    </button>
  )
}
