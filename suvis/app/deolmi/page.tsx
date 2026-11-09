"use client"

import { useEffect, useRef, useState } from "react"
import { Bot, Loader2, ShieldCheck, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  demoVerify,
  startSession,
  type DeolmiResult,
  type DeolmiSession,
  type DeolmiSignals,
  type Verdict,
} from "@/lib/deolmi-api"
import { cn } from "@/lib/utils"

type Who = "human" | "bot"

type Outcome = { result: DeolmiResult; signals: DeolmiSignals }

const VERDICT_LABEL: Record<Verdict, { text: string; className: string }> = {
  allow: { text: "통과", className: "bg-emerald-100 text-emerald-800" },
  challenge: { text: "추가 확인", className: "bg-amber-100 text-amber-800" },
  block: { text: "차단", className: "bg-red-100 text-red-800" },
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

// 흔한 매크로 흉내: 직선으로 커서 이동, 같은 간격으로 키 입력, 곧바로 클릭 — 모두 스크립트가 만든 이벤트다.
async function actLikeMacro(input: HTMLInputElement) {
  for (let i = 0; i <= 20; i++) {
    document.dispatchEvent(
      new PointerEvent("pointermove", {
        clientX: 100 + i * 20,
        clientY: 200 + i * 10,
        pointerType: "mouse",
        bubbles: true,
      })
    )
  }
  const text = "매크로봇"
  input.value = ""
  for (let i = 0; i < 10; i++) {
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "a", bubbles: true }))
    input.value = text.slice(0, Math.min(text.length, i + 1))
    await sleep(40)
  }
  document.dispatchEvent(new MouseEvent("click", { bubbles: true }))
}

export default function DeolmiDemoPage() {
  const sessionRef = useRef<DeolmiSession | null>(null)
  const nameRef = useRef<HTMLInputElement>(null)
  const [ready, setReady] = useState(false)
  const [running, setRunning] = useState<Who | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [outcomes, setOutcomes] = useState<Partial<Record<Who, Outcome>>>({})

  const mountedRef = useRef(true)

  // 측정 세션은 한 번에 하나만 둔다. 바꿀 때·화면을 떠날 때 stop()으로 SDK 리스너를 해제한다.
  const replaceSession = async (): Promise<DeolmiSession | null> => {
    sessionRef.current?.stop()
    sessionRef.current = null
    if (!mountedRef.current) return null
    const next = await startSession()
    if (!mountedRef.current) {
      next.stop()
      return null
    }
    sessionRef.current = next
    return next
  }

  useEffect(() => {
    mountedRef.current = true
    replaceSession()
      .then(() => setReady(true))
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "SDK를 불러오지 못했습니다.")
      )
    return () => {
      mountedRef.current = false
      sessionRef.current?.stop()
      sessionRef.current = null
    }
  }, [])

  const judge = async (who: Who, session: DeolmiSession) => {
    const signals = session.features()
    const { token } = await session.score()
    const result = await demoVerify(token)
    setOutcomes((prev) => ({ ...prev, [who]: { result, signals } }))
  }

  const run = async (who: Who) => {
    if (running) return
    setRunning(who)
    setError(null)
    try {
      // 매크로는 사람의 움직임이 섞이지 않게 새 세션에서 센다.
      const session = who === "bot" ? await replaceSession() : sessionRef.current
      const input = nameRef.current
      if (!session || !input) return
      if (who === "bot") await actLikeMacro(input)
      await judge(who, session)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "판정을 받지 못했습니다.")
    } finally {
      // 다음 시도는 새로 센다 — 앞선 시도의 움직임이 섞이지 않게.
      await replaceSession().catch(() => null)
      if (mountedRef.current) setRunning(null)
    }
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    void run("human")
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <div className="mb-8 space-y-2">
        <p className="text-muted-foreground flex items-center gap-2 text-sm font-medium">
          <ShieldCheck className="size-4" /> 덜미 · 매크로 탐지
        </p>
        <h1 className="text-3xl font-bold tracking-tight">
          사람인지 매크로인지, 행동으로 가려냅니다
        </h1>
        <p className="text-muted-foreground">
          예매 폼을 직접 써 보고, 같은 폼을 매크로가 채우게도 해 보세요. 덜미는 마우스 궤적·키 입력
          간격·머문 시간만 보고 판정합니다. 입력한 글자는 보내지 않습니다.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>공연 예매(데모)</CardTitle>
          <CardDescription>
            이름을 입력하고 예매하기를 누르세요. 실제 예매는 되지 않습니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
            <Input
              ref={nameRef}
              placeholder="예매자 이름"
              aria-label="예매자 이름"
              autoComplete="off"
            />
            <Button type="submit" disabled={!ready || running !== null}>
              {running === "human" ? <Loader2 className="animate-spin" /> : <User />}
              예매하기
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={!ready || running !== null}
              onClick={() => void run("bot")}
            >
              {running === "bot" ? <Loader2 className="animate-spin" /> : <Bot />}
              매크로로 예매
            </Button>
          </form>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <ResultCard title="직접 예매" icon={<User className="size-4" />} outcome={outcomes.human} />
        <ResultCard title="매크로" icon={<Bot className="size-4" />} outcome={outcomes.bot} />
      </div>

      <p className="text-muted-foreground mt-6 text-xs">
        판정은 위험 신호이지 사람이라는 증명이 아닙니다. 실제 서비스는 이 결과를 로그인·구매 수량
        제한 같은 자체 확인과 함께 씁니다.
      </p>
    </main>
  )
}

function ResultCard({
  title,
  icon,
  outcome,
}: {
  title: string
  icon: React.ReactNode
  outcome?: Outcome
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {icon} {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {outcome ? (
          <ResultBody outcome={outcome} />
        ) : (
          <p className="text-muted-foreground">아직 시도하지 않았습니다.</p>
        )}
      </CardContent>
    </Card>
  )
}

function ResultBody({ outcome: { result, signals } }: { outcome: Outcome }) {
  const label = VERDICT_LABEL[result.verdict]
  return (
    <>
      <div className="flex items-center justify-between">
        <span className={cn("rounded-full px-3 py-1 text-sm font-semibold", label.className)}>
          {label.text}
        </span>
        <span className="text-muted-foreground tabular-nums">
          의심 점수 {result.score.toFixed(2)}
        </span>
      </div>
      <div className="bg-muted h-2 overflow-hidden rounded-full">
        <div
          className="bg-foreground/70 h-full"
          style={{ width: `${Math.round(result.score * 100)}%` }}
        />
      </div>
      {result.reasons.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5">
          {result.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      ) : (
        <p className="text-muted-foreground">걸린 규칙이 없습니다.</p>
      )}
      <details className="text-muted-foreground text-xs">
        <summary className="cursor-pointer">
          보낸 신호 보기 ({result.decided_by === "model" ? "모델" : "규칙"}이 판정)
        </summary>
        <pre className="bg-muted mt-2 overflow-x-auto rounded p-2">
          {JSON.stringify(signals, null, 2)}
        </pre>
      </details>
    </>
  )
}
