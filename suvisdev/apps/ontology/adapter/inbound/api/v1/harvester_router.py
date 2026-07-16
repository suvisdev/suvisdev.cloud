"""어드민 크롤러/스크래퍼 화면 — POST /ontology/harvester/{scrape,crawl}, GET .../sites.

두 모드를 지원한다:
- 등록된 사이트 모드(site_id): harvester CLI와 같은 use case(ScrapeDatasetInteractor,
  CrawlScheduleInteractor)를 재사용. 자연어 명령을 keyword/limit으로 해석한다.
- 임의 URL 모드(url): CustomUrlScrapeInteractor. robots.txt 확인 후 그 페이지 1개만
  가져와 자연어 지시(command_text 전체) 그대로 LLM에 넘겨 원하는 내용만 추출한다.
  keyword/limit 해석은 여기선 의미가 없어서 건너뛴다.

동기 use case 호출은 asyncio.to_thread로 감싼다(CustomUrlScrapeInteractor는 내부에서
직접 감쌈 — LLM 호출이 섞여 있어 인터랙터 자체가 async라서).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from ontology.adapter.inbound.api.schemas.harvester_schema import (
    HarvesterCommandRequestSchema,
    HarvesterRunResponseSchema,
    HarvesterSiteSchema,
)
from ontology.adapter.outbound.config.api_keys import MissingApiKeyError
from ontology.adapter.outbound.scraper.registry import SITE_REGISTRY
from ontology.app.dtos.scrape_dto import ScrapeTarget
from ontology.app.ports.output.crawl_errors import CrawlFetchError
from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.dependencies.harvester_provider import (
    UnknownSiteError,
    build_crawl_schedule_use_case,
    build_custom_url_scrape_use_case,
    build_harvester_command_parser,
    build_scrape_dataset_use_case,
    build_site_scraper,
    custom_url_crawl_out_path,
    custom_url_scrape_out_path,
    default_scrape_out_path,
)

harvester_router = APIRouter(prefix="/harvester", tags=["ontology-harvester"])


@harvester_router.get("/sites", response_model=list[HarvesterSiteSchema])
async def sites() -> list[HarvesterSiteSchema]:
    return [
        HarvesterSiteSchema(site_id=site_id, fetcher_kind=cls.fetcher_kind)
        for site_id, cls in sorted(SITE_REGISTRY.items())
    ]


async def _run_custom_url(url: str, instruction: str, *, append: bool) -> HarvesterRunResponseSchema:
    out_path = custom_url_crawl_out_path() if append else custom_url_scrape_out_path(url)
    service = build_custom_url_scrape_use_case()
    try:
        meta = await service.run(url=url, instruction=instruction, out_path=out_path, append=append)
    except (CrawlFetchError, HubRagError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    return HarvesterRunResponseSchema(
        record_count=meta.record_count,
        path=meta.path,
        parsed_keyword=instruction[:80],
        parsed_limit=1,
    )


@harvester_router.post("/scrape", response_model=HarvesterRunResponseSchema)
async def scrape(req: HarvesterCommandRequestSchema) -> HarvesterRunResponseSchema:
    """스크래퍼 탭 — 온디맨드 1회 수집 (파일 덮어쓰기)."""
    if req.url:
        return await _run_custom_url(req.url, req.command_text, append=False)
    if not req.site_id:
        raise HTTPException(status_code=400, detail="site_id 또는 url 중 하나는 있어야 합니다.")

    parser = build_harvester_command_parser()
    command = await parser.parse(req.command_text)

    try:
        scraper = build_site_scraper(req.site_id, rate=1.0, dedup=True)
    except UnknownSiteError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    service = build_scrape_dataset_use_case(scraper)
    out_path = default_scrape_out_path(req.site_id, command.keyword)
    target = ScrapeTarget(site_id=req.site_id, keyword=command.keyword)
    try:
        meta = await asyncio.to_thread(service.run, target, limit=command.limit, out_path=out_path)
    except MissingApiKeyError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return HarvesterRunResponseSchema(
        record_count=meta.record_count,
        path=meta.path,
        parsed_keyword=command.keyword,
        parsed_limit=command.limit,
    )


@harvester_router.post("/crawl", response_model=HarvesterRunResponseSchema)
async def crawl(req: HarvesterCommandRequestSchema) -> HarvesterRunResponseSchema:
    """크롤러 탭 — 즉시 1회 수집 (날짜별 append)."""
    if req.url:
        return await _run_custom_url(req.url, req.command_text, append=True)
    if not req.site_id:
        raise HTTPException(status_code=400, detail="site_id 또는 url 중 하나는 있어야 합니다.")

    parser = build_harvester_command_parser()
    command = await parser.parse(req.command_text)

    service = build_crawl_schedule_use_case()
    try:
        meta = await asyncio.to_thread(
            service.run_once,
            site_id=req.site_id,
            keywords=(command.keyword,),
            limit=command.limit,
        )
    except UnknownSiteError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MissingApiKeyError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return HarvesterRunResponseSchema(
        record_count=meta.record_count,
        path=meta.path,
        parsed_keyword=command.keyword,
        parsed_limit=command.limit,
    )
