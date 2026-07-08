import Image from "next/image"
import { Clapperboard } from "lucide-react"
import { coercePosterUrl } from "@/lib/mova-poster"

const PLACEHOLDER =
  "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80"

type MovaRankingPosterProps = {
  src: string
  alt: string
  sizes: string
  className?: string
}

export function MovaRankingPoster({ src, alt, sizes, className }: MovaRankingPosterProps) {
  const posterSrc = coercePosterUrl(src) ?? PLACEHOLDER
  return (
    <Image
      src={posterSrc}
      alt={alt}
      fill
      className={className ?? "object-cover"}
      sizes={sizes}
    />
  )
}

export function MovaRankingPosterFallback({ className }: { className?: string }) {
  return (
    <div
      className={`flex h-full w-full items-center justify-center bg-neutral-800 ${className ?? ""}`}
      aria-hidden
    >
      <Clapperboard className="h-6 w-6 text-neutral-600" />
    </div>
  )
}
