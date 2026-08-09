import type { Metadata } from "next"
import { notFound } from "next/navigation"
import { MovaTitleView } from "@/components/mova/title/mova-title-view"
import {
  fetchMovaRating,
  fetchMovaReviewsByMovie,
  fetchSimilarMovies,
  movaReviewToComment,
  type ApiMovieRow,
} from "@/lib/mova-api"
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
  let similarMovies: ApiMovieRow[] = []

  if (movie.movieDbId) {
    const [reviewRows, ratingSummary, similar] = await Promise.all([
      fetchMovaReviewsByMovie(movie.movieDbId).catch(() => null),
      fetchMovaRating(movie.movieDbId).catch(() => null),
      fetchSimilarMovies(movie.id).catch(() => []),
    ])
    if (reviewRows && reviewRows.length > 0) {
      comments = reviewRows.map(movaReviewToComment)
    }
    if (ratingSummary) {
      initialAverageRating = ratingSummary.average_rating
      initialReviewCount = ratingSummary.review_count
    }
    similarMovies = similar
  }

  return (
    <MovaTitleView
      movie={{ ...movie, comments }}
      initialAverageRating={initialAverageRating}
      initialReviewCount={initialReviewCount}
      similarMovies={similarMovies}
    />
  )
}
