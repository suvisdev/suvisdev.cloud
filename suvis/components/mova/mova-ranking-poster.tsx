import Image from "next/image"
import { coercePosterUrl } from "@/lib/mova-poster"

const PLACEHOLDER = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80"

type MovaRankingPosterProps = {
  src: string
  alt: string
  sizes: string
  className?: string
}

export function MovaRankingPoster({ src, alt, sizes, className }: MovaRankingPosterProps) {
  const posterSrc = coercePosterUrl(src) ?? PLACEHOLDER
  return (
    <Image src={posterSrc} alt={alt} fill className={className ?? "object-cover"} sizes={sizes} />
  )
}
