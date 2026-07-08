import Link from "next/link"
import { MovaHeader } from "@/components/mova/mova-header"
import { Button } from "@/components/ui/button"

export default function MovaTitleNotFound() {
  return (
    <>
      <MovaHeader />
      <main className="mx-auto flex min-h-[50vh] max-w-[1400px] flex-col items-center justify-center gap-4 px-4 py-16 text-center md:px-6">
        <h1 className="text-lg font-semibold text-[var(--mova-text)]">작품을 찾을 수 없습니다</h1>
        <p className="max-w-md text-sm text-neutral-400">
          요청한 영화가 카탈로그에 없거나 삭제되었을 수 있습니다.
        </p>
        <Button asChild variant="outline">
          <Link href="/mova/movies">영화 목록으로</Link>
        </Button>
      </main>
    </>
  )
}
