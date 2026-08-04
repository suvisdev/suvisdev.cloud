"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { getPhotosWithOcr, type OcrPhotoItem } from "@/lib/media-api"

type ScanState = {
  status: "loading" | "error" | "ready"
  items: OcrPhotoItem[]
  message: string | null
}

export default function LessonPhotosPage() {
  const [scan, setScan] = useState<ScanState>({ status: "loading", items: [], message: null })

  useEffect(() => {
    let cancelled = false
    getPhotosWithOcr()
      .then((items) => {
        if (!cancelled) setScan({ status: "ready", items, message: null })
      })
      .catch((e) => {
        if (cancelled) return
        setScan({
          status: "error",
          items: [],
          message: e instanceof Error ? e.message : "사진을 불러오지 못했습니다.",
        })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#f3f3f3] px-4 py-4 md:px-6 md:py-6 dark:bg-[#0d0f14]">
      <main className="mx-auto grid max-w-[1500px] gap-4 md:grid-cols-[220px_1fr]">
        <aside className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-wide text-neutral-500">수업명</p>
          <div className="mt-4 space-y-2">
            <Link
              href="/lesson"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              LESSON 홈
            </Link>
            <Link
              href="/titanic"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              타이타닉
            </Link>
            <Link
              href="/titanic/data-collection"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              1. 데이터 수집
            </Link>
            <Link
              href="/titanic/passengers"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              2. 승객목록
            </Link>
            <Link
              href="/titanic/smith-captain"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              3. 스미스 선장과 대화
            </Link>
          </div>
          <p className="mt-6 text-xs font-semibold tracking-wide text-neutral-500">VISION</p>
          <div className="mt-2 space-y-2">
            <Link
              href="/vision"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              이미지 업로드
            </Link>
            <Link
              href="/vision/object-detection"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              객체 탐지
            </Link>
          </div>
          <p className="mt-6 text-xs font-semibold tracking-wide text-neutral-500">MEDIA</p>
          <div className="mt-2 space-y-2">
            <Link
              href="/lesson/photos"
              className="block rounded-md bg-neutral-100 px-3 py-2 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-200 dark:bg-[#252b3b] dark:text-neutral-100 dark:hover:bg-[#2d3447]"
            >
              S3 사진 OCR
            </Link>
          </div>
          <p className="mt-6 text-xs font-semibold tracking-wide text-neutral-500">SOCCER</p>
          <div className="mt-2 space-y-2">
            <Link
              href="/soccer/chat"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              채팅
            </Link>
          </div>
          <p className="mt-6 text-xs font-semibold tracking-wide text-neutral-500">LANGCHAIN</p>
          <div className="mt-2 space-y-2">
            <Link
              href="/langchain/chat"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              채팅
            </Link>
          </div>
        </aside>

        <section className="rounded-xl border border-neutral-200 bg-white p-6 md:p-8 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">MEDIA</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            S3 사진 OCR
          </h1>
          <p className="mt-5 max-w-3xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            susu(모바일) 카메라로 찍어 S3에 올린 내 사진을 불러와, Gemini로 사진 속
            텍스트를 추출해서 함께 보여줍니다.
          </p>

          <div className="mt-8">
            <LessonPhotosBody scan={scan} />
          </div>
        </section>
      </main>
    </div>
  )
}

function LessonPhotosBody({ scan }: { scan: ScanState }) {
  if (scan.status === "loading") {
    return <p className="text-sm text-neutral-500 dark:text-neutral-400">불러오는 중...</p>
  }
  if (scan.status === "error") {
    return <p className="text-sm text-red-600 dark:text-red-400">{scan.message}</p>
  }
  if (scan.items.length === 0) {
    return (
      <p className="text-sm text-neutral-500 dark:text-neutral-400">
        아직 S3에 올라온 사진이 없습니다. susu 앱 카메라로 사진을 올려보세요.
      </p>
    )
  }
  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
      {scan.items.map((item) => (
        <figure
          key={item.image_url}
          className="overflow-hidden rounded-xl border border-neutral-200 dark:border-[#252b3b]"
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- presigned S3 URL, next/image remotePatterns 설정 불필요한 범위 */}
          <img src={item.image_url} alt="" className="h-56 w-full object-cover" />
          <figcaption className="whitespace-pre-wrap p-3 text-sm text-neutral-700 dark:text-neutral-300">
            {item.extracted_text || "(텍스트 없음)"}
          </figcaption>
        </figure>
      ))}
    </div>
  )
}
