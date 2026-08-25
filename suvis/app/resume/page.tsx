import type { Metadata } from "next"
import { ResumeContent } from "./_components/resume-content"

export const metadata: Metadata = { title: "Resume — Suvisdev" }

export default function ResumePage() {
  return (
    <main className="min-h-screen bg-white px-4 py-12 md:px-8 md:py-16">
      <ResumeContent />
    </main>
  )
}
