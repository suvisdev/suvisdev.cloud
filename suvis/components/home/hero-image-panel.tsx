/** 로컬 히어로 영상 — 외부 URL 없이 항상 표시 */
const HERO_VIDEO = "/hero-holographic-mask.mp4"
const HERO_POSTER = "/hero-ai.jpg"

export function HeroImagePanel({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={`relative overflow-hidden bg-neutral-900 ${
        compact ? "min-h-[14rem] w-full" : "h-full min-h-[400px] w-full"
      }`}
    >
      <video
        src={HERO_VIDEO}
        poster={HERO_POSTER}
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-br from-violet-950/30 via-transparent to-cyan-900/15" />
    </div>
  )
}
