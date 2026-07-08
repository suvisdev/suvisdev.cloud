"use client"

/** 아이언맨 JARVIS HUD 느낌의 히어로 비주얼 (이미지 없이 CSS) */
export function HeroJarvisPanel({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={`relative overflow-hidden bg-[#030812] ${
        compact ? "h-full min-h-[7rem] w-full" : "h-full min-h-[400px] w-full"
      }`}
    >
      {/* 배경 그라데이션 */}
      <div
        className="absolute inset-0 opacity-90"
        style={{
          background: `
            radial-gradient(ellipse 80% 60% at 50% 40%, rgba(34, 211, 238, 0.18), transparent 55%),
            radial-gradient(ellipse 50% 40% at 80% 80%, rgba(239, 68, 68, 0.12), transparent 50%),
            linear-gradient(160deg, #0a1628 0%, #020617 45%, #0c0a0a 100%)
          `,
        }}
        aria-hidden
      />

      {/* 그리드 */}
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(34, 211, 238, 0.15) 1px, transparent 1px),
            linear-gradient(90deg, rgba(34, 211, 238, 0.15) 1px, transparent 1px)
          `,
          backgroundSize: compact ? "12px 12px" : "28px 28px",
        }}
        aria-hidden
      />

      {/* 원형 HUD 링 */}
      {!compact && (
        <>
          <div
            className="absolute left-1/2 top-1/2 h-[min(72vw,420px)] w-[min(72vw,420px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-400/30"
            aria-hidden
          />
          <div
            className="absolute left-1/2 top-1/2 h-[min(55vw,320px)] w-[min(55vw,320px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-500/20"
            aria-hidden
          />
          <div
            className="absolute left-1/2 top-1/2 h-[min(38vw,220px)] w-[min(38vw,220px)] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-cyan-400/50 shadow-[0_0_60px_rgba(34,211,238,0.35)]"
            aria-hidden
          />
        </>
      )}

      {/* 스캔 라인 */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-400/80 to-transparent"
        aria-hidden
      />
      {!compact && (
        <div
          className="pointer-events-none absolute inset-x-0 bottom-[30%] h-px bg-gradient-to-r from-transparent via-cyan-300/40 to-transparent"
          aria-hidden
        />
      )}

      {/* 중앙 코어 */}
      <div
        className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 ${
          compact ? "h-8 w-8" : "h-16 w-16 md:h-20 md:w-20"
        }`}
      >
        <div className="absolute inset-0 animate-pulse rounded-full bg-cyan-400/20 blur-md" />
        <div className="relative h-full w-full rounded-full border border-cyan-400/70 bg-cyan-950/40 shadow-[inset_0_0_20px_rgba(34,211,238,0.3)]" />
      </div>

      {/* 라벨 */}
      {!compact && (
        <div className="absolute bottom-8 left-8 right-8 font-mono text-xs tracking-[0.2em] text-cyan-200 uppercase md:text-sm">
          <p className="font-medium">Just A Rather Very Intelligent System</p>
          <p className="mt-2 text-cyan-300/90">SUVIS DEV · AI INTERFACE</p>
        </div>
      )}

      {/* 코너 HUD */}
      {!compact && (
        <>
          <span className="absolute top-6 left-6 font-mono text-xs font-medium text-cyan-300">SYS.ONLINE</span>
          <span className="absolute top-6 right-6 font-mono text-xs font-medium text-red-300/90">ARC.REACTOR</span>
        </>
      )}
    </div>
  )
}
