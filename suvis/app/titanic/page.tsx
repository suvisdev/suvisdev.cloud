"use client"

import Link from "next/link"
import { BarChart3, Bot, Database, Ship } from "lucide-react"

export default function TitanicHomePage() {
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
              className="block rounded-md bg-neutral-100 px-3 py-2 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-200 dark:bg-[#252b3b] dark:text-neutral-100 dark:hover:bg-[#2d3447]"
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
        </aside>

        <section className="rounded-xl border border-neutral-200 bg-white p-6 md:p-8 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">LESSON</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            타이타닉 모델 분석
          </h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            역사 속 가장 유명한 해상사고인 타이타닉 침몰 사건을 데이터 분석을 통해 살펴봅니다.
            머신러닝 모델을 활용하여 승객의 생존 확률을 예측하는 방법을 배웁니다.
          </p>

          <div className="mt-8 grid gap-4 lg:grid-cols-[1fr_240px]">
            <article className="rounded-xl border border-neutral-200 bg-neutral-50 p-6 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
              <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
                학습 목표
              </h2>
              <ul className="mt-4 space-y-2 text-sm leading-7 text-neutral-700 dark:text-neutral-300">
                <li>• 데이터 수집 및 전처리 기술 습득</li>
                <li>• 탐색적 데이터 분석(EDA) 실습</li>
                <li>• 분류 모델 개발 및 성능 평가</li>
                <li>• 실제 데이터 기반 인사이트 도출</li>
              </ul>

              <h3 className="mt-8 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                주요 내용
              </h3>
              <ul className="mt-4 space-y-2 text-sm leading-7 text-neutral-700 dark:text-neutral-300">
                <li>• 타이타닉 탑승객 데이터셋 분석</li>
                <li>• 성별, 연령, 좌석 등급에 따른 생존율 분석</li>
                <li>• 로지스틱 회귀 모델을 이용한 생존 예측</li>
                <li>• 모델 성능 평가 및 해석</li>
              </ul>
            </article>

            <aside className="rounded-xl border border-neutral-200 bg-neutral-50 p-5 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
              <div className="space-y-5 text-center text-neutral-700 dark:text-neutral-300">
                <div>
                  <Ship className="mx-auto size-8 text-sky-500" />
                  <p className="mt-2 font-semibold">Titanic</p>
                  <p className="text-xs text-neutral-500">1912년 침몰</p>
                  <p className="text-xs text-neutral-500">1,500명 이상 사망</p>
                </div>
                <div>
                  <Database className="mx-auto size-7 text-violet-500" />
                  <p className="mt-1 text-sm">2,224명 탑승객</p>
                </div>
                <div>
                  <BarChart3 className="mx-auto size-7 text-teal-500" />
                  <p className="mt-1 text-sm">데이터 분석</p>
                </div>
                <div>
                  <Bot className="mx-auto size-7 text-rose-500" />
                  <p className="mt-1 text-sm">머신러닝 모델</p>
                </div>
              </div>
            </aside>
          </div>

          <article className="mt-6 rounded-xl border border-neutral-200 bg-neutral-50 p-5 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
            <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              2. 승객목록
            </h2>
            <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              업로드된 승객 데이터를 페이지당 50명 단위로 조회합니다.
            </p>
            <Link
              href="/titanic/passengers"
              className="mt-4 inline-block rounded-md bg-white px-4 py-2 text-sm font-medium text-neutral-800 ring-1 ring-neutral-200 transition-colors hover:bg-neutral-100 dark:bg-[#252b3b] dark:text-neutral-200 dark:ring-[#2d3447] dark:hover:bg-[#2d3447]"
            >
              승객목록 페이지로 이동
            </Link>
          </article>
        </section>
      </main>
    </div>
  )
}
