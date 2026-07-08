import { cn } from "@/lib/utils"

type Platform = "netflix" | "disney" | string | undefined | null

const PLATFORM_STYLES: Record<string, string> = {
  netflix: "bg-rose-950/80 text-rose-200 ring-rose-500/30",
  disney: "bg-sky-950/80 text-sky-200 ring-sky-500/30",
}

export function MovaPlatformBadge({ platform }: { platform?: Platform }) {
  if (!platform) return null
  const key = String(platform).toLowerCase()
  const isNetflix = key.includes("netflix")
  const isDisney = key.includes("disney")
  const label = isNetflix ? "N+" : isDisney ? "D+" : String(platform).slice(0, 3).toUpperCase()
  const style = isNetflix
    ? PLATFORM_STYLES.netflix
    : isDisney
      ? PLATFORM_STYLES.disney
      : "bg-zinc-800/90 text-zinc-300 ring-white/10"

  return (
    <span
      className={cn(
        "inline-flex h-4 min-w-4 items-center justify-center rounded px-0.5 text-[8px] font-bold ring-1",
        style,
      )}
      title={String(platform)}
    >
      {label}
    </span>
  )
}
