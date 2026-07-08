"use client"

import { useEffect, useRef } from "react"
import { useTheme } from "next-themes"

export function MovaThemeSetter() {
  const { theme, setTheme } = useTheme()
  const prevRef = useRef<string | undefined>(undefined)

  useEffect(() => {
    prevRef.current = theme
    setTheme("dark")
    return () => {
      setTheme(prevRef.current ?? "light")
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return null
}
