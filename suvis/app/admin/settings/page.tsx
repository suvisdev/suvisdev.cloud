"use client"

import { useEffect, useState } from "react"
import { Loader2, ShieldAlert } from "lucide-react"
import { AdminMenuButton } from "../_components/admin-menu-button"
import { getSettings, saveSettings, type AdminSettings } from "@/lib/admin-settings-api"

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-slate-600">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-slate-400">{hint}</span>}
    </label>
  )
}

const inputClass =
  "w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400"

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-4 text-sm font-bold text-slate-800">{title}</h2>
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </section>
  )
}

/** 값 노출 주의 — 실제 ADMIN_EMAILS는 클라이언트로 절대 내려보내지 않고 마스킹된 표시값만 하드코딩한다. */
const MASKED_ADMIN_EMAIL = "s******v@gmail.com"

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch((e: Error) => setError(e.message))
  }, [])

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    setSaved(false)
    try {
      await saveSettings(settings)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장에 실패했습니다.")
    } finally {
      setSaving(false)
    }
  }

  const update = <K extends keyof AdminSettings>(key: K, value: AdminSettings[K]) => {
    setSettings((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  return (
    <div className="min-h-screen">
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AdminMenuButton />
          <div>
            <h1 className="text-base font-bold text-slate-800 md:text-lg">설정</h1>
            <p className="text-xs text-slate-400">사이트·에이전트·연동·보안 설정</p>
          </div>
        </div>
      </header>

      <div className="p-4 md:p-6 lg:p-8">
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        {!settings ? (
          <div className="flex items-center justify-center py-20 text-sm text-slate-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            불러오는 중...
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <Section title="일반">
              <Field label="사이트명">
                <input
                  type="text"
                  className={inputClass}
                  value={settings.siteName}
                  onChange={(e) => update("siteName", e.target.value)}
                />
              </Field>
              <Field label="사이트 설명">
                <input
                  type="text"
                  className={inputClass}
                  value={settings.siteDescription}
                  onChange={(e) => update("siteDescription", e.target.value)}
                />
              </Field>
            </Section>

            <Section title="에이전트 기본값">
              <Field label="기본 모델">
                <select
                  className={inputClass}
                  value={settings.defaultModel}
                  onChange={(e) => update("defaultModel", e.target.value)}
                >
                  <option value="EXAONE-3.5-2.4B-Instruct">EXAONE-3.5-2.4B-Instruct</option>
                  <option value="Qwen2.5-1.5B">Qwen2.5-1.5B</option>
                </select>
              </Field>
              <Field label="응답 타임아웃 (초)">
                <input
                  type="number"
                  min={1}
                  className={inputClass}
                  value={settings.responseTimeoutSec}
                  onChange={(e) => update("responseTimeoutSec", Number(e.target.value))}
                />
              </Field>
              <div className="sm:col-span-2">
                <span className="mb-1.5 block text-xs font-medium text-slate-600">자동 재시도</span>
                <button
                  type="button"
                  onClick={() => update("autoRetry", !settings.autoRetry)}
                  className={`flex h-8 w-fit items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors ${
                    settings.autoRetry
                      ? "border-emerald-200 bg-emerald-100 text-emerald-700"
                      : "border-slate-300 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {settings.autoRetry ? "켜짐" : "꺼짐"}
                </button>
              </div>
            </Section>

            <Section title="API / 연동">
              <Field label="Ollama Base URL" hint="컨테이너 내부에서만 접근 가능(host.docker.internal)">
                <input
                  type="text"
                  className={inputClass}
                  value={settings.ollamaBaseUrl}
                  onChange={(e) => update("ollamaBaseUrl", e.target.value)}
                />
              </Field>
              <Field label="Webhook URL" hint="에이전트 실행 완료 알림을 보낼 URL (선택)">
                <input
                  type="text"
                  placeholder="https://"
                  className={inputClass}
                  value={settings.webhookUrl}
                  onChange={(e) => update("webhookUrl", e.target.value)}
                />
              </Field>
            </Section>

            <Section title="보안">
              <Field label="관리자 이메일 (ADMIN_EMAILS)" hint="읽기전용 — 보안상 마스킹되어 표시됩니다.">
                <input type="text" disabled className={`${inputClass} bg-slate-50 text-slate-400`} value={MASKED_ADMIN_EMAIL} />
              </Field>
              <Field label="세션 정책" hint="로그인 세션은 브라우저 종료 시 만료됩니다(세션 쿠키).">
                <input type="text" disabled className={`${inputClass} bg-slate-50 text-slate-400`} value="세션 쿠키 (브라우저 종료 시 만료)" />
              </Field>
              <p className="flex items-start gap-1.5 text-[11px] text-slate-400 sm:col-span-2">
                <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                실제 관리자 이메일 값은 서버 환경변수에만 존재하며 클라이언트로 전달되지 않습니다.
              </p>
            </Section>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving}
                className="flex h-9 items-center gap-1.5 rounded-full bg-emerald-500 px-4 text-sm font-medium text-white transition-colors hover:bg-emerald-600 disabled:opacity-50"
              >
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                저장
              </button>
              {saved && <span className="text-xs text-emerald-600">저장되었습니다. (mock — 실제 반영 안 됨)</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
