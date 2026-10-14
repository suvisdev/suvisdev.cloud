"use client"

import { useState, useEffect, useRef } from "react"
import { User, Trophy, FolderKanban, Layers, GraduationCap, Mail, Github, Globe, Phone } from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { id: "about", label: "ABOUT", icon: User },
  { id: "experience", label: "EXPERIENCE", icon: Trophy },
  { id: "projects", label: "PROJECTS", icon: FolderKanban },
  { id: "techstack", label: "TECH STACK", icon: Layers },
  { id: "education", label: "EDUCATION", icon: GraduationCap },
  { id: "contact", label: "CONTACT", icon: Mail },
] as const

// 끝줄에 한두 글자만 남지 않게 마지막 두 어절을 줄바꿈 없는 공백으로 묶는다(둘이 4글자 이하면 세 어절).
function glue(text: string) {
  const words = text.split(" ")
  const n = words.slice(-2).join("").length <= 4 ? 3 : 2
  if (words.length <= n) return text
  return `${words.slice(0, -n).join(" ")} ${words.slice(-n).join(" ")}`
}

const ROLE = "AI Engineer"
const HEADLINE = "LLM 에이전트와 AI 서비스를 직접 개발하고 운영하는 AI 엔지니어"

// 문구와 수치는 PDF 이력서 v18(2026-10-13)과 같게 둔다. 한쪽만 고치면 서로 어긋난다.
const STRENGTHS = [
  {
    label: "LLM 에이전트",
    text: "Claude Tool Calling으로 채용 에이전트 도구 12종을 구현하고, 데이터를 바꾸는 작업 5종은 담당자 승인 뒤에만 실행되게 설계",
  },
  {
    label: "모델 학습과 평가",
    text: "EXAONE 2.4B를 파인튜닝해 도구 선택 정확도 83% → 94%(평가 66건), Qwen3-8B는 도구 호출 평가 23건에서 Claude Haiku 4.5와 같은 정답 수",
  },
  {
    label: "서빙과 운영",
    text: "개인 서비스를 k3s 서버 2대로 이중화해 노트북이 꺼지면 약 31초 뒤 자택 서버가 API를 이어받게 하고, GPU 추론을 두 서버에 나눠 AWS 서버 없이 운영",
  },
  {
    label: "팀 프로젝트 리딩",
    text: "4인 팀 팀장, 원티드 AI Championship 2026 본선 진출(참가 1,300여 팀 중 TOP 20)",
  },
]

const EXPERIENCE = [
  {
    period: "2026.10",
    title: "원티드 AI Championship 2026 본선 진출(참가 1,300여 팀 중 TOP 20)",
    desc: "참가작 공개 투표 1위(2026.10.05 기준), 4인 팀 팀장으로 팀 프로젝트 Arda 출품",
  },
]

const TECH_STACK = [
  { category: "LLM 에이전트", items: ["Claude API", "Tool Calling"], usage: "에이전트 도구 12종, 쓰기 작업 승인 카드, 규칙 라우터" },
  { category: "모델 학습", items: ["QLoRA", "LoRA"], usage: "Qwen3-8B, EXAONE 2.4B 파인튜닝, 라벨 마스킹" },
  { category: "평가", items: ["자동 채점기", "Recall@8"], usage: "Qwen과 Claude 비교, 평가셋 66건, 임베딩 3종 비교" },
  { category: "RAG와 체인", items: ["pgvector", "bge-m3"], usage: "시맨틱 검색, 3단 프롬프트 체인(요약, 평가, 추천)" },
  { category: "서빙", items: ["Ollama", "llama.cpp", "HAProxy"], usage: "GGUF 로컬 서빙, GPU 추론 중계, 비전 모델 MCP 서버" },
  { category: "백엔드", items: ["Python", "FastAPI", "PostgreSQL"], usage: "채용 시스템 API, 1인 모듈러 모놀리식 백엔드" },
  { category: "인프라", items: ["Docker", "k3s", "AWS", "GitHub Actions"], usage: "자동 배포, 서버 2대 자동 전환, PC 3대 온프레미스" },
  { category: "프론트와 앱", items: ["React", "Next.js", "TypeScript", "Flutter"], usage: "웹 화면, Android 앱(Google Play 내부 테스트)" },
]

const PROJECTS = [
  {
    name: "Arda (Eval-ATS)",
    desc: "AI 기반 채용 프로세스 자동화 및 지원자 통합 관리 플랫폼",
    meta: ["IBM x Red Hat AI 과정 팀 프로젝트(4인)", "2026.08 ~ 2026.10", "에이전트 담당(08.24~)에서 팀장 겸 인프라 총괄(09.04~)"],
    overview:
      "채용 과정의 반복 업무를 자동화하고 흩어진 지원자 정보를 한 플랫폼으로 모아, 채용 담당자가 '지원자라는 사람'에 집중할 수 있게 하는 시스템",
    results: [
      { label: "Claude Haiku 4.5와 같은 정답 수", text: "Qwen3-8B를 파인튜닝해 도구 호출 평가 23건 중 17건(73.9%)" },
      { label: "온프레미스 시연", text: "AWS 의존을 낮추려고 로컬 모델로 바꿔 컴퓨터 3대로 시연과 점검까지 직접 운영" },
      { label: "AI 면접 기능 구현", text: "음성 인식과 팀원이 학습한 표정 ViT를 실시간 화상 면접에 연결" },
    ],
    points: [
      "담당자가 채팅으로 지원자 검색, 단계 변경, 면접관 배정을 시킬 수 있는 에이전트 '아르'의 도구 12종을 만들고, 데이터를 바꾸는 작업은 확인 카드로 승인받게 함",
      "Qwen3-8B를 QLoRA로 파인튜닝하며, 긴 시스템 프롬프트에 손실이 쏠리던 문제를 답변 부분만 학습하게(라벨 마스킹) 바꿔 해결하고, Claude와 같은 평가 23건으로 비교함",
      "지원서를 요약, 평가, 추천 체인으로 읽어 공고 기준 100점으로 채점하고 서류 단계를 자동 판정함",
      "클린 아키텍처 중 필요한 부분만 골라 헥사고날 구조로 재편해, 모델 파일 하나를 71개 파일이 불러 쓰던 백엔드를 업무 단위 4개로 나누고 고칠 범위를 좁힘(PR 20개)",
      "팀장을 맡은 뒤 전임 팀장 계정의 AWS를 본인 계정으로 옮기고 권한을 역할별로 나눴으며, 자동 배포와 매일 DB 백업, 알람 6종을 갖춤",
    ],
    tech: ["Python", "FastAPI", "PostgreSQL(pgvector)", "Claude API", "Qwen3-8B(QLoRA)", "Ollama", "Docker", "AWS", "React", "Flutter"],
    links: [
      { label: "서비스", href: "https://seuk.suvisdev.cloud" },
      { label: "GitHub", href: "https://github.com/Seuk-Team/Arda" },
      { label: "기술 문서", href: "https://ats.suvisdev.cloud" },
    ],
  },
  {
    name: "suvisdev.cloud",
    desc: "AI 영화 추천(Mova)과 반려견 산책 경로(Gildle) 통합 플랫폼",
    meta: ["개인 프로젝트(1인)", "2026.07 ~ 현재", "풀스택 개발, ML 파이프라인, 인프라, 데이터 수집"],
    overview:
      "좋아하는 영화와 반려견 산책에 AI를 붙여, 대화로 영화를 찾고 그늘진 산책 길을 추천받는 서비스를 기획부터 운영까지 혼자 만든 플랫폼(현재 개인 운영과 내부 테스트 단계)",
    results: [
      { label: "도구 선택 정확도 83% → 94%", text: "EXAONE 2.4B 파인튜닝 전후, 평가 66건 기준(프롬프트만 쓴 7.8B는 89%)" },
      { label: "영화 검색 적중률 39% → 86%", text: "임베딩 모델을 바꿔, 질문 60개에서 찾는 영화가 검색 결과 상위 8개 안에 드는 비율(Recall@8)을 높임" },
      { label: "AWS EC2 사용액 월 약 70달러 절감", text: "백엔드를 노트북과 자택 서버로 옮겨 GPU 추론까지 직접 운영" },
      { label: "서버 2대 이중화", text: "노트북이 꺼져도 약 31초 뒤 자택 서버가 API를 이어받음(노트북을 끄는 시험으로 확인)" },
    ],
    points: [
      "EXAONE 2.4B를 LoRA로 파인튜닝해 영화 채팅에서 다음에 쓸 도구 하나만 고르게 하고, 출연진, 상영 시간표 같은 사실은 코드가 답하게 나눠 모델이 지어내지 못하게 함",
      "임베딩 모델 3종을 영화 205편, 질문 60개로 직접 비교해 가장 잘 찾는 bge-m3로 바꾸고 검색 데이터를 다시 만듦(2,965건)",
      "서울 보행로 약 23만 구간에 건물 약 80만 동의 그림자를 달마다, 시간대마다 미리 계산해 그늘진 산책 길을 찾아 줌",
      "노트북(GPU)과 자택 서버 두 대를 Cloudflare Tunnel로 묶어 노트북이 꺼지면 자택 서버가 넘겨받게 하고, Ollama 추론은 노트북 GPU로 먼저 보냄",
    ],
    tech: ["FastAPI", "PostgreSQL(pgvector)", "Redis", "EXAONE 3.5(LoRA)", "Gemini", "Ollama", "llama.cpp", "Next.js", "Flutter", "k3s"],
    links: [
      { label: "서비스", href: "https://suvisdev.cloud" },
      { label: "Mova", href: "https://suvisdev.cloud/mova" },
      { label: "Gildle", href: "https://suvisdev.cloud/gildle" },
      { label: "GitHub", href: "https://github.com/suvisdev/suvisdev.cloud" },
      { label: "기술 문서", href: "https://jk.suvisdev.cloud" },
    ],
  },
]

const EDUCATION = [
  {
    period: "2026.04 ~ 2026.10",
    title: "IBM x Red Hat AI Transformation AX Academy (대한상공회의소, 하이미디어)",
    desc: "팀 Seuk 팀장, 2026.10.27 수료 예정. 과정 내 실습 Red Hat OpenShift Administration I (DO180), 2026.08",
  },
  { period: "2020.06 ~ 2021.08", title: "모션랩학원 모션그래픽 과정", desc: "" },
  { period: "2009.03 ~ 2014.05", title: "경상대학교 건축공학과 중퇴", desc: "" },
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
    <div className="mx-auto flex min-h-screen max-w-[1200px] flex-col gap-0 md:flex-row md:gap-12 lg:gap-16">
      {/* LEFT SIDEBAR */}
      <aside className="hidden w-[280px] shrink-0 md:block">
        <div className="sticky top-20 space-y-8">
          <div>
            <h1 className="text-4xl font-black tracking-tight text-neutral-900">
              진수택
            </h1>
            <p className="mt-2 text-sm font-semibold uppercase tracking-[0.25em] text-amber-600">
              {ROLE}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-neutral-500 [word-break:keep-all]">
              {glue(HEADLINE)}
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
                      ? "border-l-2 border-amber-500 bg-amber-50 text-amber-600"
                      : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              )
            })}
          </nav>

          <div className="space-y-3 border-t border-neutral-200 pt-6 text-sm text-neutral-500">
            <a href="mailto:ssuvisdev@gmail.com" className="flex items-center gap-3 transition-colors hover:text-amber-600">
              <Mail className="h-4 w-4" /> ssuvisdev@gmail.com
            </a>
            <a href="https://github.com/suvisdev" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 transition-colors hover:text-amber-600">
              <Github className="h-4 w-4" /> github.com/suvisdev
            </a>
            <a href="https://suvisdev.cloud" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 transition-colors hover:text-amber-600">
              <Globe className="h-4 w-4" /> suvisdev.cloud
            </a>
          </div>
        </div>
      </aside>

      {/* MOBILE HEADER */}
      <div className="mb-6 w-full border-b border-neutral-200 pb-6 md:hidden">
        <h1 className="text-3xl font-black tracking-tight text-neutral-900">진수택</h1>
        <p className="mt-1 text-sm font-semibold uppercase tracking-[0.25em] text-amber-600">
          {ROLE}
        </p>
        <p className="mt-2 text-sm leading-relaxed text-neutral-500 [word-break:keep-all]">{glue(HEADLINE)}</p>
      </div>

      {/* RIGHT CONTENT */}
      <main className="min-w-0 flex-1 space-y-20 pb-32">
        {/* ABOUT */}
        <section id="about" ref={(el) => { sectionRefs.current.about = el }}>
          <SectionHeader num="01" title="About" />
          <dl className="mt-6 space-y-4 text-[15px] leading-relaxed [word-break:keep-all]">
            {STRENGTHS.map((s) => (
              <div key={s.label} className="sm:grid sm:grid-cols-[140px_1fr] sm:gap-4">
                <dt className="font-semibold text-neutral-800">{s.label}</dt>
                <dd className="mt-0.5 text-neutral-600 sm:mt-0">{glue(s.text)}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3">
            <StatCard label="원티드 AI Championship 2026 본선" value="TOP 20" />
            <StatCard label="도구 선택 정확도(평가 66건)" value="83% → 94%" />
            <StatCard label="노트북이 꺼질 때 자동 전환" value="약 31초" />
          </div>
        </section>

        {/* EXPERIENCE */}
        <section id="experience" ref={(el) => { sectionRefs.current.experience = el }}>
          <SectionHeader num="02" title="Experience" />
          <div className="mt-6 space-y-6">
            {EXPERIENCE.map((e) => (
              <TimelineItem key={e.title} period={e.period} title={glue(e.title)} desc={glue(e.desc)} />
            ))}
          </div>
        </section>

        {/* PROJECTS */}
        <section id="projects" ref={(el) => { sectionRefs.current.projects = el }}>
          <SectionHeader num="03" title="Projects" />
          <div className="mt-6 space-y-6">
            {PROJECTS.map((p) => (
              <article
                key={p.name}
                className="rounded-xl border border-neutral-200 bg-white p-5 [word-break:keep-all] transition-colors hover:border-amber-400"
              >
                <h3 className="text-lg font-bold text-neutral-900">{p.name}</h3>
                <p className="mt-0.5 text-sm text-neutral-500">{p.desc}</p>
                <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs font-medium text-amber-600">
                  {p.meta.map((m) => (
                    <span key={m}>{m}</span>
                  ))}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-neutral-600">{glue(p.overview)}</p>

                <h4 className="mt-4 text-xs font-bold tracking-wider text-neutral-400">성과</h4>
                <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-neutral-600">
                  {p.results.map((r) => (
                    <li key={r.label} className="relative pl-3.5 before:absolute before:left-0 before:top-[0.6em] before:h-1 before:w-1 before:rounded-full before:bg-amber-500">
                      <span className="font-semibold text-neutral-800">{r.label}</span>: {glue(r.text)}
                    </li>
                  ))}
                </ul>

                <h4 className="mt-4 text-xs font-bold tracking-wider text-neutral-400">주요 구현</h4>
                <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-neutral-600">
                  {p.points.map((pt) => (
                    <li key={pt} className="relative pl-3.5 before:absolute before:left-0 before:top-[0.6em] before:h-1 before:w-1 before:rounded-full before:bg-neutral-300">
                      {glue(pt)}
                    </li>
                  ))}
                </ul>

                <div className="mt-4 flex flex-wrap gap-2">
                  {p.tech.map((t) => (
                    <Badge key={t}>{t}</Badge>
                  ))}
                </div>

                <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 border-t border-neutral-100 pt-3 text-sm">
                  {p.links.map((l) => (
                    <a
                      key={l.href}
                      href={l.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-neutral-500 transition-colors hover:text-amber-600"
                    >
                      {l.label === "GitHub" ? <Github className="h-3.5 w-3.5" /> : <Globe className="h-3.5 w-3.5" />}
                      {l.label}
                    </a>
                  ))}
                </div>
              </article>
            ))}
            <p className="text-sm text-neutral-400">구현 과정과 수치 근거는 각 프로젝트의 기술 문서에 정리했습니다.</p>
          </div>
        </section>

        {/* TECH STACK */}
        <section id="techstack" ref={(el) => { sectionRefs.current.techstack = el }}>
          <SectionHeader num="04" title="Tech Stack" />
          <div className="mt-6 space-y-8">
            {TECH_STACK.map((group) => (
              <div key={group.category}>
                <h3 className="mb-3 text-xs font-bold tracking-wider text-neutral-400">
                  {group.category}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {group.items.map((item) => (
                    <Badge key={item}>{item}</Badge>
                  ))}
                </div>
                <p className="mt-2 text-sm text-neutral-500 [word-break:keep-all]">{glue(group.usage)}</p>
              </div>
            ))}
          </div>
        </section>

        {/* EDUCATION */}
        <section id="education" ref={(el) => { sectionRefs.current.education = el }}>
          <SectionHeader num="05" title="Education" />
          <div className="mt-6 space-y-6">
            {EDUCATION.map((e) => (
              <TimelineItem key={e.title} period={e.period} title={glue(e.title)} desc={glue(e.desc)} />
            ))}
          </div>
        </section>

        {/* CONTACT */}
        <section id="contact" ref={(el) => { sectionRefs.current.contact = el }}>
          <SectionHeader num="06" title="Contact" />
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <ContactCard icon={Phone} label="Phone" value="010-****-****" />
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
    <div className="flex items-baseline gap-3 border-b border-neutral-200 pb-4">
      <span className="text-sm font-bold text-amber-600">{num}.</span>
      <h2 className="text-2xl font-bold text-neutral-900">{title}</h2>
    </div>
  )
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-neutral-200 bg-neutral-100 px-3 py-1 text-sm text-neutral-600 transition-colors hover:border-amber-400 hover:text-amber-600">
      {children}
    </span>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3 text-center">
      <p className="text-lg font-bold text-amber-600">{value}</p>
      <p className="mt-0.5 text-xs text-neutral-400 [word-break:keep-all]">{label}</p>
    </div>
  )
}

function TimelineItem({ period, title, desc }: { period: string; title: string; desc: string }) {
  return (
    <div className="relative border-l-2 border-neutral-200 pl-5 [word-break:keep-all]">
      <div className="absolute -left-[5px] top-1.5 h-2 w-2 rounded-full bg-amber-500" />
      {period && <p className="text-xs font-medium text-amber-600">{period}</p>}
      <h3 className="mt-1 font-semibold text-neutral-800">{title}</h3>
      {desc && <p className="mt-0.5 text-sm text-neutral-500">{desc}</p>}
    </div>
  )
}

// 전화번호는 공개하지 않아 링크 없이 가린 번호만 보인다(예전 tel: 링크는 가짜 번호로 걸렸다).
function ContactCard({ icon: Icon, label, value, href }: { icon: typeof Mail; label: string; value: string; href?: string }) {
  const body = (
    <>
      <Icon className="h-5 w-5 text-amber-600" />
      <div>
        <p className="text-xs text-neutral-400">{label}</p>
        <p className="text-sm font-medium text-neutral-800">{value}</p>
      </div>
    </>
  )
  if (!href) {
    return <div className="flex items-center gap-4 rounded-xl border border-neutral-200 bg-neutral-50 p-4">{body}</div>
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-4 rounded-xl border border-neutral-200 bg-neutral-50 p-4 transition-all hover:border-amber-400 hover:bg-amber-50"
    >
      {body}
    </a>
  )
}
