"use client"

import Link from "next/link"
import { useCallback, useRef, useState } from "react"
import { ScanFace, Upload, UserCheck, UserX } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

const ACCEPT = ".jpg,.jpeg,.png,image/jpeg,image/png"
const MAX_BYTES = 20 * 1024 * 1024 // 20MB
const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) || "http://127.0.0.1:8000"

function isImageFile(file: File): boolean {
  const name = file.name.toLowerCase()
  if (!name.endsWith(".jpg") && !name.endsWith(".jpeg") && !name.endsWith(".png")) return false
  const okMime = !file.type || file.type === "image/jpeg" || file.type === "image/png"
  return okMime
}

interface PredictResponse {
  predicted_name?: string
  confidence?: number
  is_known?: boolean
  detail?: string | { msg?: string }[]
}

export default function VisionObjectDetectionPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [dragActive, setDragActive] = useState(false)
  const [predicting, setPredicting] = useState(false)
  const [predictedName, setPredictedName] = useState<string>("")
  const [confidence, setConfidence] = useState<number | null>(null)
  const [isKnown, setIsKnown] = useState<boolean>(true)
  const [predictError, setPredictError] = useState<string>("")

  const handleFile = useCallback((f: File | undefined) => {
    setError("")
    setPreviewUrl("")
    setPredictedName("")
    setConfidence(null)
    setIsKnown(true)
    setPredictError("")
    if (!f) {
      setFile(null)
      return
    }
    if (f.size > MAX_BYTES) {
      setFile(null)
      setError(`파일이 너무 큽니다. (${MAX_BYTES / 1024 / 1024}MB 이하)`)
      return
    }
    if (!isImageFile(f)) {
      setFile(null)
      setError("JPG 또는 PNG 이미지 파일만 업로드할 수 있습니다.")
      return
    }
    setFile(f)
    setPreviewUrl(URL.createObjectURL(f))
  }, [])

  const predictFace = useCallback(async () => {
    if (!file) return
    setPredicting(true)
    setPredictError("")
    setPredictedName("")
    setConfidence(null)
    setIsKnown(true)
    try {
      const formData = new FormData()
      formData.append("file", file)
      // 백엔드가 require_user로 잠김(2026-09-11) — 인증은 쿠키(/api/backend 프록시)가 붙인다
      const res = await fetch(`/api/backend/api/vision/face/predict`, {
        method: "POST",
        body: formData,
      })
      let data: PredictResponse = {}
      try {
        data = (await res.json()) as PredictResponse
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
              : `예측 실패 (HTTP ${res.status})`
        throw new Error(message)
      }
      setPredictedName(data.predicted_name ?? "")
      setConfidence(typeof data.confidence === "number" ? data.confidence : null)
      setIsKnown(data.is_known ?? true)
    } catch (e) {
      const message = e instanceof Error ? e.message : "예측에 실패했습니다."
      setPredictError(
        message === "Failed to fetch"
          ? `백엔드에 연결할 수 없습니다. 서버가 ${API_BASE} 에서 실행 중인지 확인하세요.`
          : message
      )
    } finally {
      setPredicting(false)
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
    handleFile(e.dataTransfer.files?.[0])
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
              className="block rounded-md bg-neutral-100 px-3 py-2 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-200 dark:bg-[#252b3b] dark:text-neutral-100 dark:hover:bg-[#2d3447]"
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
          <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">VISION</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            객체 탐지
          </h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            사람 얼굴 사진을 업로드하면 YOLO 분류 모델이 학습된 인물 중 누구인지 이름과
            정확도(신뢰도)를 맞춰줍니다.
          </p>

          <div className="mt-8 grid gap-4 lg:grid-cols-[1fr_240px]">
            <Card className="rounded-xl border border-neutral-200 bg-neutral-50 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
              <CardHeader className="border-b border-neutral-200 dark:border-[#252b3b]">
                <CardTitle className="text-xl text-neutral-900 dark:text-neutral-100">
                  얼굴 사진 업로드
                </CardTitle>
                <CardDescription className="text-neutral-600 dark:text-neutral-400">
                  JPG 또는 PNG 파일을 드래그하거나 버튼으로 선택하세요.
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
                    여기로 얼굴 사진을 끌어다 놓으세요
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
                  <ScanFace className="mx-auto size-8 text-emerald-500" />
                  <p className="mt-2 text-sm font-semibold">JPG · PNG</p>
                  <p className="text-xs text-neutral-500">최대 20MB</p>
                </div>
                <div>
                  <Upload className="mx-auto size-7 text-sky-500" />
                  <p className="mt-1 text-sm">드래그 앤 드롭</p>
                </div>
                <div>
                  <UserCheck className="mx-auto size-7 text-violet-500" />
                  <p className="mt-1 text-sm">인물 예측</p>
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
                    <div className="flex gap-4">
                      {previewUrl ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={previewUrl}
                          alt={file.name}
                          className="h-28 w-28 shrink-0 rounded-lg border border-neutral-200 object-cover dark:border-[#252b3b]"
                        />
                      ) : null}
                      <dl className="grid flex-1 gap-2 tracking-tight text-neutral-600 dark:text-neutral-400">
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
                      </dl>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <Button
                        type="button"
                        onClick={() => void predictFace()}
                        disabled={predicting}
                        className="bg-neutral-900 text-white hover:bg-neutral-800 disabled:opacity-60 dark:bg-indigo-600 dark:hover:bg-indigo-500"
                      >
                        {predicting
                          ? "예측 중... (최초 1회는 학습 때문에 오래 걸릴 수 있어요)"
                          : "이 사람은 누구일까요?"}
                      </Button>
                      {predictError ? (
                        <p className="text-sm text-rose-700 dark:text-rose-400">{predictError}</p>
                      ) : null}
                    </div>

                    {predictedName ? (
                      <div
                        className={cn(
                          "mt-4 rounded-lg border p-4",
                          isKnown
                            ? "border-emerald-200 bg-emerald-50 dark:border-emerald-900/50 dark:bg-emerald-950/30"
                            : "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30"
                        )}
                      >
                        <div className="flex items-center gap-3">
                          {isKnown ? (
                            <UserCheck className="size-8 shrink-0 text-emerald-600 dark:text-emerald-400" />
                          ) : (
                            <UserX className="size-8 shrink-0 text-amber-600 dark:text-amber-400" />
                          )}
                          <div>
                            <p
                              className={cn(
                                "text-lg font-bold tracking-tight",
                                isKnown
                                  ? "text-emerald-800 dark:text-emerald-300"
                                  : "text-amber-800 dark:text-amber-300"
                              )}
                            >
                              {predictedName}
                            </p>
                            <p
                              className={cn(
                                "text-xs",
                                isKnown
                                  ? "text-emerald-700 dark:text-emerald-400"
                                  : "text-amber-700 dark:text-amber-400"
                              )}
                            >
                              정확도(신뢰도){" "}
                              {confidence !== null ? (confidence * 100).toFixed(1) : "?"}%
                              {isKnown ? "" : " — 학습된 인물과 충분히 비슷하지 않아요"}
                            </p>
                          </div>
                        </div>
                        {confidence !== null ? (
                          <div
                            className={cn(
                              "mt-3 h-2 w-full overflow-hidden rounded-full",
                              isKnown
                                ? "bg-emerald-100 dark:bg-emerald-900/40"
                                : "bg-amber-100 dark:bg-amber-900/40"
                            )}
                          >
                            <div
                              className={cn(
                                "h-full rounded-full",
                                isKnown
                                  ? "bg-emerald-500 dark:bg-emerald-400"
                                  : "bg-amber-500 dark:bg-amber-400"
                              )}
                              style={{ width: `${Math.min(100, Math.max(0, confidence * 100))}%` }}
                            />
                          </div>
                        ) : null}
                      </div>
                    ) : null}
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
