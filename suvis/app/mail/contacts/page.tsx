"use client"

import Link from "next/link"
import { useCallback, useRef, useState } from "react"
import { BookUser, FileSpreadsheet, Upload, UserPlus, X } from "lucide-react"
import { cn } from "@/lib/utils"

const ACCEPT = ".csv,text/csv"
const MAX_BYTES = 20 * 1024 * 1024

function isCsvFile(file: File): boolean {
  if (!file.name.toLowerCase().endsWith(".csv")) return false
  const okMime =
    !file.type ||
    file.type === "text/csv" ||
    file.type === "application/vnd.ms-excel" ||
    file.type === "text/plain"
  return okMime
}

export default function MailContactsPage() {
  const [showModal, setShowModal] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState("")
  const [fileError, setFileError] = useState("")
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState("")
  const [uploadError, setUploadError] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const openModal = () => {
    setFile(null)
    setPreview("")
    setFileError("")
    setUploadResult("")
    setUploadError("")
    setShowModal(true)
  }
  const closeModal = () => setShowModal(false)

  const readPreview = useCallback((f: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : ""
      setPreview(text.split(/\r?\n/).slice(0, 5).join("\n") || "(내용 없음)")
    }
    reader.readAsText(f.slice(0, Math.min(f.size, 64 * 1024)), "UTF-8")
  }, [])

  const handleFile = useCallback(
    (f: File | undefined) => {
      setFileError("")
      setPreview("")
      setUploadResult("")
      setUploadError("")
      if (!f) {
        setFile(null)
        return
      }
      if (f.size > MAX_BYTES) {
        setFile(null)
        setFileError(`파일이 너무 큽니다. (20MB 이하)`)
        return
      }
      if (!isCsvFile(f)) {
        setFile(null)
        setFileError("CSV 파일(.csv)만 업로드할 수 있습니다.")
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
      const res = await fetch("/api/dispatch/adress/upload", { method: "POST", body: formData })
      const data = (await res.json()) as { row_count?: number; detail?: string }
      if (!res.ok) throw new Error(data.detail ?? `업로드 실패 (${res.status})`)
      setUploadResult(`업로드 성공: ${data.row_count ?? 0}개 연락처 등록됨`)
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "업로드에 실패했습니다.")
    } finally {
      setUploading(false)
    }
  }, [file])

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#f3f3f3] px-4 py-4 md:px-6 md:py-6 dark:bg-[#0d0f14]">
      <main className="mx-auto grid max-w-[1500px] gap-4 md:grid-cols-[220px_1fr]">
        {/* 사이드바 */}
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
          <p className="mt-6 text-xs font-semibold tracking-wide text-neutral-500">SOCCER</p>
          <div className="mt-2 space-y-2">
            <Link
              href="/soccer/chat"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              채팅
            </Link>
          </div>
        </aside>

        {/* 메인 */}
        <section className="rounded-xl border border-neutral-200 bg-white p-6 md:p-8 dark:border-[#252b3b] dark:bg-[#161a24]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">DISPATCH</p>
              <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
                주소록
              </h1>
            </div>
            <button
              type="button"
              onClick={openModal}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-600"
            >
              <UserPlus className="size-4" aria-hidden />
              등록
            </button>
          </div>
          <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-400">
            CSV 파일로 연락처를 일괄 등록할 수 있습니다. (이름, 이메일, 메모)
          </p>

          {/* 연락처 테이블 */}
          <div className="mt-6 overflow-hidden rounded-xl border border-neutral-200 dark:border-[#252b3b]">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-neutral-100/95 text-neutral-900 dark:bg-[#252b3b]/95 dark:text-neutral-100">
                <tr>
                  <th className="px-4 py-3 font-semibold">이름</th>
                  <th className="px-4 py-3 font-semibold">이메일</th>
                  <th className="px-4 py-3 font-semibold">메모</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td
                    colSpan={3}
                    className="px-4 py-16 text-center text-neutral-400 dark:text-neutral-600"
                  >
                    <BookUser className="mx-auto mb-3 size-10 opacity-30" />
                    <p className="text-sm">등록된 연락처가 없습니다.</p>
                    <p className="mt-1 text-xs">상단 등록 버튼으로 CSV 파일을 업로드하세요.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>

      {/* 모달 */}
      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
          onClick={closeModal}
        >
          <div
            className="w-full max-w-xl rounded-2xl border border-neutral-200 bg-white shadow-2xl dark:border-[#252b3b] dark:bg-[#161a24]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 모달 헤더 */}
            <div className="flex items-center justify-between border-b border-neutral-200 px-6 py-4 dark:border-[#252b3b]">
              <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                주소록 파일 업로드
              </h2>
              <button
                type="button"
                onClick={closeModal}
                className="rounded-md p-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-[#252b3b]"
              >
                <X className="size-5" />
              </button>
            </div>

            {/* 모달 본문 */}
            <div className="space-y-4 p-6">
              <p className="text-xs text-neutral-500">
                CSV 형식:{" "}
                <code className="rounded bg-neutral-100 px-1 font-mono dark:bg-[#252b3b]">
                  이름,이메일,메모
                </code>{" "}
                (헤더 포함)
              </p>

              <input
                ref={inputRef}
                type="file"
                accept={ACCEPT}
                className="sr-only"
                onChange={(e) => {
                  handleFile(e.target.files?.[0])
                  e.target.value = ""
                }}
              />

              {/* 드래그 영역 */}
              <div
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    inputRef.current?.click()
                  }
                }}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragActive(true)
                }}
                onDragLeave={(e) => {
                  e.preventDefault()
                  setDragActive(false)
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragActive(false)
                  handleFile(e.dataTransfer.files?.[0])
                }}
                onClick={() => inputRef.current?.click()}
                className={cn(
                  "flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition-all",
                  dragActive
                    ? "border-indigo-400 bg-indigo-50 dark:border-indigo-700 dark:bg-indigo-900/20"
                    : "border-neutral-300 bg-neutral-50 hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-[#252b3b] dark:bg-[#1a1f2d] dark:hover:border-indigo-700"
                )}
              >
                <Upload className="mb-2 size-8 text-neutral-400" />
                <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  CSV 파일을 여기에 끌어다 놓으세요
                </p>
                <p className="mt-1 text-xs text-neutral-500">또는 클릭하여 파일 선택 · 최대 20MB</p>
              </div>

              {/* 파일 에러 */}
              {fileError && <p className="text-xs text-rose-600 dark:text-rose-400">{fileError}</p>}

              {/* 파일 선택됨 */}
              {file && (
                <div className="space-y-2 rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="size-4 shrink-0 text-emerald-500" />
                    <span className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {file.name}
                    </span>
                    <span className="ml-auto shrink-0 text-xs text-neutral-500">
                      {(file.size / 1024).toFixed(1)} KB
                    </span>
                  </div>
                  {preview && (
                    <pre className="max-h-28 overflow-auto rounded border border-neutral-200 bg-white p-2 font-mono text-xs text-neutral-700 dark:border-[#252b3b] dark:bg-[#0d0f14] dark:text-neutral-300">
                      {preview}
                    </pre>
                  )}
                  {uploadResult && (
                    <p className="text-xs text-emerald-600 dark:text-emerald-400">{uploadResult}</p>
                  )}
                  {uploadError && (
                    <p className="text-xs text-rose-600 dark:text-rose-400">{uploadError}</p>
                  )}
                  <button
                    type="button"
                    onClick={() => void uploadCsv()}
                    disabled={uploading}
                    className="mt-1 inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-600 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {uploading ? "업로드 중…" : "업로드"}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
