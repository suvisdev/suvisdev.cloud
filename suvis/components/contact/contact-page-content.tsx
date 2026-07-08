"use client"

import Link from "next/link"
import { ArrowUpRight, Mail, MapPin, Clock, Instagram } from "lucide-react"
import { useEffect, useState } from "react"
import { CONTACT_PROFILE } from "@/lib/contact-profile"
import { getSuvisSession, type SuvisSession } from "@/lib/suvis-session"

export function ContactPageContent() {
  const [session, setSession] = useState<SuvisSession | null>(null)

  useEffect(() => {
    setSession(getSuvisSession())
  }, [])

  const p = CONTACT_PROFILE

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#e8e8e8] px-4 pb-8 pt-0 dark:bg-[#0d0f14] md:px-6 md:pb-10">
      <main className="mx-auto max-w-3xl py-8 md:py-12">
        <Link
          href="/"
          className="text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100"
        >
          ← 홈
        </Link>

        {session && (
          <section
            className="mt-6 rounded-2xl border border-[#f0dc3a]/60 bg-[#fffef5] px-5 py-4 shadow-sm dark:border-[#f0dc3a]/20 dark:bg-[#1a1a0a]"
            aria-label="로그인 회원 정보"
          >
            <p className="text-xs font-semibold tracking-wide text-neutral-500 dark:text-neutral-500 uppercase">
              내 계정
            </p>
            <p className="mt-1 text-lg font-bold text-neutral-900 dark:text-neutral-100">{session.username}</p>
            <p className="mt-0.5 text-sm text-neutral-600 dark:text-neutral-400">
              회원 ID {session.id} · Suvisdev·Mova 서비스에 로그인된 상태입니다.
            </p>
          </section>
        )}

        <header id="about" className="mt-8 scroll-mt-24 md:mt-10">
          <p className="text-sm font-medium tracking-[0.2em] text-neutral-500 dark:text-neutral-500 uppercase">
            About
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 md:text-4xl">
            {p.brand}
          </h1>
          <p className="mt-2 text-base font-medium text-neutral-700 dark:text-neutral-300">{p.role}</p>
        </header>

        <section className="mt-8 space-y-6 rounded-3xl border border-neutral-300/80 bg-white px-6 py-8 shadow-sm dark:border-[#252b3b] dark:bg-[#161a24] sm:px-10 sm:py-10">
          <div className="space-y-2">
            <p className="text-lg font-semibold leading-snug text-neutral-900 dark:text-neutral-100">
              {p.taglineKo}
            </p>
            <p className="font-display text-sm font-bold tracking-wide text-neutral-500 dark:text-neutral-500 uppercase">
              {p.taglineEn}
            </p>
          </div>

          <hr className="border-neutral-200 dark:border-[#252b3b]" />

          <p className="text-pretty text-sm leading-relaxed text-neutral-700 dark:text-neutral-300 sm:text-[0.9375rem] sm:leading-[1.75]">
            {p.summary}
          </p>

          <div>
            <h2 className="text-sm font-bold text-neutral-900 dark:text-neutral-100">주요 영역</h2>
            <ul className="mt-3 space-y-2">
              {p.focusAreas.map((item) => (
                <li
                  key={item}
                  className="flex gap-2 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300"
                >
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-neutral-400 dark:bg-neutral-600" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="text-sm font-bold text-neutral-900 dark:text-neutral-100">프로젝트</h2>
            <ul className="mt-3 space-y-3">
              {p.projects.map((project) => (
                <li key={project.href}>
                  <Link
                    href={project.href}
                    className="group inline-flex items-center gap-1 text-sm font-semibold text-neutral-900 transition-colors hover:text-neutral-600 dark:text-neutral-100 dark:hover:text-neutral-400"
                  >
                    {project.name}
                    <ArrowUpRight
                      className="h-4 w-4 opacity-70 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                      aria-hidden
                    />
                  </Link>
                  <p className="mt-0.5 text-sm text-neutral-600 dark:text-neutral-400">{project.description}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section
          id="contact"
          className="mt-6 scroll-mt-24 rounded-3xl border border-neutral-300/80 bg-white px-6 py-8 shadow-sm dark:border-[#252b3b] dark:bg-[#161a24] sm:px-10 sm:py-10"
        >
          <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-100">연락처</h2>
          <ul className="mt-5 space-y-4">
            <li className="flex gap-3 text-sm text-neutral-700 dark:text-neutral-300">
              <Mail className="mt-0.5 h-5 w-5 shrink-0 text-neutral-800 dark:text-neutral-400" aria-hidden />
              <div>
                <p className="font-medium text-neutral-900 dark:text-neutral-100">이메일</p>
                <a
                  href={`mailto:${p.email}`}
                  className="mt-0.5 inline-block text-neutral-700 underline-offset-2 hover:text-neutral-900 hover:underline dark:text-neutral-400 dark:hover:text-neutral-200"
                >
                  {p.email}
                </a>
              </div>
            </li>
            <li className="flex gap-3 text-sm text-neutral-700 dark:text-neutral-300">
              <Clock className="mt-0.5 h-5 w-5 shrink-0 text-neutral-800 dark:text-neutral-400" aria-hidden />
              <div>
                <p className="font-medium text-neutral-900 dark:text-neutral-100">문의 시간</p>
                <p className="mt-0.5">{p.inquiryHours}</p>
              </div>
            </li>
            <li className="flex gap-3 text-sm text-neutral-700 dark:text-neutral-300">
              <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-neutral-800 dark:text-neutral-400" aria-hidden />
              <div>
                <p className="font-medium text-neutral-900 dark:text-neutral-100">위치</p>
                <p className="mt-0.5">{p.location}</p>
              </div>
            </li>
            <li className="flex gap-3 text-sm text-neutral-700 dark:text-neutral-300">
              <Instagram className="mt-0.5 h-5 w-5 shrink-0 text-neutral-800 dark:text-neutral-400" aria-hidden />
              <div>
                <p className="font-medium text-neutral-900 dark:text-neutral-100">인스타그램</p>
                <a
                  href={`https://instagram.com/${p.instagram}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-0.5 inline-block text-neutral-700 underline-offset-2 hover:text-neutral-900 hover:underline dark:text-neutral-400 dark:hover:text-neutral-200"
                >
                  @{p.instagram}
                </a>
              </div>
            </li>
            <li className="flex gap-3 text-sm text-neutral-700 dark:text-neutral-300">
              <svg className="mt-0.5 h-5 w-5 shrink-0 text-neutral-800 dark:text-neutral-400" fill="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
              <div>
                <p className="font-medium text-neutral-900 dark:text-neutral-100">X</p>
                <a
                  href={`https://x.com/${p.x}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-0.5 inline-block text-neutral-700 underline-offset-2 hover:text-neutral-900 hover:underline dark:text-neutral-400 dark:hover:text-neutral-200"
                >
                  @{p.x}
                </a>
              </div>
            </li>
          </ul>

          <Link
            href={`mailto:${p.email}`}
            className="mt-8 inline-flex w-full items-center justify-center rounded-2xl bg-[#f0dc3a] px-8 py-4 text-base font-bold text-neutral-900 shadow-sm transition-colors hover:bg-[#e8d020] sm:w-fit"
          >
            메일로 문의하기
          </Link>
        </section>
      </main>
    </div>
  )
}
