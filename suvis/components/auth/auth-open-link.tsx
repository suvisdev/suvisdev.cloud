"use client"

import { useState } from "react"
import type { LucideIcon } from "lucide-react"
import { AuthDialog } from "@/components/auth/auth-dialog"
import type { AuthFormsMode } from "@/app/login/auth-forms"

type AuthOpenLinkProps = {
  defaultTab?: AuthFormsMode
  className?: string
  children: React.ReactNode
  icon?: LucideIcon
}

/** 링크처럼 보이지만 로그인 팝업을 연다 */
export function AuthOpenLink({
  defaultTab = "login",
  className,
  children,
  icon: Icon,
}: AuthOpenLinkProps) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className={className}>
        {Icon && <Icon className="h-5 w-5 stroke-[1.25] text-neutral-800" aria-hidden />}
        {children}
      </button>
      <AuthDialog open={open} onOpenChange={setOpen} defaultTab={defaultTab} />
    </>
  )
}
