import type { Metadata } from "next"
import { FileText } from "lucide-react"

export const metadata: Metadata = { title: "Resume — Suvisdev" }

export default function ResumePage() {
  return (
    <main className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <FileText className="h-12 w-12 text-neutral-400 dark:text-neutral-500" />
      <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
        Resume
      </h1>
      <p className="text-sm text-neutral-500 dark:text-neutral-400">
        준비 중입니다.
      </p>
    </main>
  )
}
