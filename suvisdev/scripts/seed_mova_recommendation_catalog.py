"""Mova 추천용 카탈로그 시드: tags.label, movies.genres, actors+characters.

Usage (suvisdev 폴더에서):
  python scripts/seed_mova_recommendation_catalog.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
APPS = ROOT / "apps"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(APPS))


async def main() -> None:
    from database import dispose_engine, reload_env
    from recommendation_catalog_seed_data import MOOD_TAG_BY_SLUG, MOVIE_SEEDS

    from mova.adapter.outbound.pg.actors_pg_repository import ActorsPgRepository
    from mova.adapter.outbound.pg.characters_pg_repository import CharactersPgRepository
    from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
    from mova.adapter.outbound.pg.tags_pg_repository import TagsPgRepository

    reload_env()
    movies_repo = MoviesPgRepository()
    actors_repo = ActorsPgRepository()
    characters_repo = CharactersPgRepository()
    tags_repo = TagsPgRepository()

    tag_count = 0
    cast_count = 0

    for spec in MOVIE_SEEDS:
        movie = await movies_repo.upsert(
            {
                "slug": spec["slug"],
                "title": spec["title"],
                "release_year": spec["release_year"],
                "rating": spec["rating"],
                "genres": list(spec["genres"]),
                "platform": spec.get("platform"),
                "poster": "",
            },
        )
        print(f"movie id={movie.id} slug={movie.slug} genres={movie.genres}")

        for director in spec.get("directors") or []:
            actor = await actors_repo.upsert(
                {"name": director, "role_type": "director", "profile_photo": ""},
            )
            link = await characters_repo.link(movie.id, actor.id)
            cast_count += 1
            await tags_repo.attach(
                {
                    "movie_id": movie.id,
                    "character_id": link.id,
                    "tag_kind": "cast",
                    "label": director,
                    "description": f"감독: {director}",
                },
            )
            tag_count += 1

        for name in spec.get("actors") or []:
            actor = await actors_repo.upsert(
                {"name": name, "role_type": "actor", "profile_photo": ""},
            )
            link = await characters_repo.link(movie.id, actor.id)
            cast_count += 1
            await tags_repo.attach(
                {
                    "movie_id": movie.id,
                    "character_id": link.id,
                    "tag_kind": "cast",
                    "label": name,
                    "description": f"출연: {name}",
                },
            )
            tag_count += 1

        for genre in spec.get("genres") or []:
            g = str(genre).strip()
            if not g:
                continue
            await tags_repo.attach(
                {
                    "movie_id": movie.id,
                    "tag_kind": "genre",
                    "label": g,
                    "description": f"장르: {g}",
                },
            )
            tag_count += 1

        for tag_slug in spec.get("tag_slugs") or []:
            tag_def = MOOD_TAG_BY_SLUG.get(tag_slug)
            if tag_def is None:
                print(f"  skip unknown tag slug: {tag_slug}")
                continue
            await tags_repo.attach(
                {
                    "movie_id": movie.id,
                    "tag_kind": "mood",
                    "slug": tag_def["slug"],
                    "label": tag_def["label"],
                    "description": tag_def["description"],
                },
            )
            tag_count += 1
            print(f"  tag {tag_def['label']!r}")

    await dispose_engine()
    print(
        f"done. movies={len(MOVIE_SEEDS)} tag_attach={tag_count} cast_links={cast_count}",
    )


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
