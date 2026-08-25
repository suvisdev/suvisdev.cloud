"use client"

import { useState, useEffect, useRef } from "react"
import { User, FolderKanban, Layers, GraduationCap, Mail, Github, Globe } from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { id: "about", label: "ABOUT", icon: User },
  { id: "projects", label: "PROJECTS", icon: FolderKanban },
  { id: "techstack", label: "TECH STACK", icon: Layers },
  { id: "education", label: "EDUCATION", icon: GraduationCap },
  { id: "contact", label: "CONTACT", icon: Mail },
] as const

const TECH_STACK = [
  {
    category: "CORE LANGUAGE",
    items: ["Python", "TypeScript", "Dart"],
  },
  {
    category: "AI · ML",
    items: ["EXAONE (LoRA/QLoRA)", "Gemini API", "LangChain", "Hugging Face Transformers", "PEFT · AWQ", "pgvector"],
  },
  {
    category: "BACKEND",
    items: ["FastAPI", "SQLAlchemy", "Alembic", "PostgreSQL", "Redis", "JWT · OAuth 2.0"],
  },
  {
    category: "FRONTEND",
    items: ["Next.js (App Router)", "React 19", "Tailwind CSS", "shadcn/ui", "Leaflet"],
  },
  {
    category: "MOBILE",
    items: ["Flutter", "Kakao SDK", "Dio"],
  },
  {
    category: "INFRA · DEVOPS",
    items: ["Docker", "AWS EC2 · S3", "Cloudflare Tunnel", "nginx", "GitHub Actions", "Vercel"],
  },
  {
    category: "DATA",
    items: ["OSM (osmnx)", "TMDB API", "KOFIC API", "Overpass API", "KOBIS"],
  },
]

const PROJECTS = [
  {
    name: "Mova",
    desc: "AI 영화 추천 플랫폼",
    detail: "LoRA(EXAONE-2.4B AWQ) + Gemini 듀얼 백엔드 개인화 추천, AI 리뷰 자동 생성, 박스오피스 랭킹, 영화 AI 챗봇",
    tech: ["FastAPI", "Next.js", "EXAONE LoRA", "Gemini", "PostgreSQL", "pgvector"],
    link: "https://suvisdev.cloud/mova",
  },
  {
    name: "Gildle",
    desc: "반려견 산책 경로 추천",
    detail: "OSM 233,964 edges 보행 그래프 + 3축 환경 점수(나무 그늘·결빙 위험·반려견 친화) 기반 최적 경로",
    tech: ["FastAPI", "OSM/osmnx", "Leaflet", "Next.js", "Overpass API"],
    link: "https://suvisdev.cloud/gildle",
  },
  {
    name: "suvisdev.cloud",
    desc: "모듈러 모놀리식 풀스택 플랫폼",
    detail: "Clean Architecture + Star Topology 기반 통합 플랫폼. 소셜 로그인(Google·Kakao·Naver), RBAC 어드민, 방문자 통계",
    tech: ["FastAPI", "Next.js", "Flutter", "Docker", "AWS", "Cloudflare"],
    link: "https://suvisdev.cloud",
  },
]

export function ResumeContent() {
  const [activeSection, setActiveSection] = useState("about")
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({})

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id)
          }
        }
      },
      { rootMargin: "-20% 0px -60% 0px" }
    )

    for (const item of NAV_ITEMS) {
      const el = sectionRefs.current[item.id]
      if (el) observer.observe(el)
    }

    return () => observer.disconnect()
  }, [])

  const scrollTo = (id: string) => {
    sectionRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-[1200px] gap-0 md:gap-12 lg:gap-16">
      {/* LEFT SIDEBAR */}
      <aside className="hidden w-[280px] shrink-0 md:block">
        <div className="sticky top-20 space-y-8">
          <div>
            <h1 className="text-4xl font-black tracking-tight text-neutral-100">
              Your Name
            </h1>
            <p className="mt-2 text-sm font-semibold uppercase tracking-[0.25em] text-emerald-400">
              Full-Stack Developer
            </p>
            <p className="mt-3 text-sm italic text-neutral-500">
              &quot;코드로 문제를 해결하는 개발자&quot;
            </p>
          </div>

          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  onClick={() => scrollTo(item.id)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-semibold tracking-wide transition-all",
                    activeSection === item.id
                      ? "border-l-2 border-emerald-400 bg-emerald-400/10 text-emerald-400"
                      : "text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              )
            })}
          </nav>

          <div className="space-y-3 border-t border-neutral-800 pt-6 text-sm text-neutral-500">
            <a href="mailto:ssuvisdev@gmail.com" className="flex items-center gap-3 transition-colors hover:text-emerald-400">
              <Mail className="h-4 w-4" /> ssuvisdev@gmail.com
            </a>
            <a href="https://github.com/suvisdev" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 transition-colors hover:text-emerald-400">
              <Github className="h-4 w-4" /> github.com/suvisdev
            </a>
            <a href="https://suvisdev.cloud" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 transition-colors hover:text-emerald-400">
              <Globe className="h-4 w-4" /> suvisdev.cloud
            </a>
          </div>
        </div>
      </aside>

      {/* MOBILE HEADER */}
      <div className="mb-6 w-full border-b border-neutral-800 pb-6 md:hidden">
        <h1 className="text-3xl font-black tracking-tight text-neutral-100">Your Name</h1>
        <p className="mt-1 text-sm font-semibold uppercase tracking-[0.25em] text-emerald-400">
          Full-Stack Developer
        </p>
        <p className="mt-2 text-sm italic text-neutral-500">&quot;코드로 문제를 해결하는 개발자&quot;</p>
      </div>

      {/* RIGHT CONTENT */}
      <main className="min-w-0 flex-1 space-y-20 pb-32">
        {/* ABOUT */}
        <section id="about" ref={(el) => { sectionRefs.current.about = el }}>
          <SectionHeader num="01" title="About" />
          <div className="mt-6 space-y-4 text-[15px] leading-relaxed text-neutral-300">
            <p>
              AI 영화 추천, 보행 경로 최적화, 모바일 앱까지 — 하나의 모듈러 모놀리식
              아키텍처 위에서 기획부터 배포까지 전 과정을 개인 프로젝트로 수행했습니다.
            </p>
            <p>
              LoRA 파인튜닝과 Gemini API를 활용한 AI 파이프라인 구축, Clean Architecture
              기반의 FastAPI 백엔드, Next.js + Flutter 멀티플랫폼 프론트엔드를 설계·구현하고
              AWS EC2 + Docker로 운영 중입니다.
            </p>
            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
              <StatCard label="개발 기간" value="10주" />
              <StatCard label="백엔드 테스트" value="550+" />
              <StatCard label="보행 그래프" value="233K edges" />
            </div>
          </div>
        </section>

        {/* PROJECTS */}
        <section id="projects" ref={(el) => { sectionRefs.current.projects = el }}>
          <SectionHeader num="02" title="Projects" />
          <div className="mt-6 space-y-6">
            {PROJECTS.map((p) => (
              <a
                key={p.name}
                href={p.link}
                target="_blank"
                rel="noopener noreferrer"
                className="group block rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 transition-all hover:border-emerald-400/40 hover:bg-emerald-400/5"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-neutral-100 group-hover:text-emerald-400">
                      {p.name}
                    </h3>
                    <p className="mt-0.5 text-sm text-neutral-400">{p.desc}</p>
                  </div>
                  <Globe className="h-4 w-4 shrink-0 text-neutral-600 transition-colors group-hover:text-emerald-400" />
                </div>
                <p className="mt-3 text-sm leading-relaxed text-neutral-400">{p.detail}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {p.tech.map((t) => (
                    <Badge key={t}>{t}</Badge>
                  ))}
                </div>
              </a>
            ))}
          </div>
        </section>

        {/* TECH STACK */}
        <section id="techstack" ref={(el) => { sectionRefs.current.techstack = el }}>
          <SectionHeader num="03" title="Tech Stack" />
          <div className="mt-6 space-y-8">
            {TECH_STACK.map((group) => (
              <div key={group.category}>
                <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">
                  {group.category}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {group.items.map((item) => (
                    <Badge key={item}>{item}</Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* EDUCATION */}
        <section id="education" ref={(el) => { sectionRefs.current.education = el }}>
          <SectionHeader num="04" title="Education" />
          <div className="mt-6 space-y-6">
            <TimelineItem
              period="2026.07 — 2026.10"
              title="SEUK 풀스택 AI 개발 과정"
              desc="Python · FastAPI · Next.js · Flutter · AI/ML 파이프라인 구축"
            />
            <TimelineItem
              period=""
              title="학력 정보를 입력해주세요"
              desc="플레이스홀더"
            />
          </div>
        </section>

        {/* CONTACT */}
        <section id="contact" ref={(el) => { sectionRefs.current.contact = el }}>
          <SectionHeader num="05" title="Contact" />
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <ContactCard icon={Mail} label="Email" value="ssuvisdev@gmail.com" href="mailto:ssuvisdev@gmail.com" />
            <ContactCard icon={Github} label="GitHub" value="suvisdev" href="https://github.com/suvisdev" />
            <ContactCard icon={Globe} label="Portfolio" value="suvisdev.cloud" href="https://suvisdev.cloud" />
            <ContactCard icon={Globe} label="Blog" value="jk.suvisdev.cloud" href="https://jk.suvisdev.cloud" />
          </div>
        </section>
      </main>
    </div>
  )
}

function SectionHeader({ num, title }: { num: string; title: string }) {
  return (
    <div className="flex items-baseline gap-3 border-b border-neutral-800 pb-4">
      <span className="text-sm font-bold text-emerald-400">{num}.</span>
      <h2 className="text-2xl font-bold text-neutral-100">{title}</h2>
    </div>
  )
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-neutral-700 bg-neutral-800/60 px-3 py-1 text-sm text-neutral-300 transition-colors hover:border-emerald-400/50 hover:text-emerald-400">
      {children}
    </span>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 px-4 py-3 text-center">
      <p className="text-lg font-bold text-emerald-400">{value}</p>
      <p className="mt-0.5 text-xs text-neutral-500">{label}</p>
    </div>
  )
}

function TimelineItem({ period, title, desc }: { period: string; title: string; desc: string }) {
  return (
    <div className="relative border-l-2 border-neutral-800 pl-5">
      <div className="absolute -left-[5px] top-1.5 h-2 w-2 rounded-full bg-emerald-400" />
      {period && <p className="text-xs font-medium text-emerald-400">{period}</p>}
      <h3 className="mt-1 font-semibold text-neutral-200">{title}</h3>
      <p className="mt-0.5 text-sm text-neutral-500">{desc}</p>
    </div>
  )
}

function ContactCard({ icon: Icon, label, value, href }: { icon: typeof Mail; label: string; value: string; href: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-4 rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 transition-all hover:border-emerald-400/40 hover:bg-emerald-400/5"
    >
      <Icon className="h-5 w-5 text-emerald-400" />
      <div>
        <p className="text-xs text-neutral-500">{label}</p>
        <p className="text-sm font-medium text-neutral-200">{value}</p>
      </div>
    </a>
  )
}
