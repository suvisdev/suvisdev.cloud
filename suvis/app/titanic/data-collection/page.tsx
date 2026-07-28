"use client"

import Link from "next/link"
import { useCallback, useRef, useState } from "react"
import { Database, FileSpreadsheet, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

const ACCEPT = ".csv,text/csv"
const MAX_BYTES = 20 * 1024 * 1024 // 20MB
const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) || "http://127.0.0.1:8000"

function isCsvFile(file: File): boolean {
  const name = file.name.toLowerCase()
  if (!name.endsWith(".csv")) return false
  const okMime =
    !file.type ||
    file.type === "text/csv" ||
    file.type === "application/vnd.ms-excel" ||
    file.type === "text/plain"
  return okMime
}

export default function TitanicDataCollectionPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<string>("")
  const [uploadError, setUploadError] = useState<string>("")

  const readPreview = useCallback((f: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : ""
      const lines = text.split(/\r?\n/).slice(0, 5).join("\n")
      setPreview(lines || "(내용 없음)")
    }
    reader.onerror = () => setPreview("(미리보기를 불러오지 못했습니다.)")
    reader.readAsText(f.slice(0, Math.min(f.size, 64 * 1024)), "UTF-8")
  }, [])

  const handleFile = useCallback(
    (f: File | undefined) => {
      setError("")
      setPreview("")
      setUploadResult("")
      setUploadError("")
      if (!f) {
        setFile(null)
        return
      }
      if (f.size > MAX_BYTES) {
        setFile(null)
        setError(`파일이 너무 큽니다. (${MAX_BYTES / 1024 / 1024}MB 이하)`)
        return
      }
      if (!isCsvFile(f)) {
        setFile(null)
        setError("CSV 파일(.csv)만 업로드할 수 있습니다. (예: 타이타닉.csv)")
        return
      }
      setFile(f)
      readPreview(f)
    },
    [readPreview]
  )

  const uploadCsv = useCallback(async () => {
    if (!file) return
    setUploading(true)
    setUploadError("")
    setUploadResult("")
    try {
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch(`${API_BASE}/api/titanic/james/upload`, {
        method: "POST",
        body: formData,
      })
      let data: { row_count?: number; detail?: string | { msg?: string }[] } = {}
      try {
        data = (await res.json()) as typeof data
      } catch {
        /* non-JSON body */
      }
      if (!res.ok) {
        const detail = data.detail
        const message =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((d) => (typeof d === "object" && d?.msg ? d.msg : String(d))).join(", ")
              : `업로드 실패 (HTTP ${res.status})`
        throw new Error(message)
      }
      setUploadResult(`업로드 성공: ${data.row_count ?? 0}개 행 수신`)
    } catch (e) {
      const message = e instanceof Error ? e.message : "업로드에 실패했습니다."
      setUploadError(
        message === "Failed to fetch"
          ? `백엔드에 연결할 수 없습니다. 서버가 ${API_BASE} 에서 실행 중인지 확인하세요.`
          : message
      )
    } finally {
      setUploading(false)
    }
  }, [file])

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFile(e.target.files?.[0])
    e.target.value = ""
  }

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(true)
  }

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    const dropped = e.dataTransfer.files?.[0]
    handleFile(dropped)
  }

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
              className="block rounded-md bg-neutral-100 px-3 py-2 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-200 dark:bg-[#252b3b] dark:text-neutral-100 dark:hover:bg-[#2d3447]"
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
            타이타닉 데이터 수집
          </h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            분석에 사용할 CSV 파일을 업로드합니다. 파일 형식 검사, 용량 제한, 상위 5줄 미리보기를
            통해 데이터 품질을 빠르게 확인할 수 있습니다.
          </p>

          <div className="mt-8 grid gap-4 lg:grid-cols-[1fr_240px]">
            <Card className="rounded-xl border border-neutral-200 bg-neutral-50 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
              <CardHeader className="border-b border-neutral-200 dark:border-[#252b3b]">
                <CardTitle className="text-xl text-neutral-900 dark:text-neutral-100">
                  CSV 업로드
                </CardTitle>
                <CardDescription className="text-neutral-600 dark:text-neutral-400">
                  `타이타닉.csv`를 드래그하거나 버튼으로 선택하세요.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5 p-5 md:p-6">
                <input
                  ref={inputRef}
                  type="file"
                  accept={ACCEPT}
                  className="sr-only"
                  onChange={onInputChange}
                />
                <div
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault()
                      inputRef.current?.click()
                    }
                  }}
                  onDragOver={onDragOver}
                  onDragLeave={onDragLeave}
                  onDrop={onDrop}
                  onClick={() => inputRef.current?.click()}
                  className={cn(
                    "flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-10 text-center transition-all duration-300",
                    dragActive
                      ? "scale-[1.01] border-sky-300 bg-sky-50 dark:border-sky-700 dark:bg-sky-900/30"
                      : "border-neutral-300 bg-white hover:border-sky-300 hover:bg-sky-50/50 dark:border-[#252b3b] dark:bg-[#161a24] dark:hover:border-sky-700 dark:hover:bg-sky-900/20"
                  )}
                >
                  <p className="text-base font-medium tracking-tight text-neutral-800 dark:text-neutral-200">
                    여기로 CSV를 끌어다 놓으세요
                  </p>
                  <p className="mt-2 text-xs tracking-tight text-neutral-500">
                    창 안 어디를 클릭해도 파일 선택이 열립니다
                  </p>
                  <div className="my-6 flex w-full max-w-xs items-center gap-3">
                    <span className="h-px flex-1 bg-gradient-to-r from-transparent to-neutral-300 dark:to-[#252b3b]" />
                    <span className="text-[11px] font-medium tracking-[0.2em] text-neutral-400 uppercase">
                      or
                    </span>
                    <span className="h-px flex-1 bg-gradient-to-l from-transparent to-neutral-300 dark:to-[#252b3b]" />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    className="pointer-events-auto border-neutral-300 bg-white px-8 text-neutral-700 hover:border-sky-300 hover:bg-sky-50 hover:text-neutral-900 dark:border-[#252b3b] dark:bg-[#252b3b] dark:text-neutral-300 dark:hover:border-sky-700 dark:hover:bg-sky-900/30 dark:hover:text-neutral-100"
                    onClick={(e) => {
                      e.stopPropagation()
                      inputRef.current?.click()
                    }}
                  >
                    파일에서 선택
                  </Button>
                </div>
              </CardContent>
            </Card>

            <aside className="rounded-xl border border-neutral-200 bg-neutral-50 p-5 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
              <div className="space-y-5 text-center text-neutral-700 dark:text-neutral-300">
                <div>
                  <FileSpreadsheet className="mx-auto size-8 text-emerald-500" />
                  <p className="mt-2 text-sm font-semibold">CSV 파일</p>
                  <p className="text-xs text-neutral-500">최대 20MB</p>
                </div>
                <div>
                  <Upload className="mx-auto size-7 text-sky-500" />
                  <p className="mt-1 text-sm">드래그 앤 드롭</p>
                </div>
                <div>
                  <Database className="mx-auto size-7 text-violet-500" />
                  <p className="mt-1 text-sm">상위 5줄 미리보기</p>
                </div>
              </div>
            </aside>
          </div>

          {(file || error) && (
            <Card className="mt-4 rounded-xl border border-neutral-200 bg-neutral-50 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
              <CardHeader
                className={cn(
                  "border-b pb-3",
                  error
                    ? "border-rose-200 bg-rose-50 dark:border-rose-900/50 dark:bg-rose-950/30"
                    : "border-neutral-200 bg-white dark:border-[#252b3b] dark:bg-[#161a24]"
                )}
              >
                <CardTitle
                  className={cn(
                    "text-base font-medium tracking-tight",
                    error
                      ? "text-rose-700 dark:text-rose-400"
                      : "text-neutral-900 dark:text-neutral-100"
                  )}
                >
                  {error ? "오류" : "선택된 파일"}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 pt-4 text-sm">
                {error ? (
                  <p className="leading-relaxed tracking-tight text-rose-700 dark:text-rose-400">
                    {error}
                  </p>
                ) : file ? (
                  <>
                    <dl className="grid gap-2 tracking-tight text-neutral-600 dark:text-neutral-400">
                      <div className="flex gap-2">
                        <dt className="min-w-[3rem] text-xs font-medium tracking-wider text-neutral-500 uppercase">
                          이름
                        </dt>
                        <dd className="truncate font-mono text-sm text-neutral-900 dark:text-neutral-100">
                          {file.name}
                        </dd>
                      </div>
                      <div className="flex gap-2">
                        <dt className="min-w-[3rem] text-xs font-medium tracking-wider text-neutral-500 uppercase">
                          크기
                        </dt>
                        <dd className="font-mono text-sm text-neutral-900 dark:text-neutral-100">
                          {(file.size / 1024).toFixed(1)} KB
                        </dd>
                      </div>
                      <div className="flex gap-2">
                        <dt className="min-w-[3rem] text-xs font-medium tracking-wider text-neutral-500 uppercase">
                          형식
                        </dt>
                        <dd className="font-mono text-sm text-neutral-900 dark:text-neutral-100">
                          {file.type || "text/csv (추정)"}
                        </dd>
                      </div>
                    </dl>
                    {preview ? (
                      <div>
                        <p className="mb-2 text-xs font-medium tracking-wider text-neutral-500 uppercase">
                          앞부분 미리보기
                        </p>
                        <pre className="max-h-40 overflow-auto rounded-lg border border-neutral-200 bg-white p-3 font-mono text-xs leading-relaxed tracking-tight text-neutral-700 dark:border-[#252b3b] dark:bg-[#0d0f14] dark:text-neutral-300">
                          {preview}
                        </pre>
                      </div>
                    ) : null}
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <Button
                        type="button"
                        onClick={() => void uploadCsv()}
                        disabled={uploading}
                        className="bg-neutral-900 text-white hover:bg-neutral-800 disabled:opacity-60 dark:bg-indigo-600 dark:hover:bg-indigo-500"
                      >
                        {uploading ? "업로드 중..." : "백엔드로 업로드"}
                      </Button>
                      {uploadResult ? (
                        <p className="text-sm text-emerald-700 dark:text-emerald-400">
                          {uploadResult}
                        </p>
                      ) : null}
                      {uploadError ? (
                        <p className="text-sm text-rose-700 dark:text-rose-400">{uploadError}</p>
                      ) : null}
                    </div>
                  </>
                ) : null}
              </CardContent>
            </Card>
          )}
        </section>
      </main>
    </div>
  )
}
