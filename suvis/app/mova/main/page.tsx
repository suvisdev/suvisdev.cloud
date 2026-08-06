import { MovaAiChatBar } from "@/components/mova/mova-ai-chat-bar"
import { MovaGenreCatalog } from "@/components/mova/mova-genre-catalog"
import { MovaHeader } from "@/components/mova/mova-header"
import { MovaPromoBanner } from "@/components/mova/mova-promo-banner"
import { MovaRankingSection } from "@/components/mova/mova-ranking-section"
import { apiMovieToMovaMovie, fetchHotRankings, fetchMovaMoviesFromApi } from "@/lib/mova-api"
import { groupMovaMoviesByGenre } from "@/lib/mova-movies"

const HOME_GENRE_ROWS = 8

export default async function MovaMainPage() {
  const [rankings, movieRows] = await Promise.all([
    fetchHotRankings(10),
    fetchMovaMoviesFromApi(100),
  ])
  const genreGroups = groupMovaMoviesByGenre(movieRows.map(apiMovieToMovaMovie)).slice(
    0,
    HOME_GENRE_ROWS,
  )

  return (
    <>
      <MovaHeader />
      <main className="mx-auto min-w-0 max-w-[1400px] space-y-4 overflow-x-clip px-4 py-4 sm:space-y-6 sm:py-5 md:space-y-8 md:px-6 md:py-6">
        <MovaPromoBanner />
        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="min-w-0 w-full">
            <MovaAiChatBar />
          </div>
          <MovaRankingSection variant="sidebar" items={rankings} />
        </div>
        {genreGroups.length > 0 && <MovaGenreCatalog groups={genreGroups} />}
      </main>
    </>
  )
}
