"use client"

import { useCallback, useRef, useState } from "react"
import { BookUser, FileSpreadsheet, Upload, UserPlus, X } from "lucide-react"
import { cn } from "@/lib/utils"

const ACCEPT = ".csv,text/csv"
const MAX_BYTES = 20 * 1024 * 1024

function isCsvFile(file: File): boolean {
  if (!file.name.toLowerCase().endsWith(".csv")) return false
  const okMime = !file.type || file.type === "text/csv" || file.type === "application/vnd.ms-excel" || file.type === "text/plain"
  return okMime
}

export default function AdminContactsPage() {
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
    setFile(null); setPreview(""); setFileError(""); setUploadResult(""); setUploadError("")
    setShowModal(true)
  }

  const readPreview = useCallback((f: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : ""
      setPreview(text.split(/\r?\n/).slice(0, 5).join("\n") || "(내용 없음)")
    }
    reader.readAsText(f.slice(0, Math.min(f.size, 64 * 1024)), "UTF-8")
  }, [])

  const handleFile = useCallback((f: File | undefined) => {
    setFileError(""); setPreview(""); setUploadResult(""); setUploadError("")
    if (!f) { setFile(null); return }
    if (f.size > MAX_BYTES) { setFile(null); setFileError("파일이 너무 큽니다. (20MB 이하)"); return }
    if (!isCsvFile(f)) { setFile(null); setFileError("CSV 파일(.csv)만 업로드할 수 있습니다."); return }
    setFile(f)
    readPreview(f)
  }, [readPreview])

  const uploadCsv = useCallback(async () => {
    if (!file) return
    setUploading(true); setUploadError(""); setUploadResult("")
    try {
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch("/api/dispatch/adress/upload", {
        method: "POST",
        body: formData,
      })
      const data = await res.json() as { row_count?: number; detail?: string }
      if (!res.ok) throw new Error(data.detail ?? `업로드 실패 (${res.status})`)
      setUploadResult(`업로드 성공: ${data.row_count ?? 0}개 연락처 등록됨`)
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "업로드에 실패했습니다.")
    } finally {
      setUploading(false)
    }
  }, [file])

  return (
    <>
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-slate-800">주소록</h2>
            <p className="text-xs text-slate-500 mt-0.5">CSV 파일로 연락처를 일괄 등록할 수 있습니다.</p>
          </div>
          <button
            type="button"
            onClick={openModal}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600"
          >
            <UserPlus className="size-4" />등록
          </button>
        </div>
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-700">
            <tr>
              <th className="px-4 py-3 font-semibold">이름</th>
              <th className="px-4 py-3 font-semibold">이메일</th>
              <th className="px-4 py-3 font-semibold">메모</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={3} className="px-4 py-16 text-center text-slate-400">
                <BookUser className="mx-auto mb-3 size-10 opacity-30" />
                <p className="text-sm">등록된 연락처가 없습니다.</p>
                <p className="mt-1 text-xs">상단 등록 버튼으로 CSV 파일을 업로드하세요.</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4" onClick={() => setShowModal(false)}>
          <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
              <h2 className="text-lg font-semibold text-slate-800">주소록 파일 업로드</h2>
              <button type="button" onClick={() => setShowModal(false)} className="rounded-md p-1 text-slate-500 hover:bg-slate-100">
                <X className="size-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-xs text-slate-500">CSV 형식: <code className="font-mono bg-slate-100 px-1 rounded">이름,이메일,메모</code></p>
              <input ref={inputRef} type="file" accept={ACCEPT} className="sr-only" onChange={(e) => { handleFile(e.target.files?.[0]); e.target.value = "" }} />
              <div
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputRef.current?.click() } }}
                onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
                onDragLeave={(e) => { e.preventDefault(); setDragActive(false) }}
                onDrop={(e) => { e.preventDefault(); setDragActive(false); handleFile(e.dataTransfer.files?.[0]) }}
                onClick={() => inputRef.current?.click()}
                className={cn(
                  "flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition-all",
                  dragActive ? "border-indigo-400 bg-indigo-50" : "border-slate-300 bg-slate-50 hover:border-indigo-300 hover:bg-indigo-50/50",
                )}
              >
                <Upload className="mb-2 size-8 text-slate-400" />
                <p className="text-sm font-medium text-slate-700">CSV 파일을 여기에 끌어다 놓으세요</p>
                <p className="mt-1 text-xs text-slate-500">또는 클릭하여 파일 선택 · 최대 20MB</p>
              </div>
              {fileError && <p className="text-xs text-rose-600">{fileError}</p>}
              {file && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="size-4 text-emerald-500 shrink-0" />
                    <span className="text-sm font-medium text-slate-800 truncate">{file.name}</span>
                    <span className="ml-auto text-xs text-slate-500 shrink-0">{(file.size / 1024).toFixed(1)} KB</span>
                  </div>
                  {preview && (
                    <pre className="max-h-28 overflow-auto rounded border border-slate-200 bg-white p-2 font-mono text-xs text-slate-700">{preview}</pre>
                  )}
                  {uploadResult && <p className="text-xs text-emerald-600">{uploadResult}</p>}
                  {uploadError && <p className="text-xs text-rose-600">{uploadError}</p>}
                  <button
                    type="button"
                    onClick={() => void uploadCsv()}
                    disabled={uploading}
                    className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
                  >
                    {uploading ? "업로드 중…" : "업로드"}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
