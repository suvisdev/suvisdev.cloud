import type { Metadata } from "next"
import { notFound } from "next/navigation"
import { MovaTitleView } from "@/components/mova/title/mova-title-view"
import { fetchMovaRating, fetchMovaReviewsByMovie, movaReviewToComment } from "@/lib/mova-api"
import { loadMovaTitle, movaTitleMetadata } from "@/lib/load-mova-title"

type PageProps = {
  params: Promise<{ slug: string }>
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  return movaTitleMetadata(slug)
}

export default async function MovaTitlePage({ params }: PageProps) {
  const { slug } = await params
  const movie = await loadMovaTitle(slug)
  if (!movie) notFound()

  let comments = movie.comments
  let initialAverageRating: number | null = null
  let initialReviewCount: number | null = null

  if (movie.movieDbId) {
    const [reviewRows, ratingSummary] = await Promise.all([
      fetchMovaReviewsByMovie(movie.movieDbId).catch(() => null),
      fetchMovaRating(movie.movieDbId).catch(() => null),
    ])
    if (reviewRows && reviewRows.length > 0) {
      comments = reviewRows.map(movaReviewToComment)
    }
    if (ratingSummary) {
      initialAverageRating = ratingSummary.average_rating
      initialReviewCount = ratingSummary.review_count
    }
  }

  return (
    <MovaTitleView
      movie={{ ...movie, comments }}
      initialAverageRating={initialAverageRating}
      initialReviewCount={initialReviewCount}
    />
  )
}
