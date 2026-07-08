import Link from "next/link"
import type { LucideIcon } from "lucide-react"
import { Clock, Layers, MapPin, Navigation, Users } from "lucide-react"
import { AuthOpenLink } from "@/components/auth/auth-open-link"

type InfoItem = {
  label: string
  href: string
  icon: LucideIcon
}

const ITEMS: InfoItem[] = [
  { label: "프로젝트", href: "#projects", icon: Layers },
  { label: "서비스", href: "#apps", icon: Users },
  { label: "빠른이동", href: "#auth", icon: Navigation },
  { label: "문의시간", href: "mailto:contact@suvisdev.cloud", icon: Clock },
  { label: "연락처", href: "/contact#contact", icon: MapPin },
]

export function QuickInfoBar() {
  return (
    <div className="flex w-full max-w-[min(100vw-2rem,42rem)] border border-black/15 bg-white shadow-sm lg:max-w-none lg:w-auto">
      <div className="flex min-w-[4.25rem] items-center justify-center bg-black px-4 py-4 text-sm font-bold tracking-[0.2em] text-white">
        INFO
      </div>
      {ITEMS.map((item) => {
        const Icon = item.icon
        const cellClass =
          "group flex min-w-[4.5rem] flex-1 flex-col items-center justify-center gap-2 border-l border-black/15 px-3 py-3 transition-colors hover:bg-neutral-50 sm:min-w-[5rem] sm:px-4 sm:py-4"

        if (item.href === "#auth") {
          return (
            <AuthOpenLink key={item.label} className={cellClass} icon={Icon}>
              <span className="text-[10px] leading-none tracking-tight text-neutral-700 sm:text-[11px]">
                {item.label}
              </span>
            </AuthOpenLink>
          )
        }

        return (
          <Link key={item.label} href={item.href} className={cellClass}>
            <Icon className="h-5 w-5 stroke-[1.25] text-neutral-800" aria-hidden />
            <span className="text-[10px] leading-none tracking-tight text-neutral-700 sm:text-[11px]">
              {item.label}
            </span>
          </Link>
        )
      })}
    </div>
  )
}
