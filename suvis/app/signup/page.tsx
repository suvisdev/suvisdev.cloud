"use client"

import { useCallback, useState } from "react"
import { useRouter } from "next/navigation"
import { AuthDialog } from "@/components/auth/auth-dialog"

/** /signup 직접 접속 시 팝업 회원가입 탭 */
export default function SignupPage() {
  const router = useRouter()
  const [open, setOpen] = useState(true)

  const onOpenChange = useCallback(
    (next: boolean) => {
      setOpen(next)
      if (!next) router.replace("/")
    },
    [router],
  )

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#e8e8e8]">
      <AuthDialog open={open} onOpenChange={onOpenChange} defaultTab="signup" />
    </div>
  )
}
