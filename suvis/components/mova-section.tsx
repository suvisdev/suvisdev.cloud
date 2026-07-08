import { Film } from "lucide-react"
import Link from "next/link"

export function MovaSection() {
  return (
    <Link
      href="/mova"
      className="group flex w-20 flex-col items-center gap-2"
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-red-900/55 bg-gradient-to-br from-red-950/80 via-zinc-950 to-zinc-950 shadow-md shadow-red-950/30 transition-all duration-200 group-hover:scale-105 group-hover:border-amber-400/40 group-hover:shadow-amber-900/15">
        <Film className="h-7 w-7 text-red-400/95 transition-colors group-hover:text-cyan-400" />
      </div>
      <span className="text-center text-xs font-medium tracking-wide text-red-200/60 transition-colors group-hover:text-red-100/90">
        Mova
      </span>
    </Link>
  )
}
