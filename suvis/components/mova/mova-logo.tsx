import Link from "next/link"
import { cn } from "@/lib/utils"

type MovaLogoProps = {
  href?: string
  className?: string
  size?: "sm" | "md" | "lg"
}

const sizeClass = {
  sm: "text-base gap-1.5",
  md: "text-lg md:text-xl gap-2",
  lg: "text-2xl md:text-3xl gap-2.5",
}

export function MovaLogo({ href = "/mova", className, size = "md" }: MovaLogoProps) {
  const inner = (
    <span
      className={cn(
        "font-display inline-flex items-center font-bold tracking-[0.12em] text-mova-text uppercase",
        sizeClass[size],
        className,
      )}
    >
      <span
        className="h-[1.1em] w-[3px] shrink-0 rounded-full bg-mova-accent shadow-[0_0_12px_var(--mova-accent-soft)]"
        aria-hidden
      />
      Mova
    </span>
  )

  if (!href) return inner
  return (
    <Link href={href} className="shrink-0 transition-opacity hover:opacity-90">
      {inner}
    </Link>
  )
}
