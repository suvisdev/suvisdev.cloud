"use client"

import { useCallback, useState } from "react"
import { useRouter } from "next/navigation"
import { AuthDialog } from "@/components/auth/auth-dialog"

/** /login 직접 접속 시 팝업으로 로그인·회원가입 */
export default function LoginPage() {
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
      <AuthDialog open={open} onOpenChange={onOpenChange} defaultTab="login" />
    </div>
  )
}
