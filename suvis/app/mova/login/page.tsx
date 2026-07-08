import { Suspense } from "react"
import { MovaAuthForms } from "@/components/mova/mova-auth-forms"

export default function MovaLoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[var(--mova-bg)] text-neutral-500">
          불러오는 중…
        </div>
      }
    >
      <MovaAuthForms />
    </Suspense>
  )
}
