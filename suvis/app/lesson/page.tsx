"use client"

import Link from "next/link"

export default function LessonHomePage() {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#f3f3f3] px-4 py-4 md:px-6 md:py-6 dark:bg-[#0d0f14]">
      <main className="mx-auto grid max-w-[1500px] gap-4 md:grid-cols-[220px_1fr]">
        <aside className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-wide text-neutral-500">수업명</p>
          <div className="mt-4 space-y-2">
            <Link
              href="/lesson"
              className="block rounded-md bg-neutral-100 px-3 py-2 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-200 dark:bg-[#252b3b] dark:text-neutral-100 dark:hover:bg-[#2d3447]"
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
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
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
          <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">LESSON</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            분석 자료 홈
          </h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            좌측 메뉴에서 수업을 선택하면 바로 해당 분석 페이지로 이동합니다. 지금은 타이타닉 수업이
            연결되어 있습니다.
          </p>

          <div className="mt-8 rounded-xl border border-neutral-200 bg-neutral-50 p-6 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
            <Link
              href="/titanic"
              className="text-lg font-semibold text-neutral-900 hover:underline dark:text-neutral-100"
            >
              타이타닉
            </Link>
            <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              승객 데이터 기반 생존 분석 수업
            </p>
            <div className="mt-4 flex gap-3">
              <Link
                href="/titanic/data-collection"
                className="rounded-md bg-white px-4 py-2 text-sm font-medium text-neutral-800 ring-1 ring-neutral-200 transition-colors hover:bg-neutral-100 dark:bg-[#252b3b] dark:text-neutral-200 dark:ring-[#2d3447] dark:hover:bg-[#2d3447]"
              >
                데이터 수집 보기
              </Link>
              <Link
                href="/titanic/passengers"
                className="rounded-md bg-white px-4 py-2 text-sm font-medium text-neutral-800 ring-1 ring-neutral-200 transition-colors hover:bg-neutral-100 dark:bg-[#252b3b] dark:text-neutral-200 dark:ring-[#2d3447] dark:hover:bg-[#2d3447]"
              >
                승객목록 보기
              </Link>
            </div>
          </div>

          <div className="mt-4 rounded-xl border border-neutral-200 bg-neutral-50 p-6 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
            <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">VISION</p>
            <Link
              href="/vision"
              className="mt-2 block text-lg font-semibold text-neutral-900 hover:underline dark:text-neutral-100"
            >
              이미지 업로드
            </Link>
            <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              JPG·PNG 이미지를 업로드해 DB에 저장하는 도구
            </p>
            <div className="mt-4 flex gap-3">
              <Link
                href="/vision"
                className="rounded-md bg-white px-4 py-2 text-sm font-medium text-neutral-800 ring-1 ring-neutral-200 transition-colors hover:bg-neutral-100 dark:bg-[#252b3b] dark:text-neutral-200 dark:ring-[#2d3447] dark:hover:bg-[#2d3447]"
              >
                이미지 업로드
              </Link>
            </div>
          </div>

          <div className="mt-4 rounded-xl border border-neutral-200 bg-neutral-50 p-6 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
            <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">MEDIA</p>
            <Link
              href="/lesson/photos"
              className="mt-2 block text-lg font-semibold text-neutral-900 hover:underline dark:text-neutral-100"
            >
              S3 사진 OCR
            </Link>
            <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              susu 카메라로 S3에 올린 전체 사용자 사진을 불러와 Gemini로 텍스트를 추출하는 도구
            </p>
            <div className="mt-4 flex gap-3">
              <Link
                href="/lesson/photos"
                className="rounded-md bg-white px-4 py-2 text-sm font-medium text-neutral-800 ring-1 ring-neutral-200 transition-colors hover:bg-neutral-100 dark:bg-[#252b3b] dark:text-neutral-200 dark:ring-[#2d3447] dark:hover:bg-[#2d3447]"
              >
                S3 사진 OCR 보기
              </Link>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}
