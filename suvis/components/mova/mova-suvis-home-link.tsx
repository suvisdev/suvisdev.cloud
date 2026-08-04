import Link from "next/link"
import { Home } from "lucide-react"
import { cn } from "@/lib/utils"

type MovaSuvisHomeLinkProps = {
  className?: string
}

/** Mova → Suvisdev 포트폴리오 메인 (`/`) */
export function MovaSuvisHomeLink({ className }: MovaSuvisHomeLinkProps) {
  return (
    <Link
      href="/"
      aria-label="Suvisdev 메인으로"
      title="Suvisdev 메인"
      className={cn(
        "inline-flex h-8 min-w-8 shrink-0 items-center justify-center rounded-md border border-mova-border bg-mova-surface-2 text-mova-muted transition-colors hover:border-mova-accent/40 hover:bg-mova-accent-soft hover:text-mova-text",
        className,
      )}
    >
      <Home className="h-3.5 w-3.5 shrink-0" aria-hidden />
    </Link>
  )
}
