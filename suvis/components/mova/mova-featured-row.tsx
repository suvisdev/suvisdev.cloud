import Image from "next/image"
import Link from "next/link"
import { Play } from "lucide-react"

const articleImg =
  "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&q=80&grayscale"
const posterImg =
  "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=600&q=80"
const trailerImg =
  "https://images.unsplash.com/photo-1478720568477-152d9b164e26?w=800&q=80"

export function MovaFeaturedRow() {
  return (
    <div className="grid gap-3 md:grid-cols-3 md:gap-4">
      <Link
        href="/mova/title/interstellar"
        className="group relative block min-h-[220px] overflow-hidden rounded-lg border border-mova-border bg-mova-surface md:min-h-[260px]"
      >
        <Image
          src={articleImg}
          alt=""
          fill
          className="object-cover object-top opacity-90 transition-transform duration-500 group-hover:scale-105"
          sizes="(max-width: 768px) 100vw, 33vw"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-mova-bg via-black/30 to-transparent" />
        <span className="absolute top-3 left-3 rounded bg-white/15 px-2 py-0.5 text-[11px] font-medium text-white backdrop-blur-sm">
          에디터 픽
        </span>
        <div className="absolute right-0 bottom-0 left-0 p-4">
          <h3 className="font-display text-base font-bold text-white md:text-lg">
            크리스토퍼 놀란, SF를 다시 쓰다
          </h3>
          <p className="mt-1 line-clamp-2 text-xs text-neutral-300 md:text-sm">
            시간과 공간을 넘나드는 서사, Mova 에디터가 정리한 필독 가이드
          </p>
        </div>
      </Link>

      <Link
        href="/mova/title/dune-2"
        className="group relative block min-h-[220px] overflow-hidden rounded-lg border border-mova-border bg-mova-surface md:min-h-[260px]"
      >
        <Image
          src={posterImg}
          alt=""
          fill
          className="object-cover opacity-60 blur-sm scale-110"
          sizes="(max-width: 768px) 100vw, 33vw"
        />
        <div className="absolute inset-0 flex flex-col items-center justify-center p-4">
          <span className="mb-2 self-start rounded bg-mova-accent px-2 py-0.5 text-[10px] font-bold text-white">
            지금 가장 핫한 작품
          </span>
          <div className="relative h-[140px] w-[95px] overflow-hidden rounded-sm shadow-2xl md:h-[160px] md:w-[108px]">
            <Image src={posterImg} alt="" fill className="object-cover" sizes="108px" />
          </div>
          <div className="mt-3 w-full text-left">
            <h3 className="font-display text-lg font-bold text-white">듄: 파트2</h3>
            <p className="mt-1 flex items-center gap-2 text-xs text-neutral-300">
              <span className="text-amber-400">★ 4.3</span>
              <span>SF · 모험</span>
            </p>
          </div>
        </div>
      </Link>

      <Link
        href="/mova/title/oppenheimer"
        className="group relative block min-h-[220px] overflow-hidden rounded-lg border border-mova-border bg-mova-surface md:min-h-[260px]"
      >
        <Image
          src={trailerImg}
          alt=""
          fill
          className="object-cover opacity-80 transition-transform duration-500 group-hover:scale-105"
          sizes="(max-width: 768px) 100vw, 33vw"
        />
        <div className="absolute inset-0 bg-black/40" />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white/90 text-black shadow-lg">
            <Play className="h-5 w-5 fill-black pl-0.5" />
          </span>
        </div>
        <div className="absolute right-0 bottom-0 left-0 flex items-end justify-between gap-2 p-4">
          <div>
            <h3 className="font-display text-base font-bold text-white md:text-lg">오펜하이머</h3>
            <p className="mt-0.5 text-xs text-neutral-300">역사를 바꾼 3시간의 서사</p>
          </div>
          <span className="shrink-0 rounded-md bg-white px-3 py-1.5 text-xs font-semibold text-black">
            상세보기
          </span>
        </div>
      </Link>
    </div>
  )
}
