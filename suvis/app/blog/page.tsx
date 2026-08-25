import type { Metadata } from "next"
import Link from "next/link"
import { ArrowLeft, BookOpen, Users } from "lucide-react"

export const metadata: Metadata = { title: "Blog — Suvisdev" }

const BLOGS = [
  {
    title: "개인 프로젝트",
    desc: "Mova · Gildle · 인프라 — 개인 풀스택 개발 기록",
    href: "https://jk.suvisdev.cloud",
    icon: BookOpen,
    tags: ["Mova", "Gildle", "FastAPI", "Next.js", "Docker"],
  },
  {
    title: "팀 프로젝트 — Eval-ATS",
    desc: "AI 기반 채용 프로세스 자동화 플랫폼 — 팀 SEUK",
    href: "https://ats.suvisdev.cloud",
    icon: Users,
    tags: ["FastAPI", "React", "Claude API", "pgvector", "AWS"],
  },
]

export default function BlogPage() {
  return (
    <div className="min-h-screen bg-white px-4 py-12 md:px-8 md:py-16">
      <div className="mx-auto max-w-[700px]">
        <Link
          href="/"
          className="text-sm font-medium text-neutral-500 transition-colors hover:text-neutral-900"
        >
          <ArrowLeft className="mr-1 inline h-4 w-4" />
          홈
        </Link>

        <h1 className="mt-6 text-3xl font-bold tracking-tight text-neutral-900">
          Blog
        </h1>
        <p className="mt-2 text-neutral-500">
          개발 기록과 프로젝트 문서를 확인하세요.
        </p>

        <div className="mt-10 space-y-4">
          {BLOGS.map((blog) => {
            const Icon = blog.icon
            return (
              <a
                key={blog.title}
                href={blog.href}
                target="_blank"
                rel="noopener noreferrer"
                className="group block rounded-xl border border-neutral-200 bg-neutral-50 p-6 transition-all hover:border-amber-400 hover:bg-amber-50"
              >
                <div className="flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-lg font-bold text-neutral-900 group-hover:text-amber-600">
                      {blog.title}
                    </h2>
                    <p className="mt-1 text-sm text-neutral-500">{blog.desc}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {blog.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full border border-neutral-200 bg-white px-2.5 py-0.5 text-xs text-neutral-500"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </a>
            )
          })}
        </div>
      </div>
    </div>
  )
}
