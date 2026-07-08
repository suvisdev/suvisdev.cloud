import Image from "next/image"

/** 로컬 히어로 — 외부 URL 만료 시에도 항상 표시 */
const HERO_IMAGE = "/hero-ai.jpg"

export function HeroImagePanel({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={`relative overflow-hidden bg-neutral-900 ${
        compact ? "min-h-[14rem] w-full" : "h-full min-h-[400px] w-full"
      }`}
    >
      <Image
        src={HERO_IMAGE}
        alt="Suvisdev — AI와 개발을 아우르는 워크스페이스"
        fill
        className="object-cover"
        sizes={compact ? "100vw" : "(max-width: 1024px) 100vw, 50vw"}
        priority
      />
      <div className="absolute inset-0 bg-gradient-to-br from-violet-950/30 via-transparent to-cyan-900/15" />
    </div>
  )
}
